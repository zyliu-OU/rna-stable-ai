"""Pareto bookkeeping for two incommensurable objectives.

The project's two score sides cannot be combined: stability is in hours on the
released STRAND in-solution scale, translation is on a released RiboNN task
scale with no inverse transform or physical unit, no weighting is justified and
`score_record_schema_v1` forbids emitting a composite.

A Pareto front is the way through that rather than around it. Dominance compares
objectives **coordinate-wise**, so it never needs them to share a unit, never
needs a weight, and never produces a single number standing for both. Nothing in
this module reduces two objectives to one, and the hypervolume below is reported
as a diagnostic of a *set*, never attached to a candidate as its score.

Everything here is pure Python. It does not import torch or botorch, so the
bookkeeping is testable and auditable without the optimizer.
"""

DIRECTIONS = ("maximize", "minimize")


def as_maximization(rows, directions):
    """Flip minimized objectives so every coordinate is maximized.

    Dominance and hypervolume below assume maximization throughout. Doing the
    flip here, once, from an explicit direction per objective, keeps the sign
    convention out of the comparison logic where a mistake would be silent.
    """
    rows = [tuple(row) for row in rows]
    directions = tuple(directions)
    if not directions or any(d not in DIRECTIONS for d in directions):
        raise ValueError(f"Each direction must be one of {DIRECTIONS}")
    for row in rows:
        if len(row) != len(directions):
            raise ValueError("Objective count differs from the direction count")
        if any(value != value or value in (float("inf"), float("-inf")) for value in row):
            raise ValueError("Objective values must be finite")
    signs = tuple(1.0 if d == "maximize" else -1.0 for d in directions)
    return [tuple(sign * value for sign, value in zip(signs, row)) for row in rows]


def dominates(a, b):
    """True when a is at least as good everywhere and strictly better somewhere.

    Maximization in every coordinate. Equal points do not dominate each other,
    so a front keeps ties rather than arbitrarily discarding one of them.
    """
    if len(a) != len(b):
        raise ValueError("Objective count mismatch")
    return all(x >= y for x, y in zip(a, b)) and any(x > y for x, y in zip(a, b))


def non_dominated_indices(rows):
    """Indices of the non-dominated rows, in input order.

    Quadratic, which is the right trade at the cohort sizes this project works
    at and keeps the definition readable.
    """
    rows = [tuple(row) for row in rows]
    return [i for i, row in enumerate(rows)
            if not any(dominates(other, row) for j, other in enumerate(rows) if j != i)]


def pareto_front(rows, directions):
    """Non-dominated indices for rows given per-objective directions."""
    return non_dominated_indices(as_maximization(rows, directions))


def hypervolume_2d(rows, reference):
    """Exact dominated hypervolume for two maximized objectives.

    `reference` is the lower-left corner: a point every candidate is expected to
    beat, chosen deliberately rather than inferred, because the number is only
    comparable across runs that share it. Points failing to dominate the
    reference in both coordinates contribute nothing instead of a negative area.

    This is a diagnostic of how much objective space a *set* covers. It is not a
    candidate's score and must not be used as one: that would be the composite
    the schema forbids, reached by a different route.
    """
    reference = tuple(reference)
    if len(reference) != 2:
        raise ValueError("Exactly two objectives are supported")
    points = sorted(
        (tuple(row) for row in rows
         if len(row) == 2 and row[0] > reference[0] and row[1] > reference[1]),
        key=lambda p: (-p[0], -p[1]),
    )
    total, ceiling = 0.0, reference[1]
    for x, y in points:
        # Sweeping from the largest first objective, each point contributes only
        # the strip above the best second objective already seen; dominated
        # points contribute zero width and are skipped implicitly.
        if y > ceiling:
            total += (x - reference[0]) * (y - ceiling)
            ceiling = y
    return total
