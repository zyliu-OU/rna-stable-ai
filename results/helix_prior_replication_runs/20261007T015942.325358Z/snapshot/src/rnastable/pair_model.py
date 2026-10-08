"""Bounded all-pair logits and optimal noncrossing decoding; no energy model."""
import math

from .scoring import base_pairs
from .sequences import validate_sequence

MAX_LENGTH = 256
CANONICAL = {'AU', 'UA', 'GC', 'CG', 'GU', 'UG'}


def legal_pairs(sequence):
    validate_sequence(sequence)
    if len(sequence) > MAX_LENGTH:
        raise ValueError('Pair pilot supports at most 256 nt')
    return [(i, j) for i in range(len(sequence)) for j in range(i+4, len(sequence))
            if sequence[i]+sequence[j] in CANONICAL]


def decode_pairs(sequence, scores):
    """Maximize summed positive logits over valid nested pairs; zero score leaves sites unpaired."""
    import numpy as np
    allowed = set(legal_pairs(sequence))
    scores = np.asarray(scores, dtype=float)
    n = len(sequence)
    if scores.shape != (n, n) or not np.isfinite(scores).all():
        raise ValueError('Expected a finite square score matrix bound to sequence length')
    if not np.allclose(scores, scores.T, rtol=0, atol=1e-6):
        raise ValueError('Pair scores must be symmetric')
    table = [[0.]*n for _ in range(n)]
    choice = [[-1]*n for _ in range(n)]
    for span in range(1, n):
        for i in range(n-span):
            j = i+span
            best = table[i][j-1]
            for k in range(i, j-3):
                if (k, j) not in allowed or scores[k, j] <= 0:
                    continue
                value = float(scores[k, j]) + (table[i][k-1] if k > i else 0.) + table[k+1][j-1]
                if value > best:
                    best, choice[i][j] = value, k
            table[i][j] = best
    structure = ['.']*n
    stack = [(0, n-1)]
    while stack:
        i, j = stack.pop()
        if i >= j:
            continue
        k = choice[i][j]
        if k == -1:
            stack.append((i, j-1))
        else:
            structure[k], structure[j] = '(', ')'
            stack.extend([(i, k-1), (k+1, j-1)])
    return ''.join(structure)


def make_pair_model(config):
    import torch
    class PairModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.embedding = torch.nn.Embedding(4, config['embedding_dim'])
            self.encoder = torch.nn.Sequential(
                torch.nn.Conv1d(config['embedding_dim'], config['channels'], 7, padding=3),
                torch.nn.GELU(), torch.nn.Conv1d(config['channels'], config['channels'], 7, padding=3), torch.nn.GELU())
            self.projection = torch.nn.Linear(config['channels'], config['pair_dim'])
            self.endpoint = torch.nn.Linear(config['channels'], 1)
            self.distance = torch.nn.Embedding(MAX_LENGTH, 1)
        def forward(self, tokens):
            if tokens.ndim != 2 or not 1 <= tokens.shape[1] <= MAX_LENGTH:
                raise ValueError('Pair model requires batch x length tokens, length 1..256')
            h = self.encoder(self.embedding(tokens).transpose(1, 2)).transpose(1, 2)
            projected = self.projection(h)
            logits = projected @ projected.transpose(1, 2)/math.sqrt(config['pair_dim'])
            endpoints = self.endpoint(h)
            positions = torch.arange(tokens.shape[1], device=tokens.device)
            distance = (positions[:, None]-positions[None, :]).abs()
            logits = logits + endpoints + endpoints.transpose(1, 2) + self.distance(distance).squeeze(-1)
            return (logits + logits.transpose(1, 2))/2
    return PairModel()


def supervision(record):
    """Supervise legal upper-triangle pairs once; record excluded reference contacts."""
    import torch
    sequence = record['sequence']
    pairs = base_pairs(record['structure'])
    if len(record['structure']) != len(sequence):
        raise ValueError('Reference structure length differs')
    eligible = legal_pairs(sequence)
    indices = torch.tensor(eligible, dtype=torch.long).reshape(-1, 2)
    labels = torch.tensor([float(pair in pairs) for pair in eligible])
    return indices, labels, len(pairs-set(eligible))


def pair_predictions(model, records, method):
    import torch
    from .structure_model import tokens
    model.eval()
    predictions = []
    with torch.inference_mode():
        for record in records:
            scores = model(tokens(record['sequence']))[0].numpy()
            predictions.append({'id': record['id'], 'sequence': record['sequence'], 'method': method,
                                'status': 'ok', 'structure': decode_pairs(record['sequence'], scores)})
    return predictions
