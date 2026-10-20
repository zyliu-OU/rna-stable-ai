"""Tests for gate v6, which opens the two campaign switches.

v6 is the version that permits scoring new sequences and selecting candidates,
before any experimental data exists. That makes it the version most likely to be
read later as evidence that the pipeline works, so these tests pin the opposite:
that v5's requirement basis is carried forward unchanged, that both accepted
limitations survive, that the span policy is still unresolved and the blinded set
still unspent, and that the prohibitions are explicit.
"""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
V5 = ROOT / "configs/stage2_to_stage3_gate_v5_2026-10-20.json"
V6 = ROOT / "configs/stage2_to_stage3_gate_v6_2026-10-20.json"


@pytest.fixture(scope="module")
def v6():
    return json.loads(V6.read_text())


@pytest.fixture(scope="module")
def v5():
    return json.loads(V5.read_text())


def test_v5_is_retained_unedited_at_its_recorded_hash(v6):
    assert hashlib.sha256(V5.read_bytes()).hexdigest() == v6["supersedes"]["sha256"]


def test_the_requirements_are_carried_forward_verbatim(v5, v6):
    assert v6["requirements_before_stage3"] == v5["requirements_before_stage3"]
    assert v6["requirements_satisfied"] == v5["requirements_satisfied"] == 6


def test_the_two_accepted_limitations_survive_as_accepted_limitations(v6):
    basis = v6["requirements_satisfied_basis_unchanged_from_v5"]
    assert basis["1"] == "accepted_as_documented_limitation"
    assert basis["3"] == "accepted_as_documented_limitation"
    assert "re-opens no requirement and re-ratifies none" in basis["note"]


def test_both_switches_are_recorded_as_opened_with_their_previous_value(v6):
    for name in ("new_sequence_scoring_enabled", "expression_candidate_design_enabled"):
        switch = v6["switches_opened_here"][name]
        assert switch["now"] is True, name
        assert switch["was"] is False, name
        assert switch["why"], name
        assert switch["binding_conditions"], name


def test_the_span_policy_is_still_unresolved_and_the_blinded_set_unspent(v6):
    conditions = " ".join(
        v6["switches_opened_here"]["new_sequence_scoring_enabled"]["binding_conditions"])
    assert "remains UNRESOLVED" in conditions
    assert "PROVISIONAL convention adopted for comparability, not a resolution" in conditions
    assert "blinded 85-record evaluation set remains UNSPENT" in conditions
    assert "MUST NOT be spent to unblock this workflow" in conditions


def test_predicted_values_are_bound_as_provisional(v6):
    conditions = " ".join(
        v6["switches_opened_here"]["new_sequence_scoring_enabled"]["binding_conditions"])
    assert "PROVISIONAL and UNVALIDATED" in conditions
    assert "No predicted half-life or translational-efficiency value may be reported as " \
           "a measurement, a calibrated quantity, or a demonstrated benefit" in conditions


def test_a_panel_is_bound_as_an_illustration_not_a_recommendation(v6):
    conditions = " ".join(
        v6["switches_opened_here"]["expression_candidate_design_enabled"]["binding_conditions"])
    assert "ILLUSTRATION OF THE PIPELINE" in conditions
    assert "not a recommendation to synthesise or assay anything" in conditions
    assert "panel size is UNKNOWN" in conditions
    assert "No composite score may be emitted" in conditions


def test_the_reference_hash_gate_is_explicitly_not_relaxed(v6):
    conditions = " ".join(
        v6["switches_opened_here"]["expression_candidate_design_enabled"]["binding_conditions"])
    assert "reference hash gate is NOT relaxed" in conditions
    assert "assemble_variant" in conditions


def test_the_switches_that_stay_closed_stay_closed(v6):
    for key, value in v6["switches_still_closed"].items():
        assert value is False, key
    assert "expression_benefit_established" in v6["switches_still_closed"]
    assert "independent_biological_validation" in v6["switches_still_closed"]


def test_the_decision_is_labelled_as_engineering_not_evidence(v6):
    record = v6["amendment_record"]
    assert "BEFORE the data that would validate it exists" in record["what_this_decision_is"]
    assert "not a finding that the pipeline's outputs are correct" in \
        record["what_this_decision_is_not"]
    assert "does not lower any evidential standard" in record["what_this_decision_is_not"]


def test_the_absence_of_experimental_data_is_recorded_first(v6):
    absent = v6["what_remains_absent"]
    assert "Any experimental measurement" in absent[0]
    assert "user has stated so" in absent[0]
    joined = " ".join(absent)
    assert "coefficients of variation" in joined
    assert "reference point on the real objective scales" in joined


def test_the_prohibitions_cover_the_predictable_misreadings(v6):
    text = " ".join(v6["what_must_not_be_claimed"])
    assert "is a measurement" in text
    assert "recommended for synthesis" in text
    assert "resolved the base-pair span policy" in text
    assert "unverified, not merely unvalidated" in text


def test_it_says_how_it_would_be_verified_later(v6):
    how = " ".join(v6["how_to_verify_this_later"])
    assert "measured CVs" in how
    assert "whichever way it comes out" in how
    assert "Supersede this gate" in how


def test_the_chain_names_every_prior_version(v6):
    chain = v6["supersedes"]["chain"]
    for version in ("v5", "v4", "v3", "v2"):
        assert version in chain
    assert "all remain frozen" in chain
    assert len(v6["amendment_record"]["prior_amendments"]) == 4
