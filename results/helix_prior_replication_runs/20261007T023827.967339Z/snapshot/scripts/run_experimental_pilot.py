#!/usr/bin/env python3
"""Freeze a processed-PDB pilot, train on CPU, then evaluate the untouched test split."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rnastable.artifacts import publish, timestamp
from rnastable.cli import versions
from rnastable.experimental_data import load_pdb_splits, load_pilot_config, write_splits
from rnastable.folding import fold_sequence
from rnastable.reference import digest, run_reference_evaluation
from rnastable.structure_model import predict, train_model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT/'configs/experimental_pilot.json')
    parser.add_argument('--output-root', type=Path, default=ROOT)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        config = load_pilot_config(args.config)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    splits, import_record = load_pdb_splits(ROOT/'external/EternaFold', config)
    print(json.dumps({'retained_counts': import_record['retained_counts'],
                      'excluded_records': len(import_record['rejected'])}, indent=2), flush=True)
    if args.dry_run:
        return
    run = args.output_root.resolve()/'results/experimental_pilot_runs'/timestamp()
    run.mkdir(parents=True, exist_ok=False)
    split_records = write_splits(run, splits)
    (run/'import_manifest.json').write_text(json.dumps(import_record, indent=2)+'\n')
    paths = [ROOT/'src/rnastable'/n for n in ('experimental_data.py', 'structure_model.py', 'reference.py', 'scoring.py', 'folding.py')]
    paths += [Path(__file__), ROOT/'external/LinearFold/bin/linearfold_v']
    manifest = {'utc': run.name, 'run_dir': str(run), 'config': config, 'splits': split_records,
                'import_manifest_sha256': digest((run/'import_manifest.json').read_bytes()),
                'provenance': {'versions': versions(), 'source_sha256': {str(p): digest(p.read_bytes()) for p in paths}},
                'methods': ['ViennaRNA', 'LinearFold', 'untrained_cnn', 'trained_cnn', 'all_unpaired'],
                'selection_policy': 'validation_only; test evaluated once after best checkpoint is frozen',
                'dataset_provenance': 'https://github.com/WaymentSteeleLab/EternaFold/tree/87b9aac55cee14fd562049d08f7b92d3131f10ce',
                'reference_citation': 'https://doi.org/10.1186/1471-2105-9-340'}
    manifest_path = run/'manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
    print(f'Frozen pilot plan: {run}', flush=True)
    initial, trained, training = train_model(splits['train'], splits['validation'], config, run)
    predictions = predict(initial, splits['test'], 'untrained_cnn') + predict(trained, splits['test'], 'trained_cnn')
    predictions += [{'id': r['id'], 'method': 'all_unpaired', 'sequence': r['sequence'],
                     'status': 'ok', 'structure': '.'*len(r['sequence'])} for r in splits['test']]
    folds = []
    for record in splits['test']:
        for method in ('ViennaRNA', 'LinearFold'):
            print(f'Experimental-reference CPU fold: {method} {record["id"]}', flush=True)
            result = fold_sequence(ROOT, record['sequence'], config, method, run/'raw'/f'{record["id"]}_{method}.txt')
            if 'raw_output' in result:
                result['raw_sha256'] = digest(Path(result['raw_output']).read_bytes())
            folds.append({'reference_id': record['id'], **result})
            row = {'id': record['id'], 'sequence': record['sequence'], 'method': method,
                   'status': result['status'] if result['status'] in ('ok', 'timeout', 'unavailable') else 'error'}
            if row['status'] == 'ok': row['structure'] = result['structure']
            else: row['error'] = result.get('error') or result['status']
            predictions.append(row)
    prediction_path = run/'test_predictions.json'
    prediction_path.write_text(json.dumps({'schema_version': 1, 'methods': manifest['methods'], 'records': predictions}, indent=2)+'\n')
    fold_path = run/'fold_results.json'; fold_path.write_text(json.dumps(folds, indent=2)+'\n')
    evaluation = run_reference_evaluation(run, Path(split_records['test']['path']), prediction_path)
    summary = {'complete': True, 'mode': 'processed_pdb_training_pilot', 'run_dir': str(run),
               'manifest_sha256': digest(manifest_path.read_bytes()), 'config': config,
               'splits': split_records, 'training': training, 'aggregates': evaluation['aggregates'],
               'evaluation_summary': str(run/'results/reference_evaluation_summary.json'),
               'evaluation_summary_sha256': digest((run/'results/reference_evaluation_summary.json').read_bytes()),
               'fold_results_sha256': digest(fold_path.read_bytes()),
               'prediction_sha256': digest(prediction_path.read_bytes()),
               'limitations': [import_record['interpretation'], *training['limitations'],
                              'Experimental-derived annotation comparison is not a biological stability measurement.']}
    (run/'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    lines = ['# Processed PDB evaluation and training pilot', '', f'Run: `{run}`', '',
             f'Splits: {import_record["retained_counts"]}; selected epoch {training["selected_epoch"]}.', '',
             '| Method | Planned test records | Measured | Mean pair F1 |', '|---|---:|---:|---:|']
    for g in evaluation['aggregates']:
        lines.append(f'| {g["method"]} | {g["planned_inputs"]} | {g["measured_inputs"]} | {g["mean_pair_f1"]} |')
    lines += ['', *summary['limitations'], '']
    publish(args.output_root, 'experimental_pilot', summary, evaluation['aggregates'],
            list(evaluation['aggregates'][0]), '\n'.join(lines))
    print(json.dumps({'run_dir': str(run), 'selected_epoch': training['selected_epoch'], 'aggregates': evaluation['aggregates']}, indent=2))


if __name__ == '__main__':
    main()
