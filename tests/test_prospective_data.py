import importlib.util
import json
from pathlib import Path

import pytest

from rnastable.family_readiness import screen_families
from rnastable.prospective_data import (
    bounded_download,
    family_urls,
    fastau_records,
    select_metadata_panel,
    sequence_overlap,
    validate_description,
)
from rnastable.reference import digest


def test_source_accession_and_fasta_normalization_are_explicit():
    validate_description(b'{"rfam":{"acc":"RF00059"}}', "RF00059")
    with pytest.raises(ValueError, match="accession"):
        validate_description(b'{"rfam":{"acc":"RF00162"}}', "RF00059")
    rows = fastau_records(b">accession/1-5\nacgtt\n>ambiguous\nNNNNN\n", "RF00059")
    assert rows[0]["sequence"] == "ACGUU"
    assert rows[0]["sequence_sha256"] != rows[0]["original_sequence_sha256"]
    assert rows[0]["normalization"] == "uppercase_and_T_to_U"
    assert not rows[1]["valid_sequence"]


@pytest.mark.parametrize(
    "content", [b"<html>error</html>", b"", b">x\nAAAA\n>x\nCCCC\n"]
)
def test_bad_responses_cannot_become_a_cohort(content):
    with pytest.raises(ValueError):
        fastau_records(content, "RF00059")


def test_length_upper_bound_matches_original_heuristic():
    from rnastable.experimental_data import sequence_similarity

    for a in ("AAAA", "ACGUACGU", "C" * 100):
        for b in ("AAAC", "ACGUACGU", "A" * 1000):
            assert sequence_overlap(a, b) == (sequence_similarity(a, b) >= 0.8)


def test_bounded_download_rejects_size_and_untrusted_redirect(monkeypatch):
    class Response:
        url = "https://rfam.org/family/RF00059/alignment/fastau"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, size):
            return b"AAAAAA"[:size]

        def geturl(self):
            return self.url

    response = Response()
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: response)
    with pytest.raises(ValueError, match="size"):
        bounded_download(response.url, 5)
    assert bounded_download(response.url, 6) == b"AAAAAA"
    response.url = "https://other.example/family"
    with pytest.raises(ValueError, match="redirected"):
        bounded_download(family_urls("RF00059")["sequences"], 6)


def test_fixed_panel_keeps_redundancy_and_cap_denominators():
    rows = fastau_records(b">a\nAAAA\n>b\nAAAA\n>c\nCCCC\n", "RF00059")
    screen = screen_families(rows, [], 1, 1024)
    panel = select_metadata_panel(rows[::-1], screen, 1)
    assert [r["id"] for r in panel["records"]] == ["RF00059:a"]
    assert [r["panel_reason"] for r in panel["decisions"]] == [
        "selected_metadata_only",
        "panel_sequence_redundancy",
        "fixed_family_cap",
    ]
    assert (
        not panel["annotation_binding_complete"] and not panel["test_inference_allowed"]
    )


@pytest.fixture
def protocol(tmp_path, monkeypatch):
    project = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "prospective_panel", project / "scripts/prepare_prospective_family_panel.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "collect_known_exposures", lambda root: [])
    config = project / "configs/prospective_family_panel.json"
    settings = json.loads(config.read_text())
    checkpoints = {}
    for name, relative in settings["model_sources"].items():
        model_config = {
            "seed": settings["model_seed"],
            "inference_decoder": "exact_sparse",
        }
        feature = {
            "baseline": None,
            "stack": "adjacent_stackability",
            "helix": "local_helix_context_v1",
        }[name]
        if feature:
            model_config["pair_features"] = feature
        weights = tmp_path / (name + ".pt")
        weights.write_bytes(name.encode())
        summary = {
            "complete": True,
            "config": model_config,
            "checkpoint_sha256": {
                "best_context_model.pt": digest(weights.read_bytes())
            },
        }
        checkpoints[str(tmp_path / relative)] = (
            json.dumps(summary).encode(),
            model_config,
            weights,
            None,
        )
    monkeypatch.setattr(module, "load_checkpoint", lambda p: checkpoints[str(p)])
    frozen = module.freeze(config)
    return module, Path(frozen["run_dir"]) / "manifest.json"


def test_dns_failure_is_replayable_missing_acquisition_not_empty_data(
    protocol, monkeypatch
):
    module, path = protocol
    calls = []

    def unavailable(url, limit):
        calls.append(url)
        raise OSError("fixture DNS failure")

    monkeypatch.setattr(module, "bounded_download", unavailable)
    result = module.acquire(path)
    assert len(calls) == 3 and result["complete"] and not result["sources_complete"]
    assert not result["test_inference_allowed"] and result["families_downloaded"] == []
    attempts = json.loads((Path(result["run_dir"]) / "attempts.json").read_text())
    assert [a["status"] for a in attempts] == ["error", "not_started"] * 3
    monkeypatch.setattr(
        module, "bounded_download", lambda *a: pytest.fail("Audit used network")
    )
    assert module.audit_acquisition(Path(result["run_dir"]) / "summary.json") == result


def test_successful_source_screen_still_does_not_authorize_test(protocol, monkeypatch):
    module, path = protocol

    def source(url, limit):
        family = url.split("/family/")[1][:7]
        if "content-type" in url:
            return json.dumps({"rfam": {"acc": family}}).encode()
        sequence = {"RF00059": "A", "RF00162": "C", "RF00167": "G"}[family] * 30
        return (">source/1-30\n" + sequence + "\n").encode()

    monkeypatch.setattr(module, "bounded_download", source)
    result = module.acquire(path)
    assert result["sources_complete"] and len(result["metadata_panel"]["records"]) == 3
    assert (
        not result["test_inference_allowed"]
        and not result["screening"]["new_structure_labels_read"]
    )
    run = Path(result["run_dir"])
    assert module.audit_acquisition(run / "summary.json") == result
    (run / "RF00059_sequences.fasta").write_bytes(b">changed\nCCCC\n")
    with pytest.raises(ValueError, match="snapshot changed"):
        module.audit_acquisition(run / "summary.json")


def test_protocol_checkpoint_change_rejected_before_acquisition(protocol, monkeypatch):
    module, path = protocol
    (path.parent / "helix_checkpoint.pt").write_bytes(b"changed")
    monkeypatch.setattr(
        module,
        "bounded_download",
        lambda *a: pytest.fail("Changed protocol fetched sources"),
    )
    with pytest.raises(ValueError, match="snapshot changed"):
        module.acquire(path)


def test_new_family_exposure_rejected_before_acquisition(protocol, monkeypatch):
    module, path = protocol
    monkeypatch.setattr(
        module,
        "collect_known_exposures",
        lambda root: [
            {"sequence": "AAAA", "family_id": "RF00059", "source": "interrupted test"}
        ],
    )
    monkeypatch.setattr(
        module,
        "bounded_download",
        lambda *a: pytest.fail("Exposed family fetched sources"),
    )
    with pytest.raises(ValueError, match="exposed since protocol freeze"):
        module.acquire(path)


def completed_acquisition(protocol, monkeypatch):
    module, path = protocol

    def source(url, limit):
        family = url.split("/family/")[1][:7]
        if "content-type" in url:
            return json.dumps({"rfam": {"acc": family}}).encode()
        sequence = {"RF00059": "A", "RF00162": "C", "RF00167": "G"}[family] * 30
        return (">source/1-30\n" + sequence + "\n").encode()

    monkeypatch.setattr(module, "bounded_download", source)
    result = module.acquire(path)
    return module, Path(result["run_dir"]) / "summary.json", result


def test_verified_screening_cache_avoids_duplicate_replay(protocol, monkeypatch):
    module, path, result = completed_acquisition(protocol, monkeypatch)
    original = module.acquisition_screen
    calls = []

    def counted(*args):
        calls.append(True)
        return original(*args)

    monkeypatch.setattr(module, "acquisition_screen", counted)
    assert module.audit_acquisition(path) == result
    assert module.audit_acquisition(path) == result
    assert len(calls) == 1
    assert module.audit_acquisition(path, recompute=True) == result
    assert len(calls) == 2
    assert not list(path.parent.glob("*cache*"))


@pytest.mark.parametrize(
    "tamper", ["snapshot", "summary", "cache_binding", "cache_output"]
)
def test_cache_does_not_hide_changed_source_or_results(protocol, monkeypatch, tamper):
    module, path, _ = completed_acquisition(protocol, monkeypatch)
    module.audit_acquisition(path)
    cache = next(
        (module.ROOT / "results/prospective_acquisition_replay_cache").glob("*.json")
    )
    if tamper == "snapshot":
        (path.parent / "exposure.json").write_text("[]\nchanged\n")
    elif tamper == "summary":
        result = json.loads(path.read_text())
        result["sources_complete"] = False
        path.write_text(json.dumps(result))
    else:
        saved = json.loads(cache.read_text())
        if tamper == "cache_binding":
            saved["binding"]["summary_sha256"] = "changed"
        else:
            saved["screening"]["sources_complete"] = False
        cache.write_text(json.dumps(saved))
    with pytest.raises(ValueError):
        module.audit_acquisition(path)


def test_implementation_change_invalidates_cache(protocol, monkeypatch, tmp_path):
    module, path, result = completed_acquisition(protocol, monkeypatch)
    code = tmp_path / "standin_project/scripts/panel.py"
    code.parent.mkdir(parents=True)
    code.write_text("first algorithm version")
    monkeypatch.setattr(module, "__file__", str(code))
    original = module.acquisition_screen
    calls = []

    def counted(*args):
        calls.append(True)
        return original(*args)

    monkeypatch.setattr(module, "acquisition_screen", counted)
    module.audit_acquisition(path)
    code.write_text("second algorithm version")
    assert module.audit_acquisition(path) == result
    assert len(calls) == 2
