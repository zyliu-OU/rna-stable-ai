"""Bound the public assay-source acquisition without treating it as validation."""

import importlib.util
import json
from pathlib import Path

import pytest

from rnastable.reference import digest

PROJECT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "degradation_source", PROJECT / "scripts/prepare_degradation_source.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def config():
    return json.loads(
        (PROJECT / "configs/degradation_source_pilot_2026-10-13.json").read_text()
    )


@pytest.mark.parametrize(
    "key,value",
    [
        ("commit", "main"),
        ("repository", "https://example.com"),
        ("maximum_bytes", 2**30),
        ("timeout_seconds", 120),
        ("test_inference_authorized", True),
        ("quality_filter_for_selection", True),
        ("reference_structures_are_experimental_gold", True),
        ("future_pilot_record_cap", 32),
    ],
)
def test_protocol_rejects_changed_source_or_scope(key, value):
    c = config()
    c[key] = value
    with pytest.raises(ValueError):
        module.validate_config(c)


@pytest.fixture
def frozen(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "collect_known_exposures", lambda root: [])
    c = config()
    source_models = {}
    for name, relative in c["model_sources"].items():
        settings = {
            "seed": c["model_seed"],
            "top_k": 16,
            "inference_decoder": "exact_sparse",
        }
        feature = {
            "baseline": None,
            "stack": "adjacent_stackability",
            "helix": "local_helix_context_v1",
        }[name]
        if feature:
            settings["pair_features"] = feature
        checkpoint = tmp_path / (name + ".pt")
        checkpoint.write_bytes(name.encode())
        source = {
            "complete": True,
            "config": settings,
            "checkpoint_sha256": {
                "best_context_model.pt": digest(checkpoint.read_bytes())
            },
        }
        source_models[str(tmp_path / relative)] = (
            json.dumps(source).encode(),
            settings,
            checkpoint,
            None,
        )
    monkeypatch.setattr(module, "load_checkpoint", lambda p: source_models[str(p)])
    cp = tmp_path / "config.json"
    cp.write_text(json.dumps(c))
    plan = module.freeze(cp)
    return Path(plan["run_dir"]) / "manifest.json"


def test_successful_bytes_are_audited_without_assay_parsing_or_inference(
    frozen, monkeypatch
):
    monkeypatch.setattr(module, "fetch", lambda *args: b"constructed fixture bytes")
    result = module.acquire(frozen)
    assert result["sources_complete"] and result["assay_labels_parsed"] is False
    assert result["test_inference_allowed"] is False
    monkeypatch.setattr(
        module, "fetch", lambda *a: pytest.fail("Audit attempted network")
    )
    path = Path(result["run_dir"]) / "summary.json"
    assert module.audit(path) == result
    (path.parent / "author_trainset.json").write_bytes(b"changed")
    with pytest.raises(ValueError, match="dataset changed"):
        module.audit(path)


def test_failed_requests_preserve_both_endpoints_and_missing_source(
    frozen, monkeypatch
):
    def failure(*args):
        raise OSError("constructed DNS failure")

    monkeypatch.setattr(module, "fetch", failure)
    result = module.acquire(frozen)
    assert not result["sources_complete"] and result["source"] is None
    attempts = json.loads((Path(result["run_dir"]) / "attempts.json").read_text())
    assert len(attempts) == 2 and all(a["status"] == "error" for a in attempts)
    assert module.audit(Path(result["run_dir"]) / "summary.json") == result


def test_checkpoint_change_rejects_before_download(frozen, monkeypatch):
    (frozen.parent / "helix_checkpoint.pt").write_bytes(b"changed")
    monkeypatch.setattr(
        module, "fetch", lambda *a: pytest.fail("Changed protocol fetched data")
    )
    with pytest.raises(ValueError, match="input changed"):
        module.acquire(frozen)


@pytest.mark.parametrize("case", ["empty", "oversized", "lfs_pointer", "redirect"])
def test_download_rejects_invalid_payload_or_redirect(monkeypatch, case):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def geturl(self):
            return (
                "https://example.com/changed"
                if case == "redirect"
                else "https://raw.githubusercontent.com/author/pinned"
            )

        def read(self, maximum):
            return {
                "empty": b"",
                "oversized": b"x" * 65,
                "lfs_pointer": b"version https://git-lfs.github.com/spec/v1\n",
                "redirect": b"x",
            }[case]

    monkeypatch.setattr(module.urllib.request, "urlopen", lambda *a, **kw: Response())
    with pytest.raises(ValueError):
        module.fetch("https://raw.githubusercontent.com/author/pinned", 64, 1)
