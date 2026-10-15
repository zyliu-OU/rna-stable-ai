#!/usr/bin/env python3
"""Audit imported experimental-derived data, split isolation, checkpoints and test evidence."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rnastable.experimental_data import load_pdb_splits
from rnastable.folding import parse_output
from rnastable.reference import digest
from rnastable.reference_audit import audit_reference, require
from rnastable.scoring import structure_agreement
from rnastable.structure_model import make_model, predict


def audit_pilot(summary_path):
    import torch
    summary_path = Path(summary_path).resolve()
    summary = json.loads(summary_path.read_text())
    require(summary['complete'] is True and summary['mode'] == 'processed_pdb_training_pilot', 'incomplete pilot')
    run = Path(summary['run_dir']).resolve()
    manifest_path = run/'manifest.json'
    require(digest(manifest_path.read_bytes()) == summary['manifest_sha256'], 'pilot manifest changed')
    manifest = json.loads(manifest_path.read_text())
    require(manifest['run_dir'] == str(run) and manifest['config'] == summary['config'], 'pilot config/identity differs')
    require(manifest['splits'] == summary['splits'], 'split plan differs')
    require(manifest['methods'] == ['ViennaRNA', 'LinearFold', 'untrained_cnn', 'trained_cnn', 'all_unpaired'], 'method plan differs')
    import_path = run/'import_manifest.json'
    require(digest(import_path.read_bytes()) == manifest['import_manifest_sha256'], 'import manifest changed')
    import_record = json.loads(import_path.read_text())
    for path, expected in import_record['source_sha256'].items():
        require(digest(Path(path).read_bytes()) == expected, 'upstream data changed')
    expected_splits, expected_import = load_pdb_splits(ROOT/'external/EternaFold', manifest['config'])
    require(expected_import == import_record, 'upstream import/filtering differs')
    splits = {}
    for split in ('train', 'validation', 'test'):
        record = manifest['splits'][split]
        path = Path(record['path']).resolve()
        require(path == run/(split+'_references.json'), 'split snapshot outside run')
        require(digest(path.read_bytes()) == record['sha256'], 'split snapshot changed')
        splits[split] = json.loads(path.read_text())['records']
        require(splits[split] == expected_splits[split] and len(splits[split]) == record['count'], 'imported records differ')
    training = summary['training']
    require(json.loads((run/'training_summary.json').read_text()) == training, 'training summary differs')
    require(training['complete'] and training['device'] == 'cpu' and training['config'] == manifest['config'], 'training config differs')
    require(training['train_records'] == len(splits['train']) and training['validation_records'] == len(splits['validation']), 'training denominators differ')
    counts = [sum(r['structure'].count(c) for r in splits['train']) for c in '.()']
    require(counts == training['class_counts_train_only'], 'training-only label counts differ')
    weights = torch.tensor(counts).float().clamp_min(1).rsqrt(); weights /= weights.mean()
    require(weights.tolist() == training['class_weights_train_only'], 'training-only class weights differ')
    history = training['history']
    require([r['epoch'] for r in history] == list(range(1, manifest['config']['epochs']+1)), 'epochs differ')
    require([json.loads(line) for line in (run/'training_events.jsonl').read_text().splitlines()] == history, 'epoch events differ')
    chosen = max(history, key=lambda r: (r['validation_mean_pair_f1'], -r['validation_mean_loss']))
    require(chosen['epoch'] == training['selected_epoch'] and chosen['validation_mean_pair_f1'] == training['selected_validation_pair_f1'], 'checkpoint selection differs')
    torch.set_num_threads(manifest['config']['cpu_threads'])
    models = {}
    for method, prefix, filename in [('untrained_cnn', 'initial', 'initial_model.pt'), ('trained_cnn', 'best', 'best_model.pt')]:
        path = Path(training[prefix+'_checkpoint']).resolve()
        require(path == run/filename and digest(path.read_bytes()) == training[prefix+'_sha256'], 'model checkpoint changed')
        model = make_model(manifest['config'])
        model.load_state_dict(torch.load(path, map_location='cpu', weights_only=True)); model.eval()
        models[method] = model
    require(any(not torch.equal(a, b) for a, b in zip(models['untrained_cnn'].parameters(), models['trained_cnn'].parameters())), 'trained weights did not change')
    val_predictions = predict(models['trained_cnn'], splits['validation'], 'validation')
    selected_f1 = sum(structure_agreement(p['structure'], r['structure'])['pair_f1']
                      for p, r in zip(val_predictions, splits['validation']))/len(splits['validation'])
    require(selected_f1 == training['selected_validation_pair_f1'], 'selected validation score differs')
    predictions_path = run/'test_predictions.json'
    require(digest(predictions_path.read_bytes()) == summary['prediction_sha256'], 'saved test predictions changed')
    prediction_data = json.loads(predictions_path.read_text())
    require(prediction_data['methods'] == manifest['methods'], 'test method plan differs')
    prediction_index = {(r['id'], r['method']): r for r in prediction_data['records']}
    for method, model in models.items():
        for row in predict(model, splits['test'], method):
            require(prediction_index[(row['id'], method)] == row, 'checkpoint inference differs from saved predictions')
    for record in splits['test']:
        row = prediction_index[(record['id'], 'all_unpaired')]
        require(row['status'] == 'ok' and row['structure'] == '.'*len(record['sequence']), 'all-unpaired baseline differs')
    fold_path = run/'fold_results.json'
    require(digest(fold_path.read_bytes()) == summary['fold_results_sha256'], 'fold ledger changed')
    folds = json.loads(fold_path.read_text())
    require(len(folds) == 2*len(splits['test']), 'fold denominators differ')
    refs = {r['id']: r for r in splits['test']}
    seen = set()
    for fold in folds:
        identity, method = fold['reference_id'], fold['tool']
        require(identity in refs and method in ('ViennaRNA', 'LinearFold') and (identity, method) not in seen, 'fold identity differs')
        seen.add((identity, method))
        row = prediction_index[(identity, method)]
        if 'raw_output' in fold:
            path = Path(fold['raw_output']).resolve()
            require(path == run/'raw'/f'{identity}_{method}.txt', 'raw output outside run')
            require(digest(path.read_bytes()) == fold['raw_sha256'], 'raw fold output changed')
        if fold['status'] == 'ok':
            raw = Path(fold['raw_output']).read_text()
            require(refs[identity]['sequence'] in raw.splitlines(), 'raw fold sequence differs from exact test input')
            parsed = parse_output(method, raw, len(refs[identity]['sequence']))
            require(parsed['structure'] == fold['structure'] == row['structure'] and row['status'] == 'ok', 'fold structure differs')
            require(parsed['mfe_kcal_mol'] == fold['mfe_kcal_mol'], 'fold energy differs')
        else:
            expected_status = fold['status'] if fold['status'] in ('timeout', 'unavailable') else 'error'
            require(row['status'] == expected_status, 'failed fold status differs')
    evaluation_path = Path(summary['evaluation_summary']).resolve()
    require(evaluation_path == run/'results/reference_evaluation_summary.json', 'evaluation outside pilot run')
    require(digest(evaluation_path.read_bytes()) == summary['evaluation_summary_sha256'], 'evaluation summary changed')
    audit_reference(evaluation_path)
    evaluation = json.loads(evaluation_path.read_text())
    require(Path(evaluation['sources']['references']['original_path']) == run/'test_references.json', 'evaluation used a different reference split')
    require(Path(evaluation['sources']['predictions']['original_path']) == predictions_path, 'evaluation used different predictions')
    require(Path(evaluation['sources']['references']['path']).read_bytes() == (run/'test_references.json').read_bytes(), 'evaluation reference snapshot differs')
    require(Path(evaluation['sources']['predictions']['path']).read_bytes() == predictions_path.read_bytes(), 'evaluation prediction snapshot differs')
    require(summary['aggregates'] == evaluation['aggregates'], 'test metrics differ')
    require(json.loads((run/'summary.json').read_text()) == summary, 'retained pilot summary differs')
    print(f'Experimental pilot audit passed: splits {import_record["retained_counts"]}; {len(history)} epochs; selected epoch {training["selected_epoch"]}; exact checkpoint predictions and {len(folds)} native folds verified.')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, default=ROOT/'results/experimental_pilot_summary.json')
    args = parser.parse_args()
    try:
        audit_pilot(args.summary)
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as exc:
        parser.exit(2, f'Experimental pilot audit failed: {exc}\n')


if __name__ == '__main__':
    main()
