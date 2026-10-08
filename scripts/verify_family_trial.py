#!/usr/bin/env python3
"""Replay frozen family selection, checkpoint predictions, exposure events and folds."""
import argparse
import json
import math
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rnastable.exposures import exposure_records, read_exposure
from rnastable.family_plan import audit_family_plan
from rnastable.folding import parse_output, tool_commands
from rnastable.pair_model import make_pair_model, pair_predictions, supervision
from rnastable.reference import digest
from rnastable.reference_audit import audit_reference, require
from rnastable.rfam_data import load_rfam_candidates, select_cohort, cohort_inputs
from rnastable.scoring import structure_agreement


def audit_trial(summary_path):
    import torch
    summary = json.loads(Path(summary_path).read_text()); run = Path(summary['run_dir'])
    require(summary['complete'] is True and summary['mode'] == 'family_disjoint_comparative_trial', 'trial identity differs')
    require(json.loads((run/'summary.json').read_text()) == summary, 'retained summary differs')
    require(digest((run/'manifest.json').read_bytes()) == summary['manifest_sha256'], 'manifest changed')
    manifest = json.loads((run/'manifest.json').read_text())
    require(manifest['run_dir'] == str(run), 'manifest run differs')
    for name, sha in summary['artifact_sha256'].items():
        require(digest((run/name).read_bytes()) == sha, 'trial artifact changed: '+name)
    require(digest((run/'family_plan/summary.json').read_bytes()) == manifest['family_plan_sha256'], 'family plan changed')
    plan = audit_family_plan(run/'family_plan')
    require(plan['counts'] == summary['counts'] and plan['families'] == summary['families'], 'split summary differs')
    imported = json.loads((run/'import.json').read_text())
    require(digest((run/'import.json').read_bytes()) == manifest['import_sha256'], 'import record changed')
    for path, sha in imported['source_sha256'].items(): require(digest(Path(path).read_bytes()) == sha, 'upstream source changed')
    config = manifest['config']
    candidates, replay = load_rfam_candidates(ROOT/'external/EternaFold', config)
    old = json.loads((run/'family_plan/effective_exposure.json').read_text())
    records, exclusions = select_cohort(candidates, config, old); replay['selection_exclusions'] = exclusions
    require(replay == imported, 'source import/selection replay differs')
    inputs = cohort_inputs(records, config)
    for name, expected in zip(('references.json', 'assignments.json', 'plan.json'), inputs):
        require(json.loads((run/'family_plan'/name).read_text()) == expected, 'selected cohort differs')
    events = summary['exposure_events']
    require([e['stage'] for e in events] == ['training_started', 'validation_started', 'test_started'], 'exposure stages differ')
    require([e['path'] for e in events] == sorted(e['path'] for e in events), 'exposure stage order differs')
    require(set(Path(e['path']).resolve() for e in events) == set(p.resolve() for p in (run/'exposures').glob('*.json')), 'exposure event inventory differs')
    for event, split in zip(events, ('train', 'validation', 'test')):
        path = Path(event['path'])
        require(path.resolve().parent == (run/'exposures').resolve(), 'event outside run')
        require(digest(path.read_bytes()) == event['sha256'], 'exposure event changed')
        data = read_exposure(path)
        require(data['stage'] == event['stage'] and data['records'] == exposure_records(plan['splits'][split], str(run)+' '+event['stage']), 'exposure records differ')
    training = json.loads((run/'model/training.json').read_text())
    require(training == summary['training'] and training['config'] == config['training'], 'training configuration differs')
    labels = [supervision(r) for r in plan['splits']['train']]
    positive = sum(int(y.sum()) for _, y, _ in labels); negative = sum(len(y)-int(y.sum()) for _, y, _ in labels)
    require(positive == training['train_positive_pairs'] and negative == training['train_negative_pairs'], 'pair counts differ')
    require(math.sqrt(negative/positive) == training['train_only_positive_weight'], 'training weight differs')
    for split in ('train', 'validation'):
        require(sum(supervision(r)[2] for r in plan['splits'][split]) == training['unrepresentable_'+split+'_reference_pairs'], 'excluded contacts differ')
    history = training['history']
    require([json.loads(line) for line in (run/'model/epochs.jsonl').read_text().splitlines()] == history, 'epoch ledger differs')
    require([r['epoch'] for r in history] == list(range(1, config['training']['epochs']+1)), 'epoch inventory differs')
    best = max(history, key=lambda r: (r['validation_mean_pair_f1'], -(r['mean_validation_loss'] or 0)))
    require(best['epoch'] == training['selected_epoch'], 'checkpoint selection differs')
    torch.set_num_threads(config['training']['cpu_threads'])
    predictions = []
    for name, method in [('best', 'trained_pair'), ('initial', 'untrained_pair')]:
        path = run/'model'/(name+'_pair_model.pt')
        require(digest(path.read_bytes()) == training[name+'_checkpoint_sha256'], 'checkpoint changed')
        model = make_pair_model(config['training']); model.load_state_dict(torch.load(path, map_location='cpu', weights_only=True))
        predictions.extend(pair_predictions(model, plan['splits']['test'], method))
        if name == 'best':
            val = pair_predictions(model, plan['splits']['validation'], 'validation')
            f1 = sum(structure_agreement(p['structure'], r['structure'])['pair_f1'] for p, r in zip(val, plan['splits']['validation']))/len(val)
            require(f1 == training['selected_validation_pair_f1'] == best['validation_mean_pair_f1'], 'validation checkpoint score differs')
    predictions += [{'id': r['id'], 'sequence': r['sequence'], 'method': 'all_unpaired', 'status': 'ok', 'structure': '.'*len(r['sequence'])} for r in plan['splits']['test']]
    folds = json.loads((run/'folds.json').read_text())
    require([(f['reference_id'], f['tool']) for f in folds] == [(r['id'], m) for r in plan['splits']['test'] for m in ('ViennaRNA', 'LinearFold')], 'fold inventory differs')
    commands = tool_commands(ROOT, config['folding'])
    for record, pair in zip(plan['splits']['test'], [folds[i:i+2] for i in range(0, len(folds), 2)]):
        for fold in pair:
            if fold['status'] != 'unavailable':
                require(fold.get('device') == 'CPU' and fold.get('command') == commands[fold['tool']][0], 'native fold command differs')
            if 'raw_output' in fold:
                raw = Path(fold['raw_output'])
                require(raw.resolve().parent == (run/'raw').resolve() and digest(raw.read_bytes()) == fold['raw_sha256'], 'raw fold changed')
                if fold['status'] == 'ok':
                    require(raw.read_text().splitlines()[0].strip() == record['sequence'], 'raw fold sequence differs')
            if fold['status'] == 'ok':
                parsed = parse_output(fold['tool'], Path(fold['raw_output']).read_text(), len(record['sequence']))
                require(all(fold[key] == value for key, value in parsed.items()), 'raw native result differs')
            row = {'id': record['id'], 'sequence': record['sequence'], 'method': fold['tool'], 'status': fold['status'] if fold['status'] in ('ok', 'timeout', 'unavailable') else 'error'}
            if row['status'] == 'ok': row['structure'] = fold['structure']
            else: row['error'] = fold.get('error') or fold['status']
            predictions.append(row)
    require(json.loads((run/'test_predictions.json').read_text()) == {'schema_version': 1, 'methods': manifest['methods'], 'records': predictions}, 'checkpoint/native predictions differ')
    require(json.loads((run/'test_references.json').read_text())['records'] == plan['splits']['test'], 'test reference split differs')
    evaluation_path = run/'results/reference_evaluation_summary.json'; audit_reference(evaluation_path)
    evaluation = json.loads(evaluation_path.read_text())
    for key, filename in [('references', 'test_references.json'), ('predictions', 'test_predictions.json')]:
        require(Path(evaluation['sources'][key]['path']).read_bytes() == (run/filename).read_bytes(), 'evaluation inputs differ')
    require(evaluation['aggregates'] == summary['aggregates'], 'evaluation aggregates differ')
    print(f'Family trial audit passed: {summary["counts"]}; exact cohort, exposure events, checkpoints and {len(folds)} native folds verified.')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, default=ROOT/'results/family_trial_summary.json')
    args = parser.parse_args()
    try: audit_trial(args.summary)
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as exc: parser.exit(2, f'Family trial audit rejected: {exc}\n')

if __name__ == '__main__': main()
