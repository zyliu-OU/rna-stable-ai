"""Tests for the reference construct's score record.

This is the project's first record carrying both a stability and a translation
score for one sequence. The things most worth pinning are the ones that keep it
honest: that the composite stays absent, that the extrapolation is stated, and
that the rejected published-STRAND component is excluded with a reason rather
than silently omitted.
"""
import csv
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results/reference_score_record/FLUC-REF-V1_score_record.json"
CALIBRATION = ROOT / "results/strand_rnafold_calibration_runs/20261019T174049.053308Z"

pytestmark = pytest.mark.skipif(not RECORD.exists(), reason="score record not built")


@pytest.fixture(scope="module")
def payload():
    return json.loads(RECORD.read_text())


@pytest.fixture(scope="module")
def record(payload):
    assert len(payload["records"]) == 1
    return payload["records"][0]


def by_component(record):
    return {entry["component"]: entry for entry in record["scores"]}


# --- the milestone --------------------------------------------------------

def test_record_carries_both_sides(payload):
    """Every prior record had one side only; this is the first with both."""
    coverage = payload["coverage"]
    assert coverage["records_with_stability_score"] == 1
    assert coverage["records_with_translation_score"] == 1
    assert coverage["records_with_both_sides"] == 1
    assert coverage["joint_scoring_available"] is True


def test_both_scores_are_present_and_finite(record):
    scores = by_component(record)
    assert set(scores) == {"strand_rnafold_calibration_v1", "ribonn_released_task"}
    for entry in scores.values():
        assert isinstance(entry["value"], float)
        assert entry["value"] == entry["value"]  # not nan


# --- the prohibitions that keep it honest ---------------------------------

def test_no_composite_score_is_emitted(record, payload):
    """Having both sides is exactly when combining them becomes tempting."""
    assert record["composite_score"] is None
    assert payload["composite_score_emitted"] is False
    assert "ncommensurable" in record["composite_blocked_reason"]


def test_record_asserts_no_independent_validation(record):
    assert record["independent_validation"] is False
    for entry in record["scores"]:
        assert entry["independent_validation"] is False


def test_the_two_scores_are_in_different_units(record):
    """The reason they may not be combined, stated in the record itself."""
    scores = by_component(record)
    stability = scores["strand_rnafold_calibration_v1"]
    translation = scores["ribonn_released_task"]
    assert stability["units"] == "hours"
    assert translation["units"] != stability["units"]
    assert "task scale" in translation["units"]


def test_published_strand_is_excluded_with_an_explicit_reason(record):
    """The rejected component must be named, not silently omitted."""
    assert len(record["exclusions"]) == 1
    exclusion = record["exclusions"][0]
    assert exclusion["component"] == "strand_reference_replay"
    assert "rejected" in exclusion["reason"]
    assert exclusion["run"]


def test_every_component_is_either_scored_or_excluded(record):
    covered = ({e["component"] for e in record["scores"]}
               | {e["component"] for e in record["exclusions"]})
    assert covered == {"strand_reference_replay", "strand_rnafold_calibration_v1",
                       "ribonn_released_task"}


# --- the extrapolation ----------------------------------------------------

def test_gc_extrapolation_is_recorded_not_hidden(payload):
    """GC sits outside the calibration's training range; that must be stated."""
    assert payload["features_outside_training_domain"] == ["GC"]


def test_gc_really_is_outside_the_training_range(payload):
    domain = payload["calibration_training_domain"]["GC"]
    features = by_component(payload["records"][0])[
        "strand_rnafold_calibration_v1"]["settings"]["features"]
    assert features["GC"] > domain["max"]


def test_the_stability_interpretation_names_the_extrapolation(record):
    text = by_component(record)["strand_rnafold_calibration_v1"]["interpretation"]
    assert "EXTRAPOLATION" in text
    assert "GC" in text


def test_the_stability_interpretation_names_its_limitations(record):
    """Unvalidated refit, wrong quantity, and an unmodelled nucleoside."""
    text = by_component(record)["strand_rnafold_calibration_v1"]["interpretation"]
    assert "NOT the published STRAND model" in text
    assert "unvalidated" in text
    assert "in-cell" in text          # in-solution vs in-cell quantity mismatch
    assert "N1-methylpseudouridine" in text


def test_the_translation_interpretation_names_its_limitations(record):
    text = by_component(record)["ribonn_released_task"]["interpretation"]
    assert "A549 arm only" in text
    assert "not a prediction of luminescence" in text
    assert "model-blind" in text


# --- provenance binding ---------------------------------------------------

def test_record_id_is_the_sequence_hash(record):
    assert record["record_id"] == record["sequence"]["sha256"]


def test_sequence_identity_matches_the_assembled_transcript(record):
    assembly = json.loads((ROOT / "results/reference_transcript/FLUC-REF-V1.json").read_text())
    assert record["sequence"]["sha256"] == hashlib.sha256(
        assembly["sequence_rna"].encode()).hexdigest()
    assert record["sequence"]["length"] == 1811


def test_annotation_carries_numeric_coding_boundaries(record):
    annotation = record["annotation"]
    assert annotation["cds_start"] == 44
    assert annotation["cds_end"] == 1697


def test_every_raw_artifact_path_exists_and_is_relative(record):
    for entry in record["scores"]:
        assert entry["raw_artifact_paths"]
        for relative in entry["raw_artifact_paths"]:
            assert not Path(relative).is_absolute()
            assert (ROOT / relative).exists()


def test_each_score_names_the_identity_that_produced_it(record):
    for entry in record["scores"]:
        for field in ("model_identity", "tool_identity"):
            evidence = [v for k, v in entry[field].items()
                        if isinstance(v, str) and v
                        and any(t in k for t in ("sha256", "version", "commit", "hash"))]
            assert evidence, f"{entry['component']}.{field} carries no identity token"


def test_poly_a_exclusion_is_recorded_in_the_translation_settings(record):
    """The frozen poly(A) decision must be visible in what was actually scored."""
    assert by_component(record)["ribonn_released_task"]["settings"]["poly_a_included"] is False


# --- the calibration arithmetic -------------------------------------------

def test_stability_value_reproduces_from_the_recorded_features(record):
    """The score must be recomputable from what the record itself carries."""
    entry = by_component(record)["strand_rnafold_calibration_v1"]
    arm = json.loads((CALIBRATION / "calibration_model.json").read_text())["component"]
    features = entry["settings"]["features"]
    expected = arm["intercept"] + sum(arm["coefficients"][f] * features[f]
                                      for f in arm["feature_order"])
    assert entry["value"] == pytest.approx(expected, abs=1e-12)


def test_the_calibration_formula_reproduces_its_own_training_predictions():
    """Guards the formula itself against the R fit it was taken from."""
    arm = json.loads((CALIBRATION / "calibration_model.json").read_text())["component"]
    rows = {r["name"]: r for r in csv.DictReader(
        (CALIBRATION / "features/train_features.csv").open())}
    checked = 0
    for row in csv.DictReader((CALIBRATION / "fit/r_predictions.csv").open()):
        if row["arm"] != "without_alo" or row["ncomp"] != "1" or row["name"] not in rows:
            continue
        features = rows[row["name"]]
        mine = arm["intercept"] + sum(arm["coefficients"][f] * float(features[f])
                                      for f in arm["feature_order"])
        assert mine == pytest.approx(float(row["prediction"]), abs=1e-9)
        checked += 1
        if checked >= 20:
            break
    assert checked >= 10


def test_stability_prediction_lands_inside_the_training_target_range(payload, record):
    """Not a validity check — only that the value is not wildly off-scale."""
    target = payload["calibration_training_domain"]["target_hours"]
    value = by_component(record)["strand_rnafold_calibration_v1"]["value"]
    assert target["min"] <= value <= target["max"]


def test_payload_states_what_it_does_not_establish(payload):
    text = " ".join(payload["no_claim"])
    assert "no stability, translation or expression benefit" in text
    assert "incommensurable" in text
