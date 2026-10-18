"""Label-informed F1 ceilings; these oracle structures are not model predictions."""

import json
import numpy as np

from .long_exact_sparse_pairs import decode_long_exact_sparse
from .pair_model import CANONICAL
from .pair_reference import pair_agreement, validate_pairs
from .scoring import base_pairs
from .sequences import validate_sequence
from .reference import digest


def candidate_set(sequence, pairs):
    validate_sequence(sequence)
    if not 1 <= len(sequence) < 3000:
        raise ValueError("Recovery diagnostics require length 1-2999 nt")
    values = np.asarray(pairs)
    if values.ndim != 2 or values.shape[1] != 2 or not np.issubdtype(values.dtype, np.integer):
        raise ValueError("Expected integer candidate pairs")
    result = set(map(tuple, values.tolist()))
    if len(result) != len(values):
        raise ValueError("Duplicate candidate pair")
    for left, right in result:
        if (not 0 <= left < right < len(sequence) or right - left < 4
                or sequence[left] + sequence[right] not in CANONICAL):
            raise ValueError("Illegal candidate pair")
    return result


def gold_oracle(sequence, reference_pairs, candidates=None):
    validate_sequence(sequence)
    if not 1 <= len(sequence) < 3000:
        raise ValueError("Recovery diagnostics require length 1-2999 nt")
    reference = validate_pairs(reference_pairs, len(sequence))
    legal = {p for p in reference if p[1] - p[0] >= 4 and sequence[p[0]] + sequence[p[1]] in CANONICAL}
    allowed = legal if candidates is None else legal & candidate_set(sequence, candidates)
    pairs = np.array(sorted(allowed), dtype=np.int32).reshape(-1, 2)
    result = decode_long_exact_sparse(sequence, pairs, np.ones(len(pairs)))
    predicted = base_pairs(result["structure"])
    if not predicted <= allowed or result["objective"] != len(predicted):
        raise ValueError("Gold-only decoder result is inconsistent")
    unsupported = reference - legal
    short_only = sum(p[1] - p[0] < 4 and sequence[p[0]] + sequence[p[1]] in CANONICAL for p in unsupported)
    chemistry_only = sum(p[1] - p[0] >= 4 and sequence[p[0]] + sequence[p[1]] not in CANONICAL for p in unsupported)
    return {"not_a_model_prediction": True, "uses_reference_labels": True,
            "sequence_sha256": digest(sequence.encode()),
            "reference_pairs_sha256": digest(json.dumps(sorted(reference), separators=(",", ":")).encode()),
            "reference_pair_count": len(reference), "legal_gold_pair_count": len(legal),
            "unsupported_gold_pair_count": len(unsupported),
            "unsupported_reasons": {"short_only": short_only, "noncanonical_only": chemistry_only,
                                    "short_and_noncanonical": len(unsupported) - short_only - chemistry_only},
            "allowed_gold_pair_count": len(allowed), "oracle_correct_pair_count": len(predicted),
            "oracle_metrics_against_full_reference": pair_agreement(predicted, reference),
            "label_informed_oracle_structure": result["structure"], "dp_array_bytes": result["dp_array_bytes"]}


def recovery_decomposition(sequence, reference_pairs, candidates, actual_structure, full_oracle=None):
    pool = candidate_set(sequence, candidates)
    reference = validate_pairs(reference_pairs, len(sequence))
    if not isinstance(actual_structure, str) or len(actual_structure) != len(sequence):
        raise ValueError("Actual prediction length differs")
    actual = base_pairs(actual_structure)
    if not actual <= pool:
        raise ValueError("Actual prediction contains a pair outside the retained pool")
    full = gold_oracle(sequence, reference_pairs) if full_oracle is None else full_oracle
    if (full["sequence_sha256"] != digest(sequence.encode())
            or full["reference_pairs_sha256"] != digest(json.dumps(sorted(reference), separators=(",", ":")).encode())):
        raise ValueError("Cached full oracle belongs to a different sequence or reference")
    retained = gold_oracle(sequence, reference_pairs, candidates)
    metrics = pair_agreement(actual, reference)
    total, legal = full["reference_pair_count"], full["legal_gold_pair_count"]
    whole, available = full["oracle_correct_pair_count"], retained["oracle_correct_pair_count"]
    correct = metrics["shared_pairs"]
    if not 0 <= correct <= available <= whole <= legal <= total:
        raise ValueError("Recovery ceiling counts are not nested")
    if not (metrics["pair_f1"] <= retained["oracle_metrics_against_full_reference"]["pair_f1"] + 1e-12
            <= full["oracle_metrics_against_full_reference"]["pair_f1"] + 2e-12):
        raise ValueError("Actual F1 exceeds its gold-only ceiling")
    losses = {"unsupported_gold": total - legal, "legal_noncrossing_limit": legal - whole,
              "retained_candidate_limit": whole - available, "score_selection_gap": available - correct}
    if sum(losses.values()) != total - correct:
        raise ValueError("Missing-gold decomposition does not balance")
    return {"actual_metrics": metrics, "retained_gold_oracle": retained,
            "missing_gold_decomposition": losses,
            "candidate_legal_gold_recall": retained["allowed_gold_pair_count"] / legal if legal else None,
            "actual_to_candidate_oracle_correct_fraction": correct / available if available else None,
            "actual_false_positive_pairs": len(actual - reference)}
