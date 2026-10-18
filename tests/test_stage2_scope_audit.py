"""Scope boundaries and weighting must remain explicit in readiness evidence."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_stage2_under3000 import aggregate


def test_bands_and_family_balance_are_distinct():
    result = aggregate([
        {"length_nt": 999, "family_id": "a", "pair_f1": 0.2},
        {"length_nt": 1000, "family_id": "a", "pair_f1": 0.4},
        {"length_nt": 2999, "family_id": "b", "pair_f1": 0.9}])
    assert result["mean_record_pair_f1"] == pytest.approx(0.5)
    assert result["mean_family_pair_f1"] == pytest.approx(0.6)
    assert [r["n"] for r in result["bands"].values()] == [1, 1, 1]


def test_out_of_scope_records_cannot_silently_inflate_aggregate():
    with pytest.raises(ValueError, match="1-2999"):
        aggregate([{"length_nt": 3000, "family_id": "a", "pair_f1": 1.0}])


def test_absent_band_is_unknown_instead_of_zero_accuracy():
    result = aggregate([])
    assert result["mean_record_pair_f1"] is None
    assert all(r["n"] == 0 and r["mean_pair_f1"] is None for r in result["bands"].values())
