import copy
import json
import random
from pathlib import Path

import pytest

from rnastable.exposures import collect_known_exposures
from rnastable.pair_reference import (
    FORMAT,
    audit,
    evaluate_rows,
    has_crossing_pairs,
    run_evaluation,
    validate_pairs,
)
from rnastable.prospective_binding import bind_pair_reference, bind_record
from rnastable.reference import aggregate_rows, digest


def inputs():
    refs = {
        "schema_version": 1,
        "format": FORMAT,
        "dataset_id": "synthetic_crossing_fixture",
        "records": [
            {
                "id": "crossing",
                "sequence": "GGAAACAC",
                "pairs": [[0, 5], [2, 7]],
                "reference_kind": "synthetic_control",
                "source": "synthetic fixture",
                "family_id": "fixture-family",
            }
        ],
    }
    pred = {
        "schema_version": 1,
        "format": FORMAT,
        "methods": ["nested", "crossing", "absent"],
        "records": [
            {
                "id": "crossing",
                "sequence": "GGAAACAC",
                "method": "nested",
                "status": "ok",
                "structure": "(....)..",
            },
            {
                "id": "crossing",
                "sequence": "GGAAACAC",
                "method": "crossing",
                "status": "ok",
                "pairs": [[0, 5], [2, 7]],
            },
        ],
    }
    return refs, pred


def test_crossing_contacts_stay_in_recall_and_f1_denominators():
    rows = evaluate_rows(*inputs())
    assert rows[0]["reference_has_crossing_pairs"]
    assert rows[0]["reference_pairs"] == 2 and rows[0]["shared_pairs"] == 1
    assert rows[0]["pair_precision"] == 1 and rows[0]["pair_recall"] == 0.5
    assert rows[0]["pair_f1"] == pytest.approx(2 / 3)
    assert rows[1]["pair_f1"] == 1
    assert rows[2]["status"] == "missing" and rows[2]["pair_f1"] is None
    assert aggregate_rows(rows)[0]["mean_pair_f1"] is None


def test_empty_contacts_and_failed_predictions_keep_explicit_outcomes():
    refs, pred = inputs()
    refs["records"][0]["pairs"] = []
    pred["records"][0]["structure"] = "." * 8
    pred["records"][1] = {
        "id": "crossing",
        "sequence": "GGAAACAC",
        "method": "crossing",
        "status": "timeout",
        "error": "fixture timeout",
    }
    rows = evaluate_rows(refs, pred)
    assert rows[0]["pair_f1"] == 1
    assert rows[1]["pair_f1"] is None and rows[2]["pair_f1"] is None


@pytest.mark.parametrize(
    "pairs",
    [
        [[True, 5]],
        [[0.0, 5]],
        [[-1, 5]],
        [[0, 8]],
        [[5, 0]],
        [[2, 2]],
        [[0, 5], [0, 5]],
        [[0, 5], [2, 5]],
        [(0, 5)],
        "(....)..",
    ],
)
def test_invalid_contacts_rejected_without_projection(pairs):
    with pytest.raises(ValueError):
        validate_pairs(pairs, 8)


def test_pair_chemistry_and_loop_size_are_not_silently_filtered():
    assert validate_pairs([[0, 9999], [5000, 5001]], 10000) == {(0, 9999), (5000, 5001)}
    with pytest.raises(ValueError, match="length"):
        validate_pairs([], 10001)


def test_crossing_detection_agrees_with_pairwise_definition():
    rng = random.Random(1729)
    for _ in range(200):
        ends = rng.sample(range(50), 2 * rng.randrange(0, 20))
        pairs = {tuple(sorted(ends[i : i + 2])) for i in range(0, len(ends), 2)}
        expected = any(
            i < a < j < b or a < i < b < j for i, j in pairs for a, b in pairs
        )
        assert has_crossing_pairs(pairs) == expected


@pytest.mark.parametrize(
    "change",
    [
        "format",
        "schema",
        "duplicate_ref",
        "duplicate_pred",
        "sequence",
        "both_representations",
        "failed_contacts",
        "structure_type",
        "missing_error",
        "unknown_method",
        "nontext_id",
    ],
)
def test_invalid_plan_creates_no_run(tmp_path, change):
    refs, pred = inputs()
    if change == "format":
        refs.pop("format")
    elif change == "schema":
        refs["schema_version"] = True
    elif change == "duplicate_ref":
        refs["records"] *= 2
    elif change == "duplicate_pred":
        pred["records"].append(copy.deepcopy(pred["records"][0]))
    elif change == "sequence":
        pred["records"][0]["sequence"] = "AAAAAAAA"
    elif change == "both_representations":
        pred["records"][0]["pairs"] = [[0, 5]]
    elif change == "failed_contacts":
        pred["records"][0].update(status="error", error="fixture")
    elif change == "structure_type":
        pred["records"][0]["structure"] = None
    elif change == "missing_error":
        pred["records"][0] = {
            "id": "crossing",
            "sequence": "GGAAACAC",
            "method": "nested",
            "status": "error",
        }
    elif change == "unknown_method":
        pred["records"][0]["method"] = "other"
    elif change == "nontext_id":
        pred["records"][0]["id"] = []
    paths = [tmp_path / "refs.json", tmp_path / "pred.json"]
    for path, data in zip(paths, (refs, pred)):
        path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        run_evaluation(tmp_path, *paths)
    assert not (tmp_path / "results").exists()


def test_frozen_scoring_replay_and_exposure_survive_live_file_changes(tmp_path):
    refs, pred = inputs()
    paths = [tmp_path / "refs.json", tmp_path / "pred.json"]
    for path, data in zip(paths, (refs, pred)):
        path.write_text(json.dumps(data))
    summary = run_evaluation(tmp_path, *paths)
    run = Path(summary["run_dir"])
    known = collect_known_exposures(tmp_path)
    assert known[0]["family_id"] == "fixture-family"
    for path in paths:
        path.unlink()
    assert audit(run / "summary.json") == summary
    (run / "references.json").write_text("{}")
    with pytest.raises(ValueError, match="input changed"):
        audit(run / "summary.json")


def test_wuss_bridge_preserves_crossing_pairs_and_legacy_rejection():
    seq = "GGAAACAC"
    record = {
        "id": "RF00059:fixture",
        "family_id": "RF00059",
        "sequence": seq,
        "sequence_sha256": digest(seq.encode()),
    }
    alignment = {
        "sequences": {"fixture": seq},
        "consensus": "<.A..>.a",
        "annotations": {},
    }
    result = bind_pair_reference(record, alignment)
    assert result["pairs"] == [[0, 5], [2, 7]]
    assert bind_record(record, alignment)["reference_status"] == "unsupported_reference"
    bad = {**record, "sequence": "GAAACAC", "sequence_sha256": digest(b"GAAACAC")}
    alignment["sequences"]["fixture"] = ".GAAACAC"
    with pytest.raises(ValueError, match="Missing annotated paired column"):
        bind_pair_reference(bad, alignment)
