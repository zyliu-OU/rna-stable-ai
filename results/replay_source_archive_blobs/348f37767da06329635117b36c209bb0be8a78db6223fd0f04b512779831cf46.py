"""Choose among saved CPU search restarts without refolding or training."""
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

from .artifacts import publish, sha256, timestamp
from .optimization import check_constraints, hamming
from .selection import select_finalist
from .sequences import generate_sequence, read_fasta, write_fasta


def choose_candidate(original, candidates):
    """Return the lowest validated energy, resolving equal energies by job ID.

    Each item contains a job ID, sequence, search status, input reference and
    candidate validation. Inconsistent successful input references fail closed.
    """
    if not candidates:
        raise ValueError('At least one saved search is required')
    seen = set()
    decisions = []
    references = []
    for candidate in candidates:
        job = candidate['job_id']
        if job in seen:
            raise ValueError('Duplicate portfolio job')
        seen.add(job)
        decision = select_finalist(original, candidate['sequence'],
                                   candidate['search_status'], candidate['reference'],
                                   candidate['validation'])
        reference = candidate['reference'] or {}
        value = reference.get('mfe_kcal_mol')
        if (reference.get('status') == 'ok' and not isinstance(value, bool)
                and isinstance(value, (int, float)) and math.isfinite(value)):
            references.append(value)
        decisions.append({'job_id': job, **decision})
    if references and max(references)-min(references) > 1e-9:
        raise ValueError('Input references disagree; candidates cannot be ranked')
    eligible = [d for d in decisions if d['source'] == 'finalist']
    reference_energy = min(references) if references else None
    if eligible:
        winner = min(eligible, key=lambda d: (d['selected_vienna_energy_kcal_mol'], d['job_id']))
        sequence = next(c['sequence'] for c in candidates if c['job_id'] == winner['job_id'])
        job_id = winner['job_id']
        energy = winner['selected_vienna_energy_kcal_mol']
    else:
        sequence, job_id, energy = original, None, reference_energy
    return {'selected_sequence': sequence, 'selected_job_id': job_id,
            'selection_source': 'finalist' if eligible else 'input',
            'selection_reason': 'best_confirmed_improvement' if eligible else 'no_eligible_improvement',
            'input_vienna_energy_kcal_mol': reference_energy,
            'selected_vienna_energy_kcal_mol': energy,
            'selected_vienna_delta_kcal_mol': energy-reference_energy if energy is not None else None,
            'search_count': len(candidates), 'eligible_candidates': len(eligible),
            'candidate_decisions': sorted(decisions, key=lambda d: d['job_id'])}


def build_portfolio(root, source_path):
    root = Path(root).resolve()
    source_path = Path(source_path).resolve()
    source_bytes = source_path.read_bytes()
    source = json.loads(source_bytes)
    if not source.get('complete') or not source.get('rows'):
        raise ValueError('Portfolio requires a nonempty, complete sweep')
    project = Path(__file__).resolve().parents[2]
    audit = subprocess.run([sys.executable, str(project/'scripts/verify_sweep.py'),
                            '--summary', str(source_path)], capture_output=True, text=True)
    if audit.returncode:
        raise ValueError(f'Source sweep audit failed (exit {audit.returncode}):\n{audit.stdout}{audit.stderr}')
    if source_path.read_bytes() != source_bytes:
        raise ValueError('Source summary changed during its audit')
    groups = defaultdict(list)
    for row in source['rows']:
        groups[(row['kind'], row['length'], row['sequence_seed'], row['input_sha256'])].append(row)
    prepared = []
    for (kind, length, seed, input_hash), group in sorted(groups.items()):
        original = generate_sequence(length, kind, seed)
        if sha256(original) != input_hash:
            raise ValueError('Input hash does not match the saved synthetic input')
        candidates, evidence_files = [], []
        for row in group:
            if not row.get('summary_path'):
                candidates.append({'job_id': row['job_id'], 'sequence': original,
                                   'search_status': 'failed', 'reference': None, 'validation': None})
                continue
            evidence_path = Path(row['summary_path'])
            evidence_bytes = evidence_path.read_bytes()
            evidence = json.loads(evidence_bytes)
            config = evidence['config']
            expected = {**source['config']['optimization'], 'seed': row['search_seed'],
                        'beam_size': row['beam_size']}
            if config != expected:
                raise ValueError('Candidates use incompatible search constraints or parameters')
            saved_input = read_fasta(evidence_path.parent/'input.fasta')
            if len(saved_input) != 1 or saved_input[0][1] != original:
                raise ValueError('Saved input FASTA disagrees with the source input')
            records = read_fasta(row['finalist_fasta'])
            if len(records) != 1:
                raise ValueError('Each candidate FASTA must contain exactly one sequence')
            sequence = records[0][1]
            check_constraints(sequence, original, config)
            candidates.append({'job_id': row['job_id'], 'sequence': sequence,
                               'search_status': evidence['search']['status'],
                               'reference': evidence['reference'], 'validation': evidence['validation']})
            evidence_files.append({'path': str(evidence_path),
                                   'sha256': hashlib.sha256(evidence_bytes).hexdigest()})
        selected = choose_candidate(original, candidates)
        check_constraints(selected['selected_sequence'], original, source['config']['optimization'])
        winner = next((r for r in group if r['job_id'] == selected['selected_job_id']), None)
        prepared.append({'input_id': f'{kind}_{length}_seed{seed}', 'kind': kind, 'length': length,
                         'sequence_seed': seed, 'input_sha256': input_hash, **selected,
                         'selected_sha256': sha256(selected['selected_sequence']),
                         'selected_mutations_from_input': hamming(selected['selected_sequence'], original),
                         'selected_beam_size': winner['beam_size'] if winner else None,
                         'selected_search_seed': winner['search_seed'] if winner else None,
                         'proposals_attempted': sum(r.get('steps_attempted', 0) for r in group),
                         'candidate_worsenings': sum(
                             d['candidate_vienna_delta_kcal_mol'] is not None
                             and d['candidate_vienna_delta_kcal_mol'] > 1e-9
                             for d in selected['candidate_decisions']),
                         'source_evidence': evidence_files})
    # Validate every group before creating output; source artifacts are never edited.
    stamp = timestamp()
    run = root/'results/portfolio_runs'/stamp
    run.mkdir(parents=True, exist_ok=False)
    rows = []
    for item in prepared:
        sequence = item.pop('selected_sequence')
        item['selected_fasta'] = str(write_fasta(run/(item['input_id']+'_selected.fasta'),
                                               item['input_id']+'_portfolio_selected', sequence))
        rows.append(item)
    limitations = [
        'Selection reuses saved CPU ViennaRNA validation; no new folds or training.',
        'Best-of-several search selection uses the full recorded search budget.',
        'Selected energy is descriptive on these inputs, not a held-out performance estimate.',
        'Computed minimum energy does not establish biological stability.',
        'Unknown reference energy remains null; input fallback does not invent a zero measurement.']
    result = {'utc': stamp, 'run_dir': str(run), 'mode': 'saved_cpu_restart_portfolio',
              'policy': 'lowest_confirmed_vienna_energy_then_job_id_v1',
              'source_summary': str(source_path),
              'source_summary_sha256': hashlib.sha256(source_bytes).hexdigest(),
              'source_audit': audit.stdout, 'source_versions': source['provenance']['versions'],
              'portfolio_code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'input_count': len(rows), 'search_count': len(source['rows']),
              'proposals_attempted': sum(r['proposals_attempted'] for r in rows),
              'selected_finalists': sum(r['selection_source'] == 'finalist' for r in rows),
              'returned_inputs': sum(r['selection_source'] == 'input' for r in rows),
              'rows': rows, 'limitations': limitations}
    (run/'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    (run/'source_audit.txt').write_text(audit.stdout)
    fields = [k for k in rows[0] if k not in ('candidate_decisions', 'source_evidence')]
    lines = ['# Portfolio selection from saved CPU searches', '', f'Source: `{source_path}`', '',
             f'{len(rows)} inputs; {result["search_count"]} searches; '
             f'{result["proposals_attempted"]} attempted proposals. No new folds or training.', '',
             '| Input | Searches | Proposals | Eligible | Selected beam | Selected seed | Energy change (kcal/mol) |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for row in rows:
        delta = row['selected_vienna_delta_kcal_mol']
        lines.append('| '+' | '.join(str(v) if v is not None else 'unknown' for v in (
            row['input_id'], row['search_count'], row['proposals_attempted'], row['eligible_candidates'],
            row['selected_beam_size'], row['selected_search_seed'], round(delta, 4) if delta is not None else None))+' |')
    lines += ['', *limitations, '']
    publish(root, 'portfolio', result, rows, fields, '\n'.join(lines))
    print(json.dumps({k: result[k] for k in ('run_dir', 'input_count', 'search_count',
                                           'proposals_attempted', 'selected_finalists', 'returned_inputs')}, indent=2))
    return result
