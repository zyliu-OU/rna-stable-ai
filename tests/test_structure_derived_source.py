"""Pinned acquisition must not silently substitute references, models, or files."""

import importlib.util
import json
from pathlib import Path

import pytest

from rnastable.native_journal import atomic_json
from rnastable.reference import digest


@pytest.fixture
def module(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "structure_derived_source_test",
        root / "scripts/prepare_structure_derived_source.py",
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.fixture
def protocol(module, tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    config = json.loads(
        (root / "configs/structure_derived_source_2026-10-14.json").read_text()
    )
    contents = {}
    for entry in config["files"]:
        content = ("synthetic bytes for " + entry["path"]).encode()
        entry.update(git_blob=module.git_blob(content), bytes=len(content))
        contents[entry["path"]] = content
    config_path = tmp_path / "config.json"
    atomic_json(config_path, config)
    policy = tmp_path / config["future_binding"]["readiness_policy"]
    policy.parent.mkdir(parents=True)
    policy.write_bytes((root / "configs/reference_readiness.json").read_bytes())
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "collect_known_exposures", lambda root: [])

    def model(path):
        name = next(
            name
            for name, value in config["model_sources"].items()
            if tmp_path / value == path
        )
        settings = {
            "seed": config["model_seed"],
            "inference_decoder": "exact_sparse",
            "top_k": 16,
        }
        features = {
            "baseline": None,
            "stack": "adjacent_stackability",
            "helix": "local_helix_context_v1",
        }
        if features[name]:
            settings["pair_features"] = features[name]
        checkpoint = tmp_path / (name + ".pt")
        checkpoint.write_bytes(name.encode())
        summary = {
            "complete": True,
            "config": settings,
            "checkpoint_sha256": {"best_context_model.pt": digest(name.encode())},
        }
        return json.dumps(summary).encode(), settings, checkpoint, None

    monkeypatch.setattr(module, "load_checkpoint", model)
    manifest = module.freeze(config_path)
    return module, Path(manifest["run_dir"]) / "manifest.json", contents, config


def test_network_starts_only_after_models_policy_and_exposures_are_frozen(
    protocol, monkeypatch
):
    module, manifest, contents, _ = protocol
    observed = []

    def download(url, limit, timeout):
        saved = module.audit_protocol(manifest)
        run = Path(saved["run_dir"])
        assert (run / "exposure.json").is_file()
        assert (run / "readiness_policy.json").is_file()
        assert len(saved["models"]) == 3
        observed.append(url)
        return next(raw for path, raw in contents.items() if url.endswith("/" + path))

    monkeypatch.setattr(module, "download_file", download)
    monkeypatch.setattr(
        module, "load_checkpoint", lambda *a: pytest.fail("Do not reread latest models")
    )
    result = module.acquire(manifest)
    assert result["sources_complete"] and result["successful_requests"] == 9
    assert len(observed) == 9
    assert (
        not result["annotation_pairs_parsed"] and not result["test_inference_allowed"]
    )
    assert not list(module.ROOT.rglob("exposures"))


@pytest.mark.parametrize("mode", ["network_failure", "wrong_blob"])
def test_failed_files_are_retained_without_reselection_or_substitution(
    protocol, monkeypatch, mode
):
    module, manifest, contents, _ = protocol

    def download(url, *args):
        if url.endswith("RF00522.sto"):
            if mode == "network_failure":
                raise OSError("fixture unavailable")
            return b"unexpected replacement"
        return next(raw for path, raw in contents.items() if url.endswith("/" + path))

    monkeypatch.setattr(module, "download_file", download)
    result = module.acquire(manifest)
    assert not result["sources_complete"] and result["successful_requests"] == 8
    assert result["planned_requests"] == 9
    attempts = json.loads((Path(result["run_dir"]) / "attempts.json").read_text())
    failed = [a for a in attempts if a["status"] == "error"]
    assert len(failed) == 1 and failed[0]["path"] == "data/output/RF00522.sto"
    assert ("sha256" in failed[0]) == (mode == "wrong_blob")
    assert module.audit(Path(result["run_dir"]) / "summary.json") == result


def test_family_exposed_after_freeze_blocks_network(protocol, monkeypatch):
    module, manifest, _, config = protocol
    monkeypatch.setattr(
        module,
        "collect_known_exposures",
        lambda root: [{"family_id": config["families"][0]}],
    )
    monkeypatch.setattr(
        module, "download_file", lambda *a: pytest.fail("Network must not start")
    )
    with pytest.raises(ValueError, match="consumed since"):
        module.acquire(manifest)


@pytest.mark.parametrize(
    "target", ["baseline_checkpoint.pt", "readiness_policy.json", "exposure.json"]
)
def test_changed_frozen_models_policy_or_exposure_block_acquisition(
    protocol, monkeypatch, target
):
    module, manifest, _, _ = protocol
    p = manifest.parent / target
    p.write_bytes(p.read_bytes() + b"\n")
    monkeypatch.setattr(
        module, "download_file", lambda *a: pytest.fail("Network must not start")
    )
    with pytest.raises(ValueError, match="snapshot changed"):
        module.acquire(manifest)


def test_source_replay_needs_neither_live_exposures_nor_network(protocol, monkeypatch):
    module, manifest, contents, _ = protocol
    monkeypatch.setattr(
        module,
        "download_file",
        lambda url, *a: next(
            raw for path, raw in contents.items() if url.endswith("/" + path)
        ),
    )
    result = module.acquire(manifest)
    monkeypatch.setattr(
        module,
        "collect_known_exposures",
        lambda *a: pytest.fail("No live exposure access"),
    )
    monkeypatch.setattr(
        module, "download_file", lambda *a: pytest.fail("No download in replay")
    )
    assert module.audit(Path(result["run_dir"]) / "summary.json") == result
    (Path(result["run_dir"]) / "source/data/output/RF00504.sto").write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed"):
        module.audit(Path(result["run_dir"]) / "summary.json")


@pytest.mark.parametrize(
    "malformation", ["path", "blob", "size", "fallback", "inference"]
)
def test_config_rejects_unpinned_sources_and_consensus_fallback(module, malformation):
    root = Path(__file__).resolve().parents[1]
    config = json.loads(
        (root / "configs/structure_derived_source_2026-10-14.json").read_text()
    )
    if malformation == "path":
        config["files"][0]["path"] = "../LICENSE"
    elif malformation == "blob":
        config["files"][0]["git_blob"] = "latest"
    elif malformation == "size":
        config["files"][0]["bytes"] = True
    elif malformation == "fallback":
        config["future_binding"]["reference_source"] = "consensus_if_missing"
    else:
        config["test_inference_authorized"] = True
    with pytest.raises(ValueError):
        module.validate_config(config)


def test_download_enforces_https_exact_url_and_byte_bound(module, monkeypatch):
    url = (
        "https://raw.githubusercontent.com/Rfam/rfam-3d-seed-alignments/"
        + "a" * 40
        + "/README.md"
    )

    class Response:
        actual = url

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def geturl(self):
            return self.actual

        def read(self, limit):
            return b"123456"[:limit]

    response = Response()
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: response)
    assert module.download_file(url, 6, 1) == b"123456"
    with pytest.raises(ValueError, match="bound"):
        module.download_file(url, 5, 1)
    response.actual = "https://other.example/README.md"
    with pytest.raises(ValueError, match="redirected"):
        module.download_file(url, 6, 1)
