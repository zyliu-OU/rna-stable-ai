"""Small CPU three-state Conv1d training pilot with a fixed nested-pair decoder."""
import copy
import json
import random
from pathlib import Path
import time

from .reference import digest
from .scoring import structure_agreement


def make_model(config):
    import torch
    class Model(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.embedding = torch.nn.Embedding(4, config['embedding_dim'])
            self.layers = torch.nn.Sequential(
                torch.nn.Conv1d(config['embedding_dim'], config['channels'], 7, padding=3),
                torch.nn.GELU(), torch.nn.Conv1d(config['channels'], config['channels'], 7, padding=3),
                torch.nn.GELU(), torch.nn.Conv1d(config['channels'], 3, 1))
        def forward(self, tokens):
            return self.layers(self.embedding(tokens).transpose(1, 2)).transpose(1, 2)
    return Model()


def tokens(sequence):
    import torch
    return torch.tensor([['ACGU'.index(c) for c in sequence]], dtype=torch.long)


def decode_states(sequence, states):
    """Greedy stack decoder: unmatched sites are unpaired, no crossing/canonical violations."""
    if len(sequence) != len(states) or any(type(s) is not int or s not in (0, 1, 2) for s in states):
        raise ValueError('Expected one 0/1/2 state per nucleotide')
    stack, structure = [], ['.']*len(sequence)
    for i, state in enumerate(states):
        if state == 1:
            stack.append(i)
        elif state == 2:
            for offset in range(len(stack)-1, -1, -1):
                j = stack[offset]
                if i-j > 3 and sequence[j]+sequence[i] in ('AU', 'UA', 'GC', 'CG', 'GU', 'UG'):
                    structure[j], structure[i] = '(', ')'
                    del stack[offset:]
                    break
    return ''.join(structure)


def predict(model, records, method):
    import torch
    model.eval()
    predictions = []
    with torch.inference_mode():
        for record in records:
            states = model(tokens(record['sequence']))[0].argmax(dim=-1).tolist()
            predictions.append({'id': record['id'], 'sequence': record['sequence'], 'method': method,
                                'status': 'ok', 'structure': decode_states(record['sequence'], states)})
    return predictions


def train_model(train, validation, config, run):
    """Test records are deliberately absent from the training API."""
    import torch
    if not train or not validation:
        raise ValueError('Training and validation records must be nonempty')
    torch.set_num_threads(config['cpu_threads'])
    torch.manual_seed(config['seed'])
    torch.use_deterministic_algorithms(True)
    rng = random.Random(config['seed'])
    run = Path(run)
    model = make_model(config)
    initial = copy.deepcopy(model).eval()
    initial_path = run/'initial_model.pt'
    torch.save(initial.state_dict(), initial_path)
    labels = [torch.tensor([['.()'.index(c) for c in r['structure']]], dtype=torch.long) for r in train]
    counts = torch.bincount(torch.cat([y.flatten() for y in labels]), minlength=3).float()
    weights = counts.clamp_min(1).rsqrt()
    weights /= weights.mean()
    criterion = torch.nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.Adam(model.parameters(), lr=config['learning_rate'])
    history, best_key, best_epoch, best_state = [], None, None, None
    start = time.monotonic()
    for epoch in range(1, config['epochs']+1):
        model.train()
        order = list(range(len(train))); rng.shuffle(order)
        loss_sum = 0.
        for index in order:
            optimizer.zero_grad(set_to_none=True)
            logits = model(tokens(train[index]['sequence']))
            loss = criterion(logits.reshape(-1, 3), labels[index].flatten())
            if not torch.isfinite(loss):
                raise ValueError('Nonfinite training loss')
            loss.backward(); optimizer.step(); loss_sum += loss.item()
        predictions = predict(model, validation, 'validation')
        f1 = sum(structure_agreement(p['structure'], r['structure'])['pair_f1']
                 for p, r in zip(predictions, validation))/len(validation)
        with torch.inference_mode():
            val_loss = sum(criterion(model(tokens(r['sequence'])).reshape(-1, 3),
                torch.tensor(['.()'.index(c) for c in r['structure']])).item()
                for r in validation)/len(validation)
        row = {'epoch': epoch, 'mean_train_loss': loss_sum/len(train), 'validation_mean_loss': val_loss,
               'validation_mean_pair_f1': f1}
        history.append(row)
        key = (f1, -val_loss)
        if best_key is None or key > best_key:
            best_key, best_epoch = key, epoch
            best_state = copy.deepcopy(model.state_dict())
            torch.save(best_state, run/'best_model.pt')
        with (run/'training_events.jsonl').open('a') as stream:
            stream.write(json.dumps(row)+'\n')
        print(f'Training epoch {epoch}/{config["epochs"]}: loss={row["mean_train_loss"]:.4f}; validation pair F1={f1:.4f}', flush=True)
    model.load_state_dict(best_state); model.eval()
    summary = {'complete': True, 'device': 'cpu', 'seed': config['seed'], 'config': config,
               'train_records': len(train), 'validation_records': len(validation),
               'class_counts_train_only': counts.int().tolist(), 'class_weights_train_only': weights.tolist(),
               'selection_policy': 'highest_validation_pair_f1_then_lowest_validation_loss_then_earliest_epoch_v1',
               'selected_epoch': best_epoch, 'selected_validation_pair_f1': best_key[0],
               'epochs_completed': len(history), 'history': history, 'wall_seconds': time.monotonic()-start,
               'initial_checkpoint': str(initial_path), 'initial_sha256': digest(initial_path.read_bytes()),
               'best_checkpoint': str(run/'best_model.pt'), 'best_sha256': digest((run/'best_model.pt').read_bytes()),
               'parameters': sum(p.numel() for p in model.parameters()),
               'limitations': ['Local three-state labels and a greedy decoder are a simple baseline, not a global pair model.',
                   'Decoder permits AU/GC/GU pairs and at least three enclosed nucleotides; processed references may contain other contacts.',
                   'Short processed PDB records do not establish long-RNA accuracy or biological stability.',
                   'One seed and one fixed hyperparameter configuration; validation-selecting checkpoints can overfit a small validation set.']}
    (run/'training_summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    return initial, model, summary
