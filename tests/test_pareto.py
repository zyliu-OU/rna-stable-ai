"""Tests for the Pareto bookkeeping.

These objectives are incommensurable by construction, so the thing most worth
pinning is what the module refuses to do: no weighting, no shared unit, no
single number standing for a candidate. The rest pins the comparison logic,
where a sign or a tie-handling mistake would be silent.
"""
import pytest

from rnastable.pareto import (
    as_maximization,
    dominates,
    hypervolume_2d,
    non_dominated_indices,
    pareto_front,
)


def test_dominance_requires_at_least_as_good_everywhere():
    assert dominates((2.0, 2.0), (1.0, 1.0))
    assert dominates((2.0, 1.0), (1.0, 1.0))
    assert not dominates((2.0, 0.0), (1.0, 1.0))
    assert not dominates((1.0, 1.0), (2.0, 2.0))


def test_equal_points_do_not_dominate_each_other():
    """A front should keep ties rather than discard one arbitrarily."""
    assert not dominates((1.0, 1.0), (1.0, 1.0))
    assert non_dominated_indices([(1.0, 1.0), (1.0, 1.0)]) == [0, 1]


def test_dominance_rejects_mismatched_objective_counts():
    with pytest.raises(ValueError):
        dominates((1.0, 1.0), (1.0,))


def test_non_dominated_indices_are_returned_in_input_order():
    rows = [(1.0, 3.0), (2.0, 2.0), (3.0, 1.0), (1.5, 1.5)]
    assert non_dominated_indices(rows) == [0, 1, 2]


def test_a_single_point_is_its_own_front():
    assert non_dominated_indices([(0.5, 0.5)]) == [0]


def test_minimized_objectives_are_flipped_before_comparison():
    rows = [(1.0, 10.0), (2.0, 20.0)]
    assert as_maximization(rows, ("maximize", "minimize")) == [(1.0, -10.0), (2.0, -20.0)]
    # With the second objective minimized, neither point dominates the other.
    assert pareto_front(rows, ("maximize", "minimize")) == [0, 1]
    # With both maximized, the second dominates the first.
    assert pareto_front(rows, ("maximize", "maximize")) == [1]


def test_directions_must_be_explicit_and_valid():
    with pytest.raises(ValueError):
        as_maximization([(1.0, 1.0)], ("maximize", "bigger"))
    with pytest.raises(ValueError):
        as_maximization([(1.0, 1.0)], ())
    with pytest.raises(ValueError):
        as_maximization([(1.0, 1.0, 1.0)], ("maximize", "minimize"))


def test_non_finite_objective_values_are_rejected():
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError):
            as_maximization([(1.0, bad)], ("maximize", "maximize"))


def test_hypervolume_of_one_point_is_its_rectangle():
    assert hypervolume_2d([(2.0, 3.0)], (0.0, 0.0)) == pytest.approx(6.0)
    assert hypervolume_2d([(2.0, 3.0)], (1.0, 1.0)) == pytest.approx(2.0)


def test_hypervolume_adds_only_the_newly_dominated_strip():
    """Two points sharing area must not have that area counted twice."""
    assert hypervolume_2d([(1.0, 2.0), (2.0, 1.0)], (0.0, 0.0)) == pytest.approx(3.0)


def test_a_dominated_point_adds_no_hypervolume():
    assert hypervolume_2d([(2.0, 2.0), (1.0, 1.0)], (0.0, 0.0)) == pytest.approx(4.0)


def test_points_not_beating_the_reference_contribute_nothing():
    """Not a negative area, which a naive sweep would produce."""
    assert hypervolume_2d([(0.5, 0.5)], (1.0, 1.0)) == 0.0
    assert hypervolume_2d([(2.0, 0.5)], (1.0, 1.0)) == 0.0
    assert hypervolume_2d([], (0.0, 0.0)) == 0.0


def test_hypervolume_is_two_objectives_only():
    with pytest.raises(ValueError):
        hypervolume_2d([(1.0, 1.0, 1.0)], (0.0, 0.0, 0.0))


def test_the_module_does_not_import_torch_or_botorch():
    """The bookkeeping must be auditable without the optimizer."""
    import ast

    source = __import__("rnastable.pareto", fromlist=["pareto"]).__file__
    tree = ast.parse(open(source).read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not imported & {"torch", "botorch", "gpytorch"}, imported


def test_nothing_here_combines_two_objectives_into_one():
    """The prohibition the Pareto formulation exists to respect."""
    import rnastable.pareto as module
    exported = [name for name in dir(module) if not name.startswith("_")]
    for banned in ("composite", "weighted", "score", "combine", "total"):
        assert not any(banned in name.lower() for name in exported), banned
