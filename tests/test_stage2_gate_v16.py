"""Tests for gate v16, the first gate version to EXTEND the target set.

v16 does two things that need pinning for different reasons.

It writes the three prohibitions handoff V11 specified and left unwritten when
that session ended early. Those are adverse findings, so the risk is that they
quietly weaken later: the tests below pin their measured basis, not just their
presence.

It also reinstates the cell-free arm that v2 retired on 2026-10-19. Extending a
target set is the easiest way to smuggle in a claim, so the tests pin that the
arm is declared but NOT defined, that its switch is closed, that the goal was
never in-cell stability in this chain, and that nothing else moved: no switch,
no requirement, no withdrawal.
"""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
V15 = ROOT / "configs/stage2_to_stage3_gate_v15_2026-10-20.json"
V16 = ROOT / "configs/stage2_to_stage3_gate_v16_2026-10-21.json"
ASSAY_V3 = ROOT / "configs/assay_definition_v3_2026-10-19.json"
ASSAY_V4 = ROOT / "configs/assay_definition_v4_2026-10-21.json"


@pytest.fixture(scope="module")
def v16():
    return json.loads(V16.read_text())


@pytest.fixture(scope="module")
def v15():
    return json.loads(V15.read_text())


@pytest.fixture(scope="module")
def assay():
    return json.loads(ASSAY_V4.read_text())


def test_v15_is_retained_unedited_at_its_recorded_hash(v16):
    assert hashlib.sha256(V15.read_bytes()).hexdigest() == v16["supersedes"]["sha256"]
    assert v16["supersedes"]["status"] == "frozen and unedited"


def test_assay_v3_is_retained_unedited_at_its_recorded_hash(assay):
    recorded = assay["supersedes"]["v3"]["sha256"]
    assert hashlib.sha256(ASSAY_V3.read_bytes()).hexdigest() == recorded


def test_nothing_was_reopened_or_rereatified(v15, v16):
    assert v16["requirements_before_stage3"] == v15["requirements_before_stage3"]
    assert v16["requirements_satisfied"] == v15["requirements_satisfied"] == 6
    assert v16["switches_unchanged_from_v6"] == v15["switches_unchanged_from_v6"]
    assert "No switch moves" in v16["amendment_record"]["what_changed"]


def test_no_prohibition_was_withdrawn(v16):
    """v15 withdrew one, with cause. v16 must not inherit that as a habit."""
    assert v16["prohibition_withdrawn_here"] is None
    assert "none withdrawn" in v16["new_prohibition_added_here"]


def test_the_goal_is_expression_and_the_modeled_axis_is_named_separately(v15, v16):
    target = v16["stage3_target"]
    assert target["goal"] == "protein_expression"
    assert target["currently_modeled_axis"] == "in_cell_mrna_stability"
    # The chain never said the GOAL was stability; v15 is the witness.
    assert v15["stage3_target"] == "transfected_cell_expression"
    assert target["prior_value_in_v2_through_v15"] == "transfected_cell_expression"


def test_the_transfected_cell_arm_is_not_removed_by_the_reinstatement(v16):
    arms = v16["stage3_target"]["arms"]
    assert "transfected_cell_expression" in arms
    assert "cell_free_ivtt_expression" in arms
    assert "does not remove" in v16["stage3_target"]["what_this_changes"]


def test_the_cell_free_arm_is_declared_but_not_defined(v16, assay):
    arm = v16["cell_free_arm_status"]
    assert arm["declared"] is True
    assert arm["defined"] is False
    assert arm["scoring_permitted"] is False
    assert v16["switch_added_here"]["cell_free_scoring_enabled"] is False
    assert assay["cell_free_scoring_enabled"] is False
    assert assay["cell_free_arm"]["scoring_permitted"] is False
    # An undefined arm must carry its open questions, not an empty list.
    assert len(assay["cell_free_arm"]["blocking_inputs"]) >= 5


def test_the_reinstatement_does_not_erase_why_cell_free_was_retired(assay):
    decision = assay["decisions_recorded_2026_10_21"]["cell_free_expression_reinstated"]
    assert "frozen and unedited" in decision["effect"]
    assert "lab" in decision["why_it_was_retired_in_the_first_place"]


def test_expression_benefit_is_still_not_established(v16, assay):
    assert v16["switches_unchanged_from_v6"]["expression_benefit_established"] is False
    assert assay["expression_benefit_established"] is False
    assert any("establishes no expression benefit" in claim
               for claim in v16["no_claim_permitted"])


def test_the_five_prohibitions_are_present_with_their_measured_basis(v16):
    added = {entry["id"]: entry for entry in v16["prohibitions_added_here"]}
    assert len(added) == 5

    ribonn = added["v16_1_ribonn_not_a_stability_feature"]["basis"]
    assert "+0.4916" in ribonn and "-0.5551" in ribonn   # the sign reversal
    assert "+0.0879" in ribonn                            # the balanced ceiling

    screen = added["v16_2_no_screened_feature_is_adopted"]["basis"]
    assert "37 features" in screen and "105 training records" in screen

    resolution = added["v16_3_resolution_is_unchanged"]["basis"]
    assert "0.500" in resolution and "0.523" in resolution

    transfer = added["v16_4_no_cross_system_transfer"]["basis"]
    assert "+0.0545" in transfer

    proxy = added["v16_5_stability_is_not_a_validated_expression_proxy"]["basis"]
    assert "13-fold" in proxy and "CHANGED SIGN" in proxy


def test_ribonn_stays_a_separate_axis_rather_than_being_banned_outright(v16):
    """The prohibition is about wiring it into stability, not about using it."""
    added = {entry["id"]: entry for entry in v16["prohibitions_added_here"]}
    permitted = added["v16_1_ribonn_not_a_stability_feature"]["what_is_still_permitted"]
    assert "SEPARATE" in permitted
    assert "Pareto" in permitted


def test_the_gate_and_the_assay_definition_point_at_each_other(v16, assay):
    assert v16["assay_definition"] == "configs/assay_definition_v4_2026-10-21.json"
    assert assay["gate"] == "configs/stage2_to_stage3_gate_v16_2026-10-21.json"


def test_the_stability_to_expression_gap_is_stated_not_implied(v16):
    added = {entry["id"]: entry for entry in v16["prohibitions_added_here"]}
    why = added["v16_5_stability_is_not_a_validated_expression_proxy"]["why_it_matters_here"]
    assert "goal" in why and "modeled axis" in why
