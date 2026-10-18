"""Conservative exposure checks for mixed and local Rfam hits."""

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "crw_panel_exposure", Path(__file__).resolve().parents[1] / "scripts/audit_crw_panel_exposure.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def record():
    return {"id": "query", "status": "completed", "sequence_verified": True,
            "length_nt": 2500, "hits": [
                {"family_id": "RF00029", "clan_id": None, "start": 2400,
                 "end": 2499, "evalue": 1e-12},
                {"family_id": "RF02012", "clan_id": "CL00102", "start": 200,
                 "end": 100, "evalue": 1e-10}]}


def test_local_and_unclanned_hits_remain_possible_exposures():
    panel = [{"family_id": "RF00029", "clan_id": None},
             {"family_id": "RF99999", "clan_id": "CL00102"},
             {"family_id": "RF99998", "clan_id": None}]
    result = MODULE.summarize([record()], panel, panel)
    assert result["panel_overlap_count"] == 2
    assert result["possible_exposed_families"] == ["RF00029", "RF02012"]
    assert result["records"][0]["hits"][1]["query_span_nt"] == 101
    assert not result["full_length_lineage_gate_satisfied"]


def test_weak_hit_does_not_exclude_panel():
    query = record()
    query["hits"][0]["evalue"] = 0.1
    result = MODULE.summarize([query], [{"family_id": "RF00029", "clan_id": None}], [])
    assert result["panel_overlap_count"] == 0
    assert not result["policy"]["independent_test_claim"]


def test_rejects_unverified_sequence_and_invalid_coordinates():
    query = record()
    query["sequence_verified"] = False
    with pytest.raises(ValueError, match="sequence-bound"):
        MODULE.summarize([query], [], [])
    query["sequence_verified"] = True
    query["hits"][0]["end"] = 2501
    with pytest.raises(ValueError, match="coordinates"):
        MODULE.summarize([query], [], [])
