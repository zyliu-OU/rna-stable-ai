"""Tests for the Pareto mechanics run and the formulation that governs it.

A formulation decision is the easiest place for a prohibition to be lost: the
reason to use a Pareto front at all is that no composite score is permitted, so
these tests pin that the artifact emits none, that the run designs no RNA, that
it does not quietly open the gate's campaign switches, and that its three seeds
are not presented as three independent confirmations when they are not.
"""
import glob
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FORMULATION = ROOT / "configs/pareto_objective_formulation_v1_2026-10-20.json"
RUNS = sorted(glob.glob(str(ROOT / "results/pareto_mechanics_runs/*/summary.json")))


@pytest.fixture(scope="module")
def formulation():
    return json.loads(FORMULATION.read_text())


@pytest.fixture(scope="module")
def run():
    if not RUNS:
        pytest.skip("Pareto mechanics not run")
    return json.loads(Path(RUNS[-1]).read_text())


def test_both_objectives_are_named_with_a_unit_and_a_direction(formulation):
    objectives = formulation["objectives"]
    assert len(objectives) == 2
    assert {o["side"] for o in objectives} == {"stability", "translation"}
    for objective in objectives:
        assert objective["direction"] == "maximize"
        assert objective["unit"] and objective["quantity"] and objective["source"]
        assert objective["caveat"]


def test_the_formulation_states_why_it_is_not_a_scalarisation(formulation):
    why = formulation["why"]
    assert "coordinate-wise" in why["why_pareto_is_not_a_workaround"]
    assert "neither a shared unit nor a weight" in why["why_pareto_is_not_a_workaround"]
    assert "weighted sum" in why["what_was_rejected"]


def test_the_reference_point_is_required_and_not_inferred(formulation):
    policy = formulation["reference_point_policy"]
    assert policy["required"] is True
    assert policy["inferred"] is False
    assert "NOT SELECTED" in policy["values_for_the_real_scales"]


def test_hypervolume_may_not_be_used_as_a_candidate_score(formulation):
    rule = formulation["hypervolume_is_a_set_diagnostic"]
    assert "MUST NOT be attached to a candidate" in rule["prohibition"]
    assert "random-selection baseline" in rule["reported_beside"]


def test_the_formulation_does_not_open_the_campaign_switches(formulation):
    unchanged = formulation["does_not_change"]
    for key in ("expression_candidate_design_enabled", "new_sequence_scoring_enabled",
                "stability_score_enabled", "model_defaults_changed"):
        assert unchanged[key] is False, key
    assert "not permission to run it" in unchanged["note"]
    assert "stage2_to_stage3_gate_v5_2026-10-20.json" in unchanged["gate"]
    gate = json.loads(
        (ROOT / "configs/stage2_to_stage3_gate_v5_2026-10-20.json").read_text())
    assert gate["expression_candidate_design_enabled"] is False
    assert gate["new_sequence_scoring_enabled"] is False


def test_the_blocking_items_name_the_design_space_problem(formulation):
    items = {item["item"]: item for item in formulation["blocking_before_a_real_campaign"]}
    assert "design space parameterisation" in items
    detail = items["design space parameterisation"]["detail"]
    assert "551 codons" in detail
    assert "10^273" in detail
    assert items["design space parameterisation"]["status"] == "not decided"
    assert "base-pair span policy" in items
    assert "assay side" in items
    assert "proxy quality" in items


def test_the_run_emits_no_composite_and_no_single_best(run):
    assert run["composite_score_emitted"] is False
    for seed in run["seeds"].values():
        assert "best_value" not in seed
        assert seed["protocol"]["composite_score_emitted"] is False
    text = " ".join(run["no_claim"])
    assert "No single best candidate is reported" in text
    assert "must not be attached to a candidate" in text


def test_the_run_designed_and_scored_no_rna(run):
    assert run["rna_designed"] is False
    assert run["rna_scored"] is False
    for seed in run["seeds"].values():
        assert "no_RNA" in seed["protocol"]["meaning"]


def test_every_front_is_non_dominated_and_resumable(run):
    assert run["all_fronts_non_dominated"] is True
    assert run["all_resumes_reproduced"] is True
    for seed in run["seeds"].values():
        assert seed["front_is_non_dominated"] is True
        assert seed["resume_reproduces_the_run"] is True
        assert seed["front_size"] > 1, "a one-point front exercises no trade-off"


def test_the_front_really_is_non_dominated(run):
    """Checked here too, rather than trusting the run's own flag."""
    from rnastable.pareto import dominates

    for seed in run["seeds"].values():
        points = [tuple(point) for point in seed["pareto_front"]]
        for point in points:
            assert not any(dominates(other, point) for other in points if other != point)


def test_the_optimizer_is_compared_against_a_random_baseline(run):
    assert run["optimizer_ahead_of_random_on_every_seed"] is True
    for seed in run["seeds"].values():
        assert seed["hypervolume"] > seed["random_hypervolume"]


def test_the_seeds_are_not_presented_as_independent_confirmations(run):
    """They select the same points, and the artifact must say so."""
    sensitivity = run["seed_sensitivity"]
    assert sensitivity["distinct_optimizer_hypervolumes"] == 1
    assert sensitivity["distinct_optimizer_histories"] == 1
    assert "NOT three independent confirmations" in sensitivity["interpretation"]
    assert "does not demonstrate robustness to seed" in sensitivity["interpretation"]


def test_the_pinned_optimizer_versions_are_recorded(run):
    versions = run["versions"]
    assert versions["botorch"] == "0.18.1"
    assert versions["gpytorch"] == "1.15.2"
    assert versions["linear_operator"] == "0.6.1"
    pinned = json.loads(
        (ROOT / "configs/four_component_build_v1_2026-10-18.json").read_text()
    )["required_optimizer_versions"]
    for name, version in pinned.items():
        assert versions[name] == version, name


def test_the_run_links_the_formulation_and_the_gate(run):
    assert run["formulation"] == "configs/pareto_objective_formulation_v1_2026-10-20.json"
    assert run["gate"] == "configs/stage2_to_stage3_gate_v5_2026-10-20.json"
    assert (ROOT / run["formulation"]).exists()
    assert (ROOT / run["gate"]).exists()
