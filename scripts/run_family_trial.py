#!/usr/bin/env python3
"""Freeze a comparative family trial, train, record test exposure, then evaluate once."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rnastable.artifacts import publish, timestamp
from rnastable.cli import versions
from rnastable.exposures import collect_known_exposures, record_exposure
from rnastable.family_plan import plan_families, save_family_plan
from rnastable.folding import fold_sequence
from rnastable.pair_model import pair_predictions
from rnastable.reference import digest, run_reference_evaluation
from rnastable.rfam_data import cohort_inputs, load_rfam_candidates, select_cohort
from train_pair_development import train_pair


def prepare(config):
    if (type(config.get('max_records_per_family')) is not int or not 1 <= config['max_records_per_family'] <= 24
            or type(config.get('min_length')) is not int or type(config.get('max_length')) is not int
            or not 1 <= config['min_length'] <= config['max_length'] <= 256):
        raise ValueError('Family trial requires bounded lengths/caps')
    training = config['training']
    for key, upper in [('epochs', 20), ('embedding_dim', 64), ('channels', 64), ('pair_dim', 64), ('cpu_threads', 2)]:
        if type(training.get(key)) is not int or not 1 <= training[key] <= upper:
            raise ValueError('Invalid training setting: '+key)
    if (training.get('mode') != 'family_disjoint_comparative_trial' or training.get('max_length') != 256
            or training.get('decoder_threshold') != 0 or type(training.get('seed')) is not int
            or not 0 <= training['seed'] < 2**32 or type(training.get('learning_rate')) not in (int, float)
            or not 0 < training['learning_rate'] < 1):
        raise ValueError('Invalid fixed family training configuration')
    folding = config['folding']
    if (folding.get('temperature_c') != 37 or type(folding.get('beam_size')) is not int or not 1 <= folding['beam_size'] <= 1000
            or type(folding.get('timeout_seconds')) not in (int, float) or not 0 < folding['timeout_seconds'] <= 120
            or type(folding.get('memory_limit_gib')) not in (int, float) or not 0 < folding['memory_limit_gib'] <= 8):
        raise ValueError('Invalid bounded folding configuration')
    exposed = collect_known_exposures(ROOT)
    candidates, imported = load_rfam_candidates(ROOT/'external/EternaFold', config)
    records, exclusions = select_cohort(candidates, config, exposed)
    imported['selection_exclusions'] = exclusions
    references, assignments, families = cohort_inputs(records, config)
    planned = plan_families(references, assignments, families, exposed)
    return references, assignments, families, exposed, planned, imported


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT/'configs/family_trial.json')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text())
        references, assignments, families, exposed, planned, imported = prepare(config)
    except (ValueError, OSError, KeyError, TypeError) as exc: parser.exit(2, f'Family trial rejected: {exc}\n')
    print(json.dumps({'families': families, 'counts': planned['counts'], 'prior_exposures': len(exposed)}, indent=2), flush=True)
    if args.dry_run: return
    run = ROOT/'results/family_trial_runs'/timestamp(); run.mkdir(parents=True, exist_ok=False)
    inputs = run/'inputs'; inputs.mkdir()
    for name, data in [('references.json', references), ('assignments.json', assignments), ('plan.json', families), ('exposure.json', exposed)]:
        (inputs/name).write_text(json.dumps(data, indent=2)+'\n')
    frozen = save_family_plan(run/'family_plan', *[inputs/name for name in ('references.json', 'assignments.json', 'plan.json', 'exposure.json')])
    (run/'import.json').write_text(json.dumps(imported, indent=2)+'\n')
    paths = [Path(__file__), ROOT/'scripts/train_pair_development.py', *[ROOT/'src/rnastable'/n for n in
        ('rfam_data.py', 'exposures.py', 'family_plan.py', 'pair_model.py', 'reference.py', 'scoring.py', 'experimental_data.py', 'structure_model.py', 'folding.py')],
        ROOT/'external/LinearFold/bin/linearfold_v']
    manifest = {'schema_version': 1, 'run_dir': str(run), 'utc': run.name, 'config': config,
        'family_plan_sha256': digest((run/'family_plan/summary.json').read_bytes()),
        'import_sha256': digest((run/'import.json').read_bytes()),
        'provenance': {'versions': versions(), 'code_sha256': {str(p): digest(p.read_bytes()) for p in paths}},
        'methods': ['trained_pair', 'untrained_pair', 'all_unpaired', 'ViennaRNA', 'LinearFold'],
        'policy': 'Family IDs disjoint within trial; checkpoint selection uses validation only; test exposure recorded before inference.',
        'reference_interpretation': 'Processed comparative annotations; not a new experimental measurement. Legacy tool-training overlap and clan independence are unestablished.'}
    (run/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(f'Frozen family trial: {run}', flush=True)
    splits = frozen['splits']
    exposures = [record_exposure(run, 'training_started', splits['train']), record_exposure(run, 'validation_started', splits['validation'])]
    model_dir = run/'model'; model_dir.mkdir()
    initial, trained, training = train_pair(splits['train'], splits['validation'], config['training'], model_dir)
    (model_dir/'training.json').write_text(json.dumps(training, indent=2, allow_nan=False)+'\n')
    # Durable marker precedes all test inference/folding; interruption cannot make this test fresh again.
    exposures.append(record_exposure(run, 'test_started', splits['test']))
    predictions = pair_predictions(trained, splits['test'], 'trained_pair') + pair_predictions(initial, splits['test'], 'untrained_pair')
    predictions += [{'id': r['id'], 'sequence': r['sequence'], 'method': 'all_unpaired', 'status': 'ok', 'structure': '.'*len(r['sequence'])} for r in splits['test']]
    folds = []
    for record in splits['test']:
        for method in ('ViennaRNA', 'LinearFold'):
            print(f'Family test CPU fold: {method} {record["id"]}', flush=True)
            fold = fold_sequence(ROOT, record['sequence'], config['folding'], method, run/'raw'/f'{record["id"]}_{method}.txt')
            if 'raw_output' in fold: fold['raw_sha256'] = digest(Path(fold['raw_output']).read_bytes())
            folds.append({'reference_id': record['id'], **fold})
            row = {'id': record['id'], 'sequence': record['sequence'], 'method': method,
                'status': fold['status'] if fold['status'] in ('ok', 'timeout', 'unavailable') else 'error'}
            if row['status'] == 'ok': row['structure'] = fold['structure']
            else: row['error'] = fold.get('error') or fold['status']
            predictions.append(row)
    for name, data in [('folds.json', folds), ('test_predictions.json', {'schema_version': 1, 'methods': manifest['methods'], 'records': predictions}),
                       ('test_references.json', {'schema_version': 1, 'dataset_id': 'rfam_disjoint_trial_test', 'records': splits['test']})]:
        (run/name).write_text(json.dumps(data, indent=2)+'\n')
    evaluation = run_reference_evaluation(run, run/'test_references.json', run/'test_predictions.json')
    summary = {'complete': True, 'mode': 'family_disjoint_comparative_trial', 'run_dir': str(run),
        'manifest_sha256': digest((run/'manifest.json').read_bytes()), 'training': training,
        'counts': frozen['counts'], 'families': frozen['families'], 'aggregates': evaluation['aggregates'], 'exposure_events': exposures,
        'artifact_sha256': {name: digest((run/name).read_bytes()) for name in ('model/training.json', 'test_references.json', 'test_predictions.json', 'folds.json', 'results/reference_evaluation_summary.json')},
        'limitations': [manifest['reference_interpretation'], 'Only one family per split; no population-wide family generalization claim.',
            'Prior PDB family assignments are unresolved; prior sequence exposure is filtered, but complete cross-study family independence is unestablished.',
            'Quadratic scores and cubic decoding remain limited to 256 nt. No long-RNA accuracy or biological stability measurement.']}
    (run/'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    lines = ['# Family-disjoint comparative trial', '', f'Run: `{run}`', '', f'Families: {families}', f'Counts: {frozen["counts"]}', '',
        '| Method | Planned | Measured | Mean pair F1 |', '|---|---:|---:|---:|']
    for group in evaluation['aggregates']: lines.append(f'| {group["method"]} | {group["planned_inputs"]} | {group["measured_inputs"]} | {group["mean_pair_f1"]} |')
    lines += ['', *summary['limitations'], '']
    publish(ROOT, 'family_trial', summary, evaluation['aggregates'], list(evaluation['aggregates'][0]), '\n'.join(lines))
    print(json.dumps({'run_dir': str(run), 'counts': frozen['counts'], 'selected_epoch': training['selected_epoch'], 'aggregates': evaluation['aggregates']}, indent=2))


if __name__ == '__main__': main()
