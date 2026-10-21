"""Tests for the two-axis comparison.

This is the test that was supposed to vindicate the project and instead produced
its three most adverse findings. All three are easy to lose, so each is pinned:

  1. in-solution and in-cell half-life of the SAME constructs rank at Spearman
     +0.05 -- "stability" is not one target
  2. a free per-nucleotide EternaFold score now BEATS the frozen calibration on
     the calibration's own home axis
  3. transcript GC alone ranks both axes about as well as the three-feature
     calibration does

It also narrows a v13 statement that was too generous to mRNAutilus, and that
narrowing is pinned too, because a correction that only ever runs in one
direction is not a correction.
"""
import glob
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/two_axis_comparison_v1_2026-10-20.json"
RUNS = sorted(glob.glob(str(ROOT / "results/two_axis_comparison_runs/*/two_axis_summary.json")))

pytestmark = pytest.mark.skipif(not RUNS, reason="two-axis comparison not run")


@pytest.fixture(scope="module")
def run():
    return json.loads(Path(RUNS[-1]).read_text())


@pytest.fixture(scope="module")
def ours_run():
    return json.loads((Path(RUNS[-1]).parent / "summary.json").read_text())


def test_the_protocol_is_pinned_at_its_hash(run):
    assert hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() == run["protocol_sha256"]


def test_the_expected_pattern_was_declared_before_any_number(run):
    """The protocol predicted each method would win its own column. One did not."""
    declared = json.loads(PROTOCOL.read_text())["declared_before_any_number_was_seen"]
    text = " ".join(declared)
    assert "this project wins the in-solution column, mRNAutilus wins the in-cell" in text
    assert "Any other pattern is informative and must be reported as measured" in text
    assert "Falsification of this project's side" in text


def test_the_source_is_pinned_and_not_redistributed(run):
    source = run["source"]
    assert len(source["archive_sha256"]) == 64 and len(source["table_sha256"]) == 64
    assert "not copied into this repository" in source["not_redistributed"]
    assert list(ROOT.rglob("*MOESM4*")) == []


def test_nothing_was_refitted(run, ours_run):
    assert run["refitting_performed"] == "none"
    assert ours_run["refitting_performed"] == "none"


def test_the_test_set_is_exactly_as_declared(run):
    counts = run["counts"]
    declared = json.loads(PROTOCOL.read_text())["test_set"]
    assert counts["records"] == declared["records_total"] == 233
    assert counts["test_set"] == declared["declared_test_set_size"] == 122
    assert counts["dropped"]["in_training_set"] == 69
    assert counts["dropped"]["reconstruction_mismatch"] == 0, (
        "every record must be reconstructed from its declared segments; a nonzero count "
        "means records are being dropped for a layout the parser does not handle")


def test_the_second_constant_region_layout_is_parsed_not_dropped(run, ours_run):
    """The library has two constant-region orders and 24 constructs use the second.

    All 24 are "CDS (Nluc) variants", and that entire design category is this
    project's 69-record training set, so none of them reaches the test set. The
    parser must still handle the layout: before it did, those 24 were dropped as
    reconstruction failures and the 122-record total was reached by coincidence,
    with only 45 records excluded as training rather than the declared 69.
    """
    assert run["counts"]["dropped"]["reconstruction_mismatch"] == 0
    assert run["counts"]["dropped"]["in_training_set"] == 69
    assert {r["constant_region_layout"] for r in ours_run["rows"]} == {0}


def test_the_test_set_excludes_the_entire_training_design_category(ours_run):
    """Our 69 training records are all "CDS (Nluc) variants", so none appear here.

    This makes the test more independent than a random split would be, and it
    also means the test set is a distribution shift: mostly UTR variants, plus
    eGFP and MEV coding variants, and no Nluc coding variants at all.
    """
    groups = {r["group"] for r in ours_run["rows"]}
    assert "CDS (Nluc) variants" not in groups
    assert any("UTR" in g for g in groups)


def test_the_two_measured_axes_barely_agree(run):
    """The finding that reframes every stability claim in this project."""
    block = run["the_two_measured_axes_barely_agree"]
    assert abs(block["spearman_between_them"]) < 0.15
    assert "very nearly unrelated orderings" in block["statement"]
    assert "must say which one it means" in block["statement"]
    assert "implies nothing about the other" in block["consequence_for_this_comparison"]


def test_our_objective_is_still_better_on_its_own_axis(run):
    """Not falsified: the in-solution framing survives, narrowly."""
    domain = run["domain_test"]
    assert domain["ours_better_in_its_own_domain"] is True
    assert domain["ours"]["spearman_home"] > domain["ours"]["spearman_away"]


def test_mrnautilus_is_not_better_on_its_own_axis(run):
    """This is what narrows v13's domain-mismatch explanation."""
    domain = run["domain_test"]
    assert domain["theirs_better_in_its_own_domain"] is False
    theirs = domain["mrnautilus"]
    assert abs(theirs["spearman_home"] - theirs["spearman_away"]) < 0.05, (
        "their head is flat across the two axes; if this ever separates, the v13 "
        "narrowing must be revisited")


def test_the_free_baseline_now_beats_our_calibration_on_our_own_axis(run):
    """The most adverse finding. It must not be softened into a tie."""
    block = run["the_free_baseline"]
    assert block["in_solution"] > block["ours_in_solution"]
    assert block["in_cell"] < 0, "the free baseline is in-solution-specific"
    assert "does not beat free folding on its own home axis" in block["statement"]


def test_gc_alone_ranks_both_axes_about_as_well_as_the_calibration(run):
    gc_sol = run["in_solution_column"]["spearman"]["transcript_gc_alone"]
    gc_cell = run["in_cell_column"]["spearman"]["transcript_gc_alone"]
    ours_sol = run["in_solution_column"]["spearman"]["ours"]
    ours_cell = run["in_cell_column"]["spearman"]["ours"]
    assert ours_sol - gc_sol < 0.10
    assert gc_cell >= ours_cell, "GC alone is at least as good as the calibration on in-cell"
    gate = json.loads((ROOT / "configs/stage2_to_stage3_gate_v14_2026-10-20.json").read_text())
    statement = gate["two_axis_comparison"][
        "the_gc_collapse_reproduces_on_real_constructs"]["statement"]
    assert "adds little to nothing over base composition" in statement


def test_the_gc_collapse_reproduces_on_real_measured_constructs(run):
    block = run["gc_diagnostic"]
    assert block["ours_vs_transcript_gc"] > 0.70
    assert "property of the objective and not an artifact" in block["statement"]


def test_neither_method_resolves_the_narrow_bin_on_either_axis(run):
    for column in ("in_solution_column", "in_cell_column"):
        narrow = run[column]["concordance"]["1.00-1.10"]
        assert narrow["pairs"] > 1000
        assert abs(narrow["ours"] - 0.50) < 0.05
        assert abs(narrow["mrnautilus"] - 0.50) < 0.05


def test_the_bin_where_they_beat_us_is_recorded(run):
    """On the largest in-cell differences our objective falls to chance and theirs does not."""
    wide = run["in_cell_column"]["concordance"]["above_2.00"]
    assert wide["mrnautilus"] > wide["ours"]
    assert abs(wide["ours"] - 0.50) < 0.05


def test_the_limits_are_carried(run):
    text = " ".join(run["no_claim"])
    assert "Nothing here is a new measurement" in text
    assert "partly circular" in text, "the shared Zheng 2025 training source must be stated"
    assert "No resolution claim" in text
    assert "generator" in text
    assert "are redistributed here" in text, "the no-redistribution line must be present"


def test_what_changed_is_stated_without_softening(run):
    changed = " ".join(run["what_this_changes"])
    assert "nearly unrelated on identical constructs" in changed
    assert "worse than previously recorded, not better" in changed
