"""Raw feasibility references preserve graph and source failures before evaluation."""

import importlib.util
import json
from pathlib import Path

import pytest

from rnastable.native_journal import atomic_json
from rnastable.reference import digest


@pytest.fixture
def module(monkeypatch):
    project = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(project / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "raw_structure_references_test",
        project / "scripts/prepare_raw_structure_references.py",
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def response(pairs=((1, 6), (2, 5)), sequence="GCGCAU"):
    return json.dumps(
        {
            "sequence": sequence,
            "annotations": [
                {"bp": "cWW", "seq_id1": a, "seq_id2": b} for a, b in pairs
            ],
        }
    ).encode()


@pytest.fixture
def selected():
    return {
        "id": "RF09999:9abc_A",
        "family_id": "RF09999",
        "pdb_accession": "9abc",
        "chain_id": "A",
        "filename": "record_000.json",
        "sequence": "GCGCAU",
        "sequence_sha256": digest(b"GCGCAU"),
    }


def test_raw_multiple_partner_graph_is_retained_and_not_projected(
    module, selected, tmp_path
):
    (tmp_path / selected["filename"]).write_bytes(response([(1, 6), (2, 5), (1, 3)]))
    result = module.bind_graphs(tmp_path, [selected], ["RF09999"])
    row = result["records"][0]
    assert row["reference_status"] == "unsupported_reference" and "pairs" not in row
    assert row["raw_cww_pairs"] == [[0, 2], [0, 5], [1, 4]]
    assert result["planned_records"] == 1 and result["supported_references"] == 0


def test_crossing_and_noncanonical_cww_contacts_remain_in_gold(
    module, selected, tmp_path
):
    (tmp_path / selected["filename"]).write_bytes(response([(1, 4), (2, 6)]))
    result = module.bind_graphs(tmp_path, [selected], ["RF09999"])
    row = result["records"][0]
    assert row["reference_status"] == "ok" and row["reference_has_crossing_pairs"]
    assert row["pairs"] == [[0, 3], [1, 5]]


@pytest.fixture
def plan():
    return {"minimum_length": 1, "maximum_length": 512, "max_records_per_family": 1}


def test_sequence_redundancy_is_global_across_families(module, selected, plan):
    attempts = [
        {**selected, "status": "ok"},
        {**selected, "id": "RF09998:9abd_A", "family_id": "RF09998"},
    ]
    sequences = {a["id"]: "GCGCAU" for a in attempts}
    result, decisions = module.select_sequences(attempts, sequences, {}, [], plan)
    assert len(result) == 1 and decisions[1]["reason"] == "panel_sequence_redundancy"


def test_failed_source_and_outside_length_records_are_retained_as_decisions(
    module, selected, plan
):
    attempts = [
        {**selected, "status": "error"},
        {**selected, "id": "other", "status": "ok"},
    ]
    selected_rows, decisions = module.select_sequences(
        attempts, {"other": "A" * 513}, {selected["id"]: "source_unavailable"}, [], plan
    )
    assert not selected_rows
    assert [r["reason"] for r in decisions] == [
        "source_unavailable",
        "outside_declared_length_range",
    ]


def test_unsupported_selected_graph_is_not_replaced_after_contact_parsing(
    module, selected, plan, tmp_path
):
    attempts = [
        {**selected, "status": "ok"},
        {**selected, "id": "later", "filename": "record_001.json", "status": "ok"},
    ]
    sequences = {selected["id"]: "GCGCAU", "later": "AAAAAA"}
    chosen, decisions = module.select_sequences(attempts, sequences, {}, [], plan)
    (tmp_path / selected["filename"]).write_bytes(response([(1, 6), (1, 3)]))
    result = module.bind_graphs(tmp_path, chosen, ["RF09999"])
    assert result["supported_references"] == 0
    assert decisions[1]["reason"] == "fixed_final_family_cap"


def test_missing_family_cannot_pass_feasibility_by_increasing_other_family_counts(
    module,
):
    requirements = {
        "feasibility_minimum_per_family": 1,
        "feasibility_minimum_supported_families": 6,
        "feasibility_minimum_total": 6,
        "study_scope": "fixture",
    }
    data = {
        "families": [{"supported_references": 20}] + [{"supported_references": 0}] * 5,
        "supported_references": 20,
    }
    result = module.feasibility(data, requirements)
    assert (
        not result["feasibility_coverage_met"]
        and not result["broad_validation_gate_satisfied"]
    )
    assert not result["model_inference_authorized_by_this_stage"]


@pytest.fixture
def protocol(module, selected, tmp_path, monkeypatch):
    project = Path(__file__).resolve().parents[1]
    config = json.loads(
        (project / "configs/raw_structure_panel_2026-10-14.json").read_text()
    )
    config["future_binding"]["minimum_length"] = 1
    config["families"] = ["RF09999"]
    planning = tmp_path / "planning"
    planning.mkdir()
    atomic_json(planning / "config.json", config)
    atomic_json(planning / "mappings.json", [["RF09999", "9abc", "A"]])
    atomic_json(
        planning / "manifest.json",
        {
            "snapshot_sha256": {
                p.name: digest(p.read_bytes()) for p in planning.iterdir()
            }
        },
    )
    metadata_run = tmp_path / "metadata"
    metadata_run.mkdir()
    candidate = {
        k: selected[k] for k in ("id", "family_id", "pdb_accession", "chain_id")
    }
    candidate["url"] = (
        "https://rna.bgsu.edu/rna3dhub/rest/getSequenceBasePairs?pdb_id=9ABC&chain=A&only_nested=False"
    )
    metadata = {
        "run_dir": str(metadata_run),
        "metadata_complete": True,
        "screening": {"metadata_candidates": [candidate]},
    }
    atomic_json(metadata_run / "summary.json", metadata)
    atomic_json(
        metadata_run / "manifest.json",
        {"protocol_run": str(planning), "snapshot_sha256": {}},
    )
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(
        module, "audit_metadata", lambda p: json.loads(Path(p).read_text())
    )
    monkeypatch.setattr(module, "collect_known_exposures", lambda root: [])
    frozen = module.freeze(metadata_run / "summary.json")
    return module, Path(frozen["run_dir"]) / "manifest.json"


def test_contacts_are_parsed_only_after_valid_source_sequence_exposure(
    protocol, monkeypatch
):
    module, path = protocol
    monkeypatch.setattr(module, "download", lambda url: response())
    original = module.parse_graph

    def guarded(raw, record):
        events = list((module.ROOT / "results").rglob("exposures/*.json"))
        assert (
            len(events) == 1
            and module.read_exposure(events[0])["stage"] == "validation_started"
        )
        return original(raw, record)

    monkeypatch.setattr(module, "parse_graph", guarded)
    result = module.acquire(path)
    assert result["binding"]["supported_references"] == 1
    assert not result["inference_performed"]


@pytest.mark.parametrize("raw", [b"<html>error</html>", response(sequence="NNNNNN")])
def test_invalid_raw_sequence_keeps_failure_decision_without_false_exposure(
    protocol, monkeypatch, raw
):
    module, path = protocol
    monkeypatch.setattr(module, "download", lambda url: raw)
    result = module.acquire(path)
    assert result["successful_source_requests"] == 1
    assert result["binding"]["planned_records"] == 0
    assert result["selection_decisions"][0]["reason"].startswith(
        "unsupported_source_sequence"
    )
    assert not list((module.ROOT / "results").rglob("exposures/*.json"))


def test_network_failure_never_becomes_an_empty_reference_graph(protocol, monkeypatch):
    module, path = protocol

    def missing(url):
        raise OSError("fixture source missing")

    monkeypatch.setattr(module, "download", missing)
    result = module.acquire(path)
    assert result["successful_source_requests"] == 0
    assert result["binding"]["records"] == []
    assert result["selection_decisions"][0]["reason"] == "source_unavailable"


def test_new_family_exposure_blocks_acquisition_before_network(protocol, monkeypatch):
    module, path = protocol
    monkeypatch.setattr(
        module,
        "collect_known_exposures",
        lambda root: [{"family_id": "RF09999", "sequence": "GCGCAU"}],
    )
    monkeypatch.setattr(
        module, "download", lambda *a: pytest.fail("No request after exposure")
    )
    with pytest.raises(ValueError, match="exposed since"):
        module.acquire(path)


def test_replay_uses_saved_sources_and_exposures_without_new_requests(
    protocol, monkeypatch
):
    module, path = protocol
    monkeypatch.setattr(module, "download", lambda url: response())
    result = module.acquire(path)
    monkeypatch.setattr(
        module, "download", lambda *a: pytest.fail("No network in replay")
    )
    monkeypatch.setattr(
        module, "record_exposure", lambda *a: pytest.fail("No new exposure")
    )
    monkeypatch.setattr(
        module,
        "collect_known_exposures",
        lambda *a: pytest.fail("No live exposure reads"),
    )
    assert module.audit(Path(result["run_dir"]) / "summary.json") == result
    (Path(result["run_dir"]) / "record_000.json").write_bytes(response([]))
    with pytest.raises(ValueError, match="changed"):
        module.audit(Path(result["run_dir"]) / "summary.json")
