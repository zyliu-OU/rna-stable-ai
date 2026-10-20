"""Tests for the whole-transcript design run.

This run cleared the resolvable threshold for the first time in the project, and
in doing so showed the objective collapses to a GC readout at r = +0.99. Both
halves must stay pinned: the success, so it is not overstated, and the collapse,
so it is not quietly dropped when it is inconvenient.
"""
import glob
import json
import statistics
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNS = sorted(glob.glob(str(ROOT / "results/full_transcript_design_runs/*/summary.json")))

pytestmark = pytest.mark.skipif(not RUNS, reason="whole-transcript design not run")


@pytest.fixture(scope="module")
def run():
    return json.loads(Path(RUNS[-1]).read_text())


@pytest.fixture(scope="module")
def scored(run):
    return [m for m in run["members"] if m.get("stability")]


def test_the_pool_did_not_collapse(run):
    assert run["pool"]["distinct_orfs"] == run["pool"]["size"]


def test_every_member_is_a_verified_designed_transcript(run, scored):
    assert run["assembly"]["utrs_designed"] is True
    assert run["assembly"]["one_protein_hash"] is True
    assert len({m["protein_sha256"] for m in scored}) == 1
    assert len({m["transcript_length_nt"] for m in scored}) == 1
    assert len({m["transcript_sha256_rna"] for m in scored}) == len(scored)


def test_both_design_axes_moved(run):
    assembly = run["assembly"]
    assert assembly["utr5_edits_range"][1] > 5
    assert assembly["utr3_edits_range"][1] > 20
    assert assembly["codon_substitution_range"][1] > 100


def test_the_resolvable_threshold_was_cleared(run):
    """The point of widening the domain. Previously the ceiling was 1.0617x."""
    block = run["stability_vs_reference"]
    assert run["verdict"]["clears_the_chance_floor"] is True
    assert run["verdict"]["clears_the_resolvable_threshold"] is True
    assert block["widest_ratio"] >= run["resolution_floor"]["resolvable_threshold"]
    assert block["members_above_resolvable_threshold"] > 0
    assert "for the first time in this project" in run["verdict"]["finding"]


def test_nothing_is_resolvably_better(run):
    """Every resolvable difference is a degradation; that must not be softened."""
    block = run["stability_vs_reference"]
    assert block["resolvably_better"] == []
    assert len(block["resolvably_worse"]) > 0
    assert block["unresolved"] > 0
    assert (len(block["resolvably_worse"]) + block["unresolved"]
            + len(block["resolvably_better"])) == run["pool"]["size"]


def test_the_calibration_domain_became_reachable(run):
    gc = run["gc"]
    assert gc["members_in_calibration_domain"] > run["pool"]["size"] // 2
    assert gc["members_extrapolating"] < gc["members_in_calibration_domain"]
    assert "every member extrapolated on GC" in gc["note"]
    low, high = gc["calibration_training_range"]
    assert gc["reference"] > high, "the reference must still be out of domain"


def test_the_objective_collapses_to_a_gc_readout(scored):
    """r = +0.99 is the finding that reframes the whole result."""
    gc = [m["transcript_gc_fraction"] for m in scored]
    hours = [m["stability"]["predicted_in_solution_half_life_hours"] for m in scored]
    correlation = statistics.correlation(gc, hours)
    assert correlation > 0.95, (
        "if this ever falls, the conclusion that the objective is essentially a GC meter "
        "must be revisited")


def test_entering_the_domain_and_improving_the_score_are_opposed(scored):
    """The mechanism behind zero resolvably-better members."""
    in_domain = [m for m in scored if not m["stability"]["extrapolating"]]
    extrapolating = [m for m in scored if m["stability"]["extrapolating"]]
    assert in_domain and extrapolating
    median_in = statistics.median(
        m["stability"]["predicted_in_solution_half_life_hours"] for m in in_domain)
    median_out = statistics.median(
        m["stability"]["predicted_in_solution_half_life_hours"] for m in extrapolating)
    assert median_in < median_out, (
        "in-domain members must score WORSE; that opposition is why no member is better")


def test_the_resolvably_worse_members_are_the_low_gc_ones(run, scored):
    worse = set(run["stability_vs_reference"]["resolvably_worse"])
    assert worse
    worse_gc = [m["transcript_gc_fraction"] for m in scored if m["member"] in worse]
    others = [m["transcript_gc_fraction"] for m in scored if m["member"] not in worse]
    assert max(worse_gc) < max(others)
    assert statistics.fmean(worse_gc) < statistics.fmean(others)


def test_the_translation_side_was_not_run(run):
    assert "deliberate" in run["ribonn_not_run"]
    assert "excluded from filtering" in run["ribonn_not_run"]
    for member in run["members"]:
        assert "translation" not in member
    text = " ".join(run["no_claim"])
    assert "translation side was not scored" in text


def test_the_limits_are_carried(run):
    text = " ".join(run["no_claim"])
    assert "Nothing here is measured" in text
    assert "NEW construct" in text
    assert "in-domain, not correct" in text
    assert "does not improve the objective's resolution" in text


def test_the_run_pins_its_design_space_and_selection_protocol(run):
    import hashlib
    spec = ROOT / run["design_space"]
    assert spec.exists()
    assert hashlib.sha256(spec.read_bytes()).hexdigest() == run["design_space_sha256"]
    assert (ROOT / run["selection_protocol"]).exists()
    assert run["resolution_floor"]["applies_to"] == "stability only"
