import pytest
from rnastable.candidate_diagnostics import diagnose, CATEGORIES


def fixture():
    # Five nested contacts: illegal chemistry, suppressed, pruned, displaced, recovered.
    return {
        "id": "fixture",
        "sequence": "AGGGGAAAAACCCCA",
        "structure": "(((((.....)))))",
    }


def test_partition_retains_every_gold_contact_and_false_positives():
    row = diagnose(
        fixture(),
        [[3, 11], [4, 10], [3, 12]],
        [1.0, 2.0, 3.0],
        {(1, 13): -1.0, (2, 12): 1.0, (3, 11): 1.0, (4, 10): 2.0},
        "...((.....).)..",
    )
    assert all(row[c] == 1 for c in CATEGORIES)
    assert sum(row[c] for c in CATEGORIES) == row["reference_pairs"] == 5
    assert row["false_positive_pairs"] == 1
    assert row["pair_recall"] == 0.2


def test_empty_reference_and_prediction_have_no_missing_contacts():
    row = diagnose(
        {"id": "empty", "sequence": "AAAA", "structure": "...."}, [], [], {}, "...."
    )
    assert row["pair_f1"] == 1
    assert sum(row[c] for c in CATEGORIES) == 0


@pytest.mark.parametrize(
    "case",
    [
        "missing_score",
        "nan",
        "nonpositive",
        "duplicate",
        "outside_pool",
        "bool_coordinate",
    ],
)
def test_rejects_inconsistent_inputs(case):
    r = {"id": "r", "sequence": "GAAAAC", "structure": "(....)"}
    pairs, scores, logits, prediction = [[0, 5]], [1.0], {(0, 5): 1.0}, "(....)"
    if case == "missing_score":
        logits = {}
    if case == "nan":
        logits[(0, 5)] = float("nan")
    if case == "nonpositive":
        scores = [0.0]
    if case == "duplicate":
        pairs, scores = pairs * 2, scores * 2
    if case == "outside_pool":
        pairs, scores = [], []
    if case == "bool_coordinate":
        pairs = [[False, 5]]
    with pytest.raises(ValueError):
        diagnose(r, pairs, scores, logits, prediction)
