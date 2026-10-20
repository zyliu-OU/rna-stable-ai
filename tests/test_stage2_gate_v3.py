"""Tests for the Stage 2 gate v3 amendment.

Requirement 3 was satisfied by accepting a documented limitation rather than by
improving coverage. The tests below pin the things that make that an honest
resolution rather than a quiet relaxation: that the claim is actually narrowed,
that the other five requirements are untouched, that the superseded gate stays
frozen, and that the record says family expansion was available and not taken.
"""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "configs/stage2_to_stage3_gate_v2_2026-10-19.json"
V3 = ROOT / "configs/stage2_to_stage3_gate_v3_2026-10-19.json"


@pytest.fixture(scope="module")
def v3():
    return json.loads(V3.read_text())


@pytest.fixture(scope="module")
def v2():
    return json.loads(V2.read_text())


def test_v2_is_retained_unedited_at_its_recorded_hash(v3):
    """Superseding must not mutate the prior gate that frozen runs reference."""
    recorded = v3["supersedes"]
    assert recorded["file"].endswith("stage2_to_stage3_gate_v2_2026-10-19.json")
    assert hashlib.sha256(V2.read_bytes()).hexdigest() == recorded["sha256"]


def test_only_requirement_three_changed(v2, v3):
    assert v3["requirements_before_stage3"] == v2["requirements_before_stage3"]
    assert v3["stage3_target"] == v2["stage3_target"]
    assert v3["active_length_nt"] == v2["active_length_nt"]


def test_exactly_one_requirement_is_satisfied(v3):
    assert v3["requirements_satisfied"] == 1
    detail = v3["requirements_satisfied_detail"]
    assert len(detail["satisfied"]) == 1
    assert len(detail["not_satisfied"]) == 5
    assert "2000_2999" in detail["satisfied"][0]


def test_the_resolution_states_it_did_not_improve_coverage(v3):
    """The honest part: the band still rests on one record."""
    resolution = v3["requirement_3_resolution"]
    assert resolution["resolution"] == "accepted_as_documented_limitation"
    assert "not_by_improving_coverage" in resolution["status"]
    assert "exactly 1 record" in resolution["what_the_limitation_is"]
    assert "no dispersion" in resolution["what_the_limitation_is"]


def test_the_claim_is_actually_narrowed(v3):
    """Accepting a limitation only means something if a claim shrinks."""
    claimed = v3["claimed_length_range"]
    assert claimed["claimable_without_caveat"]["maximum_exclusive"] == 2000
    assert claimed["claimable_only_with_the_recorded_limitation"] == {
        "minimum_inclusive": 2000, "maximum_exclusive": 3000}
    assert "MUST NOT be claimed" in v3["requirement_3_resolution"]["binding_consequence"]


def test_active_scope_is_unchanged_only_the_claim_moved(v3):
    """The band stays in scope for inference; it leaves unqualified claims."""
    assert v3["active_length_nt"]["maximum_exclusive"] == 3000
    assert v3["claimed_length_range"]["active_length_nt_unchanged"]["maximum_exclusive"] == 3000


def test_the_record_says_expansion_was_available_and_not_taken(v3):
    """A later reader must not mistake a choice for an impossibility."""
    available = v3["requirement_3_resolution"]["what_was_available_and_not_taken"]
    assert available["family_level_expansion"].startswith("available")
    assert "56 eligible records" in available["family_level_expansion"]
    assert available["clan_level_expansion"].startswith("NOT available")
    assert "by choice" in available["note"]


def test_satisfying_one_requirement_does_not_open_the_gate(v3):
    assert v3["stage3_ready"] is False
    assert v3["stage3_development_started"] is False
    assert v3["new_sequence_scoring_enabled"] is False
    assert v3["expression_candidate_design_enabled"] is False
    assert v3["expression_benefit_established"] is False


def test_the_record_cautions_against_reading_this_as_progress(v3):
    caution = v3["requirements_satisfied_detail"]["caution"]
    assert "not progress toward structure accuracy" in caution


def test_every_cited_evidence_path_exists(v3):
    for relative in v3["requirement_3_resolution"]["evidence"]:
        assert (ROOT / relative).exists(), relative


def test_the_prior_target_amendment_is_preserved(v3):
    """v2's amendment must survive into v3 rather than being dropped."""
    assert v3["stage3_target"] == "transfected_cell_expression"
    assert "transfected" in v3["amendment_record"]["prior_amendment"]
