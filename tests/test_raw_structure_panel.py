"""Metadata screening cannot authorize inference or reuse known family/clan sources."""

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
        "raw_structure_panel_test", project / "scripts/plan_raw_structure_panel.py"
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.fixture
def config():
    return json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "configs/raw_structure_panel_2026-10-14.json"
        ).read_text()
    )


def description(family, clan=None, release="15.1"):
    return json.dumps(
        {"rfam": {"acc": family, "release": {"number": release}, "clan": {"acc": clan}}}
    ).encode()


def test_metadata_candidate_selection_is_deterministic_capped_and_not_an_evaluation(
    module, config
):
    families = config["families"]
    mappings = {(f, f"9{index:03d}", "A") for index, f in enumerate(families)}
    mappings |= {(families[0], f"8{index:03d}", "A") for index in range(10)}
    descriptions = {f: description(f) for f in families}
    a = module.screen(config, mappings, [], descriptions)
    b = module.screen(config, set(reversed(sorted(mappings))), [], descriptions)
    assert a == b and a["candidate_counts"][families[0]] == 5
    assert not a["inference_allowed"] and not a["broad_validation_gate_satisfied"]
    assert not a["sequence_or_annotation_bytes_read"]
    assert not a["unknown_training_tool_provenance_resolved"]


def test_known_pdb_mapping_infers_family_exposure_without_claiming_sequence_assignment(
    module, config
):
    family = config["families"][0]
    mappings = {(family, "1abc", "A"), (family, "2abc", "B")}
    exposed = [{"pdb_accession": "1ABC", "sequence": "AAAA"}]
    result = module.screen(
        config, mappings, exposed, {f: description(f) for f in config["families"]}
    )
    assert not result["metadata_candidates"]
    assert {r["reason"] for r in result["decisions"]} == {
        "prior_family_or_pdb_exposure"
    }


def test_clan_overlap_excludes_unseen_family(module, config):
    family = config["families"][0]
    exposed = [{"family_id": "RF09999", "sequence": "AAAA"}]
    descriptions = {f: description(f) for f in config["families"]}
    descriptions[family] = description(family, "CL00001")
    descriptions["RF09999"] = description("RF09999", "CL00001")
    result = module.screen(config, {(family, "1abc", "A")}, exposed, descriptions)
    assert result["metadata_candidates"] == []
    assert result["decisions"][0]["reason"] == "prior_clan_exposure"


def test_same_pdb_chain_cannot_count_in_two_target_families(module, config):
    mappings = {(f, "1abc", "A") for f in config["families"]}
    result = module.screen(
        config, mappings, [], {f: description(f) for f in config["families"]}
    )
    assert len(result["metadata_candidates"]) == 1
    assert (
        sum(
            r["reason"] == "cross_family_pdb_chain_redundancy"
            for r in result["decisions"]
        )
        == 5
    )


@pytest.mark.parametrize("variant", ["missing_clan", "wrong_family", "wrong_release"])
def test_unknown_or_changed_provenance_cannot_be_assumed_clear(module, variant):
    data = json.loads(description("RF09999"))
    if variant == "missing_clan":
        data["rfam"].pop("clan")
    elif variant == "wrong_family":
        data["rfam"]["acc"] = "RF09998"
    else:
        data["rfam"]["release"]["number"] = "next"
    with pytest.raises(ValueError):
        module.clan(json.dumps(data).encode(), "RF09999", "15.1")


@pytest.mark.parametrize(
    "variant", ["infer", "broad_gate", "project", "replace", "cap"]
)
def test_metadata_protocol_cannot_be_promoted_to_inference_or_projection(
    module, config, variant
):
    if variant == "infer":
        config["model_inference_authorized"] = True
    elif variant == "broad_gate":
        config["future_binding"]["broad_validation_gate_satisfied"] = True
    elif variant == "project":
        config["future_binding"]["raw_graph_multiple_partners"] = (
            "delete_extra_contacts"
        )
    elif variant == "replace":
        config["future_binding"]["replace_unsupported_records"] = True
    else:
        config["metadata_pdb_chain_cap_per_family"] = True
    with pytest.raises(ValueError):
        module.validate_config(config)


@pytest.fixture
def protocol(module, config, tmp_path, monkeypatch):
    monkeypatch.setattr(module, "ROOT", tmp_path)
    source = tmp_path / "source"
    (source / "source").mkdir(parents=True)
    mapping = "\n".join(
        f"{f} 9{i:03d} A 1 10 30.0 1e-6 1 10 fixture 1"
        for i, f in enumerate(config["families"])
    )
    (source / "source/pdb_full_region.txt").write_text(mapping)
    (source / "source/pdb_full_region_curated.txt").write_text("")
    atomic_json(
        source / "summary.json", {"run_dir": str(source), "sources_complete": True}
    )
    atomic_json(source / "manifest.json", {})
    model_run = tmp_path / "model"
    model_run.mkdir()
    models = {}
    for name in ("baseline", "stack", "helix"):
        weights = name.encode()
        (model_run / (name + "_checkpoint.pt")).write_bytes(weights)
        atomic_json(model_run / (name + "_summary.json"), {"fixture": True})
        models[name] = {"checkpoint_sha256": digest(weights)}
    model = {"run_dir": str(model_run), "models": models}
    atomic_json(model_run / "manifest.json", model)
    config["model_protocol"] = str(model_run / "manifest.json")
    config["mapping_source_summary"] = str(source / "summary.json")
    config_path = tmp_path / "config.json"
    atomic_json(config_path, config)
    monkeypatch.setattr(
        module, "audit_source", lambda p: json.loads(Path(p).read_text())
    )
    monkeypatch.setattr(
        module, "audit_models", lambda p: json.loads(Path(p).read_text())
    )
    monkeypatch.setattr(module, "collect_known_exposures", lambda root: [])
    result = module.freeze(config_path)
    return module, Path(result["run_dir"]) / "manifest.json"


def test_freeze_retains_all_models_before_metadata_requests(protocol, monkeypatch):
    module, path = protocol

    def download(url, size, timeout):
        assert module.audit_protocol(path)
        family = url.split("/family/")[1].split("?")[0]
        return description(family)

    monkeypatch.setattr(module, "bounded_download", download)
    result = module.acquire(path)
    assert result["metadata_complete"]
    assert len(result["screening"]["metadata_candidates"]) == 6
    assert (
        not result["new_structure_labels_read"]
        and not result["model_inference_authorized"]
    )
    assert not list(module.ROOT.rglob("exposures/*.json"))


def test_missing_metadata_blocks_raw_contact_plan_without_hiding_requests(
    protocol, monkeypatch
):
    module, path = protocol

    def unavailable(*a):
        raise OSError("fixture unavailable")

    monkeypatch.setattr(module, "bounded_download", unavailable)
    result = module.acquire(path)
    assert not result["metadata_complete"] and result["screening"] is None
    assert result["successful_requests"] == 0 and result["planned_requests"] == 6


def test_metadata_replay_does_not_query_network_or_live_exposures(
    protocol, monkeypatch
):
    module, path = protocol
    monkeypatch.setattr(
        module,
        "bounded_download",
        lambda url, *a: description(url.split("/family/")[1].split("?")[0]),
    )
    result = module.acquire(path)
    monkeypatch.setattr(
        module, "bounded_download", lambda *a: pytest.fail("No network in replay")
    )
    monkeypatch.setattr(
        module,
        "collect_known_exposures",
        lambda *a: pytest.fail("No live exposure reads"),
    )
    assert module.audit(Path(result["run_dir"]) / "summary.json") == result
    target = next(Path(result["run_dir"]).glob("RF*.json"))
    target.write_bytes(target.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="changed"):
        module.audit(Path(result["run_dir"]) / "summary.json")
