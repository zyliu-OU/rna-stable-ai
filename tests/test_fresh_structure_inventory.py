"""Exposure and metadata gates for the fresh-structure inventory."""

from scripts.audit_fresh_structure_inventory import inventory


def test_inventory_blocks_exposure_and_unresolved_clans():
    mappings = {
        ("RF00001", "1abc", "A"),
        ("RF00002", "2def", "A"),
        ("RF00003", "3ghi", "A"),
        ("RF00004", "4jkl", "A"),
        ("RF00005", "5mno", "A"),
    }
    exposures = [{"sequence": "ACGU", "pdb_accession": "1ABC"}]
    clans = {"RF00001": "CL00001", "RF00002": "CL00001",
             "RF00003": None, "RF00004": None}
    result = inventory(mappings, exposures, clans, {"RF00004"})
    states = {row["family_id"]: row["status"] for row in result["families"]}
    assert states == {
        "RF00001": "exposed_family",
        "RF00002": "exposed_clan",
        "RF00003": "metadata_candidate_only",
        "RF00004": "development_source_screened",
        "RF00005": "clan_unresolved",
    }
    assert result["model_inference_authorized"] is False
    assert result["independent_experimental_panel_ready"] is False
