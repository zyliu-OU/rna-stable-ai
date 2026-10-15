"""Family/clan splits are fixed by metadata before any labels or model outcomes."""

import importlib.util
import json
from pathlib import Path

import pytest

from rnastable.native_journal import atomic_json


@pytest.fixture
def module(monkeypatch):
    project = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(project / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "family_provenance_dataset_test",
        project / "scripts/plan_family_provenance_dataset.py",
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.fixture
def config():
    return json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "configs/family_provenance_dataset_2026-10-14.json"
        ).read_text()
    )


def description(family, clan=None, seeds=10):
    return json.dumps(
        {
            "rfam": {
                "acc": family,
                "release": {"number": "15.1"},
                "clan": {"acc": clan},
                "curation": {"num_seed": seeds},
            }
        }
    ).encode()


def test_null_clans_do_not_merge_unrelated_families_and_split_is_order_invariant(
    module, config
):
    records = {f: description(f) for f in config["candidate_families"]}
    a = module.split_groups(config, records, [])
    b = module.split_groups(config, dict(reversed(list(records.items()))), [])
    assert a == b and a["metadata_ready"] and a["eligible_groups"] == 48
    assert sum(f["role"] == "train" for f in a["selected_families"]) == 12
    assert sum(f["role"] == "validation" for f in a["selected_families"]) == 4
    assert not a["training_authorized"] and not a["inference_authorized"]


def test_related_families_are_one_group_and_never_cross_train_validation(
    module, config
):
    records = {f: description(f) for f in config["candidate_families"]}
    members = config["candidate_families"][:8]
    for family in members:
        records[family] = description(family, "CL00001")
    result = module.split_groups(config, records, [])
    assert result["eligible_groups"] == 41
    selected = [r for r in result["selected_families"] if r["group"] == "clan:CL00001"]
    assert len(selected) <= 1
    if selected:
        assert selected[0]["family_id"] == min(members)


def test_known_exposed_clans_exclude_unseen_family_ids(module, config):
    records = {f: description(f) for f in config["candidate_families"]}
    target = config["candidate_families"][0]
    records[target] = description(target, "CL00001")
    records["RF99999"] = description("RF99999", "CL00001")
    result = module.split_groups(config, records, ["RF99999"])
    assert (
        next(r for r in result["decisions"] if r["family_id"] == target)["reason"]
        == "prior_clan_exposure"
    )
    assert target not in {r["family_id"] for r in result["selected_families"]}


def test_missing_prior_clan_metadata_blocks_instead_of_assuming_independence(
    module, config
):
    with pytest.raises(ValueError, match="Prior family"):
        module.split_groups(config, {}, ["RF99999"])


def test_insufficient_eligible_groups_do_not_lower_threshold_or_replenish_from_labels(
    module, config
):
    descriptions = {f: description(f, seeds=1) for f in config["candidate_families"]}
    result = module.split_groups(config, descriptions, [])
    assert not result["metadata_ready"] and result["selected_families"] == []
    assert not result["new_structure_labels_read"]


@pytest.mark.parametrize("value", [True, "8", -1, None])
def test_malformed_seed_counts_are_not_admitted(module, value):
    with pytest.raises(ValueError):
        module.seed_count(description("RF09999", seeds=value), "RF09999")


@pytest.mark.parametrize(
    "change",
    ["train", "inference", "pretrained", "broad_claim", "projection", "bad_cap"],
)
def test_metadata_protocol_cannot_authorize_training_or_inherit_old_weights(
    module, config, change
):
    if change == "train":
        config["model_training_authorized"] = True
    elif change == "inference":
        config["model_inference_authorized"] = True
    elif change == "pretrained":
        config["future_training"]["initialization"] = "reuse_old_helix"
    elif change == "broad_claim":
        config["independent_test_or_broad_validation_claim"] = True
    elif change == "projection":
        config["future_binding"]["retain_crossing_and_noncanonical_gold"] = False
    else:
        config["maximum_metadata_bytes"] = True
    with pytest.raises(ValueError):
        module.validate_config(config)


@pytest.fixture
def protocol(module, config, tmp_path, monkeypatch):
    monkeypatch.setattr(module, "ROOT", tmp_path)
    dependency = tmp_path / "scripts/plan_raw_structure_panel.py"
    dependency.parent.mkdir()
    dependency.write_text("# fixture metadata dependency\n")
    source = tmp_path / "mapping"
    (source / "source").mkdir(parents=True)
    (source / "source/pdb_full_region.txt").write_text("")
    (source / "source/pdb_full_region_curated.txt").write_text("")
    atomic_json(
        source / "summary.json", {"run_dir": str(source), "sources_complete": True}
    )
    atomic_json(source / "manifest.json", {})
    reused = tmp_path / "reused"
    reused.mkdir()
    (reused / "RF00002.json").write_bytes(description("RF00002"))
    atomic_json(
        reused / "summary.json", {"run_dir": str(reused), "metadata_complete": True}
    )
    atomic_json(reused / "manifest.json", {})
    config["mapping_source_summary"] = str(source / "summary.json")
    config["reusable_metadata_summary"] = str(reused / "summary.json")
    path = tmp_path / "config.json"
    atomic_json(path, config)
    monkeypatch.setattr(
        module, "audit_mapping", lambda p: json.loads(Path(p).read_text())
    )
    monkeypatch.setattr(
        module, "audit_metadata", lambda p: json.loads(Path(p).read_text())
    )
    monkeypatch.setattr(module, "collect_known_exposures", lambda root: [])
    manifest = module.freeze(path)
    return module, Path(manifest["run_dir"]) / "manifest.json"


def test_verified_metadata_reuse_avoids_network_and_preserves_frozen_identity(
    protocol, monkeypatch
):
    module, path = protocol
    calls = []

    def download(url, size, timeout):
        family = url.split("/family/")[1].split("?")[0]
        assert family != "RF00002"
        calls.append(family)
        return description(family)

    monkeypatch.setattr(module, "bounded_download", download)
    result = module.acquire(path)
    assert (
        result["successful_metadata_records"] == 48
        and result["reused_metadata_records"] == 1
    )
    assert len(calls) == 47 and result["selection"]["metadata_ready"]
    assert (
        not result["new_sequence_or_structure_bytes_read"]
        and not result["model_training_authorized"]
    )
    assert not list(module.ROOT.rglob("exposures/*.json"))


def test_candidate_metadata_failures_remain_visible_without_inventing_source_groups(
    protocol, monkeypatch
):
    module, path = protocol

    def unavailable(*a):
        raise OSError("fixture metadata missing")

    monkeypatch.setattr(module, "bounded_download", unavailable)
    result = module.acquire(path)
    assert (
        result["successful_metadata_records"] == 1
        and not result["selection"]["metadata_ready"]
    )
    assert (
        sum(
            r["reason"] == "metadata_unavailable"
            for r in result["selection"]["decisions"]
        )
        == 47
    )


def test_metadata_replay_rejects_changed_cache_and_uses_no_live_state(
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
        lambda *a: pytest.fail("No live exposure in replay"),
    )
    assert module.audit(Path(result["run_dir"]) / "summary.json") == result
    (path.parent / "cache/RF00002.json").write_bytes(description("RF00002", "CL00001"))
    with pytest.raises(ValueError, match="snapshot changed"):
        module.audit(Path(result["run_dir"]) / "summary.json")
