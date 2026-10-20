"""Tests for the native-control Stage 2 validation.

Gate v4 amended requirement 4 to concern the accuracy of LinearFold and
ViennaRNA rather than the retired learned model. These tests pin the properties
that make the resulting artifact usable as gate evidence: that it reports by
band, family AND clan, that it performs no inference, that the separation
argument is correctly limited to thermodynamic folders, and that the baseline
gaps are stated rather than implied.
"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "results/native_control_validation/native_control_validation.json"

pytestmark = pytest.mark.skipif(not ARTIFACT.exists(), reason="validation not built")


@pytest.fixture(scope="module")
def payload():
    return json.loads(ARTIFACT.read_text())


def test_both_native_controls_are_reported(payload):
    assert set(payload["methods"]) == {"LinearFold", "ViennaRNA"}
    for method in payload["methods"]:
        assert method in payload["cohorts"]


def test_no_inference_and_no_fitting_occurred(payload):
    """Gate evidence must not be produced by running the model it evaluates."""
    assert payload["no_new_inference"] is True
    assert payload["model_fitted"] is False


def test_accuracy_is_reported_by_band_family_and_clan(payload):
    """Requirement 2 asks for band and family; the gate's concern is clan too."""
    for method in payload["methods"]:
        cohort = payload["cohorts"][method]["long_rfam_consensus"]
        assert cohort["families"] >= 3
        assert cohort["clans"] >= 2, "clan mapping must resolve, not fall back to unmapped"
        assert set(cohort["bands"]) == {"1_999", "1000_1999", "2000_2999"}
        assert cohort["family_means"] and cohort["clan_means"]


def test_family_and_clan_means_are_reported_beside_the_record_mean(payload):
    """A record mean is dominated by the largest family on cohorts this small."""
    for method in payload["methods"]:
        cohort = payload["cohorts"][method]["long_rfam_consensus"]
        for key in ("mean_record_pair_f1", "mean_family_pair_f1", "mean_clan_pair_f1"):
            assert isinstance(cohort[key], float)


def test_three_cohorts_are_covered(payload):
    for method in payload["methods"]:
        cohorts = payload["cohorts"][method]
        assert set(cohorts) == {"long_rfam_consensus", "short_bprna_five_clan",
                                "structure_derived"}
        assert all(value is not None for value in cohorts.values())


def test_the_2000_2999_band_still_holds_one_record(payload):
    """The accepted limitation must remain visible in the evidence itself."""
    for method in payload["methods"]:
        band = payload["cohorts"][method]["long_rfam_consensus"]["bands"]["2000_2999"]
        assert band["n"] == 1


def test_separation_argument_is_limited_to_the_native_controls(payload):
    """It must not be readable as a general exemption for learned components."""
    argument = payload["separation_argument"]
    assert "no training set" in argument["reason"]
    assert "ONLY to the native controls" in argument["scope_limit"]
    assert "would not apply to any" in argument["scope_limit"]
    assert "not a claim that the cohorts are" in argument["scope_limit"]


def test_baseline_gaps_name_the_specific_weaknesses(payload):
    gaps = " ".join(payload["baseline_gaps"])
    assert "computational Rfam consensus" in gaps
    assert "6 records across 3 families and 2 clans" in gaps
    assert "no dispersion" in gaps
    assert "broad_validation_gate_satisfied false" in gaps


def test_the_claimed_length_range_limitation_is_carried(payload):
    claimed = payload["claimed_length_range"]
    assert claimed["claimable_without_caveat"]["maximum_exclusive"] == 2000


def test_it_does_not_assert_that_a_requirement_is_satisfied(payload):
    """Satisfying a requirement is a gate-review judgement, not a script output."""
    text = " ".join(payload["no_claim"])
    assert "gate-review judgement, not an output of this script" in text
    assert "not biological validation" in text
    assert "satisfied" not in json.dumps(payload.get("cohorts", {}))


def test_structure_derived_cohort_matches_its_source_run(payload):
    source = json.loads((ROOT / "results/raw_structure_feasibility_runs"
                         / "20261015T025936.192087Z/summary.json").read_text())
    expected = {a["method"]: a["mean_pair_f1"] for a in source["aggregates"]}
    for method in payload["methods"]:
        assert payload["cohorts"][method]["structure_derived"]["mean_pair_f1"] == pytest.approx(
            expected[method])


def test_native_controls_outperform_the_retired_model_on_every_cohort(payload):
    """The premise of the retirement, re-checked against this artifact."""
    retired = {"long_rfam_consensus": 0.2965, "structure_derived": 0.3255}
    for method in payload["methods"]:
        for cohort, learned in retired.items():
            value = payload["cohorts"][method][cohort]
            actual = value.get("mean_record_pair_f1") or value.get("mean_pair_f1")
            assert actual > learned
