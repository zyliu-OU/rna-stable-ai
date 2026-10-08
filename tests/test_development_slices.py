import copy
import pytest
from rnastable.development_slices import analyze, HEADS, SEEDS


def fixture():
    records = [
        {
            "id": "validation_PDB_fixture",
            "sequence": "GGAAAACC",
            "structure": "((....))",
            "reference_kind": "experimental",
        },
        {
            "id": "validation_CRW_fixture",
            "sequence": "GGGAAACCC",
            "structure": "(((...)))",
            "reference_kind": "computational",
        },
    ]
    components = []
    for seed in SEEDS:
        for head in HEADS:
            predictions = [
                {
                    **record,
                    "status": "ok",
                    "structure": record["structure"]
                    if head == "helix"
                    else "." * len(record["sequence"]),
                }
                for record in records
            ]
            components.append(
                (
                    {
                        "seed": seed,
                        "head": head,
                        "selected_validation_pair_f1": 1.0 if head == "helix" else 0.0,
                    },
                    predictions,
                )
            )
    return records, components


def test_slice_diagnostics_preserve_all_records_and_empty_denominators():
    records, components = fixture()
    result = analyze(records, components)
    assert (
        result["planned_checkpoint_record_predictions"]
        == result["measured_checkpoint_record_predictions"]
        == 18
    )
    assert len(result["per_record_mean_across_model_seeds"]) == 2
    assert all(
        row["helix_minus_baseline_mean_f1"] == 1.0
        for row in result["per_record_mean_across_model_seeds"]
    )
    empty = [
        row
        for row in result["slices"]
        if row["dimension"] == "source_group" and row["group"] == "Rfam-comparative"
    ]
    assert len(empty) == 9 and all(
        row["planned_records"] == 0 and row["pair_f1"] is None for row in empty
    )
    assert result["test_evaluated"] is False and result["checkpoint_selected"] is False


@pytest.mark.parametrize(
    "mutation", ["missing_component", "missing_record", "sequence", "failed", "score"]
)
def test_diagnostics_reject_missing_or_misbound_predictions(mutation):
    records, components = fixture()
    components = copy.deepcopy(components)
    if mutation == "missing_component":
        components.pop()
    elif mutation == "missing_record":
        components[0][1].pop()
    elif mutation == "sequence":
        components[0][1][0]["sequence"] = "AAUUUUAA"
    elif mutation == "failed":
        components[0][1][0]["status"] = "error"
    elif mutation == "score":
        components[0][0]["selected_validation_pair_f1"] = 0.5
    with pytest.raises(ValueError):
        analyze(records, components)
