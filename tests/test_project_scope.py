"""The active length boundary must preserve deferred long-sequence records."""

import pytest

from rnastable.project_scope import (
    length_scope,
    load_policy,
    partition_records,
    require_active_length,
)


def test_exclusive_5000_nt_boundary():
    policy = load_policy()
    assert length_scope(1, policy) == "active_under_5000_nt"
    assert length_scope(4999, policy) == "active_under_5000_nt"
    assert length_scope(5000, policy) == "deferred_5000_nt_or_longer"
    assert length_scope(10000, policy) == "deferred_5000_nt_or_longer"
    assert require_active_length(4999, policy) == 4999
    with pytest.raises(ValueError, match="under 5000"):
        require_active_length(5000, policy)


def test_partition_preserves_long_records_without_truncation():
    records = [
        {"id": "short", "sequence": "A" * 4999},
        {"id": "boundary", "sequence": "C" * 5000},
        {"id": "long", "sequence": "G" * 10000},
    ]
    result = partition_records(records)
    assert [row["id"] for row in result["active_under_5000_nt"]] == ["short"]
    assert [row["id"] for row in result["deferred_5000_nt_or_longer"]] == [
        "boundary", "long"
    ]
    assert len(result["deferred_5000_nt_or_longer"][0]["sequence"]) == 5000
    assert len(result["deferred_5000_nt_or_longer"][1]["sequence"]) == 10000


@pytest.mark.parametrize("length", [0, -1, True, 1.5])
def test_invalid_lengths_are_rejected(length):
    with pytest.raises(ValueError):
        length_scope(length)
