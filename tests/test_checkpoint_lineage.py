"""Distinguish explicit source family labels from conservative PDB-level candidates."""

import importlib.util
import json
from pathlib import Path

import pytest

from rnastable.exposures import record_exposure
from rnastable.native_journal import atomic_json
from rnastable.reference import digest


@pytest.fixture
def module(monkeypatch):
    project = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(project / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "checkpoint_lineage_test", project / "scripts/audit_checkpoint_lineage.py"
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_pdb_any_chain_matches_never_become_confirmed_sequence_family_assignments(
    module,
):
    records = [
        {
            "id": "pdb",
            "sequence": "GCGCAU",
            "pdb_accession": "9ABC",
            "rna_type": "riboswitch",
        }
    ]
    result = module.describe_records(
        records,
        {("RF09998", "9abc", "A"), ("RF09999", "9abc", "B")},
        "baseline",
        "train",
    )
    assert result[0]["supplied_family_id"] is None
    assert result[0]["pdb_candidate_families"] == ["RF09998", "RF09999"]
    assert result[0]["family_provenance_status"] == "pdb_family_candidates_only"


def test_rna_type_and_organism_do_not_invent_rfam_accessions(module):
    rows = [
        {
            "id": "unresolved",
            "sequence": "GCGCAU",
            "rna_type": "16S Ribosomal RNA",
            "organism": "Aquifex aeolicus",
        }
    ]
    result = module.describe_records(rows, set(), "baseline", "train")
    assert result[0]["supplied_family_id"] is None
    assert result[0]["family_provenance_status"] == "family_unresolved"


def test_upstream_test_role_is_preserved_when_used_as_project_validation(module):
    rows = [
        {
            "id": "source-test",
            "sequence": "GCGCAU",
            "family_id": "RF00001",
            "upstream_split": "test",
        }
    ]
    result = module.describe_records(rows, set(), "baseline", "validation")
    assert result[0]["role"] == "validation" and result[0]["upstream_split"] == "test"
    assert result[0]["supplied_family_id"] == "RF00001"


@pytest.mark.parametrize(
    "field,value",
    [("family_id", "family name"), ("pdb_accession", "../bad"), ("sequence", "NNNN")],
)
def test_malformed_source_identifiers_or_sequences_fail_closed(module, field, value):
    row = {"id": "fixture", "sequence": "GCGCAU", field: value}
    with pytest.raises(ValueError):
        module.describe_records([row], set(), "baseline", "train")


@pytest.fixture
def model_source(module, tmp_path, monkeypatch):
    run = tmp_path / "model"
    run.mkdir()
    train = [
        {
            "id": "train",
            "sequence": "GCGCAU",
            "family_id": "RF00001",
            "reference_kind": "computational",
            "upstream_split": "holdout",
        }
    ]
    validation = [
        {
            "id": "val",
            "sequence": "AAAAAA",
            "reference_kind": "computational",
            "upstream_split": "test",
            "rna_type": "Group II Intron",
        }
    ]
    atomic_json(run / "train.json", {"records": train})
    atomic_json(run / "validation.json", {"records": validation})
    manifest = {
        "snapshot_sha256": {
            name: digest((run / name).read_bytes())
            for name in ("train.json", "validation.json")
        }
    }
    atomic_json(run / "manifest.json", manifest)
    (run / "weights.pt").write_bytes(b"fixture weights")
    summary = {
        "run_dir": str(run),
        "complete": True,
        "config": {"seed": 20261006},
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "exposure_events": [
            record_exposure(run, "training_started", train),
            record_exposure(run, "validation_started", validation),
        ],
    }
    atomic_json(run / "summary.json", summary)
    monkeypatch.setattr(
        module,
        "load_checkpoint",
        lambda p: (
            p.read_bytes(),
            json.loads(p.read_text())["config"],
            run / "weights.pt",
            None,
        ),
    )
    return module, run


def test_training_corpus_and_exposure_roles_are_checked_by_exact_identity(model_source):
    module, run = model_source
    result, inputs = module.inspect_models({"baseline": run / "summary.json"}, set())
    assert result["models"]["baseline"]["corpora"]["train"][
        "upstream_split_counts"
    ] == {"holdout": 1}
    assert result["models"]["baseline"]["corpora"]["validation"][
        "upstream_split_counts"
    ] == {"test": 1}
    assert (
        not result["training_tool_independence_certified"]
        and not result["new_exposure_recorded"]
    )
    assert str(run / "weights.pt") in inputs


def test_hash_consistent_dataset_metadata_still_must_match_historical_exposure(
    model_source,
):
    module, run = model_source
    data = json.loads((run / "train.json").read_text())
    data["records"][0]["family_id"] = "RF00002"
    atomic_json(run / "train.json", data)
    manifest = json.loads((run / "manifest.json").read_text())
    manifest["snapshot_sha256"]["train.json"] = digest(
        (run / "train.json").read_bytes()
    )
    atomic_json(run / "manifest.json", manifest)
    summary = json.loads((run / "summary.json").read_text())
    summary["manifest_sha256"] = digest((run / "manifest.json").read_bytes())
    atomic_json(run / "summary.json", summary)
    with pytest.raises(ValueError, match="record/exposure"):
        module.inspect_models({"baseline": run / "summary.json"}, set())


def test_changed_frozen_data_rejects_without_rehashing_or_repair(model_source):
    module, run = model_source
    p = run / "validation.json"
    p.write_bytes(p.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="data changed"):
        module.inspect_models({"baseline": run / "summary.json"}, set())
