"""Deterministic matched random/hard selection from a fixed teacher-negative pool."""

import random
import numpy as np


def select_training_pairs(sequence, base_pairs, base_labels, pool_pairs, pool_scores, *, seed, mode):
    from .pair_model import CANONICAL
    from .sequences import validate_sequence

    validate_sequence(sequence)
    if not 1 <= len(sequence) < 3000:
        raise ValueError("Hard-negative supervision requires length 1-2999 nt")
    if type(seed) is not int or not 0 <= seed < 2**32 or mode not in ("pool_random", "hard_mixture"):
        raise ValueError("Invalid sampling seed or mode")
    base_pairs, pool_pairs = np.asarray(base_pairs), np.asarray(pool_pairs)
    base_labels, pool_scores = np.asarray(base_labels), np.asarray(pool_scores)
    for pairs in (base_pairs, pool_pairs):
        if pairs.ndim != 2 or pairs.shape[1] != 2 or not np.issubdtype(pairs.dtype, np.integer):
            raise ValueError("Expected integer pair rows")
        if len(set(map(tuple, pairs.tolist()))) != len(pairs):
            raise ValueError("Duplicate pair rows")
        for i, j in pairs:
            if not 0 <= i < j < len(sequence) or j - i < 4 or sequence[i] + sequence[j] not in CANONICAL:
                raise ValueError("Illegal pair coordinate or base identity")
    if (base_labels.shape != (len(base_pairs),) or not np.isin(base_labels, [0, 1]).all()
            or pool_scores.shape != (len(pool_pairs),) or not np.isfinite(pool_scores).all()):
        raise ValueError("Expected binary labels and finite pool scores")
    if len(pool_pairs) > 8 * len(sequence) + 8192:
        raise ValueError("Teacher pool exceeds the declared storage cap")
    positive = {tuple(p) for p in base_pairs[base_labels == 1].tolist()}
    uniform = sorted(map(tuple, base_pairs[base_labels == 0].tolist()))
    scored = {tuple(p): float(s) for p, s in zip(pool_pairs.tolist(), pool_scores.tolist(), strict=True)
              if tuple(p) not in positive}
    if not set(uniform) <= set(scored):
        raise ValueError("Teacher pool must retain every original uniform negative")
    rng = random.Random(seed)
    reserved = set(rng.sample(uniform, len(uniform) // 2))
    remaining = sorted(set(scored) - reserved)
    count = len(uniform) - len(reserved)
    if len(remaining) < count:
        raise ValueError("Insufficient pool negatives to preserve the sample budget")
    if mode == "pool_random":
        chosen = rng.sample(remaining, count)
    else:
        chosen = sorted(remaining, key=lambda p: (-scored[p], p[0], p[1]))[:count]
    negatives = reserved | set(chosen)
    pairs = sorted(positive | negatives)
    import torch

    return (torch.tensor(pairs, dtype=torch.long).reshape(-1, 2),
            torch.tensor([float(p in positive) for p in pairs]),
            {"positive_count": len(positive), "negative_count": len(negatives),
             "reserved_uniform_count": len(reserved), "selected_pool_count": count,
             "pool_negative_count": len(scored),
             "mean_selected_pool_logit": sum(scored[p] for p in chosen) / count if count else None})
