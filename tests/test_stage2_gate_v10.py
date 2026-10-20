"""Tests for gate v10, which removes the meaning of the design workflow's output.

This is the gate version with the most to lose from being softened: it says the
ordering the pipeline exists to produce is, at the scale the design space works
at, indistinguishable from chance. These tests pin the number to its pair count
and its chance baseline, pin that the coarse-filter permission is not a loophole,
and pin that the two ways out are recorded as open decisions rather than taken.
"""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
V9 = ROOT / "configs/stage2_to_stage3_gate_v9_2026-10-20.json"
V10 = ROOT / "configs/stage2_to_stage3_gate_v10_2026-10-20.json"


@pytest.fixture(scope="module")
def v10():
    return json.loads(V10.read_text())


@pytest.fixture(scope="module")
def v9():
    return json.loads(V9.read_text())


@pytest.fixture(scope="module")
def evidence(v10):
    return v10["external_evidence_added"]["objective_has_no_fine_resolution"]


def test_v9_is_retained_unedited_at_its_recorded_hash(v10):
    assert hashlib.sha256(V9.read_bytes()).hexdigest() == v10["supersedes"]["sha256"]


def test_nothing_was_reopened_or_rereatified(v9, v10):
    assert v10["requirements_before_stage3"] == v9["requirements_before_stage3"]
    assert v10["requirements_satisfied"] == v9["requirements_satisfied"] == 6
    assert v10["requirements_satisfied_basis_unchanged_from_v5"] == \
        v9["requirements_satisfied_basis_unchanged_from_v5"]
    assert v10["switches_unchanged_from_v6"] == v9["switches_unchanged_from_v6"]
    assert "no switch moves" in v10["amendment_record"]["what_changed"]


def test_it_says_why_a_prohibition_rather_than_a_limitation(v10):
    why = v10["amendment_record"]["why_this_is_a_gate_matter"]
    assert "whole output is an ORDERING" in why
    assert "removes the meaning of that output" in why
    assert "a prohibition, not a limitation" in why


def test_the_chance_result_is_pinned_to_its_pair_count(evidence):
    narrow = evidence["concordance_by_measured_fold_difference"]["1.00-1.10"]
    assert narrow["pairs"] > 1000
    assert narrow["concordance"] == pytest.approx(0.50, abs=0.02)
    assert "which is chance" in evidence["finding"]
    assert "NO resolving power in the narrow regime" in evidence["finding"]


def test_the_coarse_regime_is_recorded_as_working(evidence):
    """Without this contrast the finding reads as 'the model is useless'."""
    coarse = evidence["concordance_by_measured_fold_difference"]["above_2.00"]
    assert coarse["concordance"] > 0.9
    assert coarse["pairs"] > 100


def test_the_link_to_this_project_design_space_is_explicit(evidence):
    why = evidence["why_it_matters_here"]
    assert "3.2" in why and "8.4 percent" in why
    assert "fall inside the chance bin" in why
    assert "design_workflow_runs" in why


def test_the_recorded_figures_match_the_run(evidence):
    run = json.loads((ROOT / evidence["run"]).read_text())
    bands = run["B_fine_ordering"]["pairwise_concordance_by_measured_fold_difference"]
    for key, recorded in evidence["concordance_by_measured_fold_difference"].items():
        assert recorded["pairs"] == bands[key]["pairs"], key
        assert recorded["concordance"] == bands[key]["concordance"], key
    assert evidence["gc_ablation"]["delta"] == run["A_gc_ablation"]["delta"]
    assert evidence["combination"]["verdict"] == run["C_combination"]["verdict"]


def test_the_gc_consequence_points_back_at_v9(evidence):
    consequence = evidence["gc_ablation"]["consequence"]
    assert "could NOT be dropped cheaply" in consequence
    assert "strongest single feature" in consequence
    assert "real liability rather than an academic one" in consequence
    assert evidence["gc_ablation"]["verdict"] != "not_load_bearing"


def test_the_refit_is_recorded_as_adding_nothing(evidence):
    block = evidence["combination"]
    assert block["verdict"] == "prefer_the_free_predictor"
    assert "adds nothing" in block["consequence"]
    assert block["combined"] < max(block["full"], block["eternafold_only"])


def test_the_training_join_is_now_confirmed_not_inferred(evidence):
    text = evidence["training_provenance_now_confirmed"]
    assert "maximum absolute difference 0.0" in text
    assert "INFERRED in v8 is now CONFIRMED" in text
    assert "reproduces the original R feature extraction exactly" in text


def test_the_prohibition_is_explicit_and_scoped(v10):
    block = v10["prohibition_added_here"]
    assert "MUST NOT be presented as a ranking" in block["prohibition"]
    assert "orders at chance" in block["prohibition"]
    assert any("design_workflow_runs" in target for target in block["applies_to"])
    assert any("1.25" in target for target in block["applies_to"])


def test_the_coarse_filter_permission_is_not_a_loophole(v10):
    """It names the regime and the measured concordance that licenses it."""
    permitted = v10["prohibition_added_here"]["what_is_still_permitted"]
    assert "COARSE FILTER" in permitted
    assert "0.90" in permitted
    assert "greater than 2 times" in permitted
    assert "with this limitation attached" in permitted


def test_the_way_out_is_recorded_as_an_open_decision_not_taken(v10):
    block = v10["prohibition_added_here"]
    assert "Neither exists today" in block["what_would_lift_it"]
    options = block["open_decision_recorded_not_taken"]
    assert len(options) == 2
    text = " ".join(options)
    assert "coarse filter plus a diversity selector" in text
    assert "void the calibration as fitted" in text


def test_the_limitations_travel_with_the_evidence(evidence):
    text = " ".join(evidence["limitations"])
    assert "no absolute accuracy" in text
    assert "labelled reference only" in text
    assert "says nothing about the translation side" in text
    assert "1811 nt at 64.4 percent GC" in text


def test_no_earlier_prohibition_was_dropped(v9, v10):
    before, after = set(v9["what_must_not_be_claimed"]), set(v10["what_must_not_be_claimed"])
    assert before <= after
    assert len(after) == len(before) + 3
    added = " ".join(after - before)
    assert "0.5007 concordance over 2958 held-out pairs" in added
    assert "free published per-nucleotide score" in added
    assert "GC can be dropped" in added
