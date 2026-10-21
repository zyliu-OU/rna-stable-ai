"""Tests for gate v14, which records the symmetric comparison v13 asked for.

v14 is the first gate version to narrow one of its predecessor's own statements
rather than only add to it. It is also the gate carrying this project's most
adverse recorded finding about its stability objective. Both need pinning: the
narrowing, so corrections run in both directions, and the adverse finding, so it
is not quietly dropped when a favourable number is available instead.
"""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
V13 = ROOT / "configs/stage2_to_stage3_gate_v13_2026-10-20.json"
V14 = ROOT / "configs/stage2_to_stage3_gate_v14_2026-10-20.json"


@pytest.fixture(scope="module")
def v14():
    return json.loads(V14.read_text())


@pytest.fixture(scope="module")
def v13():
    return json.loads(V13.read_text())


@pytest.fixture(scope="module")
def comparison(v14):
    return v14["two_axis_comparison"]


def test_v13_is_retained_unedited_at_its_recorded_hash(v14):
    assert hashlib.sha256(V13.read_bytes()).hexdigest() == v14["supersedes"]["sha256"]
    assert v14["supersedes"]["status"] == "frozen and unedited"


def test_nothing_was_reopened_or_rereatified(v13, v14):
    assert v14["requirements_before_stage3"] == v13["requirements_before_stage3"]
    assert v14["requirements_satisfied"] == v13["requirements_satisfied"] == 6
    assert v14["switches_unchanged_from_v6"] == v13["switches_unchanged_from_v6"]
    assert "No switch moves" in v14["amendment_record"]["what_changed"]


def test_the_comparison_is_pinned_and_unrefitted(comparison):
    protocol = ROOT / comparison["protocol"]
    assert protocol.exists()
    assert hashlib.sha256(protocol.read_bytes()).hexdigest() == comparison["protocol_sha256"]
    assert comparison["refitting_performed"] == "none"
    assert (ROOT / comparison["run"]).exists()


def test_the_endogenous_atlas_rejection_is_recorded_with_its_reason(comparison):
    text = comparison["why_this_test_set_was_chosen_over_an_endogenous_atlas"]
    assert "13921 human genes" in text
    assert "leakage would be at the GENE level" in text
    assert "date-filtering source datasets would not remove it" in text


def test_the_axis_finding_is_recorded_as_dominant(comparison):
    block = comparison["the_finding_that_dominates_everything_else"]
    assert abs(block["spearman_between_the_two_measured_axes"]) < 0.15
    assert "separate tasks" in block["statement"]


def test_the_full_2x2_is_recorded(comparison):
    cells = comparison["the_2x2"]
    for key in ("ours_in_solution", "ours_in_cell",
                "mrnautilus_in_solution", "mrnautilus_in_cell",
                "free_eternafold_in_solution", "free_eternafold_in_cell",
                "transcript_gc_alone_in_solution", "transcript_gc_alone_in_cell"):
        assert isinstance(cells[key], float)
    assert cells["ours_in_solution"] > cells["ours_in_cell"]
    assert cells["free_eternafold_in_cell"] < 0


def test_v13s_explanation_is_narrowed_in_both_directions(comparison):
    """A correction that only ever helps this project is not a correction."""
    block = comparison["what_it_overturned_in_v13"]
    assert "does not hold on this test set" in block["what_the_two_axis_test_shows"]
    assert "narrowed, not withdrawn" in block["but_the_narrowing_is_partial"]
    assert "sequence type is not" in block["but_the_narrowing_is_partial"]
    assert "still may not claim general superiority" in block["net_effect_on_this_projects_claim"]


def test_the_free_baseline_finding_is_recorded_as_adverse(comparison):
    block = comparison["the_free_baseline_got_worse_not_better"]
    assert block["in_solution_free_eternafold"] > block["in_solution_ours"]
    assert "BEATEN on its own home axis" in block["statement"]
    assert "most adverse finding" in block["statement"]


def test_the_gc_collapse_on_real_constructs_is_recorded(comparison):
    block = comparison["the_gc_collapse_reproduces_on_real_constructs"]
    assert block["ours_vs_transcript_gc"] > 0.70
    assert "adds little to nothing over base composition" in block["statement"]
    assert "not of the design pool" in block["statement"]


def test_the_comparison_authorizes_nothing_on_its_own(comparison):
    text = comparison["what_this_does_not_authorize"]
    assert "No change to the production path" in text
    assert "separately recorded decision" in text


def test_no_earlier_prohibition_was_dropped(v13, v14):
    before = set(v13["what_must_not_be_claimed"])
    after = set(v14["what_must_not_be_claimed"])
    assert before <= after
    assert len(after) == len(before) + 4
    added = " ".join(after - before)
    assert "without naming the axis" in added
    assert "beats free folding" in added
    assert "over transcript GC" in added
    assert "domain mismatch alone" in added
