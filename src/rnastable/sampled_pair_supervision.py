"""Bounded complete-reference supervision for RNAs below 5,000 nt.

Retain every legal labeled contact and sample legal negatives without building
the quadratic all-pairs tensor. This is a development labeler, not a claim that
sampled BCE is equivalent to full-pair BCE.
"""

import random

from .pair_model import CANONICAL
from .pair_reference import validate_pairs
from .sequences import validate_sequence


def sampled_pair_supervision(record, *, seed, max_negatives=8192,
                             negatives_per_positive=4):
    """Return pair indices, binary labels, and the count of unsupported gold pairs.

    All legal gold pairs are kept. Negatives are sampled uniformly from ordered
    coordinate pairs by rejection, then a bounded-memory scan fills any shortfall.
    The scan may take quadratic time when legal negatives are scarce.
    """
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("seed must be an unsigned 32-bit integer")
    if type(max_negatives) is not int or not 1 <= max_negatives <= 65536:
        raise ValueError("max_negatives must be in 1..65536")
    if type(negatives_per_positive) is not int or not 1 <= negatives_per_positive <= 64:
        raise ValueError("negatives_per_positive must be in 1..64")
    sequence = validate_sequence(record["sequence"])
    n = len(sequence)
    if n > 4999:
        raise ValueError("Active sampled supervision supports at most 4,999 nt")
    gold = validate_pairs(record["pairs"], n)
    positive = {pair for pair in gold
                if pair[1] - pair[0] >= 4
                and sequence[pair[0]] + sequence[pair[1]] in CANONICAL}
    target = min(max_negatives, max(1, negatives_per_positive * len(positive)))
    negatives = set()
    rng = random.Random(seed)
    for _ in range(max(1024, 32 * target)):
        if len(negatives) == target:
            break
        i, j = sorted(rng.sample(range(n), 2)) if n >= 2 else (0, 0)
        pair = (i, j)
        if j - i >= 4 and sequence[i] + sequence[j] in CANONICAL and pair not in positive:
            negatives.add(pair)
    if len(negatives) < target:
        for j in range(4, n):
            for i in range(j - 3):
                pair = (i, j)
                if (sequence[i] + sequence[j] in CANONICAL
                        and pair not in positive and pair not in negatives):
                    negatives.add(pair)
                    if len(negatives) == target:
                        break
            if len(negatives) == target:
                break
    pairs = sorted(positive | negatives)
    import torch

    indices = torch.tensor(pairs, dtype=torch.long).reshape(-1, 2)
    labels = torch.tensor([float(pair in positive) for pair in pairs])
    return indices, labels, len(gold - positive)
