import importlib.util
import json
from pathlib import Path

import pytest

from rnastable.native_journal import atomic_json


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    project = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(project / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "prospective_evidence", project / "scripts/download_prospective_evidence.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    source = tmp_path / "source"
    source.mkdir()
    families = ["RF00059", "RF00162", "RF00167"]
    for family in families:
        atomic_json(
            source / (family + "_description.json"),
            {"rfam": {"acc": family, "release": {"number": "15.1"}}},
        )
    atomic_json(
        source / "exposure.json",
        [{"family_id": "RF00001", "sequence": "AAAA", "source": "fixture"}],
    )
    acquisition = {
        "run_dir": str(source),
        "sources_complete": True,
        "families_downloaded": families,
        "metadata_panel": {"records": [{"id": "selected"}]},
    }
    monkeypatch.setattr(module, "audit_acquisition", lambda path: acquisition)
    return module, source, acquisition


def test_evidence_plan_binds_existing_selection_and_release(evidence):
    module, _, acquisition = evidence
    plan, release = module.source_plan(acquisition)
    assert release == "15.1" and len(plan) == 7
    assert [r["resource"] for r in plan] == ["pdb_mapping"] * 3 + [
        "exposed_family_description"
    ] + ["stockholm"] * 3
    assert all(r["url"].startswith("https://rfam.org/family/") for r in plan)


def test_release_change_rejects_new_description_and_source_plan(evidence):
    module, source, acquisition = evidence
    row = {"resource": "exposed_family_description", "family_id": "RF00001"}
    with pytest.raises(ValueError, match="release changed"):
        module.validate_source(
            b'{"rfam":{"acc":"RF00001","release":{"number":"future"}}}', row, "15.1"
        )
    atomic_json(
        source / "RF00162_description.json",
        {"rfam": {"acc": "RF00162", "release": {"number": "future"}}},
    )
    with pytest.raises(ValueError, match="inconsistent releases"):
        module.source_plan(acquisition)


@pytest.mark.parametrize(
    "raw",
    [
        b"<html>error</html>",
        b"# STOCKHOLM 1.0\n#=GF AC RF00162\n//\n",
        b"# STOCKHOLM 1.0\n#=GF AC RF00059\n",
    ],
)
def test_stockholm_wrong_family_or_truncated_file_rejected(evidence, raw):
    module, _, _ = evidence
    with pytest.raises(ValueError):
        module.validate_source(
            raw, {"family_id": "RF00059", "resource": "stockholm"}, "15.1"
        )


def test_unavailable_provenance_skips_labels_and_replays(evidence, monkeypatch):
    module, source, _ = evidence
    calls = []

    def unavailable(url, limit):
        calls.append(url)
        raise OSError("fixture network failure")

    monkeypatch.setattr(module, "bounded_download", unavailable)
    summary = module.download(source / "summary.json")
    assert len(calls) == 4 and not any("alignment" in url for url in calls)
    assert not summary["sources_complete"] and summary["successful_requests"] == 0
    assert (
        not summary["reference_pairs_parsed"] and not summary["test_inference_allowed"]
    )
    monkeypatch.setattr(
        module, "bounded_download", lambda *a: pytest.fail("Audit used network")
    )
    assert module.audit(Path(summary["run_dir"]) / "summary.json") == summary


def test_envelope_success_is_not_annotation_or_evaluation_success(
    evidence, monkeypatch
):
    module, source, _ = evidence

    def downloaded(url, limit):
        family = url.split("/family/")[1][:7]
        if "stockholm" in url:
            return f"# STOCKHOLM 1.0\n#=GF AC {family}\n#=GC SS_cons Aa\n//\n".encode()
        if "/structures" in url:
            return b'{"mappings":[]}'
        return json.dumps(
            {"rfam": {"acc": family, "release": {"number": "15.1"}}}
        ).encode()

    monkeypatch.setattr(module, "bounded_download", downloaded)
    summary = module.download(source / "summary.json")
    assert summary["sources_complete"] and summary["successful_requests"] == 7
    assert (
        not summary["reference_pairs_parsed"] and not summary["test_inference_allowed"]
    )
    run = Path(summary["run_dir"])
    assert module.audit(run / "summary.json") == summary
    (run / "RF00059.sto").write_bytes(b"changed")
    with pytest.raises(ValueError, match="snapshot changed"):
        module.audit(run / "summary.json")


def test_invalid_new_accession_preserved_as_failed_request(evidence, monkeypatch):
    module, source, _ = evidence

    def downloaded(url, limit):
        if "/structures" in url:
            return b"{}"
        return b'{"rfam":{"acc":"RF99999","release":{"number":"15.1"}}}'

    monkeypatch.setattr(module, "bounded_download", downloaded)
    summary = module.download(source / "summary.json")
    assert not summary["sources_complete"] and summary["successful_requests"] == 3
    run = Path(summary["run_dir"])
    attempts = json.loads((run / "attempts.json").read_text())
    failed = next(a for a in attempts if a["resource"] == "exposed_family_description")
    assert failed["status"] == "error" and "sha256" in failed
    assert (run / failed["filename"]).exists()
    assert module.audit(run / "summary.json") == summary
