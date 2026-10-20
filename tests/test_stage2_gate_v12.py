"""Tests for gate v12, which records a success and the finding that undercuts it.

v12 is the first gate version where something worked: the widened domain cleared
the resolvable threshold. The risk is that the success travels and the finding
underneath it does not. These tests pin both, and pin that the four independent
findings now converging on GC are named together rather than left scattered
across five gate versions.
"""
import hashlib
import json
import statistics
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
V11 = ROOT / "configs/stage2_to_stage3_gate_v11_2026-10-20.json"
V12 = ROOT / "configs/stage2_to_stage3_gate_v12_2026-10-20.json"


@pytest.fixture(scope="module")
def v12():
    return json.loads(V12.read_text())


@pytest.fixture(scope="module")
def v11():
    return json.loads(V11.read_text())


@pytest.fixture(scope="module")
def widened(v12):
    return v12["design_domain_widened"]


def test_v11_is_retained_unedited_at_its_recorded_hash(v12):
    assert hashlib.sha256(V11.read_bytes()).hexdigest() == v12["supersedes"]["sha256"]


def test_nothing_was_reopened_or_rereatified(v11, v12):
    assert v12["requirements_before_stage3"] == v11["requirements_before_stage3"]
    assert v12["requirements_satisfied"] == v11["requirements_satisfied"] == 6
    assert v12["switches_unchanged_from_v6"] == v11["switches_unchanged_from_v6"]
    assert "no switch moves" in v12["amendment_record"]["what_changed"]


def test_both_v10_options_are_recorded_as_taken_and_complementary(v12):
    text = v12["amendment_record"]["both_v10_options_now_taken"]
    assert "v11 took option 1" in text
    assert "v12 takes option 2" in text
    assert "option 1 made the output honest, option 2 made it non-empty" in text


def test_the_success_is_recorded_with_the_previous_ceiling(widened):
    assert widened["result"]["previous_domain_ceiling"] == 1.0617
    assert widened["result"]["widest_ratio_vs_reference"] > 1.25
    assert widened["result"]["members_above_resolvable_threshold"] > 0
    assert "CONSTRAINT was indeed the binding limit" in widened["what_succeeded"]


def test_zero_resolvably_better_is_stated_plainly(widened):
    assert widened["result"]["resolvably_better"] == 0
    assert widened["result"]["resolvably_worse"] > 0
    text = widened["zero_members_are_resolvably_better"]
    assert "Every resolvable difference is a degradation" in text
    assert "HIGHER GC than the reference" in text


def test_the_gc_collapse_is_recorded_with_its_mechanism(widened):
    exposed = widened["what_it_exposed"]
    assert "collapses to a GC readout" in exposed["finding"]
    assert "+0.98" in exposed["finding"] or "+0.99" in exposed["finding"]
    assert "one-component PLS" in exposed["mechanism"]
    assert "explanation, not a defect" in exposed["mechanism"]


def test_the_opposition_between_domain_and_score_is_recorded(widened):
    text = widened["what_it_exposed"]["the_opposition"]
    assert "LOWERING GC" in text
    assert "1.0558" in text and "1.3223" in text
    assert "near-deterministic opposition" in text


def test_the_four_findings_converging_on_gc_are_named_together(widened):
    text = widened["what_it_exposed"]["why_this_matters_most"]
    assert "3.7" in text
    assert "extrapolates" in text
    assert "strongest single feature" in text
    assert "Four independent findings now converge on GC" in text


def test_the_recorded_figures_match_the_run(widened):
    run = json.loads((ROOT / widened["run"]).read_text())
    block = run["stability_vs_reference"]
    recorded = widened["result"]
    assert recorded["widest_ratio_vs_reference"] == pytest.approx(block["widest_ratio"])
    assert recorded["resolvably_better"] == len(block["resolvably_better"])
    assert recorded["resolvably_worse"] == len(block["resolvably_worse"])
    assert recorded["unresolved"] == block["unresolved"]
    assert recorded["members_above_resolvable_threshold"] == \
        block["members_above_resolvable_threshold"]


def test_the_recorded_correlation_matches_the_run(widened):
    run = json.loads((ROOT / widened["run"]).read_text())
    scored = [m for m in run["members"] if m.get("stability")]
    actual = statistics.correlation(
        [m["transcript_gc_fraction"] for m in scored],
        [m["stability"]["predicted_in_solution_half_life_hours"] for m in scored])
    assert f"{actual:+.4f}" in widened["what_it_exposed"]["finding"]


def test_the_domain_and_its_protected_motifs_are_recorded(widened):
    domain = widened["domain"]
    assert "38 of 44" in domain and "111 of" in domain
    assert "GCCACC Kozak preserved" in domain
    assert "TAA tandem stop preserved" in domain
    assert "every length fixed" in domain
    grounded = widened["constraint_grounded_in_own_measurement"]
    assert "-1.56" in grounded and "-1.32" in grounded
    assert "stable across the modification" in grounded


def test_the_calibration_domain_becoming_reachable_is_recorded(widened):
    text = widened["and_the_calibration_domain_became_reachable"]
    assert "inside the calibration's fitted GC range" in text
    assert "every member extrapolated on GC" in text


def test_no_earlier_prohibition_was_dropped(v11, v12):
    before, after = set(v11["what_must_not_be_claimed"]), set(v12["what_must_not_be_claimed"])
    assert before <= after
    assert len(after) == len(before) + 3
    added = " ".join(after - before)
    assert "zero members are resolvably better" in added
    assert "effectively a GC readout" in added
    assert "in the direction the model calls worse" in added
