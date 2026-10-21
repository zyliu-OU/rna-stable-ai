"""Tests for the mRNAutilus comparison.

This comparison is the first time an independent published model has scored the
same sequences as this project's objective. It produced one favourable result and
one genuinely useful one, and both are easy to misreport:

  - the favourable result (better rank correlation on held-out measured records)
    comes from a test set where mRNAutilus is out of domain, so it must stay
    attached to that caveat
  - the useful result is that their half-life head is NOT a GC readout on the
    same 512-member pool where this project's objective sits at r = +0.99, which
    means the GC collapse recorded in gate v12 is escapable rather than inherent

These tests pin both, pin that spread was not reported as resolution, and pin
that the two arms of this project's own estimator stay labelled separately.
"""
import glob
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/mrnautilus_comparison_v1_2026-10-20.json"
RUNS = sorted(glob.glob(str(ROOT / "results/mrnautilus_comparison_runs/*/summary.json")))

pytestmark = pytest.mark.skipif(not RUNS, reason="mRNAutilus comparison not run")


@pytest.fixture(scope="module")
def run():
    return json.loads(Path(RUNS[-1]).read_text())


@pytest.fixture(scope="module")
def held(run):
    return run["run_b_held_out_measured_records"]


@pytest.fixture(scope="module")
def pool(run):
    return run["run_a_same_pool_both_methods"]


def test_the_protocol_is_pinned_at_its_hash(run):
    assert PROTOCOL.exists()
    assert hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() == run["protocol_sha256"]


def test_the_comparison_was_declared_before_any_number_was_seen():
    declared = json.loads(PROTOCOL.read_text())["declared_before_any_number_was_seen"]
    text = " ".join(declared)
    assert "Rank statistics only" in text
    assert "not a symmetric comparison" in text
    assert "Saluki" in text and "in-solution" in text
    assert "longest ATG" in text


def test_their_artifacts_are_not_redistributed():
    """Same policy as the RiboNN weights and the Rfam sources: hashes, not copies."""
    block = json.loads(PROTOCOL.read_text())["their_artifacts_not_redistributed"]
    assert "No mRNAutilus code or weights are vendored" in block["policy"]
    assert len(block["checkpoint_sha256"]) == 64
    assert "CC BY-NC" in block["license"]
    vendored = list(ROOT.rglob("scoring_functions.py")) + list(ROOT.rglob("*.ckpt"))
    assert vendored == [], f"mRNAutilus artifacts must not be vendored: {vendored}"


def test_every_environment_adaptation_is_justified_as_equivalent():
    """Three upstream API drifts were worked around; none may silently change maths."""
    adaptations = json.loads(PROTOCOL.read_text())["environment_adaptations"]
    assert len(adaptations) == 3
    text = " ".join(adaptations)
    assert "weights_only" in text and "pinned hash" in text
    assert "verified equivalent in the flash-attn source" in text
    assert "informational and unused" in text


def test_the_held_out_set_is_the_same_123_records(held):
    assert held["records"] == 123
    assert "123 of 123" in held["cds_inference"]
    bins = held["concordance_by_measured_fold_difference"]
    assert bins["1.00-1.10"]["pairs"] == 2958
    assert sum(b["pairs"] for b in bins.values()) == 7503


def test_our_objective_ranks_the_measured_records_better_overall(held):
    rank = held["spearman_vs_measured"]
    assert rank["ours"] > rank["mrnautilus_halflife_head"]
    assert rank["ours"] == pytest.approx(0.32677251679973174)
    assert rank["mrnautilus_halflife_head"] == pytest.approx(0.1747, abs=1e-3)


def test_the_favourable_result_stays_attached_to_its_caveat(held):
    assert "NOT symmetric" in held["fairness"]
    assert "must not be cited as mRNAutilus being worse at its own task" in held["fairness"]
    assert "out-of-domain" in held["fairness"]


def test_the_narrow_bin_is_not_claimed_either_way(held):
    """Both sit at chance there; the gap must not be read as a result."""
    narrow = held["concordance_by_measured_fold_difference"]["1.00-1.10"]
    assert narrow["mrnautilus"] > narrow["ours"], "mRNAutilus is nominally ahead here"
    assert abs(narrow["ours"] - 0.50) < 0.02 and abs(narrow["mrnautilus"] - 0.50) < 0.03
    assert "both sit at chance there" in held["finding"]
    assert "not independent" in held["finding"] and "not a result" in held["finding"]


def test_we_win_every_bin_at_or_above_1_25(held):
    bins = held["concordance_by_measured_fold_difference"]
    for key in ("1.25-1.50", "1.50-2.00", "above_2.00"):
        assert bins[key]["ours"] > bins[key]["mrnautilus"]


def test_their_head_inverts_on_moderate_differences(held):
    """Below chance in two middle bins while strong above 2x: it orders something else."""
    block = held["their_head_is_non_monotonic"]
    assert set(block["bins_below_chance"]) == {"1.25-1.50", "1.50-2.00"}
    bins = held["concordance_by_measured_fold_difference"]
    assert bins["1.25-1.50"]["mrnautilus"] < 0.50
    assert bins["1.50-2.00"]["mrnautilus"] < 0.50
    assert bins["above_2.00"]["mrnautilus"] > 0.85
    assert "not simply weaker" in block["statement"]
    assert "Saluki" in block["most_likely_explanation"]


def test_the_two_arms_of_our_own_estimator_stay_labelled(held):
    """0.5007 was the OLS refit; the frozen calibration is 0.4936. Different arms."""
    text = held["which_arm_is_ours"]
    assert "FROZEN production calibration" in text
    assert "0.5007" in text and "0.4936" in text
    assert "Both are at chance" in text
    bins = held["concordance_by_measured_fold_difference"]
    assert bins["1.00-1.10"]["ours"] != bins["1.00-1.10"]["ours_ols_refit_arm"]


def test_the_pool_was_regenerated_exactly(pool):
    assert pool["pool_size"] == 512
    assert pool["transcript_hashes_matched"] == 512


def test_their_half_life_head_is_not_a_gc_readout(pool):
    """The most useful result: the GC collapse is escapable, not inherent to the pool."""
    gc = pool["their_correlation_with_transcript_gc"]["halflife"]
    ours = pool["their_correlation_with_our_objective"]["halflife"]
    assert abs(gc) < 0.40, "if this ever approaches +0.99 the escapability claim fails"
    assert ours < 0, "their stability head disagrees with ours in sign"
    text = pool["finding_their_half_life_head_is_not_a_gc_readout"]
    assert "+0.99" in text
    assert "property of this project's calibration, not an unavoidable fact" in text


def test_their_translation_head_carries_the_same_confound(pool):
    """Being a learned model does not by itself escape composition confounding."""
    gc = pool["their_correlation_with_transcript_gc"]
    assert gc["translation_rate"] > 0.60
    assert "does not by itself escape composition confounding" in \
        pool["but_their_translation_head_is_substantially_gc_driven"]


def test_spread_was_not_reported_as_resolution(pool):
    """Their scale has no measurement-derived error model, so nothing is resolvable on it."""
    text = pool["no_resolution_claim"]
    assert "arbitrary normalised scale" in text
    assert "cannot be transferred" in text
    assert "Spread is not resolution" in text
    assert all(spread["stdev"] > 0 for spread in pool["their_spread"].values())


def test_the_limits_are_carried(run):
    text = " ".join(run["no_claim"])
    assert "Nothing here is a measurement" in text
    assert "No claim that this project's method is better than mRNAutilus in general" in text
    assert "which is what it was trained for and was not tested here" in text
    assert "spread on an arbitrary scale is not resolution" in text
    assert "collapse is escapable, not escaped" in text
    assert "not redistributed" in text


def test_what_changed_is_stated_without_overreach(run):
    changed = " ".join(run["what_this_changes"])
    assert "not forced by the design pool" in changed
    assert "not uniformly better" in changed
    assert "Both are at chance below 1.10x" in changed
