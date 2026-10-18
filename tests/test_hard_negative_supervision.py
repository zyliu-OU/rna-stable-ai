"""Matched mining must preserve positives, budgets and legal pair identities."""

import numpy as np
import pytest

from rnastable.hard_negative_supervision import select_training_pairs


def inputs():
    sequence = "GGGGGGCCCCCC"
    positive = [(0, 11), (1, 10)]
    negatives = [(0, 6), (0, 7), (1, 6), (1, 7)]
    pool = positive + negatives + [(2, 8), (2, 9), (3, 8), (3, 9)]
    return sequence, np.array(positive + negatives), np.array([1, 1, 0, 0, 0, 0]), np.array(pool), np.arange(len(pool), dtype=float)


def test_both_arms_retain_all_gold_and_exact_negative_budget():
    data = inputs()
    output = [select_training_pairs(*data, seed=7, mode=mode) for mode in ("pool_random", "hard_mixture")]
    for indices, labels, info in output:
        assert set(map(tuple, indices[labels.bool()].tolist())) == {(0, 11), (1, 10)}
        assert int((labels == 0).sum()) == 4
        assert info["reserved_uniform_count"] == info["selected_pool_count"] == 2
        assert len(indices) == len(set(map(tuple, indices.tolist())))
    assert output[1][2]["mean_selected_pool_logit"] >= output[0][2]["mean_selected_pool_logit"]
    again = select_training_pairs(*data, seed=7, mode="hard_mixture")
    assert again[0].equal(output[1][0]) and again[1].equal(output[1][1])


def test_tied_scores_use_coordinate_order_after_reserved_selection():
    data = inputs()
    scores = np.zeros(len(data[-1]))
    out = select_training_pairs(*data[:-1], scores, seed=7, mode="hard_mixture")
    assert out[2]["negative_count"] == 4
    assert out[2]["mean_selected_pool_logit"] == 0


def test_absent_teacher_candidates_falls_back_to_original_uniform_pool():
    seq, pairs, labels, _, _ = inputs()
    pool = pairs[labels == 0]
    result = select_training_pairs(seq, pairs, labels, pool, np.zeros(len(pool)), seed=0, mode="hard_mixture")
    assert set(map(tuple, result[0].tolist())) == set(map(tuple, pairs.tolist()))


def test_rejects_missing_original_negative_and_nonfinite_scores():
    data = inputs()
    with pytest.raises(ValueError, match="retain every"):
        select_training_pairs(*data[:3], data[3][6:], data[4][6:], seed=0, mode="hard_mixture")
    bad = data[4].copy()
    bad[0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        select_training_pairs(*data[:4], bad, seed=0, mode="hard_mixture")


def test_rejects_scope_and_illegal_pairs():
    data = inputs()
    with pytest.raises(ValueError, match="1-2999"):
        select_training_pairs("A" * 3000, *data[1:], seed=0, mode="pool_random")
    bad = data[3].copy()
    bad[0] = [0, 1]
    with pytest.raises(ValueError, match="Illegal"):
        select_training_pairs(*data[:3], bad, data[4], seed=0, mode="pool_random")
