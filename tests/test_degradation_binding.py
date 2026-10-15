"""Preserve assay coordinates, negative values, failures and fixed selection."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from rnastable.reference import digest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "degradation_binding", PROJECT / "scripts/prepare_degradation_binding.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def record(identity="r"):
    row = {
        "id": identity,
        "sequence": "GAAAAC",
        "seq_length": 6,
        "seq_scored": 2,
        "SN_filter": 0,
        "structure": "not experimental gold",
    }
    for target, error in module.ERROR_FIELDS.items():
        row[target] = [-2.0, 3.0]
        row[error] = [0.1, 0.2]
    return row


def test_negative_values_remain_unclipped_with_exact_prefix_coordinates():
    row = record()
    assert module.headers([row]) == [{"id": "r", "sequence": "GAAAAC"}]
    bound = module.bind_row(row, False)
    assert bound["assays"]["reactivity"]["values"] == [-2, 3]
    assert bound["assays"]["reactivity"]["mean"] == 0.5
    assert bound["prediction_allowed"] and "structure" not in bound


@pytest.mark.parametrize(
    "key,value",
    [
        ("reactivity", [None, 3]),
        ("reactivity", [True, 3]),
        ("reactivity", [float("nan"), 3]),
        ("reactivity", [1]),
        ("reactivity_error", [-0.1, 0.2]),
        ("reactivity_error", None),
    ],
)
def test_invalid_assay_retains_null_outcome_without_dropping_other_assays(key, value):
    row = record()
    row[key] = value
    bound = module.bind_row(row, False)
    assert bound["assays"]["reactivity"]["status"] == "unsupported"
    assert bound["assays"]["reactivity"]["mean"] is None
    assert bound["assays"]["deg_Mg_pH10"]["status"] == "ok"


@pytest.mark.parametrize(
    "key,value",
    [
        ("seq_length", 5),
        ("seq_scored", 7),
        ("seq_scored", 0),
        ("seq_scored", True),
        ("sequence", "GAAAAX"),
    ],
)
def test_bad_input_coordinates_or_sequence_reject_before_binding(key, value):
    row = record()
    row[key] = value
    with pytest.raises(ValueError):
        module.headers([row])


def test_missing_or_duplicate_identity_rejected():
    rows = [record(), record()]
    with pytest.raises(ValueError):
        module.read_records("\n".join(json.dumps(r) for r in rows).encode())
    del rows[0]["id"]
    with pytest.raises(ValueError):
        module.read_records(json.dumps(rows[0]).encode())


def test_selection_ignores_quality_values_and_keeps_failed_assays():
    rows = [record(f"r{i:02d}") for i in reversed(range(70))]
    rows[-1]["reactivity"] = None
    result = module.compute(rows, [])
    assert [r["id"] for r in result["records"]] == [f"r{i:02d}" for i in range(64)]
    assert result["planned_assay_outcomes"] == 320
    assert result["supported_assay_outcomes"] == 319
    assert (
        not result["test_inference_allowed"]
        and not result["reference_structures_used_as_gold"]
    )


def test_prior_overlap_blocks_predictions_without_dropping_measured_targets():
    result = module.compute([record()], [{"sequence": "GAAAAC"}])
    assert result["overlap_records"] == 1
    assert not result["records"][0]["prediction_allowed"]
    assert result["supported_assay_outcomes"] == 5


def test_binding_exposure_precedes_assay_inspection_and_audit_creates_no_event(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(module, "ROOT", tmp_path)
    raw = (json.dumps(record()) + "\n").encode()
    source = tmp_path / "source"
    source.mkdir()
    (source / "author.json").write_bytes(raw)
    summary = {
        "complete": True,
        "run_dir": str(source),
        "sources_complete": True,
        "source": {"filename": "author.json", "sha256": digest(raw)},
    }
    monkeypatch.setattr(module, "audit_source", lambda path: summary)
    monkeypatch.setattr(module, "collect_known_exposures", lambda root: [])
    original = module.compute
    observed = []

    def compute(*args):
        events = list(
            (tmp_path / "results").glob("degradation_binding_runs/*/exposures/*.json")
        )
        assert len(events) == 1
        observed.append(events[0])
        return original(*args)

    monkeypatch.setattr(module, "compute", compute)
    result = module.prepare()
    path = Path(result["run_dir"]) / "summary.json"
    assert module.audit(path) == result
    assert len(observed) == 2 and observed[0] == observed[1]
    (path.parent / "binding.json").write_text("{}\n")
    with pytest.raises(ValueError, match="binding replay differs"):
        module.audit(path)


def test_columnar_author_json_preserves_row_identity_and_assay_coordinates():
    rows = [record("r1"), record("r2")]
    rows[1]["reactivity"] = [9.0, 10.0]
    columns = {key: {str(i): row[key] for i, row in enumerate(rows)} for key in rows[0]}
    assert module.read_records(json.dumps(columns).encode()) == rows
    assert module.read_records(json.dumps(rows).encode()) == rows
    assert (
        module.bind_row(module.read_records(json.dumps(columns).encode())[1], False)[
            "assays"
        ]["reactivity"]["mean"]
        == 9.5
    )


@pytest.mark.parametrize("tamper", ["missing_column_row", "bad_index", "duplicate_id"])
def test_columnar_source_rejects_missing_or_ambiguous_row_bindings(tamper):
    rows = [record("r1"), record("r2")]
    columns = {key: {str(i): row[key] for i, row in enumerate(rows)} for key in rows[0]}
    if tamper == "missing_column_row":
        columns["reactivity"].pop("1")
    elif tamper == "bad_index":
        for column in columns.values():
            column["01"] = column.pop("1")
    else:
        columns["id"]["1"] = "r1"
    with pytest.raises(ValueError):
        module.read_records(json.dumps(columns).encode())
