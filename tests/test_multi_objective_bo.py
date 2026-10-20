"""Tests for the multi-objective optimizer mechanics.

The counterpart of `test_discrete_bo.py`, for the Pareto formulation chosen on
2026-10-20. What matters here is that the mechanics are deterministic and
resumable, that the pool and feasibility contracts fail loudly, that the toy
objectives genuinely conflict so a trade-off is exercised, and that no single
"best" value is produced — which with two incommensurable objectives would be
the composite the score-record schema forbids.
"""
import pytest

pytest.importorskip("botorch")

from rnastable.multi_objective_bo import (  # noqa: E402
    run_toy_pareto,
    select_next_pareto,
    toy_objectives,
)


@pytest.fixture(scope="module")
def run():
    return run_toy_pareto(seed=7, budget=8)


def test_the_toy_objectives_conflict(run):
    """Agreeing objectives would pass the mechanics without a trade-off."""
    front = run["pareto_front"]
    assert len(front) > 1
    first = [point[0] for point in front]
    second = [point[1] for point in front]
    # Ordering by one objective must reverse the other across the front.
    pairs = sorted(zip(first, second))
    assert [b for _, b in pairs] == sorted(second, reverse=True)


def test_the_front_is_non_dominated(run):
    from rnastable.pareto import dominates

    front = [tuple(point) for point in run["pareto_front"]]
    for point in front:
        assert not any(dominates(other, point) for other in front if other != point)


def test_every_front_member_was_actually_evaluated(run):
    evaluated = {row["index"]: tuple(row["values"]) for row in run["history"]}
    for index, point in zip(run["pareto_indices"], run["pareto_front"]):
        assert evaluated[index] == tuple(point)


def test_no_single_best_value_is_reported(run):
    """With two incommensurable objectives there is no one best point."""
    assert "best_value" not in run
    assert run["protocol"]["composite_score_emitted"] is False


def test_the_budget_is_respected_and_evaluations_are_unique(run):
    assert run["unique_evaluations"] == 8
    indices = [row["index"] for row in run["history"]]
    assert len(set(indices)) == len(indices) == 8


def test_the_initial_design_is_fixed_and_the_rest_is_acquired(run):
    assert [row["index"] for row in run["history"][:3]] == [0, 10, 30]
    assert all(row["log_acquisition"] is None for row in run["history"][:3])
    assert all(row["log_acquisition"] is not None for row in run["history"][3:])


def test_infeasible_pool_members_are_never_evaluated(run):
    features = run["protocol"]["features"]
    for row in run["history"]:
        assert not 0.40 <= features[row["index"]][0] <= 0.60


def test_the_run_is_deterministic():
    a = run_toy_pareto(seed=7, budget=8)
    b = run_toy_pareto(seed=7, budget=8)
    assert a["history"] == b["history"]
    assert a["hypervolume"] == b["hypervolume"]
    assert a["pareto_indices"] == b["pareto_indices"]


def test_resume_reproduces_the_uninterrupted_run(run):
    partial = {"protocol": run["protocol"], "history": run["history"][:5]}
    resumed = run_toy_pareto(seed=7, budget=8, state=partial)
    assert resumed["history"] == run["history"]
    assert resumed["pareto_indices"] == run["pareto_indices"]


def test_resume_rejects_a_different_protocol(run):
    tampered = dict(run["protocol"], budget=9)
    with pytest.raises(ValueError):
        run_toy_pareto(seed=7, budget=8, state={"protocol": tampered, "history": []})


def test_resume_rejects_a_tampered_cached_objective(run):
    history = [dict(row) for row in run["history"][:4]]
    history[3]["values"] = [row + 1.0 for row in history[3]["values"]]
    with pytest.raises(ValueError):
        run_toy_pareto(seed=7, budget=8,
                       state={"protocol": run["protocol"], "history": history})


def test_hypervolume_shares_the_recorded_reference_point(run):
    from rnastable.pareto import hypervolume_2d

    reference = tuple(run["protocol"]["reference_point"])
    rows = [tuple(row["values"]) for row in run["history"]]
    assert run["hypervolume"] == pytest.approx(hypervolume_2d(rows, reference))
    assert run["random_hypervolume"] == pytest.approx(
        hypervolume_2d([toy_objectives(i / 30) for i in run["random_indices"]], reference))


def test_a_random_baseline_is_reported_beside_the_optimizer(run):
    """Without it, a hypervolume number says nothing about the optimizer."""
    assert run["random_hypervolume"] > 0
    assert len(run["random_indices"]) == run["unique_evaluations"]


def test_only_two_objectives_are_supported():
    features, feasible = [[0.0], [1.0]], [True, True]
    observed = {0: (0.0, 0.0, 0.0), 1: (1.0, 1.0, 1.0)}
    with pytest.raises(ValueError):
        select_next_pareto(features, observed, feasible, 7, (0.0, 0.0, 0.0))


def test_the_pool_and_observation_contracts_fail_loudly():
    features, feasible = [[0.0], [0.5], [1.0]], [True, True, True]
    good = {0: (0.0, 1.0), 2: (1.0, 0.0)}
    with pytest.raises(ValueError):  # features outside [0, 1]
        select_next_pareto([[0.0], [2.0]], {0: (0.0, 1.0), 1: (1.0, 0.0)},
                           [True, True], 7, (0.0, 0.0))
    with pytest.raises(ValueError):  # duplicate pool representations
        select_next_pareto([[0.5], [0.5]], {0: (0.0, 1.0), 1: (1.0, 0.0)},
                           [True, True], 7, (0.0, 0.0))
    with pytest.raises(ValueError):  # feasibility length mismatch
        select_next_pareto(features, good, [True, True], 7, (0.0, 0.0))
    with pytest.raises(ValueError):  # too few observations
        select_next_pareto(features, {0: (0.0, 1.0)}, feasible, 7, (0.0, 0.0))
    with pytest.raises(ValueError):  # observation on an infeasible member
        select_next_pareto(features, good, [True, True, False], 7, (0.0, 0.0))
    with pytest.raises(ValueError):  # non-finite objective value
        select_next_pareto(features, {0: (0.0, float("nan")), 2: (1.0, 0.0)},
                           feasible, 7, (0.0, 0.0))
    with pytest.raises(ValueError):  # nothing left to evaluate
        select_next_pareto([[0.0], [1.0]], {0: (0.0, 1.0), 1: (1.0, 0.0)},
                           [True, True], 7, (0.0, 0.0))


def test_it_designs_no_rna(run):
    """Expression candidate design is gate-disabled; this must not open it."""
    assert "no_RNA" in run["protocol"]["meaning"]
    features = run["protocol"]["features"]
    assert all(len(row) == 1 and 0.0 <= row[0] <= 1.0 for row in features)
