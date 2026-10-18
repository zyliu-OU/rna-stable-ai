"""Metadata source triage must not promote partial or exposed RNA models."""

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_rcsb_long_source_leads import disposition
from inspect_rcsb_long_shortlist import validate_batch
from inspect_rcsb_long_coverage_v2 import validate, QUERY
from survey_rcsb_long_rna_metadata import queries


def status(**changes):
    args = dict(full_model=True, exposed_pdb=False, exposed_family=False,
                exposed_clan=False, group_ii=False,
                description="Genomic RNA", title="Phage virion")
    args.update(changes)
    return disposition(**args)


def test_partial_model_cannot_advance_as_source_lead():
    assert status(full_model=False) == "no_full_length_model_by_residue_count"
    assert status() == "source_lead_lineage_sequence_and_contacts_unresolved"


def test_exposures_and_quarantine_override_full_coverage():
    assert status(exposed_pdb=True) == "exposed_pdb"
    assert status(exposed_family=True) == "exposed_family"
    assert status(exposed_clan=True) == "exposed_clan"
    assert status(group_ii=True) == "quarantined_group_II_architecture"


def test_generic_rna_description_does_not_hide_ribosome_context():
    assert status(title="Mitochondrial ribosome") == "ribosome_context_requires_entity_identity"
    assert status(description="LSUb_rRNA_chain_2") == "ribosomal_description_requires_family_binding"


def test_metadata_response_rejects_missing_duplicate_and_outside_scope():
    row = {"rcsb_id": "7LHD_1", "entity_poly": {"type": "polyribonucleotide", "rcsb_sample_sequence_length": 4217}}
    with pytest.raises(ValueError, match="identities"):
        validate_batch({"data": {"polymer_entities": [row, row]}}, ["7LHD_1"])
    with pytest.raises(ValueError, match="identities"):
        validate_batch({"data": {"polymer_entities": [None]}}, ["7LHD_1"])
    row["entity_poly"]["rcsb_sample_sequence_length"] = 5000
    with pytest.raises(ValueError, match="outside"):
        validate_batch({"data": {"polymer_entities": [row]}}, ["7LHD_1"])


def test_coverage_response_rejects_graphql_errors_and_missing_instances():
    with pytest.raises(ValueError):
        validate({"errors": [{"message": "field undefined"}]}, ["7LHD.A"])
    with pytest.raises(ValueError, match="identity"):
        validate({"data": {"polymer_entity_instances": [None]}}, ["7LHD.A"])


def test_corrected_instance_fields_exist_in_official_schema():
    schema = json.loads((ROOT / "tests/fixtures/rcsb_instance_schema_2026-10-18.json").read_text())
    assert "rcsb_polymer_entity_instance_container_identifiers" in schema["properties"]
    assert "modeled_residue_count" in schema["properties"]["rcsb_polymer_instance_info"]["properties"]
    assert "rcsb_polymer_entity_instance_container_identifiers" in QUERY
    for query in queries().values():
        assert query["request_options"]["results_content_type"] == ["experimental"]
        nodes = query["query"]["nodes"]
        bounds = nodes[1]["parameters"]["value"]
        assert bounds == {"from": 1000, "to": 4999, "include_lower": True, "include_upper": True}
