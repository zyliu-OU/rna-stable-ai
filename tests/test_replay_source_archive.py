"""Exact source-byte recovery and immutable availability accounting."""

import importlib.util
import json
from pathlib import Path

import pytest

from rnastable.native_journal import atomic_json

PROJECT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "source_archive", PROJECT / "scripts/archive_replay_sources.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def project(tmp_path, monkeypatch):
    src = tmp_path / "src/rnastable"
    src.mkdir(parents=True)
    current = src / "module.py"
    current.write_bytes(b"current = 1\n")
    archive = tmp_path / "reports/source_snapshots/older/src/rnastable"
    archive.mkdir(parents=True)
    (archive / "module.py").write_bytes(b"older = 1\n")
    manifest = tmp_path / "results/study/manifest.json"
    atomic_json(
        manifest,
        {
            "code_sha256": {
                str(current): module.sha(b"older = 1\n"),
                str(src / "missing.py"): module.sha(b"missing = 1\n"),
                str(src / "staged.py"): module.sha(b"staged = 1\n"),
            }
        },
    )
    monkeypatch.setattr(
        module,
        "indexed_sources",
        lambda root: iter(
            [(b"staged = 1\n", {"kind": "git_index", "object_id": "constructed"})]
        ),
    )
    return tmp_path, manifest


def test_exact_snapshots_and_staged_bytes_recovered_missing_versions_remain_explicit(
    tmp_path, monkeypatch
):
    root, manifest = project(tmp_path, monkeypatch)
    result = module.build(root)
    assert result["required_python_bindings"] == 3
    assert (
        result["available_python_bindings"] == 2
        and result["missing_python_bindings"] == 1
    )
    assert result["current_python_files"] == 1
    origins = {r.get("origin", {}).get("kind") for r in result["rows"]}
    assert {"saved_snapshot", "git_index"} <= origins
    assert module.audit(Path(result["run_dir"]) / "summary.json") == result
    (root / "src/rnastable/module.py").write_bytes(b"future = 2\n")
    atomic_json(root / "results/new/manifest.json", {"code_sha256": {}})
    assert module.audit(Path(result["run_dir"]) / "summary.json") == result


def test_changed_blob_rejected_without_overwrite(tmp_path):
    directory = tmp_path / "blobs"
    p = Path(module.save_blob(directory, b"original"))
    p.write_bytes(b"changed")
    with pytest.raises(ValueError, match="refusing overwrite"):
        module.save_blob(directory, b"original")
    assert p.read_bytes() == b"changed"


@pytest.mark.parametrize("tamper", ["blob", "study_manifest", "binding_inventory"])
def test_archive_tampering_is_detected(tmp_path, monkeypatch, tamper):
    root, manifest = project(tmp_path, monkeypatch)
    result = module.build(root)
    path = Path(result["run_dir"]) / "summary.json"
    if tamper == "blob":
        Path(
            next(r["blob"] for r in result["rows"] if r["status"] == "available")
        ).write_bytes(b"changed")
    elif tamper == "study_manifest":
        manifest.write_bytes(b"{}\n")
    else:
        result["rows"][0]["path"] = str(root / "src/rnastable/another.py")
        atomic_json(path, result)
    with pytest.raises(ValueError):
        module.audit(path)


def test_external_recorded_python_binding_is_reported_without_copying(
    tmp_path, monkeypatch
):
    root, manifest = project(tmp_path, monkeypatch)
    data = json.loads(manifest.read_text())
    data["code_sha256"]["/outside/workspace/unknown.py"] = module.sha(b"external")
    atomic_json(manifest, data)
    result = module.build(root)
    assert len(result["external_python_bindings"]) == 1
    assert result["required_python_bindings"] == 3
    assert module.audit(Path(result["run_dir"]) / "summary.json") == result


def test_ignored_studies_and_sources_remain_in_authoritative_inventory(
    tmp_path, monkeypatch
):
    root, manifest = project(tmp_path, monkeypatch)
    (root / ".ignore").write_text("results/study/\nsrc/rnastable/module.py\n")
    result = module.build(root)
    assert result["required_python_bindings"] == 3
    assert result["current_python_files"] == 1
    assert str(manifest) in result["manifest_sha256"]
    assert module.audit(Path(result["run_dir"]) / "summary.json") == result


def test_embedded_run_source_snapshots_are_searched(tmp_path, monkeypatch):
    root, manifest = project(tmp_path, monkeypatch)
    archive = root / "results/another_study/snapshot/src/rnastable"
    archive.mkdir(parents=True)
    (archive / "missing.py").write_bytes(b"missing = 1\n")
    result = module.build(root)
    assert (
        result["available_python_bindings"] == result["required_python_bindings"] == 3
    )
    assert result["missing_python_bindings"] == 0
    assert module.audit(Path(result["run_dir"]) / "summary.json") == result


def test_local_publication_history_can_supply_exact_missing_bytes(
    tmp_path, monkeypatch
):
    root, manifest = project(tmp_path, monkeypatch)
    monkeypatch.setattr(
        module,
        "published_history_sources",
        lambda root: iter(
            [
                (
                    b"missing = 1\n",
                    {"kind": "local_publication_history", "object_id": "constructed"},
                )
            ]
        ),
    )
    result = module.build(root)
    assert (
        result["available_python_bindings"] == 3
        and result["missing_python_bindings"] == 0
    )
    assert any(
        r.get("origin", {}).get("kind") == "local_publication_history"
        for r in result["rows"]
    )
    assert module.audit(Path(result["run_dir"]) / "summary.json") == result
