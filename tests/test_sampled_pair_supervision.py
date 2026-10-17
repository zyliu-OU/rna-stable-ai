"""Long-sequence supervision preserves complete legal contacts within a cap."""

import pytest

from rnastable.sampled_pair_supervision import sampled_pair_supervision
from rnastable.pair_set_training import pair_set_supervision


def test_all_legal_gold_retained_and_negative_sampling_is_reproducible():
    record = {"sequence": "G" * 2500 + "C" * 2499,
              "pairs": [[i, 4998 - i] for i in range(100)]}
    first = sampled_pair_supervision(record, seed=17, max_negatives=500)
    again = sampled_pair_supervision(record, seed=17, max_negatives=500)
    indices, labels, excluded = first
    assert excluded == 0
    assert len(indices) == 500  # 100 positives and 400 negatives
    assert int(labels.sum()) == 100
    assert set(map(tuple, indices[labels.bool()].tolist())) == {
        tuple(pair) for pair in record["pairs"]}
    assert first[0].equal(again[0]) and first[1].equal(again[1])
    assert all(j - i >= 4 and record["sequence"][i] + record["sequence"][j]
               in {"AU", "UA", "GC", "CG", "GU", "UG"}
               for i, j in indices.tolist())


def test_unsupported_gold_counted_and_no_fake_negatives():
    record = {"sequence": "AAAAACCCCC", "pairs": [[0, 9]]}
    indices, labels, excluded = sampled_pair_supervision(record, seed=3)
    assert excluded == 1
    assert indices.shape == (0, 2)
    assert len(labels) == 0


def test_exhaustive_small_case_matches_full_pair_labels():
    record = {"sequence": "GCAUGCAUGCAUGCAU", "pairs": [[0, 13], [1, 12]]}
    sparse_indices, sparse_labels, sparse_excluded = sampled_pair_supervision(
        record, seed=9, max_negatives=1000, negatives_per_positive=64)
    full_indices, full_labels, full_excluded = pair_set_supervision(record)
    assert sparse_excluded == full_excluded
    assert {tuple(pair): label for pair, label in zip(
        sparse_indices.tolist(), sparse_labels.tolist(), strict=True)} == {
        tuple(pair): label for pair, label in zip(
            full_indices.tolist(), full_labels.tolist(), strict=True)}


def test_rejects_out_of_scope_and_invalid_cap():
    with pytest.raises(ValueError, match="4,999"):
        sampled_pair_supervision({"sequence": "A" * 5000, "pairs": []}, seed=0)
    with pytest.raises(ValueError, match="max_negatives"):
        sampled_pair_supervision({"sequence": "A" * 20, "pairs": []},
                                 seed=0, max_negatives=0)
