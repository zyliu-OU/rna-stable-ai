"""The long exact recurrence agrees with the established short decoder."""

import numpy as np
import pytest

from rnastable.exact_sparse_pairs import decode_exact_sparse
from rnastable.long_exact_sparse_pairs import decode_long_exact_sparse


def test_short_exact_agreement_with_crossing_candidates():
    sequence = "G" * 20 + "C" * 20
    pairs = np.array([[0, 39], [1, 38], [2, 37], [0, 30], [10, 39]], dtype=np.int32)
    scores = np.array([1.0, 1.1, 1.2, 2.0, 2.1])
    original = decode_exact_sparse(sequence, pairs, scores)
    longer = decode_long_exact_sparse(sequence, pairs, scores)
    assert longer["structure"] == original["structure"]
    assert longer["objective"] == original["objective"]
    assert longer["accepted_pairs"] == original["accepted_pairs"]


def test_4999_nt_array_bound_and_scope():
    result = decode_long_exact_sparse("A" * 4999, np.empty((0, 2), dtype=np.int32),
                                      np.empty(0))
    assert result["dp_array_bytes"] <= 300 * 1024 * 1024
    assert result["accepted_pairs"] == 0
    with pytest.raises(ValueError, match="4,999"):
        decode_long_exact_sparse("A" * 5000, np.empty((0, 2), dtype=np.int32),
                                 np.empty(0))
