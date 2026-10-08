#!/usr/bin/env python3
"""Audit validation-only pair training and checkpoint inference, without fitting."""
import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rnastable.pair_model import make_pair_model, pair_predictions, supervision
from rnastable.experimental_data import sequence_similarity
from rnastable.reference import digest
from rnastable.reference_audit import audit_reference, require
from rnastable.scoring import structure_agreement


def audit_pair(summary_path):
    import torch
    summary = json.loads(Path(summary_path).read_text()); run = Path(summary['run_dir'])
    require(summary['complete'] and summary['mode'] == 'development_validation_only' and summary['test_evaluated'] is False,
            'not a validation-only development run')
    require(digest((run/'manifest.json').read_bytes()) == summary['manifest_sha256'], 'pair manifest changed')
    manifest = json.loads((run/'manifest.json').read_text())
    require(manifest['mode'] == summary['mode'] and manifest['run_dir'] == str(run), 'pair manifest identity differs')
    training = json.loads((run/'training.json').read_text()); require(training == summary['training'], 'training summary differs')
    require(training['config'] == manifest['config'], 'pair training configuration differs')
    sources = list(manifest['sources'].items())
    require(len(sources) == 2, 'pair run must have only train and validation sources')
    data = []
    for name, (_, sha) in zip(('train.json', 'validation.json'), sources):
        require(digest((run/name).read_bytes()) == sha, 'development snapshot changed')
        data.append(json.loads((run/name).read_text())['records'])
    require(len(data[0]) == summary['train_records'] and len(data[1]) == summary['validation_records'], 'development counts differ')
    for first in data[0]:
        for second in data[1]:
            require(sequence_similarity(first['sequence'], second['sequence']) < .8
                and not (first.get('pdb_accession') and first['pdb_accession'] == second.get('pdb_accession')),
                'train/validation overlap')
    labels = [supervision(r) for r in data[0]]
    positive = sum(int(y.sum()) for _, y, _ in labels)
    negative = sum(len(y)-int(y.sum()) for _, y, _ in labels)
    require(positive == training['train_positive_pairs'] and negative == training['train_negative_pairs'], 'train pair counts differ')
    require(training['train_only_positive_weight'] == math.sqrt(negative/positive), 'train-only positive weight differs')
    require(sum(x[2] for x in labels) == training['unrepresentable_train_reference_pairs'], 'excluded train contacts differ')
    require(sum(supervision(r)[2] for r in data[1]) == training['unrepresentable_validation_reference_pairs'], 'excluded validation contacts differ')
    history = training['history']
    require([json.loads(line) for line in (run/'epochs.jsonl').read_text().splitlines()] == history, 'epoch ledger differs')
    require([r['epoch'] for r in history] == list(range(1, training['config']['epochs']+1)), 'epoch count differs')
    best = max(history, key=lambda r: (r['validation_mean_pair_f1'], -(r['mean_validation_loss'] or 0)))
    require(best['epoch'] == training['selected_epoch'], 'validation checkpoint selection differs')
    torch.set_num_threads(training['config']['cpu_threads'])
    predictions = []
    for name, method in [('initial', 'untrained_pair'), ('best', 'trained_pair')]:
        path = run/(name+'_pair_model.pt')
        require(digest(path.read_bytes()) == training[name+'_checkpoint_sha256'], 'pair checkpoint changed')
        model = make_pair_model(training['config'])
        model.load_state_dict(torch.load(path, map_location='cpu', weights_only=True))
        predictions.extend(pair_predictions(model, data[1], method))
    require(json.loads((run/'predictions.json').read_text())['records'] == predictions, 'pair checkpoint predictions differ')
    final = [p for p in predictions if p['method'] == 'trained_pair']
    score = sum(structure_agreement(p['structure'], r['structure'])['pair_f1'] for p, r in zip(final, data[1]))/len(data[1])
    require(score == training['selected_validation_pair_f1'] == best['validation_mean_pair_f1'], 'selected validation score differs')
    evaluation_path = run/'results/reference_evaluation_summary.json'; audit_reference(evaluation_path)
    evaluation = json.loads(evaluation_path.read_text())
    require(Path(evaluation['sources']['references']['path']).read_bytes() == (run/'validation.json').read_bytes(), 'evaluation reference split differs')
    require(Path(evaluation['sources']['predictions']['path']).read_bytes() == (run/'predictions.json').read_bytes(), 'evaluation predictions differ')
    require(evaluation['aggregates'] == summary['aggregates'], 'development aggregates differ')
    require(json.loads((run/'summary.json').read_text()) == summary, 'retained pair summary differs')
    print(f'Pair development audit passed: {len(data[0])} training / {len(data[1])} validation; selected epoch {training["selected_epoch"]}; no test input/evaluation.')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, default=ROOT/'results/pair_development_summary.json')
    args = parser.parse_args()
    try: audit_pair(args.summary)
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as exc: parser.exit(2, f'Pair audit rejected: {exc}\n')


if __name__ == '__main__': main()
