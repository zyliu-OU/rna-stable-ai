"""Gold-only ceilings must preserve the full scoring denominator and topology."""

import itertools
import numpy as np
import pytest

from rnastable.pair_reference import has_crossing_pairs, pair_agreement
from rnastable.recovery_ceiling import gold_oracle, recovery_decomposition


def test_crossing_gold_cannot_be_reported_as_fully_recoverable():
    oracle = gold_oracle("GGGGCCCC", [[0, 5], [1, 6]])
    assert oracle["oracle_correct_pair_count"] == 1
    assert oracle["oracle_metrics_against_full_reference"]["pair_f1"] == pytest.approx(2 / 3)
    assert oracle["reference_pair_count"] == 2


def test_unsupported_gold_stays_in_the_f1_denominator():
    oracle = gold_oracle("GGGGCCCC", [[0, 5], [1, 6], [2, 3]])
    assert oracle["unsupported_reasons"]["short_and_noncanonical"] == 1
    assert oracle["oracle_metrics_against_full_reference"]["pair_f1"] == 0.5
    assert oracle["not_a_model_prediction"] and oracle["uses_reference_labels"]


def test_count_decomposition_and_false_positives_are_separate():
    result = recovery_decomposition("GGGGCCCC", [[0, 5], [1, 6], [2, 3]],
                                    np.array([[0, 5], [0, 7]]), "(......)")
    assert result["missing_gold_decomposition"] == {
        "unsupported_gold": 1, "legal_noncrossing_limit": 1,
        "retained_candidate_limit": 0, "score_selection_gap": 1}
    assert result["actual_false_positive_pairs"] == 1
    assert result["actual_metrics"]["pair_f1"] == 0


def test_oracle_f1_matches_brute_force_over_legal_predictions():
    sequence = "GGGGCCCC"
    gold = {(0, 5), (1, 6)}
    candidates = [(i, j) for i in range(4) for j in range(4, 8) if j - i >= 4]
    best = 0
    for flags in itertools.product((False, True), repeat=len(candidates)):
        pairs = {p for p, keep in zip(candidates, flags) if keep}
        endpoints = [i for p in pairs for i in p]
        if len(set(endpoints)) != len(endpoints) or has_crossing_pairs(pairs):
            continue
        best = max(best, pair_agreement(pairs, gold)["pair_f1"])
    oracle = gold_oracle(sequence, [list(p) for p in sorted(gold)], np.array(candidates))
    assert oracle["oracle_metrics_against_full_reference"]["pair_f1"] == best


def test_empty_reference_and_missing_candidate_gold_have_explicit_scores():
    empty = np.empty((0, 2), dtype=np.int32)
    assert gold_oracle("AAAAAAAA", [], empty)["oracle_metrics_against_full_reference"]["pair_f1"] == 1
    result = recovery_decomposition("GGGGCCCC", [[0, 7]], empty, "........")
    assert result["missing_gold_decomposition"]["retained_candidate_limit"] == 1
    assert result["actual_to_candidate_oracle_correct_fraction"] is None


def test_illegal_candidates_outside_pool_predictions_and_scope_rejected():
    with pytest.raises(ValueError, match="Illegal"):
        gold_oracle("GGGGCCCC", [[0, 7]], np.array([[0, 1]]))
    with pytest.raises(ValueError, match="outside"):
        recovery_decomposition("GGGGCCCC", [[0, 7]], np.array([[0, 6]]), "(......)")
    with pytest.raises(ValueError, match="1-2999"):
        gold_oracle("A" * 3000, [])


def test_full_oracle_cache_is_bound_to_exact_sequence_and_reference():
    cached = gold_oracle("GGGGCCCC", [[0, 7]])
    with pytest.raises(ValueError, match="different sequence or reference"):
        recovery_decomposition("GGGGCCCC", [[0, 6]], np.array([[0, 6]]), "........", cached)
