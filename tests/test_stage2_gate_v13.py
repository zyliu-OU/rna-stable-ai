"""Tests for gate v13, which records the first comparison against an outside model.

v13 carries this project's first favourable head-to-head result. That makes it the
gate version most at risk of being quoted without its caveat, so these tests pin
the caveat as tightly as the result, and pin that the comparison authorized
nothing by itself.
"""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
V12 = ROOT / "configs/stage2_to_stage3_gate_v12_2026-10-20.json"
V13 = ROOT / "configs/stage2_to_stage3_gate_v13_2026-10-20.json"


@pytest.fixture(scope="module")
def v13():
    return json.loads(V13.read_text())


@pytest.fixture(scope="module")
def v12():
    return json.loads(V12.read_text())


@pytest.fixture(scope="module")
def comparison(v13):
    return v13["independent_model_comparison"]


def test_v12_is_retained_unedited_at_its_recorded_hash(v13):
    assert hashlib.sha256(V12.read_bytes()).hexdigest() == v13["supersedes"]["sha256"]
    assert v13["supersedes"]["status"] == "frozen and unedited"


def test_nothing_was_reopened_or_rereatified(v12, v13):
    assert v13["requirements_before_stage3"] == v12["requirements_before_stage3"]
    assert v13["requirements_satisfied"] == v12["requirements_satisfied"] == 6
    assert v13["switches_unchanged_from_v6"] == v12["switches_unchanged_from_v6"]
    assert "No switch moves" in v13["amendment_record"]["what_changed"]
    assert "Stage 2 stays closed at six of six" in v13["amendment_record"]["what_changed"]


def test_the_comparison_is_pinned_to_a_protocol_and_a_checkpoint(comparison):
    protocol = ROOT / comparison["protocol"]
    assert protocol.exists()
    assert hashlib.sha256(protocol.read_bytes()).hexdigest() == comparison["protocol_sha256"]
    assert len(comparison["their_checkpoint_sha256"]) == 64
    assert "URLs and hashes only" in comparison["nothing_redistributed"]


def test_the_favourable_result_is_recorded_with_its_asymmetry(comparison):
    held = comparison["result_on_held_out_measured_records"]
    assert held["spearman_ours"] > held["spearman_theirs"]
    assert held["we_are_better_in_every_bin_at_or_above"] == "1.25x"
    assert "NOT symmetric" in held["why_this_is_not_a_symmetric_win"]


def test_the_bin_we_lose_is_recorded_too(comparison):
    """A gate that records only the bins we win is not a record."""
    narrow = comparison["result_on_held_out_measured_records"]["narrow_bin_both_at_chance"]
    assert narrow["theirs"] > narrow["ours"]
    assert "nominally ahead" in narrow["statement"]
    assert "Neither side may claim that bin" in narrow["statement"]


def test_their_head_inverting_on_moderate_differences_is_recorded(comparison):
    bins = comparison["result_on_held_out_measured_records"]["their_head_is_below_chance_in"]
    assert set(bins) == {"1.25-1.50", "1.50-2.00"}


def test_the_escapable_gc_collapse_is_recorded_as_escapable_not_escaped(comparison):
    pool = comparison["result_on_our_512_member_pool"]
    assert abs(pool["their_halflife_vs_transcript_gc"]) < 0.40
    assert pool["our_objective_vs_transcript_gc"] > 0.95
    text = pool["the_finding_that_matters"]
    assert "property of THIS project's one-component PLS calibration" in text
    assert "It is escapable. It has not been escaped." in text


def test_learning_alone_is_not_recorded_as_the_remedy(comparison):
    pool = comparison["result_on_our_512_member_pool"]
    assert pool["their_translation_vs_transcript_gc"] > 0.60
    assert "is not by itself the remedy" in pool["and_the_confound_is_not_cured_by_learning"]
    assert "Spread is not resolution" in pool["no_resolution_claim"]


def test_the_comparison_authorizes_nothing_on_its_own(comparison):
    text = comparison["what_this_does_not_authorize"]
    assert "No change to the production path" in text
    assert "no adoption of mRNAutilus" in text
    assert "separate, separately recorded decision" in text


def test_no_earlier_prohibition_was_dropped(v12, v13):
    before = set(v12["what_must_not_be_claimed"])
    after = set(v13["what_must_not_be_claimed"])
    assert before <= after
    assert len(after) == len(before) + 3
    added = " ".join(after - before)
    assert "better than mRNAutilus" in added
    assert "spread is not resolution" in added
    assert "escapable" in added
