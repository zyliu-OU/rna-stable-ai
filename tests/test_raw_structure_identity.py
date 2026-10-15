"""A matching sequence alone does not certify source identity or contact coordinates."""

import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def module(monkeypatch):
    project = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(project / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "raw_structure_identity_test",
        project / "scripts/verify_raw_structure_identity.py",
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.fixture
def data():
    return {
        "pdb_id": "9ABC",
        "chain_id": "A",
        "sequence": "GCGCAU",
        "annotations": [
            {"seq_id1": "1", "seq_id2": "6", "nt1": "G", "nt2": "U", "bp": "cWW"}
        ],
    }


def test_returned_pdb_case_is_normalized_but_chain_case_is_preserved(module, data):
    row = module.validate_identity(
        json.dumps(data).encode(), {"pdb_accession": "9abc", "chain_id": "A"}
    )
    assert row["validated_cww_rows"] == 1
    data["chain_id"] = "a"
    with pytest.raises(ValueError, match="chain"):
        module.validate_identity(
            json.dumps(data).encode(), {"pdb_accession": "9abc", "chain_id": "A"}
        )


@pytest.mark.parametrize(
    "change",
    [
        "pdb",
        "chain",
        "nt1",
        "nt2",
        "zero",
        "out_of_bounds",
        "boolean",
        "missing_identifier",
    ],
)
def test_wrong_identity_or_nucleotide_mapping_cannot_certify_a_valid_looking_graph(
    module, data, change
):
    if change == "pdb":
        data["pdb_id"] = "9ABD"
    elif change == "chain":
        data["chain_id"] = "B"
    elif change in ("nt1", "nt2"):
        data["annotations"][0][change] = "A"
    elif change == "zero":
        data["annotations"][0]["seq_id1"] = 0
    elif change == "out_of_bounds":
        data["annotations"][0]["seq_id1"] = 7
    elif change == "boolean":
        data["annotations"][0]["seq_id1"] = True
    else:
        data.pop("pdb_id")
    with pytest.raises(ValueError):
        module.validate_identity(
            json.dumps(data).encode(), {"pdb_accession": "9abc", "chain_id": "A"}
        )


def test_non_cww_contacts_are_also_checked_for_coordinate_identity(module, data):
    data["annotations"][0].update(bp="tWW", nt1="C")
    with pytest.raises(ValueError, match="nucleotide"):
        module.validate_identity(
            json.dumps(data).encode(), {"pdb_accession": "9abc", "chain_id": "A"}
        )
