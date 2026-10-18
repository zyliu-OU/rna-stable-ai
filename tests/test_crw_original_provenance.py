"""Alignment evidence must disclose clipping and sequence differences."""

import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "crw_original_provenance", Path(__file__).resolve().parents[1] / "scripts/audit_crw_original_provenance.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_exact_internal_query_has_no_clipping():
    result = MODULE.alignment_evidence("AAAAACGUACGUGGGG", "ACGUACGU")
    assert result["exact_full_query_substring"]
    assert result["identities"] == 8
    assert result["query_aligned_nt"] == 8
    assert result["mismatches"] == result["query_unaligned_prefix_nt"] == 0


def test_local_match_discloses_unaligned_query_ends():
    result = MODULE.alignment_evidence("ACGUACGUACGU", "NNNACGUACGUACGUNN")
    assert not result["exact_full_query_substring"]
    assert result["query_unaligned_prefix_nt"] == 3
    assert result["query_unaligned_suffix_nt"] == 2
    assert result["identities"] == 12


def test_internal_insertion_is_not_counted_as_identity():
    query = "ACGUACGUACGUACGU" + "N" + "UGCAUGCAUGCAUGCA"
    result = MODULE.alignment_evidence(query.replace("N", ""), query)
    assert result["query_inserted_bases"] == 1
    assert result["identities"] == len(query) - 1
    assert result["mismatches"] == 0
    assert result["query_aligned_nt"] == len(query)
