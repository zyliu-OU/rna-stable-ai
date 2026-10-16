"""Explicit pair references survive training-label projection and full scoring."""

import pytest

from rnastable.pair_set_training import pair_set_supervision, score_predictions


def test_unlearnable_crossing_gold_is_counted_and_full_gold_is_scored():
    record = {"id": "crossing", "sequence": "GCAAAACU", "pairs": [[0, 6], [1, 7]]}
    edges, labels, excluded = pair_set_supervision(record)
    positives = {tuple(pair) for pair, label in zip(edges.tolist(), labels.tolist()) if label}
    assert positives == {(0, 6)}
    assert excluded == 1
    f1, details = score_predictions(
        [{"id": "crossing", "sequence": record["sequence"], "status": "ok",
          "structure": "(.....)."}], [record]
    )
    assert f1 == pytest.approx(2 / 3)
    assert details[0]["reference_pairs"] == 2
    assert details[0]["shared_pairs"] == 1


def test_pair_set_labels_reject_duplicate_partner_and_changed_prediction_identity():
    record = {"id": "r", "sequence": "GCAAAACU", "pairs": [[0, 6], [0, 7]]}
    with pytest.raises(ValueError, match="multiple partners"):
        pair_set_supervision(record)
    record["pairs"] = [[0, 6]]
    with pytest.raises(ValueError, match="identity"):
        score_predictions(
            [{"id": "other", "sequence": record["sequence"], "status": "ok",
              "structure": "(.....)."}], [record]
        )
