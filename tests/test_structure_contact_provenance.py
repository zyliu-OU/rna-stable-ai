"""Raw interaction graphs must remain complete even when strings cannot encode them."""

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
        "contact_provenance_test",
        project / "scripts/audit_structure_contact_provenance.py",
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.fixture
def record():
    return {
        "id": "RF09999:9abc_A:fixture",
        "family_id": "RF09999",
        "pdb_accession": "9abc",
        "chain_id": "A",
        "sequence": "GCGCAU",
        "sequence_sha256": digest(b"GCGCAU"),
        "pairs": [[0, 5], [1, 4]],
        "reference_status": "ok",
    }


def response(pairs, sequence="GCGCAU"):
    return json.dumps(
        {
            "sequence": sequence,
            "annotations": [
                {"bp": "cWW", "seq_id1": a, "seq_id2": b} for a, b in pairs
            ],
        }
    ).encode()


def test_raw_graph_preserves_reverse_duplicates_without_inflating_contacts(
    module, record
):
    result = module.compare(response([(1, 6), (6, 1), (2, 5)]), record)
    assert result["exact_contact_set_match"]
    assert result["raw_cww_rows"] == 3 and result["raw_unique_cww_contacts"] == 2
    assert result["repeated_or_reverse_cww_rows"] == 1


def test_multiple_partner_and_crossing_graph_edges_are_not_projected_away(
    module, record
):
    result = module.compare(response([(1, 6), (2, 5), (1, 3), (3, 6)]), record)
    assert result["raw_cww_pairs"] == [[0, 2], [0, 5], [1, 4], [2, 5]]
    assert result["raw_nucleotides_with_multiple_cww_partners"] == [0, 2, 5]
    assert result["current_raw_contacts_absent_from_supplied"] == [[0, 2], [2, 5]]
    assert not result["exact_contact_set_match"] and not result["reference_replaced"]


def test_sequence_mismatch_cannot_be_scored_as_reference_contact_loss(module, record):
    result = module.compare(response([], sequence="AAAAAA"), record)
    assert result["status"] == "sequence_mismatch"
    assert "raw_unique_cww_contacts" not in result
    assert not result["reference_replaced"]


@pytest.mark.parametrize("pair", [(0, 3), (1, 7), (2, 2), (True, 3), (1.2, 4)])
def test_bad_raw_coordinates_are_not_silently_reindexed_or_truncated(
    module, record, pair
):
    with pytest.raises(ValueError):
        module.compare(response([pair]), record)


def test_non_cww_contacts_are_counted_without_becoming_canonical_truth(module, record):
    raw = json.loads(response([(1, 6), (2, 5)]))
    raw["annotations"].append({"bp": "tWW", "seq_id1": 1, "seq_id2": 3})
    result = module.compare(json.dumps(raw).encode(), record)
    assert result["exact_contact_set_match"] and result["other_annotation_rows"] == 1


@pytest.fixture
def frozen(module, record, tmp_path, monkeypatch):
    binding = {"run_dir": str(tmp_path / "binding"), "binding": {"records": [record]}}
    path = tmp_path / "binding/summary.json"
    path.parent.mkdir()
    atomic_json(path, binding)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "audit_binding", lambda p: binding)
    monkeypatch.setattr(
        module, "source_inputs", lambda p: {str(path): digest(path.read_bytes())}
    )
    protocol = module.freeze(path)
    return module, Path(protocol["run_dir"]) / "manifest.json"


def test_valid_source_is_exposed_before_graph_contacts_are_parsed(frozen, monkeypatch):
    module, protocol = frozen
    monkeypatch.setattr(module, "download", lambda url: response([(1, 6), (2, 5)]))
    original = module.compare

    def compare_after_event(raw, record):
        events = list((module.ROOT / "results").rglob("exposures/*.json"))
        assert len(events) == 1
        assert module.read_exposure(events[0])["stage"] == "validation_started"
        return original(raw, record)

    monkeypatch.setattr(module, "compare", compare_after_event)
    result = module.acquire(protocol)
    assert result["outcomes"][0]["exact_contact_set_match"]
    assert not result["inference_performed"] and not result["references_replaced"]


def test_missing_sources_are_unknown_not_empty_contact_sets(frozen, monkeypatch):
    module, protocol = frozen

    def unavailable(url):
        raise OSError("fixture unavailable")

    monkeypatch.setattr(module, "download", unavailable)
    result = module.acquire(protocol)
    assert result["successful_requests"] == 0 and result["planned_requests"] == 1
    assert result["outcomes"][0]["status"] == "source_unavailable"
    assert "raw_cww_pairs" not in result["outcomes"][0]
    assert not list((module.ROOT / "results").rglob("exposures/*.json"))


@pytest.mark.parametrize(
    "raw",
    [
        b"<html>error</html>",
        b'{"sequence":"No sequence was found for the given id"}',
        b'{"sequence":"GCGCAU"}',
    ],
)
def test_bad_payloads_remain_unsupported_with_retained_bytes(frozen, monkeypatch, raw):
    module, protocol = frozen
    monkeypatch.setattr(module, "download", lambda url: raw)
    result = module.acquire(protocol)
    assert result["successful_requests"] == 1
    assert result["outcomes"][0]["status"] == "unsupported_source_schema"
    assert (Path(result["run_dir"]) / "record_000.json").read_bytes() == raw


def test_retained_replay_never_redownloads_or_records_new_exposure(frozen, monkeypatch):
    module, protocol = frozen
    monkeypatch.setattr(module, "download", lambda url: response([(1, 6), (2, 5)]))
    result = module.acquire(protocol)
    monkeypatch.setattr(
        module, "download", lambda *a: pytest.fail("No network in replay")
    )
    monkeypatch.setattr(
        module, "record_exposure", lambda *a: pytest.fail("No new exposure")
    )
    assert module.audit(Path(result["run_dir"]) / "summary.json") == result
    (Path(result["run_dir"]) / "record_000.json").write_bytes(response([]))
    with pytest.raises(ValueError, match="changed"):
        module.audit(Path(result["run_dir"]) / "summary.json")
