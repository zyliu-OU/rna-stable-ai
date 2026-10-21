"""Tests for gate v15, the first gate version to withdraw a prohibition.

Every gate from v8 to v14 only ever added prohibitions, and the suite asserted
the set grows. v15 breaks that pattern deliberately, because one v14 prohibition
was derived from this project's own measurement error and is factually wrong.

That makes v15 the easiest gate to abuse: "a prohibition can be withdrawn" is one
bad precedent away from "inconvenient findings can be withdrawn". These tests pin
that exactly one prohibition left, that it left with a recorded reason, that it
was replaced by a correct narrower one, and that the adverse conclusion it
carried still stands in corrected form.
"""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
V14 = ROOT / "configs/stage2_to_stage3_gate_v14_2026-10-20.json"
V15 = ROOT / "configs/stage2_to_stage3_gate_v15_2026-10-20.json"


@pytest.fixture(scope="module")
def v15():
    return json.loads(V15.read_text())


@pytest.fixture(scope="module")
def v14():
    return json.loads(V14.read_text())


def test_v14_is_retained_unedited_at_its_recorded_hash(v15):
    assert hashlib.sha256(V14.read_bytes()).hexdigest() == v15["supersedes"]["sha256"]
    assert v15["supersedes"]["status"] == "frozen and unedited"
    assert "remains frozen and unedited" in v15["correction_to_v14"]["status"]


def test_nothing_was_reopened_or_rereatified(v14, v15):
    assert v15["requirements_before_stage3"] == v14["requirements_before_stage3"]
    assert v15["requirements_satisfied"] == v14["requirements_satisfied"] == 6
    assert v15["switches_unchanged_from_v6"] == v14["switches_unchanged_from_v6"]
    assert "No switch moves" in v15["amendment_record"]["what_changed"]


def test_exactly_one_prohibition_was_withdrawn_and_four_added(v14, v15):
    before = set(v14["what_must_not_be_claimed"])
    after = set(v15["what_must_not_be_claimed"])
    removed, added = before - after, after - before
    assert len(removed) == 1, "a withdrawal must be surgical"
    assert len(added) == 4
    assert len(after) == len(before) - 1 + 4


def test_the_withdrawal_is_recorded_with_its_reason(v14, v15):
    block = v15["prohibition_withdrawn_here"]
    assert block["text"] in v14["what_must_not_be_claimed"]
    assert block["text"] not in v15["what_must_not_be_claimed"]
    assert "factually wrong" in block["why"]
    assert "only when it is shown false" in block["why"]


def test_the_correction_names_the_mechanism_not_just_the_verdict(v15):
    block = v15["correction_to_v14"]
    assert "SUB-REGION" in block["why_it_is_wrong"]
    assert "673" in block["why_it_is_wrong"] and "1034" in block["why_it_is_wrong"]
    decomposition = block["decomposition"]
    assert abs(decomposition["region_fraction_alone_vs_in_solution"]) > \
        abs(decomposition["aup_alone_vs_in_solution"])
    assert "length-composition artifact" in decomposition["statement"]


def test_the_earlier_123_record_result_is_explicitly_defended(v15):
    """Over-correcting would be as wrong as the original error."""
    scope = v15["correction_to_v14"]["scope_of_the_error"]
    assert "123 of 123" in scope
    assert "was therefore CORRECT" in scope
    assert "No other artifact or gate entry is affected" in scope


def test_the_adverse_conclusion_survives_the_correction(v15):
    block = v15["correction_to_v14"]["but_the_adverse_finding_survives_in_another_form"]
    assert block["gc_content_cds_alone"] > 0.32
    assert "still beats the fitted calibration" in block["statement"]
    assert "The identity of the baseline changes; the conclusion" in block["statement"]
    assert "+0.0545" in block["and_it_is_axis_specific"]


def test_the_engine_swap_is_recorded_as_a_dead_hypothesis(v15):
    block = v15["folding_engine_swap"]
    assert "Dead hypothesis" in block["step_1_verdict"]
    assert "dead hypothesis" in block["step_2_skipped_and_why"]


def test_the_overfitting_result_is_recorded_with_both_directions(v15):
    block = v15["folding_engine_swap"]["step_3_refitting_actively_hurts"]
    arms = block["arms"]
    single = min(arms.values(), key=lambda a: a["features"])
    widest = max(arms.values(), key=lambda a: a["features"])
    assert widest["train_spearman"] > single["train_spearman"]
    assert widest["test_spearman_vs_in_solution"] < single["test_spearman_vs_in_solution"]
    assert block["success_by_declared_criterion"] is False
    assert block["best_arm_is_the_single_free_column"] is True
    assert "supports about one feature" in block["statement"]


def test_the_declared_conclusion_for_this_outcome_is_carried(v15):
    text = v15["folding_engine_swap"][
        "the_conclusion_the_protocol_declared_in_advance_for_this_outcome"]
    assert "adds no value over a single free feature" in text
    assert "REDUCED to that feature rather than defended" in text


def test_the_outcome_authorizes_nothing_on_its_own(v15):
    text = v15["folding_engine_swap"]["what_this_does_not_authorize"]
    assert "No change to the production path" in text
    assert "recorded as indicated, not taken" in text
