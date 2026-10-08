"""Compare saved LinearFold-V structures with CPU ViennaRNA references."""
import json
from pathlib import Path
import sys
from .artifacts import publish, sha256, timestamp
from .folding import fold_sequence, parse_output, run_bounded
from .scoring import structure_agreement
from .sequences import read_fasta

FIELDS = ['sequence_id', 'kind', 'length', 'status', 'baseline_origin', 'error',
          'vienna_mfe_kcal_mol', 'linearfold_energy_kcal_mol', 'reported_energy_gap_kcal_mol',
          'gap_kcal_mol_per_nt', 'linearfold_vienna_eval_kcal_mol', 'reevaluated_gap_kcal_mol',
          'reference_pairs', 'predicted_pairs', 'shared_pairs', 'pair_precision', 'pair_recall',
          'pair_f1', 'pair_jaccard', 'base_pair_distance']


def evaluate_structure(sequence, structure, config):
    request = json.dumps({'sequence': sequence, 'structure': structure, 'temperature_c': config['temperature_c']})
    command = [sys.executable, '-m', 'rnastable.energy_worker']
    result = run_bounded(command, request, config['timeout_seconds'], config['memory_limit_gib'])
    output = result.pop('stdout', '')
    result['command'] = command
    if result['status'] == 'ok':
        try:
            result.update(json.loads(output))
        except (ValueError, TypeError) as exc:
            result.update(status='parse_error', error=str(exc))
    return result


def saved_fold(row, sequence):
    if row is None:
        return {'status': 'unavailable', 'error': 'No saved folding result'}
    result = dict(row)
    if result['status'] == 'ok':
        output = Path(result['raw_output']).read_text()
        # Bind raw structures to this exact sequence, not just to its length.
        if sequence not in output.splitlines():
            raise ValueError('Raw output sequence differs from input FASTA')
        result.update(parse_output(row['tool'], output, len(sequence)))
    return result


def compare_saved(root, benchmark_path, retry_timeout=None):
    root = Path(root)
    source = json.loads(Path(benchmark_path).read_text())
    config = dict(source['config'])
    if retry_timeout is not None:
        if not 0 < retry_timeout < float('inf'):
            raise ValueError('retry-timeout must be finite and positive')
        config['timeout_seconds'] = retry_timeout
    stamp = timestamp()
    run_dir = root/'results/quality_runs'/stamp
    run_dir.mkdir(parents=True)
    index = {(r['sequence_id'], r['tool']): r for r in source['folding']}
    rows, evidence = [], []
    for item in source['synthetic_manifest']:
        row = {k: item[k] for k in ('kind', 'length')}
        row.update(sequence_id=item['id'], status='unavailable', baseline_origin='saved')
        detail = {'sequence_id': item['id']}
        try:
            records = read_fasta(item['path'])
            if len(records) != 1:
                raise ValueError('Expected one FASTA record per benchmark input')
            sequence = records[0][1]
            if sha256(sequence) != item['sha256'] or len(sequence) != item['length']:
                raise ValueError('FASTA changed since original benchmark')
            ref = saved_fold(index.get((item['id'], 'ViennaRNA')), sequence)
            pred = saved_fold(index.get((item['id'], 'LinearFold')), sequence)
            if ref['status'] != 'ok' and retry_timeout is not None:
                print(f'CPU reference retry: {item["id"]}; timeout={retry_timeout}s', flush=True)
                ref = fold_sequence(root, sequence, config, 'ViennaRNA', run_dir/f'{item["id"]}_ViennaRNA.txt')
                row['baseline_origin'] = 'retry'
            detail.update(reference=ref, prediction=pred)
            if ref['status'] != 'ok' or pred['status'] != 'ok':
                row.update(status='reference_unavailable', error=f'ViennaRNA={ref["status"]}, LinearFold={pred["status"]}')
            else:
                row.update(status='ok', **structure_agreement(pred['structure'], ref['structure']))
                gap = pred['mfe_kcal_mol']-ref['mfe_kcal_mol']
                row.update(vienna_mfe_kcal_mol=ref['mfe_kcal_mol'], linearfold_energy_kcal_mol=pred['mfe_kcal_mol'],
                           reported_energy_gap_kcal_mol=gap, gap_kcal_mol_per_nt=gap/len(sequence))
                evaluated = evaluate_structure(sequence, pred['structure'], config)
                detail['vienna_evaluation'] = evaluated
                if evaluated['status'] == 'ok':
                    row.update(linearfold_vienna_eval_kcal_mol=evaluated['energy_kcal_mol'],
                               reevaluated_gap_kcal_mol=evaluated['energy_kcal_mol']-ref['mfe_kcal_mol'])
                else:
                    row.update(status='evaluation_failed', error=evaluated.get('error', evaluated['status']))
        except (ValueError, OSError, KeyError) as exc:
            row.update(status='error', error=str(exc))
        rows.append(row); evidence.append(detail)
    from .cli import versions
    summary = {'utc': stamp, 'source_benchmark': str(Path(benchmark_path).resolve()), 'source_utc': source['utc'],
               'config': config, 'versions': versions(), 'rows': rows, 'evidence': evidence,
               'interpretation': 'Agreement with a computational reference, not experimental structure accuracy. Energy models can differ; reevaluation uses current ViennaRNA parameters with dangles=2.'}
    (run_dir/'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    lines = ['# Folding-quality comparison', '', summary['interpretation'], '',
             '| Sequence | Reference | Status | LF reported gap kcal/mol | LF reevaluated gap kcal/mol | Pair F1 | Pair distance |',
             '|---|---|---|---:|---:|---:|---:|']
    for row in rows:
        lines.append('| '+' | '.join(str(row.get(k, '')) for k in ['sequence_id','baseline_origin','status','reported_energy_gap_kcal_mol','reevaluated_gap_kcal_mol','pair_f1','base_pair_distance'])+' |')
    lines += ['', 'All folds and fixed-structure evaluations use CPU. Gaps are LinearFold minus ViennaRNA; lower gaps mean closer energies. Matching energies need not mean matching structures. No biological validation or training was performed.', '',
              'Sources: [ViennaRNA structure evaluation](https://viennarna.readthedocs.io/en/latest/eval/eval_structures.html), [LinearFold](https://github.com/LinearFold/LinearFold).', '']
    publish(root, 'folding_quality', summary, rows, FIELDS, '\n'.join(lines))
    print(json.dumps({'quality_status': {s: sum(r['status']==s for r in rows) for s in sorted({r['status'] for r in rows})}, 'run_dir': str(run_dir)}, indent=2))
    return summary
