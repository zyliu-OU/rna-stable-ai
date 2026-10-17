"""Exact noncrossing decoding of retained candidates below 5,000 nt.

This extends the existing short exact recurrence with an explicit array budget.
It is a development method and does not replace any frozen inference default.
"""

import numpy as np

from .pair_model import CANONICAL
from .sequences import validate_sequence

MAX_DP_BYTES = 300 * 1024 * 1024


def decode_long_exact_sparse(sequence, pairs, scores):
    validate_sequence(sequence)
    n = len(sequence)
    if n > 4999:
        raise ValueError("Active long exact decoder supports at most 4,999 nt")
    dp_bytes = n * n * (np.dtype(np.float64).itemsize + np.dtype(np.int32).itemsize)
    if dp_bytes > MAX_DP_BYTES:
        raise ValueError("Long exact decoder exceeds its 300 MiB array budget")
    pairs = np.asarray(pairs)
    scores = np.asarray(scores, dtype=np.float64)
    if (pairs.ndim != 2 or pairs.shape[1] != 2
            or not np.issubdtype(pairs.dtype, np.integer)
            or scores.shape != (len(pairs),)
            or not np.isfinite(scores).all()):
        raise ValueError("Expected integer candidate pairs with finite scores")
    if len({tuple(map(int, pair)) for pair in pairs}) != len(pairs):
        raise ValueError("Duplicate candidate pairs")
    by_right = [[] for _ in range(n)]
    for (left, right), score in zip(pairs, scores, strict=True):
        left, right = int(left), int(right)
        if (not 0 <= left < right < n or right - left < 4
                or sequence[left] + sequence[right] not in CANONICAL):
            raise ValueError("Illegal sparse candidate pair")
        if score > 0:
            by_right[right].append((left, float(score)))
    if any(len(rows) > 64 for rows in by_right):
        raise ValueError("Long exact decoder supports at most 64 candidates per endpoint")
    dp = np.zeros((n, n), dtype=np.float64)
    choice = np.full((n, n), -1, dtype=np.int32)
    for right in range(n):
        if right:
            dp[:right, right] = dp[:right, right - 1]
        for partner, score in sorted(by_right[right]):
            before = dp[:partner + 1, partner - 1].copy() if partner else np.zeros(1)
            before[partner] = 0
            candidate = before + score + dp[partner + 1, right - 1]
            better = candidate > dp[:partner + 1, right]
            dp[:partner + 1, right][better] = candidate[better]
            choice[:partner + 1, right][better] = partner
    structure = ["."] * n
    intervals = [(0, n - 1)]
    while intervals:
        left, right = intervals.pop()
        if left >= right:
            continue
        partner = int(choice[left, right])
        if partner < 0:
            intervals.append((left, right - 1))
        else:
            structure[partner], structure[right] = "(", ")"
            intervals.extend(((left, partner - 1), (partner + 1, right - 1)))
    return {"structure": "".join(structure), "objective": float(dp[0, n - 1]),
            "accepted_pairs": structure.count("("), "dp_array_bytes": dp_bytes,
            "interpretation": "Exact maximum positive logit sum over retained sparse candidates; O(n²) arrays and O(n × candidates) work."}
