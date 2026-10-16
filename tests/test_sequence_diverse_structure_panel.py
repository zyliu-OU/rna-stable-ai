"""Metadata-only stratification for the second fresh-structure panel."""

import pytest

from scripts.plan_sequence_diverse_structure_panel import evenly_spaced, select


def config():
    return {
        "stage": "metadata_only_sequence_diverse_structure_panel",
        "families": [f"RF{i:05d}" for i in range(1, 9)],
        "minimum_pdb_chains_per_family": 5,
        "maximum_pdb_chains_per_family": 5,
        "candidate_order": "family_then_evenly_spaced_sorted_distinct_pdb_then_first_chain",
        "future_binding": {
            "minimum_length": 20,
            "maximum_length": 512,
            "sequence_similarity_threshold": 0.8,
            "maximum_supported_records_per_family": 4,
            "contact_target": "all_returned_cWW_contacts_without_projection",
            "multiple_partners": "unsupported_do_not_delete_contacts",
            "replace_unsupported_records": False,
            "minimum_supported_total": 12,
            "minimum_supported_families": 3,
            "minimum_supported_per_family": 3,
            "reference_kind": "computational_PDB_derived",
            "require_per_sequence_annotation_audit": True,
            "require_tool_training_provenance_audit": True,
        },
        "structure_labels_allowed_at_freeze": False,
        "candidate_sequences_allowed_at_freeze": False,
        "model_inference_authorized": False,
    }


def inventory():
    return {
        "stage": "metadata_only_inventory",
        "annotation_labels_read": False,
        "candidate_sequences_bound": False,
        "model_inference_authorized": False,
        "families": [{
            "family_id": f"RF{i:05d}",
            "status": "metadata_candidate_only",
            "unexposed_pdb_count": 8,
            "clan_id": f"CL{i:05d}" if i <= 4 else None,
        } for i in range(1, 9)],
    }


def test_evenly_spaced_covers_full_sorted_range():
    assert evenly_spaced(list("abcdefgh"), 4) == ["a", "c", "f", "h"]


def test_selection_is_metadata_only_stratified_and_exposure_safe():
    mappings = set()
    for i in range(1, 9):
        family = f"RF{i:05d}"
        for j in range(8):
            mappings.add((family, f"{i}{j:03d}", "B"))
            mappings.add((family, f"{i}{j:03d}", "A"))
    exposures = [{"sequence": "ACGU", "pdb_accession": "1000"}]
    result = select(config(), inventory(), mappings, exposures)
    assert result["candidate_counts"] == {f"RF{i:05d}": 5 for i in range(1, 9)}
    assert all(row["chain_id"] == "A" for row in result["candidates"])
    assert all(row["pdb_accession"] != "1000" for row in result["candidates"])
    assert result["selection_used_structure_labels"] is False
    assert result["model_inference_authorized"] is False


def test_selection_rejects_exposed_family():
    data = inventory()
    data["families"][0]["status"] = "exposed_family"
    with pytest.raises(ValueError, match="metadata/exposure"):
        select(config(), data, set(), [])
