"""Unit tests for versioned score-record provenance binding."""
import json
from pathlib import Path

import pytest

from rnastable.score_records import (
    build_record, coding_annotation, coverage, exclusion_entry, score_entry,
    sequence_identity,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT/"configs/score_record_schema_v1_2026-10-19.json"
COMPONENTS = ("strand_reference_replay", "strand_rnafold_calibration_v1", "ribonn_released_task")


def test_schema_forbids_composites_and_floors_and_scoring():
    schema = json.loads(SCHEMA.read_text())
    assert schema["composite_prohibition"]["composite_score_permitted"] is False
    assert schema["floor_selection"]["stability_floor"]["value"] is None
    assert schema["floor_selection"]["translation_floor"]["value"] is None
    assert schema["floor_selection"]["stability_floor"]["status"] == "not_selected"
    assert schema["floor_selection"]["translation_floor"]["status"] == "not_selected"
    assert schema["new_sequence_scoring_enabled"] is False
    assert schema["expression_candidate_design_enabled"] is False
    assert schema["stage3_ready"] is False


def test_schema_records_task_selection_as_blocked():
    schema = json.loads(SCHEMA.read_text())
    assert schema["ribonn_task_selection"]["status"] == "blocked"
    assert len(schema["ribonn_task_selection"]["blockers_recorded_2026-10-19"]) >= 3
    assert "demonstration_only_not_assay_selected" in schema["ribonn_task_selection"]["interim_rule"]


def test_sequence_identity_hashes_canonical_rna():
    identity = sequence_identity("ACGU")
    assert identity["length"] == 4 and identity["alphabet"] == "ACGU"
    assert identity["sha256"] == sequence_identity("ACGU")["sha256"]
    assert identity["sha256"] != sequence_identity("ACGUA")["sha256"]


@pytest.mark.parametrize("bad", ["", "ACGT", "acgu", "ACGUN"])
def test_sequence_identity_rejects_noncanonical(bad):
    with pytest.raises(ValueError):
        sequence_identity(bad)


def test_numeric_annotation_derives_segment_sizes():
    annotation = coding_annotation(100, 10, 70)
    assert annotation["numeric_boundaries_available"] is True
    assert (annotation["utr5_size"], annotation["cds_size"], annotation["utr3_size"]) == (10, 60, 30)


@pytest.mark.parametrize("start,end", [(-1, 50), (50, 50), (60, 50), (0, 101)])
def test_numeric_annotation_rejects_invalid_bounds(start, end):
    with pytest.raises(ValueError):
        coding_annotation(100, start, end)


def test_numeric_annotation_rejects_nonintegers():
    with pytest.raises(ValueError):
        coding_annotation(100, 10.0, 70)


def test_absent_annotation_requires_a_reason():
    with pytest.raises(ValueError):
        coding_annotation(100)
    annotation = coding_annotation(100, absent_reason="descriptions only")
    assert annotation["numeric_boundaries_available"] is False
    assert annotation["annotation_absent_reason"] == "descriptions only"


def valid_entry(**overrides):
    fields = {"component": "strand_reference_replay",
              "score_name": "predicted_in_solution_half_life",
              "value": 1.25, "units": "hours",
              "target_scale": "released STRAND in-solution half-life",
              "model_identity": {"model_name": "m", "reference_model_sha256": "a"*64},
              "tool_identity": {"engine": "LinearPartition", "engine_version": "unknown"},
              "settings": {"feature_source": "released_LinearPartition_features"},
              "raw_artifact_paths": ["configs/score_record_schema_v1_2026-10-19.json"],
              "run": "results/x", "interpretation": "replay only",
              "independent_validation": False}
    fields.update(overrides)
    return fields


def test_score_entry_accepts_a_fully_bound_entry():
    entry = score_entry(ROOT, **valid_entry())
    assert entry["units"] == "hours"
    assert entry["independent_validation"] is False


def test_score_entry_requires_every_bound_field():
    fields = valid_entry()
    del fields["model_identity"]
    with pytest.raises(ValueError, match="missing bound fields"):
        score_entry(ROOT, **fields)


def test_score_entry_rejects_unbound_extra_fields():
    with pytest.raises(ValueError, match="Unbound"):
        score_entry(ROOT, **valid_entry(composite_rank=1))


@pytest.mark.parametrize("units", ["", "unknown", "Arbitrary", "n/a", "none"])
def test_score_entry_rejects_vague_units(units):
    with pytest.raises(ValueError, match="units"):
        score_entry(ROOT, **valid_entry(units=units))


def test_score_entry_rejects_empty_target_scale():
    with pytest.raises(ValueError, match="target scale"):
        score_entry(ROOT, **valid_entry(target_scale="   "))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), "1.0", None])
def test_score_entry_rejects_nonnumeric_values(value):
    with pytest.raises(ValueError, match="finite number"):
        score_entry(ROOT, **valid_entry(value=value))


def test_score_entry_requires_identity_evidence():
    with pytest.raises(ValueError, match="model_identity"):
        score_entry(ROOT, **valid_entry(model_identity={"model_name": "m"}))
    with pytest.raises(ValueError, match="model_identity"):
        score_entry(ROOT, **valid_entry(model_identity={}))
    with pytest.raises(ValueError, match="tool_identity"):
        score_entry(ROOT, **valid_entry(tool_identity={"engine": "x"}))


def test_score_entry_requires_existing_relative_artifact_paths():
    with pytest.raises(ValueError, match="At least one raw artifact"):
        score_entry(ROOT, **valid_entry(raw_artifact_paths=[]))
    with pytest.raises(ValueError, match="does not exist"):
        score_entry(ROOT, **valid_entry(raw_artifact_paths=["configs/not_a_real_file.json"]))
    with pytest.raises(ValueError, match="workspace-relative"):
        score_entry(ROOT, **valid_entry(raw_artifact_paths=["/etc/hostname"]))


def test_score_entry_refuses_claimed_independent_validation():
    with pytest.raises(ValueError, match="independent validation"):
        score_entry(ROOT, **valid_entry(independent_validation=True))


def test_exclusion_entry_requires_exact_fields_and_a_reason():
    entry = exclusion_entry(component="ribonn_released_task", reason="no boundaries", run="results/x")
    assert entry["reason"] == "no boundaries"
    with pytest.raises(ValueError):
        exclusion_entry(component="c", reason="r")
    with pytest.raises(ValueError, match="explicit reason"):
        exclusion_entry(component="c", reason="  ", run="results/x")


def built_record():
    identity = sequence_identity("ACGUACGUAC")
    annotation = coding_annotation(10, 1, 7)
    scores = [score_entry(ROOT, **valid_entry())]
    exclusions = [exclusion_entry(component=c, reason="not scored", run="results/x")
                  for c in COMPONENTS[1:]]
    return build_record(identity, annotation, scores, exclusions, COMPONENTS)


def test_build_record_emits_no_composite():
    record = built_record()
    assert record["composite_score"] is None
    assert record["composite_blocked_reason"]
    assert record["independent_validation"] is False
    assert record["record_id"] == record["sequence"]["sha256"]


def test_build_record_requires_every_component_scored_or_excluded():
    identity = sequence_identity("ACGUACGUAC")
    annotation = coding_annotation(10, 1, 7)
    with pytest.raises(ValueError, match="missing"):
        build_record(identity, annotation, [score_entry(ROOT, **valid_entry())], [], COMPONENTS)


def test_build_record_rejects_a_component_appearing_twice():
    identity = sequence_identity("ACGUACGUAC")
    annotation = coding_annotation(10, 1, 7)
    scores = [score_entry(ROOT, **valid_entry())]
    exclusions = [exclusion_entry(component=c, reason="not scored", run="results/x")
                  for c in COMPONENTS]
    with pytest.raises(ValueError, match="once per record"):
        build_record(identity, annotation, scores, exclusions, COMPONENTS)


def test_coverage_reports_the_joint_gap():
    stability_only = built_record()
    translation = dict(build_record(
        sequence_identity("ACGUACGUACGU"), coding_annotation(12, 1, 7),
        [score_entry(ROOT, **valid_entry(component="ribonn_released_task",
                                         score_name="predicted_TE_HEK293T",
                                         units="released RiboNN task scale",
                                         target_scale="released model task scale",
                                         model_identity={"model_name": "r", "source_commit": "c"*40},
                                         tool_identity={"framework": "PyTorch",
                                                        "framework_version": "1.13.1"}))],
        [exclusion_entry(component=c, reason="not applicable", run="results/x")
         for c in COMPONENTS[:2]], COMPONENTS))
    counts = coverage([stability_only, translation], list(COMPONENTS))
    assert counts["records"] == 2
    assert counts["records_with_stability_score"] == 1
    assert counts["records_with_translation_score"] == 1
    assert counts["records_with_both_sides"] == 0
    assert counts["joint_scoring_available"] is False
    assert counts["scored_per_component"]["ribonn_released_task"] == 1
    assert counts["excluded_per_component"]["ribonn_released_task"] == 1


def test_coverage_detects_a_genuine_both_sides_record():
    record = build_record(
        sequence_identity("ACGUACGUAC"), coding_annotation(10, 1, 7),
        [score_entry(ROOT, **valid_entry()),
         score_entry(ROOT, **valid_entry(component="ribonn_released_task",
                                         units="released RiboNN task scale",
                                         model_identity={"model_name": "r", "source_commit": "c"*40},
                                         tool_identity={"framework": "PyTorch",
                                                        "framework_version": "1.13.1"}))],
        [exclusion_entry(component="strand_rnafold_calibration_v1", reason="not scored",
                         run="results/x")], COMPONENTS)
    counts = coverage([record], list(COMPONENTS))
    assert counts["records_with_both_sides"] == 1
    assert counts["joint_scoring_available"] is True
