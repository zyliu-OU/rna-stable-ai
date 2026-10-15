#!/usr/bin/env python3
"""Fit pair scores on development data only; no test input or test evaluation."""
import argparse
import copy
import json
import math
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rnastable.artifacts import timestamp, write_artifact
from rnastable.cli import versions
from rnastable.pair_model import make_pair_model, pair_predictions, supervision
from rnastable.reference import digest, run_reference_evaluation, validate_inputs
from rnastable.scoring import structure_agreement
from rnastable.structure_model import tokens

PILOT = ROOT/'results/experimental_pilot_runs/20261006T010347.964097Z'


def train_pair(train, validation, config, run):
    import torch
    torch.set_num_threads(config['cpu_threads']); torch.manual_seed(config['seed'])
    torch.use_deterministic_algorithms(True)
    rng = random.Random(config['seed'])
    model = make_pair_model(config)
    initial = copy.deepcopy(model)
    torch.save(initial.state_dict(), run/'initial_pair_model.pt')
    labels = [supervision(r) for r in train]
    positive = sum(int(y.sum()) for _, y, _ in labels)
    negative = sum(len(y)-int(y.sum()) for _, y, _ in labels)
    if not positive or not negative:
        raise ValueError('Development training requires positive and negative legal pairs')
    pos_weight = math.sqrt(negative/positive)
    loss_fn = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(pos_weight))
    optimizer = torch.optim.Adam(model.parameters(), lr=config['learning_rate'])
    history, best_key, best_state, chosen = [], None, None, None
    for epoch in range(1, config['epochs']+1):
        order = list(range(len(train))); rng.shuffle(order)
        model.train(); losses = []
        for index in order:
            indices, target, _ = labels[index]
            if not len(target):
                continue
            optimizer.zero_grad(set_to_none=True)
            logits = model(tokens(train[index]['sequence']))[0]
            loss = loss_fn(logits[indices[:, 0], indices[:, 1]], target)
            if not torch.isfinite(loss):
                raise ValueError('Nonfinite pair training loss')
            loss.backward(); optimizer.step(); losses.append(loss.item())
        predictions = pair_predictions(model, validation, 'pair_validation')
        f1 = sum(structure_agreement(p['structure'], r['structure'])['pair_f1'] for p, r in zip(predictions, validation))/len(validation)
        model.eval(); val_losses = []
        with torch.inference_mode():
            for record in validation:
                indices, target, _ = supervision(record)
                if len(target):
                    logits = model(tokens(record['sequence']))[0]
                    val_losses.append(loss_fn(logits[indices[:, 0], indices[:, 1]], target).item())
        row = {'epoch': epoch, 'mean_train_loss': sum(losses)/len(losses),
               'validation_mean_pair_f1': f1, 'mean_validation_loss': sum(val_losses)/len(val_losses) if val_losses else None}
        history.append(row)
        key = (f1, -(row['mean_validation_loss'] or 0))
        if best_key is None or key > best_key:
            best_key, chosen = key, epoch
            best_state = copy.deepcopy(model.state_dict())
            torch.save(best_state, run/'best_pair_model.pt')
        with (run/'epochs.jsonl').open('a') as stream: stream.write(json.dumps(row)+'\n')
        print(f'Pair development epoch {epoch}/{config["epochs"]}: loss={row["mean_train_loss"]:.4f}; validation F1={f1:.4f}', flush=True)
    model.load_state_dict(best_state); model.eval()
    return initial, model, {'config': config, 'history': history, 'selected_epoch': chosen,
        'selected_validation_pair_f1': best_key[0], 'train_positive_pairs': positive, 'train_negative_pairs': negative,
        'train_only_positive_weight': pos_weight, 'unrepresentable_train_reference_pairs': sum(x[2] for x in labels),
        'unrepresentable_validation_reference_pairs': sum(supervision(r)[2] for r in validation),
        'records_without_train_loss': [r['id'] for r, (_, target, _) in zip(train, labels) if not len(target)],
        'parameters': sum(p.numel() for p in model.parameters()),
        'initial_checkpoint_sha256': digest((run/'initial_pair_model.pt').read_bytes()),
        'best_checkpoint_sha256': digest((run/'best_pair_model.pt').read_bytes()),
        'selection_policy': 'highest_validation_pair_f1_then_lowest_validation_loss_then_earliest_epoch_v1'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--train', type=Path, default=PILOT/'train_references.json')
    parser.add_argument('--validation', type=Path, default=PILOT/'validation_references.json')
    parser.add_argument('--config', type=Path, default=ROOT/'configs/pair_development.json')
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    for key, upper in [('epochs', 20), ('embedding_dim', 64), ('channels', 64), ('pair_dim', 64), ('cpu_threads', 2)]:
        if type(config.get(key)) is not int or not 1 <= config[key] <= upper:
            parser.error(f'{key} must be an integer in 1..{upper}')
    if (config.get('mode') != 'development_validation_only' or config.get('decoder_threshold') != 0
            or config.get('max_length') != 256 or type(config.get('seed')) is not int
            or not 0 <= config['seed'] < 2**32 or type(config.get('learning_rate')) not in (int, float)
            or not 0 < config['learning_rate'] < 1):
        parser.error('Invalid bounded development configuration')
    inputs = [p.read_bytes() for p in (args.train, args.validation)]
    datasets = [json.loads(c) for c in inputs]
    for dataset in datasets:
        validate_inputs(dataset, {'schema_version': 1, 'methods': ['development'], 'records': []})
        if any(len(r['sequence']) > 256 for r in dataset['records']): parser.error('Maximum length is 256')
    from rnastable.experimental_data import sequence_similarity
    for first in datasets[0]['records']:
        for second in datasets[1]['records']:
            if (first['sequence'] == second['sequence'] or sequence_similarity(first['sequence'], second['sequence']) >= .8
                    or first.get('pdb_accession') and first.get('pdb_accession') == second.get('pdb_accession')):
                parser.error('Train/validation sequence or accession overlap')
    run = ROOT/'results/pair_development_runs'/timestamp(); run.mkdir(parents=True, exist_ok=False)
    for name, content in zip(('train.json', 'validation.json'), inputs): (run/name).write_bytes(content)
    paths = [Path(__file__), *[ROOT/'src/rnastable'/name for name in
        ('pair_model.py', 'scoring.py', 'structure_model.py', 'experimental_data.py', 'reference.py')]]
    manifest = {'mode': 'development_validation_only', 'config': config, 'run_dir': str(run),
        'sources': {str(p.resolve()): digest(c) for p, c in zip((args.train, args.validation), inputs)},
        'versions': versions(), 'code_sha256': {str(p): digest(p.read_bytes()) for p in paths},
        'policy': 'Fixed zero logit threshold; validation-only checkpoint selection; no test input.'}
    (run/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    initial, trained, training = train_pair(datasets[0]['records'], datasets[1]['records'], config, run)
    (run/'training.json').write_text(json.dumps(training, indent=2, allow_nan=False)+'\n')
    predictions = pair_predictions(initial, datasets[1]['records'], 'untrained_pair') + pair_predictions(trained, datasets[1]['records'], 'trained_pair')
    (run/'predictions.json').write_text(json.dumps({'schema_version': 1, 'methods': ['untrained_pair', 'trained_pair'], 'records': predictions}, indent=2)+'\n')
    evaluation = run_reference_evaluation(run, run/'validation.json', run/'predictions.json')
    summary = {'complete': True, 'mode': 'development_validation_only', 'run_dir': str(run),
        'manifest_sha256': digest((run/'manifest.json').read_bytes()), 'training': training,
        'train_records': len(datasets[0]['records']), 'validation_records': len(datasets[1]['records']),
        'test_evaluated': False, 'aggregates': evaluation['aggregates'],
        'limitations': ['Previously used development data; validation scores are not independent test accuracy.',
            'O(n^2) pair scores and O(n^3) decoding are bounded to 256 nt; not a long-RNA system.',
            'Local convolutional features score global pairs; decoder optimizes learned logits, not physical energy.',
            'Only canonical nested pairs and at least three enclosed nucleotides are representable; excluded training contacts are counted.']}
    (run/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    write_artifact(ROOT/'results/pair_development_summary.json', json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__': main()
