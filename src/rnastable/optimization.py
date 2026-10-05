"""Deterministic constrained hill climbing on a CPU folding surrogate; no training."""
from collections import Counter
import json
from pathlib import Path
import random
from .artifacts import publish, sha256, timestamp
from .folding import fold_sequence
from .scoring import gc_fraction, mfe_per_nt
from .sequences import read_fasta, validate_sequence, write_fasta
from .selection import select_finalist

HISTORY_FIELDS = ['step', 'status', 'accepted', 'proposal_sha256', 'changed_positions',
                  'mutations_from_input', 'gc_fraction', 'proposed_energy_kcal_mol',
                  'best_energy_kcal_mol', 'best_energy_per_nt', 'wall_seconds', 'peak_rss_mib', 'error']


def load_optimization_config(path):
    return validate_optimization_config(json.loads(Path(path).read_text()))


def validate_optimization_config(config):
    for key in ('seed', 'steps', 'max_mutations', 'beam_size'):
        if type(config[key]) is not int or config[key] < (0 if key == 'seed' else 1):
            raise ValueError(f'{key} must be an integer in the supported range')
    for key in ('timeout_seconds', 'finalist_timeout_seconds', 'memory_limit_gib', 'min_improvement_kcal_mol'):
        if isinstance(config[key], bool) or not isinstance(config[key], (int, float)) or not 0 < config[key] < float('inf'):
            raise ValueError(f'{key} must be finite and positive')
    if config['temperature_c'] != 37:
        raise ValueError('LinearFold-V requires temperature_c=37 for this comparison')
    if type(config['preserve_protein']) is not bool:
        raise ValueError('preserve_protein must be boolean')
    positions = config['protected_positions']
    if not isinstance(positions, list) or any(type(i) is not int or i < 1 for i in positions):
        raise ValueError('protected_positions must be one-based positive integers')
    if len(positions) != len(set(positions)):
        raise ValueError('protected_positions must be unique')
    return config


def translation(sequence):
    """Standard genetic code, full sequence in frame 0; stop positions preserved."""
    validate_sequence(sequence)
    if len(sequence) % 3:
        raise ValueError('Protein preservation requires full codons in frame 0 (length divisible by 3)')
    from Bio.Data import CodonTable
    table = CodonTable.unambiguous_rna_by_id[1]
    return ''.join('*' if sequence[i:i+3] in table.stop_codons else table.forward_table[sequence[i:i+3]]
                   for i in range(0, len(sequence), 3))


def hamming(a, b):
    if len(a) != len(b):
        raise ValueError('Length mismatch')
    return sum(x != y for x, y in zip(a, b))


def check_constraints(sequence, original, config):
    validate_sequence(sequence, len(original))
    if (sequence.count('G')+sequence.count('C')) != (original.count('G')+original.count('C')):
        raise ValueError('GC count changed')
    if hamming(sequence, original) > config['max_mutations']:
        raise ValueError('Mutation budget exceeded')
    for position in config['protected_positions']:
        if position > len(original):
            raise ValueError('Protected position exceeds sequence length')
        if sequence[position-1] != original[position-1]:
            raise ValueError('Protected position changed')
    if config['preserve_protein']:
        if translation(sequence) != translation(original):
            raise ValueError('Encoded protein changed')
    elif Counter(sequence) != Counter(original):
        raise ValueError('Nucleotide composition changed')
    return True


def propose_mutation(current, original, config, rng):
    """Noncoding mode swaps different nucleotides, preserving all base counts.

    Coding mode substitutes one synonymous codon with the same GC count. CDS
    annotation/start selection is the caller's responsibility; frame 0/table 1 only.
    """
    protected = {p-1 for p in config['protected_positions']}
    current_distance = hamming(current, original)
    if config['preserve_protein']:
        from Bio.Data import CodonTable
        table = CodonTable.unambiguous_rna_by_id[1]
        moves = []
        for i in range(0, len(current), 3):
            codon = current[i:i+3]
            if codon in table.stop_codons:
                continue
            for alt in sorted(table.forward_table):
                if alt == codon or table.forward_table[alt] != table.forward_table[codon]:
                    continue
                if sum(c in 'GC' for c in alt) != sum(c in 'GC' for c in codon):
                    continue
                if any(i+j in protected and alt[j] != codon[j] for j in range(3)):
                    continue
                old_changes = sum(codon[j] != original[i+j] for j in range(3))
                new_changes = sum(alt[j] != original[i+j] for j in range(3))
                if current_distance-old_changes+new_changes <= config['max_mutations']:
                    moves.append((i, alt))
        if not moves:
            return None
        i, alt = rng.choice(moves)
        return current[:i]+alt+current[i+3:]
    eligible = [i for i in range(len(current)) if i not in protected]
    if len(eligible) < 2:
        return None
    for _ in range(256):
        i, j = rng.sample(eligible, 2)
        if current[i] == current[j]:
            continue
        old_changes = (current[i] != original[i])+(current[j] != original[j])
        new_changes = (current[j] != original[i])+(current[i] != original[j])
        if current_distance-old_changes+new_changes <= config['max_mutations']:
            chars = list(current); chars[i], chars[j] = chars[j], chars[i]
            return ''.join(chars)
    return None


def optimize_sequence(original, config, evaluator):
    """Pure search core; successful folds cached, strict improvements accepted."""
    validate_sequence(original)
    check_constraints(original, original, config)
    rng = random.Random(config['seed'])
    baseline = evaluator(original, 0)
    if baseline['status'] != 'ok':
        return {'status': 'baseline_failed', 'baseline': baseline, 'best': baseline,
                'sequence': original, 'history': [], 'accepted_steps': 0}
    mfe_per_nt(baseline['mfe_kcal_mol'], original)
    best, current = baseline, original
    seen = {sha256(original)}
    history = []
    for step in range(1, config['steps']+1):
        proposal = propose_mutation(current, original, config, rng)
        if proposal is None:
            history.append({'step': step, 'status': 'no_legal_proposal', 'accepted': False,
                            'error': 'No proposal found within 256 draws, or all positions/codons are fixed'})
            break
        check_constraints(proposal, original, config)
        row = {'step': step, 'proposal_sha256': sha256(proposal), 'accepted': False,
               'changed_positions': json.dumps([i+1 for i,(a,b) in enumerate(zip(current,proposal)) if a!=b]),
               'mutations_from_input': hamming(proposal, original), 'gc_fraction': gc_fraction(proposal)}
        if row['proposal_sha256'] in seen:
            row.update(status='duplicate', error='Previously evaluated candidate skipped')
        else:
            result = evaluator(proposal, step)
            row.update(status=result['status'], wall_seconds=result.get('wall_seconds', ''),
                       peak_rss_mib=result.get('peak_rss_mib', ''), error=result.get('error', ''))
            if result['status'] == 'ok':
                seen.add(row['proposal_sha256'])
                energy = result['mfe_kcal_mol']
                mfe_per_nt(energy, proposal)  # reject nonfinite energies
                row['proposed_energy_kcal_mol'] = energy
                if energy <= best['mfe_kcal_mol']-config['min_improvement_kcal_mol']+1e-9:
                    current, best = proposal, result
                    row['accepted'] = True
        row.update(best_energy_kcal_mol=best['mfe_kcal_mol'], best_energy_per_nt=mfe_per_nt(best['mfe_kcal_mol'], current))
        history.append(row)
    return {'status': 'completed', 'baseline': baseline, 'best': best, 'sequence': current,
            'history': history, 'accepted_steps': sum(row['accepted'] for row in history)}


def run_optimization(root, fasta, config):
    root = Path(root)
    records = read_fasta(fasta)
    if len(records) != 1:
        raise ValueError('Optimization requires exactly one FASTA record')
    name, original = records[0]
    if not 1000 <= len(original) <= 10000:
        raise ValueError('V1 optimization supports 1000–10000 nt')
    check_constraints(original, original, config)
    stamp = timestamp()
    run_dir = root/'results/optimization_runs'/stamp
    run_dir.mkdir(parents=True)
    write_fasta(run_dir/'input.fasta', name, original)
    def evaluate(sequence, step):
        print(f'CPU LinearFold search: step {step}/{config["steps"]}', flush=True)
        return fold_sequence(root, sequence, config, 'LinearFold', run_dir/f'step_{step:04d}.txt')
    result = optimize_sequence(original, config, evaluate)
    sequence = result.pop('sequence')
    check_constraints(sequence, original, config)
    write_fasta(run_dir/'finalist.fasta', name+'_finalist', sequence)
    validation = {}
    if result['status'] == 'completed':
        validation_config = {**config, 'timeout_seconds': config['finalist_timeout_seconds']}
        for label, seq in [('input', original), ('finalist', sequence)]:
            print(f'CPU ViennaRNA validation: {label}, {len(seq)} nt', flush=True)
            if label == 'finalist' and seq == original:
                validation[label] = dict(validation['input'], reused_input_result=True)
            else:
                validation[label] = fold_sequence(root, seq, validation_config, 'ViennaRNA', run_dir/f'{label}_ViennaRNA.txt')
    selection = select_finalist(original, sequence, result['status'],
                               validation.get('input'), validation.get('finalist'))
    selected = sequence if selection['source'] == 'finalist' else original
    check_constraints(selected, original, config)
    selected_path = write_fasta(run_dir/'selected.fasta', name+'_selected', selected)
    verified = selection['vienna_improvement_confirmed']
    vienna_delta = selection['candidate_vienna_delta_kcal_mol']
    from .cli import versions
    summary = {'utc': stamp, 'input_path': str(Path(fasta).resolve()), 'input_id': name,
               'config': config, 'versions': versions(), 'length': len(original), 'run_dir': str(run_dir),
               'input_sha256': sha256(original), 'finalist_sha256': sha256(sequence),
               'finalist_fasta': str(run_dir/'finalist.fasta'), 'constraints_passed': True,
               'selection': selection, 'selected_fasta': str(selected_path),
               'selected_sha256': sha256(selected), 'selected_mutations_from_input': hamming(selected, original),
               'gc_fraction': gc_fraction(sequence), 'mutations_from_input': hamming(sequence, original),
               'final_mutations': [{'position':i+1,'from':a,'to':b} for i,(a,b) in enumerate(zip(original,sequence)) if a!=b],
               'search': result, 'validation': validation, 'vienna_energy_delta_kcal_mol': vienna_delta,
               'vienna_improvement_confirmed': verified,
               'objective': 'Minimize LinearFold-V reported approximate energy per nucleotide at fixed sequence length; no biological stability claim.'}
    if result['status'] == 'completed':
        summary['linearfold_energy_delta_kcal_mol'] = result['best']['mfe_kcal_mol']-result['baseline']['mfe_kcal_mol']
    (run_dir/'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    lines = ['# Constrained CPU mutation search', '', summary['objective'], '',
             f'Input: `{name}` ({len(original)} nt); seed {config["seed"]}; attempted steps {len(result["history"])}; accepted {result["accepted_steps"]}.', '',
             f'Search status: {result["status"]}. Mutation count: {summary["mutations_from_input"]}/{config["max_mutations"]}. GC fraction: {summary["gc_fraction"]:.4f}. Constraints passed: True.', '',
             'Noncoding mode preserves every nucleotide count by swaps. Protein-preserving mode supports full codons in frame 0 using standard genetic code 1 and preserves GC count. Protected positions use one-based coordinates.', '',
             f'LinearFold energy change: {summary.get("linearfold_energy_delta_kcal_mol")} kcal/mol.',
             f'ViennaRNA energy change: {vienna_delta} kcal/mol. Improvement independently confirmed by ViennaRNA: {verified}.', '',
             f'Selected output: `{selected_path}`; source: {selection["source"]}; reason: {selection["reason"]}; changed positions: {hamming(selected, original)}.', '',
             f'Proposed finalist retained for evidence: `{run_dir/"finalist.fasta"}`', '',
             'Use selected.fasta as the output. An unconfirmed, unchanged or worsened finalist returns the original input. Failed search/validation also returns the input; unknown reference energy stays unknown. Candidate energy deltas and mutation counts above describe the retained search finalist.', '',
             'Negative changes mean lower computed folding energy. ViennaRNA input/finalist folds run on CPU with a separate timeout. A failed validation remains unknown, not successful. Search trajectories and failed folds are retained. No training or experimental biological validation was performed.', '',
             'Sources: [LinearFold](https://github.com/LinearFold/LinearFold), [ViennaRNA MFE](https://viennarna.readthedocs.io/en/latest/mfe/global.html), [Biopython codon tables](https://biopython.org/docs/latest/api/Bio.Data.html).', '']
    publish(root, 'optimization_history', summary, result['history'], HISTORY_FIELDS, '\n'.join(lines))
    print(json.dumps({k: summary[k] for k in ('run_dir','selected_fasta','selected_mutations_from_input',
                     'selection','mutations_from_input','vienna_energy_delta_kcal_mol','vienna_improvement_confirmed')}, indent=2))
    return summary
