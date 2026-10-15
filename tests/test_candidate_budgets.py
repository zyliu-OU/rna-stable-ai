"""Check complete inventories, empty slices, costs and competing-contact regressions."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from rnastable.candidate_diagnostics import CATEGORIES, diagnose
from rnastable.exact_sparse_pairs import decode_exact_sparse

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location(
    "budget_study", SCRIPTS / "compare_candidate_budgets.py"
)
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


def outcomes():
    return [
        {
            "seed": seed,
            "head": head,
            "top_k": k,
            "id": f"r{i}",
            "source_group": "PDB-derived",
            "length_group": "1..64",
            "reference_kind": "experimental",
            "pair_f1": 0.5 if k == 16 else 0.25,
            **dict.fromkeys(study.COUNTS, 0),
            "score_seconds": 0.1,
            "decode_seconds": 0.2,
            "candidate_array_bytes": 0,
            "dp_array_bytes": 432,
            "peak_score_tile_elements": 36,
            "length": 6,
        }
        for seed in study.SEEDS
        for head in study.HEADS
        for i in range(47)
        for k in study.BUDGETS
    ]


def test_complete_grid_keeps_regressions_and_empty_slices():
    aggregates = study.aggregate(outcomes())
    assert len(aggregates) == 270
    all32 = next(r for r in aggregates if r["dimension"] == "all" and r["top_k"] == 32)
    assert all32["records"] == all32["regressed_records"] == 47
    assert all32["mean_f1_change_from_16"] == -0.25
    empty = next(r for r in aggregates if r["group"] == "CRW-comparative")
    assert empty["records"] == 0
    assert empty["mean_pair_f1"] is None
    assert empty["score_seconds"] == empty["candidate_array_bytes"] == 0


@pytest.mark.parametrize(
    "change",
    ["missing", "duplicate", "unknown_seed", "unknown_budget", "missing_record"],
)
def test_inventory_rejects_incomplete_or_unplanned_outcomes(change):
    rows = outcomes()
    if change == "missing":
        rows.pop()
    elif change == "duplicate":
        rows[-1] = rows[0]
    elif change == "unknown_seed":
        rows[0]["seed"] = 42
    elif change == "unknown_budget":
        rows[0]["top_k"] = 128
    else:
        for r in rows:
            if r["id"] == "r46":
                r["id"] = "r0"
    with pytest.raises(ValueError):
        study.aggregate(rows)


@pytest.mark.parametrize(
    "key,value",
    [
        ("score_seconds", float("nan")),
        ("decode_seconds", -1),
        ("score_seconds", True),
        ("candidate_array_bytes", 16),
        ("dp_array_bytes", 0),
        ("peak_score_tile_elements", -1),
    ],
)
def test_rejects_invalid_or_inconsistent_measured_costs(key, value):
    row = outcomes()[0]
    study.validate_costs(row)
    row[key] = value
    with pytest.raises(ValueError):
        study.validate_costs(row)


def test_nested_pool_can_retain_gold_but_reduce_accuracy():
    record = {"id": "competition", "sequence": "GGAAACC", "structure": "(.....)"}
    small = [[0, 6]]
    larger = [[0, 6], [1, 6]]
    first = decode_exact_sparse(record["sequence"], np.array(small), [1.0])
    second = decode_exact_sparse(record["sequence"], np.array(larger), [1.0, 2.0])
    a = diagnose(record, small, [1.0], {(0, 6): 1.0}, first["structure"])
    b = diagnose(record, larger, [1.0, 2.0], {(0, 6): 1.0}, second["structure"])
    assert a["pair_f1"] == 1 and b["pair_f1"] == 0
    assert a["positive_not_retained"] == b["positive_not_retained"] == 0
    assert b["retained_not_decoded"] == b["false_positive_pairs"] == 1
    assert sum(b[c] for c in CATEGORIES) == 1


@pytest.mark.parametrize("failure", ["top16_mismatch", "pool_not_nested"])
def test_driver_retains_partial_outcomes_and_failure_identity(
    tmp_path, monkeypatch, failure
):
    import torch

    record = {
        "id": "PDB_fixture",
        "sequence": "GAAAAC",
        "structure": "(....)",
        "reference_kind": "experimental",
    }
    source = tmp_path / "source.json"
    source.write_text(
        json.dumps({"run_dir": str(tmp_path), "seed": 20261006, "head": "baseline"})
    )
    (tmp_path / "predictions.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "id": record["id"],
                        "method": "trained_exact_sparse",
                        "structure": "......"
                        if failure == "top16_mismatch"
                        else "(....)",
                    }
                ]
            }
        )
    )
    monkeypatch.setattr(
        study,
        "load_checkpoint",
        lambda path: (
            None,
            {"top_k": 16, "inference_decoder": "exact_sparse", "block_size": 64},
            None,
            lambda tokenized, indices: torch.ones(len(indices)),
        ),
    )

    def pool(model, sequence, top_k, block_size):
        pairs = (
            np.array([[0, 5]], dtype=np.int32)
            if top_k == 16
            else np.empty((0, 2), dtype=np.int32)
        )
        scores = np.ones(len(pairs), dtype=np.float64)
        return {
            "pairs": pairs,
            "scores": scores,
            "candidate_array_bytes": pairs.nbytes + scores.nbytes,
            "peak_score_tile_elements": 36,
        }

    monkeypatch.setattr(study, "sparse_candidates", pool)
    with pytest.raises(ValueError, match="Top-16|not nested"):
        study.evaluate([record], [{"summary": str(source)}], tmp_path)
    failure_row = json.loads((tmp_path / "failure.json").read_text())
    partial = json.loads((tmp_path / "outcomes.json").read_text())
    assert failure_row["id"] == record["id"]
    assert failure_row["complete"] is False
    assert (
        failure_row["completed_predictions"]
        == len(partial)
        == (0 if failure == "top16_mismatch" else 1)
    )
