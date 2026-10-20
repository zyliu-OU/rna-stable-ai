"""Tests for the m1-pseudouridine feature-slope check.

This is the project's strongest evidence about the modification assumption: the
right nucleoside, 40,000 sequences per arm, and a denominator measured from
replicates rather than assumed. It is also a result that argues against the
project's own interests, which makes understating its weaknesses as damaging as
overstating its strength. The tests therefore pin both: that GC comes out
sequence-dependent on the recorded numbers, and that every weakness is carried
with it -- the missing m1-psi replicate, the borrowed denominator, the
mid-run preprocessing correction, and the within-arm standardisation that the
differing fraction counts force.
"""
import glob
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/m1pseudouridine_feature_slope_check_v1_2026-10-20.json"
RUNS = sorted(glob.glob(str(ROOT / "results/m1pseudouridine_slope_runs/*/summary.json")))
FEATURES = ("out_of_frame_uaug", "gc_fraction", "vienna_mfe")


@pytest.fixture(scope="module")
def protocol():
    return json.loads(PROTOCOL.read_text())


@pytest.fixture(scope="module")
def run():
    if not RUNS:
        pytest.skip("m1-pseudouridine slope check not run")
    return json.loads(Path(RUNS[-1]).read_text())


def test_the_protocol_was_declared_before_any_slope_was_computed(protocol, run):
    assert "DECLARED BEFORE ANY FEATURE-TO-RIBOSOME-LOAD RELATIONSHIP" in protocol["status"]
    assert "No slope, correlation or feature effect had been looked at" in protocol["status"]
    assert hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() == run["protocol_sha256"]


def test_the_three_features_are_the_declared_ones(protocol, run):
    declared = [f["name"] for f in protocol["features_declared_in_advance"]]
    assert declared == list(FEATURES)
    assert set(run["comparison"]) == set(FEATURES)
    for feature in protocol["features_declared_in_advance"]:
        assert feature["definition"] and feature["why"] and feature["statistic"]


def test_every_source_file_hash_was_verified(run):
    assert run["all_file_hashes_verified"] is True
    assert len(run["conventions_detected"]) == 4


def test_the_right_nucleoside_was_tested(protocol, run):
    assert "N1-methylpseudouridine" in run["modification"]
    assert "the nucleoside this project's molecules carry" in run["modification"]
    supersede = protocol["why_this_supersedes_the_earlier_check"]
    assert "pseudouridine_effect_check_v1" in supersede["earlier"]
    assert "different nucleoside" in supersede["earlier_limitation"]
    assert "N1-METHYLPSEUDOURIDINE" in supersede["what_changes_here"]
    assert "stands as what it was" in supersede["what_does_not_change"]


def test_the_different_library_arm_was_excluded_with_its_reason(run):
    excluded = run["arms_excluded"]
    assert "m1pseudo_2" in excluded
    assert excluded["m1pseudo_2"]["modal_length"] == 54
    assert excluded["m1pseudo_2"]["usable"] is False
    assert excluded["m1pseudo_2"]["suffix_rate"] < 0.5
    assert "m1pseudo_2" not in run["slopes_per_arm"]


def test_the_borrowed_denominator_is_flagged_on_every_feature(run):
    """The single biggest weakness; it must not be findable only in prose."""
    for feature in FEATURES:
        assert run["comparison"][feature][
            "denominator_borrowed_from_unmodified_replicates"] is True, feature
    correction = run["preprocessing_correction"]
    assert "NO replicate arm" in correction["consequence"]
    assert "borrowed from the unmodified" in correction["consequence"]
    assert "weakens the test" in correction["consequence"]


def test_the_preprocessing_correction_is_disclosed(run):
    correction = run["preprocessing_correction"]
    assert "the 9-nt ATGGGCGAA suffix is trimmed from the m1-pseudouridine records" in \
        correction["what_was_declared"]
    assert "PER-FILE export convention" in correction["what_is_actually_true"]
    assert "unmod_2 carries it too" in correction["what_is_actually_true"]
    assert correction["justification"].startswith("mechanical")
    assert correction["effect_on_features_or_decision_rule"].startswith("none")


def test_the_suffix_convention_was_detected_per_file_not_per_condition(run):
    conventions = run["conventions_detected"]
    assert conventions["unmod_1"]["trim_suffix"] is False
    assert conventions["unmod_2"]["trim_suffix"] is True, \
        "an unmodified arm carries the suffix; a per-condition rule would be wrong"
    assert conventions["m1pseudo_1"]["trim_suffix"] is True
    assert conventions["m1pseudo_2"]["trim_suffix"] is False


def test_each_verdict_follows_from_its_ratio(protocol, run):
    rule = protocol["declared_criteria"]["decision_rule"]
    for feature in FEATURES:
        block = run["comparison"][feature]
        assert block["decision_rule"] == rule
        ratio, verdict = block["ratio"], block["verdict"]
        if ratio <= 1.0:
            assert verdict == "consistent_with_constant", feature
        elif ratio <= 2.0:
            assert verdict == "ambiguous", feature
        else:
            assert verdict == "sequence_dependent", feature


def test_the_ratio_is_between_over_within(run):
    for feature in FEATURES:
        block = run["comparison"][feature]
        assert block["ratio"] == pytest.approx(
            block["between_modification_difference"]
            / block["within_modification_replicate_difference"])


def test_gc_content_comes_out_sequence_dependent(run):
    """The finding, pinned so a later edit cannot soften it quietly."""
    block = run["comparison"]["gc_fraction"]
    assert block["verdict"] == "sequence_dependent"
    assert block["ratio"] > 2.0
    # The unmodified replicates must agree far better than the conditions differ.
    assert block["within_modification_replicate_difference"] < 0.2
    assert block["between_modification_difference"] > 0.5
    # Magnitude change, not a sign flip: both arms still lose load with GC.
    assert block["unmodified_mean"] < 0 and block["m1pseudo_mean"] < 0
    assert block["sign_changed"] is False
    assert abs(block["unmodified_mean"]) > 2 * abs(block["m1pseudo_mean"])


def test_the_other_two_features_are_stable_within_noise(run):
    for feature in ("out_of_frame_uaug", "vienna_mfe"):
        assert run["comparison"][feature]["verdict"] in (
            "consistent_with_constant", "ambiguous"), feature


def test_the_uaug_effect_is_negative_in_every_arm(run):
    """A sanity check on the assay: an out-of-frame uAUG must cost ribosome load."""
    for arm, slopes in run["slopes_per_arm"].items():
        assert slopes["out_of_frame_uaug"]["slope"] < 0, arm


def test_the_adverse_conclusion_is_recorded(run):
    assert run["supports_the_project_ranking_assumption"] is False
    assert run["verdicts"]["gc_fraction"] == "sequence_dependent"


def test_the_libraries_are_drawn_from_the_same_distribution(run):
    """Without this, a between-library slope comparison would be confounded."""
    check = run["library_distribution_check"]
    assert check["same_distribution"] is True
    assert check["gc_mean_difference_between_conditions"] < 0.01
    assert "share no sequences" in check["note"]


def test_the_arms_are_equally_sized_and_standardised_within_arm(protocol, run):
    sizes = {arm: data["subsampled"] for arm, data in run["arms"].items()}
    assert len(set(sizes.values())) == 1, "unequal arms would make slope precision differ"
    assert set(sizes.values()) == {protocol["preprocessing"]["subsample_size"]}
    assert "z-scored WITHIN each arm" in protocol["preprocessing"][
        "ribosome_load_standardisation"]
    text = " ".join(run["no_claim"])
    assert "14 polysome fractions and the m1psi library into 13" in text
    assert "Only within-arm relationships are compared" in text


def test_the_depth_filter_is_a_within_arm_quantile(protocol, run):
    assert "MEDIAN read depth" in protocol["preprocessing"]["depth_filter"]
    assert "would bias one arm" in protocol["preprocessing"]["depth_filter"]
    for arm, data in run["arms"].items():
        assert data["rows_after_depth_filter"] < data["rows_usable"], arm
        assert data["subsampled"] <= data["rows_after_depth_filter"], arm


def test_the_limits_are_carried(protocol, run):
    assert run["what_this_cannot_establish"] == protocol["what_this_cannot_establish"]
    text = " ".join(run["what_this_cannot_establish"])
    assert "1811 nt" in text
    assert "not a complete account" in " ".join(run["no_claim"]) or \
        "not be complete" in text or "not being complete" in text
    assert "stability side" in text


def test_the_source_is_not_redistributed(protocol, run):
    assert "Not republished" in protocol["source"]["redistribution"]
    assert protocol["source"]["accession"] == "GSE114002"
    # No UTR sequence may appear in the published artifact.
    assert "utr" not in json.dumps(run["arms"]).lower()
