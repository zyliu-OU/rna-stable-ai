"""Partition reference contacts without altering labels or selecting a model."""

import math
from .pair_model import CANONICAL
from .scoring import base_pairs, paired_fraction, structure_agreement
from .sequences import validate_sequence

CATEGORIES = (
    "illegal_reference",
    "nonpositive_logit",
    "positive_not_retained",
    "retained_not_decoded",
    "recovered",
)


def diagnose(record, candidate_pairs, candidate_scores, gold_logits, prediction):
    sequence = record["sequence"]
    validate_sequence(sequence)
    if len(sequence) > 1024:
        raise ValueError("Development diagnostics bounded to1024 nt")
    paired_fraction(record["structure"], len(sequence))
    paired_fraction(prediction, len(sequence))
    gold = base_pairs(record["structure"])
    predicted = base_pairs(prediction)
    legal = {p for p in gold if p[1] - p[0] >= 4 and sequence[p[0]] + sequence[p[1]] in CANONICAL}
    if set(gold_logits) != legal or any(not math.isfinite(v) for v in gold_logits.values()):
        raise ValueError("Expected finite scores for every legal reference pair")
    if len(candidate_pairs) != len(candidate_scores):
        raise ValueError("Candidate score inventory differs")
    retained = set()
    for raw, score in zip(candidate_pairs, candidate_scores):
        if len(raw) != 2 or any(type(x) is not int for x in raw):
            raise ValueError("Candidate coordinates must be integers")
        i, j = raw
        if not (0 <= i < j < len(sequence) and j - i >= 4 and sequence[i] + sequence[j] in CANONICAL):
            raise ValueError("Illegal candidate")
        if not math.isfinite(score) or score <= 0 or (i, j) in retained:
            raise ValueError("Expected distinct positive finite candidates")
        retained.add((i, j))
    if not predicted.issubset(retained):
        raise ValueError("Prediction contains a pair outside the candidate pool")
    if any(gold_logits[p] <= 0 for p in legal & retained):
        raise ValueError("Retained gold pair has nonpositive diagnostic score")
    counts = dict.fromkeys(CATEGORIES, 0)
    for pair in gold:
        category = (
            "illegal_reference" if pair not in legal
            else "nonpositive_logit" if gold_logits[pair] <= 0
            else "positive_not_retained" if pair not in retained
            else "retained_not_decoded" if pair not in predicted
            else "recovered"
        )
        counts[category] += 1
    return {
        "id": record["id"],
        "length": len(sequence),
        "reference_pairs": len(gold),
        "candidate_pairs": len(retained),
        "predicted_pairs": len(predicted),
        "false_positive_pairs": len(predicted - gold),
        **counts,
        **structure_agreement(prediction, record["structure"]),
    }
