"""Tests for gate v11, which takes v10's option 1 and reframes the selection.

v11 is the version that changes what the pipeline IS. The risk is that a
reframe quietly restores ranking under another name, or that the stability
resolution floor leaks onto the translation side. These tests pin that the
option taken is recorded as a choice with the alternative left open, that the
floor stays stability-only, and that the per-pool figures match the runs.
"""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
V10 = ROOT / "configs/stage2_to_stage3_gate_v10_2026-10-20.json"
V11 = ROOT / "configs/stage2_to_stage3_gate_v11_2026-10-20.json"


@pytest.fixture(scope="module")
def v11():
    return json.loads(V11.read_text())


@pytest.fixture(scope="module")
def v10():
    return json.loads(V10.read_text())


@pytest.fixture(scope="module")
def reframe(v11):
    return v11["selection_reframe"]


def test_v10_is_retained_unedited_at_its_recorded_hash(v11):
    assert hashlib.sha256(V10.read_bytes()).hexdigest() == v11["supersedes"]["sha256"]


def test_nothing_was_reopened_or_rereatified(v10, v11):
    assert v11["requirements_before_stage3"] == v10["requirements_before_stage3"]
    assert v11["requirements_satisfied"] == v10["requirements_satisfied"] == 6
    assert v11["requirements_satisfied_basis_unchanged_from_v5"] == \
        v10["requirements_satisfied_basis_unchanged_from_v5"]
    assert v11["switches_unchanged_from_v6"] == v10["switches_unchanged_from_v6"]
    assert "no switch moves" in v11["amendment_record"]["what_changed"]


def test_the_option_taken_is_recorded_and_the_other_left_open(v10, v11):
    taken = v11["amendment_record"]["which_v10_option_was_taken"]
    assert "Option 1" in taken
    assert "Option 2" in taken
    assert "NOT taken and remains open" in taken
    # v10 recorded exactly these two options.
    assert len(v10["prohibition_added_here"]["open_decision_recorded_not_taken"]) == 2


def test_the_reframe_names_what_it_replaces_and_retains(reframe):
    assert "hypervolume-maximising subset selection" in reframe["replaces"]
    assert "presupposes the objectives order candidates meaningfully" in reframe["replaces"]
    assert "protein verification" in reframe["retains"]
    assert "only the selection and the permitted claims change" in reframe["retains"]
    assert (ROOT / reframe["protocol"]).exists()
    assert (ROOT / reframe["driver"]).exists()


def test_the_resolution_floor_is_measured_and_stability_only(reframe):
    floor = reframe["resolution_floor"]
    assert floor["chance_floor"] == 1.10
    assert floor["resolvable_threshold"] == 1.25
    assert floor["applies_to"] == "the stability objective only"
    assert (ROOT / floor["measured_from"]).exists()
    assert "1.15-fold" in floor["why_two_numbers"]


def test_the_translation_side_is_excluded_with_the_trap_named(reframe):
    text = reframe["translation_side_excluded_from_the_filter"]
    assert "never been evaluated against any measurement" in text
    assert "unresolved regardless of size" in text
    assert "11 members exceed the STABILITY chance floor" in text
    assert "different model on a different quantity" in text
    assert "enforced in code" in text


def test_every_pool_is_recorded_as_entirely_unresolved(reframe):
    pools = reframe["applied_to_all_three_pools"]
    assert set(pools) == {"30", "50", "549"}
    for width, block in pools.items():
        assert block["resolvably_better"] == 0, width
        assert block["resolvably_worse"] == 0, width
        assert block["unresolved"] == block["pool_size"], width
        assert block["widest_fold_difference_from_reference"] < 1.10, width


def test_the_recorded_per_pool_figures_match_their_runs(reframe):
    for width, block in reframe["applied_to_all_three_pools"].items():
        run = json.loads((ROOT / block["run"] / "summary.json").read_text())
        assert run["pool"]["window_codons"] == int(width)
        assert run["pool"]["size"] == block["pool_size"]
        classification = run["stability_classification"]
        assert len(classification["resolvably_better"]) == block["resolvably_better"]
        assert classification["unresolved_count"] == block["unresolved"]
        assert classification["widest_fold_difference_from_reference"] == pytest.approx(
            block["widest_fold_difference_from_reference"])
        assert run["panel"]["minimum_pairwise_hamming"] == \
            block["panel_minimum_pairwise_hamming"]


def test_the_finding_is_stated_without_softening(reframe):
    finding = reframe["finding"]
    assert "Every member of every pool is UNRESOLVED" in finding
    assert "1.0617-fold" in finding
    assert "below even the 1.10-fold chance floor" in finding
    assert "entirely inside the objective's noise floor" in finding


def test_the_panel_is_described_as_ties_and_uses_no_predictions(reframe):
    text = reframe["what_the_panel_now_is"]
    assert "diversity panel over ties" in text
    assert "NO predicted values" in text
    assert "reference as the anchor" in text
    assert "Minimum pairwise Hamming distance is reported" in text


def test_the_honest_output_rationale_and_its_limit_are_both_recorded(reframe):
    assert "more useful than a confident ordering of ties" in \
        reframe["why_this_is_the_honest_output"]
    assert "does NOT mean the design space is bad" in reframe["what_it_does_not_mean"]
    assert "the objective cannot see it" in reframe["what_it_does_not_mean"]


def test_no_earlier_prohibition_was_dropped(v10, v11):
    before, after = set(v10["what_must_not_be_claimed"]), set(v11["what_must_not_be_claimed"])
    assert before <= after
    assert len(after) == len(before) + 3
    added = " ".join(after - before)
    assert "diversity panel is ranked" in added
    assert "RiboNN has no measured resolution at all" in added
    assert "defensible one given an objective that cannot rank" in added
