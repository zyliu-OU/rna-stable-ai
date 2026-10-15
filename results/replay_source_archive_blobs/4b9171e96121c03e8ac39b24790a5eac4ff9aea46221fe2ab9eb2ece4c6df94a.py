"""Explicit nonnegative pair-logit penalty; not a native folding-energy adjustment."""

import math
import numpy as np


def validate_pair_penalty(value):
    if (
        type(value) not in (int, float)
        or not math.isfinite(value)
        or not 0 <= value <= 8
    ):
        raise ValueError("Pair logit penalty must be finite in 0..8")
    return float(value)


def penalize_candidates(candidates, penalty):
    penalty = validate_pair_penalty(penalty)
    if penalty == 0:
        return candidates
    pairs = np.asarray(candidates["pairs"])
    scores = np.asarray(candidates["scores"], dtype=np.float64)
    if (
        pairs.ndim != 2
        or pairs.shape[1] != 2
        or not np.issubdtype(pairs.dtype, np.integer)
        or scores.shape != (len(pairs),)
        or not np.isfinite(scores).all()
    ):
        raise ValueError("Expected integer candidates with finite logits")
    adjusted = scores - penalty
    positive = adjusted > 0
    retained_pairs = pairs[positive]
    retained_scores = adjusted[positive]
    return {
        **candidates,
        "pairs": retained_pairs,
        "scores": retained_scores,
        "candidate_pair_penalty": penalty,
        "retained_after_penalty": len(retained_scores),
        "penalty_candidate_array_bytes": retained_pairs.nbytes + retained_scores.nbytes,
        "penalty_interpretation": "Uniform nonnegative learned-logit penalty before sparse decoding. Original candidate count/storage refer to scoring; additional retained arrays are reported separately. Not an energy or biological-stability quantity.",
    }
