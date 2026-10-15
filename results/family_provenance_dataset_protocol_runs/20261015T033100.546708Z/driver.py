#!/usr/bin/env python3
"""Plan a source-labelled development corpus from family/clan metadata only."""
# ruff: noqa: E402 -- standalone source bootstrap.

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp, write_artifact
from rnastable.exposures import collect_known_exposures
from rnastable.native_journal import atomic_json
from rnastable.prospective_data import bounded_download, validate_description
from rnastable.reference import digest
from rnastable.reference_audit import require
from prepare_structure_derived_source import audit as audit_mapping
from prepare_structure_derived_binding import mapping_rows
from plan_raw_structure_panel import (
    audit as audit_metadata,
    clan,
    infer_exposed_families,
)

NAME = "family_provenance_dataset"


def validate_config(config):
    require(
        type(config.get("schema_version")) is int
        and config["schema_version"] == 1
        and config.get("stage") == "family_provenance_metadata_only"
        and config.get("model_training_authorized") is False
        and config.get("model_inference_authorized") is False
        and config.get("independent_test_or_broad_validation_claim") is False,
        "Family data plan must remain metadata-only",
    )
    families = config["candidate_families"]
    require(
        isinstance(families, list)
        and 16 <= len(families) <= 64
        and len(set(families)) == len(families)
        and all(isinstance(f, str) and re.fullmatch(r"RF\d{5}", f) for f in families),
        "Invalid fixed candidate family pool",
    )
    for name in (
        "minimum_seed_sequences",
        "training_groups",
        "validation_groups",
        "maximum_metadata_bytes",
        "metadata_timeout_seconds",
    ):
        require(
            type(config[name]) is int and config[name] > 0,
            "Invalid positive metadata parameter: " + name,
        )
    require(
        config["training_groups"] == 12
        and config["validation_groups"] == 4
        and config["minimum_seed_sequences"] == 8
        and config["maximum_metadata_bytes"] <= 2 * 1024 * 1024
        and config["metadata_timeout_seconds"] <= 30
        and type(config["family_split_seed"]) is int
        and config["expected_metadata_release"] == "15.1"
        and config["grouping"] == "clan_if_assigned_else_family"
        and config["representative_family"] == "lexicographic_minimum_per_group"
        and config["split_order"]
        == "sha256_of_seed_and_group_training_then_validation",
        "Declared group/split policy differs",
    )
    plan = config["future_binding"]
    for name in (
        "minimum_length",
        "maximum_length",
        "train_candidate_cap_per_family",
        "validation_candidate_cap_per_family",
        "minimum_supported_training_records",
        "minimum_supported_validation_records",
        "minimum_supported_per_selected_family",
    ):
        require(
            type(plan[name]) is int and plan[name] > 0,
            "Invalid positive source parameter: " + name,
        )
    require(
        plan["reference_format"] == "pair_set_zero_based_v1"
        and plan["reference_kind"] == "computational"
        and plan["reference_source"]
        == "complete_Rfam_WUSS_consensus_without_contact_deletion"
        and type(plan["minimum_length"]) is int
        and type(plan["maximum_length"]) is int
        and 1 <= plan["minimum_length"] <= plan["maximum_length"] <= 1024
        and plan["train_candidate_cap_per_family"] == 12
        and plan["validation_candidate_cap_per_family"] == 8
        and plan["minimum_supported_training_records"] == 48
        and plan["minimum_supported_validation_records"] == 16
        and plan["minimum_supported_per_selected_family"] == 1
        and plan["sequence_similarity_threshold"] == 0.8
        and plan["selection_order"] == "family_then_sequence_id_before_pair_parsing"
        and plan["replace_unsupported_records"] is False
        and plan["retain_crossing_and_noncanonical_gold"] is True,
        "Future source annotation/selection policy differs",
    )
    training = config["future_training"]
    require(
        training["initialization"] == "declared_random_seeds_no_pretrained_weights"
        and training["heads"] == ["baseline", "stack", "helix"]
        and training["model_seeds"] == [20261015, 7, 1729]
        and training["epochs"] == 10
        and training["learning_rate"] == 0.001
        and training["cpu_threads"] == 2
        and training["device"] == "cpu"
        and training["top_k"] == 16
        and training["decoder"] == "exact_sparse"
        and training["pair_penalty"] == 0
        and training["training_contact_policy"]
        == "retain_full_gold_and_report_unlearnable_contacts"
        and training["checkpoint_selection"]
        == "declared_validation_only_not_completed_test_cohorts",
        "Future training declaration differs",
    )
    return config


def seed_count(raw, family):
    data = validate_description(raw, family)["rfam"]
    value = data.get("curation", {}).get("num_seed")
    require(type(value) is int and value >= 0, "Seed metadata count missing or invalid")
    return value


def split_groups(config, descriptions, exposed_families):
    prior = set(exposed_families)
    require(prior <= set(descriptions), "Prior family/clan metadata unavailable")
    prior_clans = {
        clan(descriptions[f], f, config["expected_metadata_release"]) for f in prior
    }
    prior_clans.discard(None)
    groups, decisions = defaultdict(list), []
    for family in sorted(config["candidate_families"]):
        row = {"family_id": family, "group": None, "seed_sequences": None}
        if family in prior:
            reason = "prior_family_exposure"
        elif family not in descriptions:
            reason = "metadata_unavailable"
        else:
            try:
                assigned = clan(
                    descriptions[family], family, config["expected_metadata_release"]
                )
                count = seed_count(descriptions[family], family)
                row.update(
                    group="clan:" + assigned if assigned else "family:" + family,
                    seed_sequences=count,
                )
                if assigned is not None and assigned in prior_clans:
                    reason = "prior_clan_exposure"
                elif count < config["minimum_seed_sequences"]:
                    reason = "below_declared_metadata_seed_minimum"
                else:
                    reason = "metadata_eligible"
                    groups[row["group"]].append(family)
            except (ValueError, KeyError, TypeError) as exc:
                reason = "unsupported_metadata: " + str(exc)
        decisions.append({**row, "reason": reason})
    ranked = sorted(
        groups,
        key=lambda g: (
            digest((str(config["family_split_seed"]) + ":" + g).encode()),
            g,
        ),
    )
    needed = config["training_groups"] + config["validation_groups"]
    selected = []
    if len(ranked) >= needed:
        for index, group in enumerate(ranked[:needed]):
            selected.append(
                {
                    "group": group,
                    "family_id": min(groups[group]),
                    "role": "train"
                    if index < config["training_groups"]
                    else "validation",
                }
            )
    return {
        "metadata_ready": len(ranked) >= needed,
        "eligible_groups": len(ranked),
        "ranked_groups": ranked,
        "selected_families": selected,
        "decisions": decisions,
        "known_exposed_clans": sorted(prior_clans),
        "new_structure_labels_read": False,
        "training_authorized": False,
        "inference_authorized": False,
        "independent_test_or_broad_validation_claim": False,
        "annotation_interpretation": "Future complete comparative Rfam labels remain computational; family/clan metadata does not prove complete evolutionary independence.",
    }


def freeze(config_path):
    raw = Path(config_path).read_bytes()
    config = validate_config(json.loads(raw))
    mapping = audit_mapping(ROOT / config["mapping_source_summary"])
    reused = audit_metadata(ROOT / config["reusable_metadata_summary"])
    require(
        mapping["sources_complete"] and reused["metadata_complete"],
        "Complete retained metadata required",
    )
    source = Path(mapping["run_dir"]) / "source"
    mappings = mapping_rows(
        (source / "pdb_full_region.txt").read_bytes()
    ) | mapping_rows(
        (source / "pdb_full_region_curated.txt").read_bytes(), curated=True
    )
    exposures = collect_known_exposures(ROOT)
    prior = infer_exposed_families(mappings, exposures)
    families = sorted(set(config["candidate_families"]) | set(prior))
    require(len(families) <= 96, "Metadata request cap exceeded")
    run = ROOT / "results" / (NAME + "_protocol_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    (run / "config.json").write_bytes(raw)
    atomic_json(run / "exposure.json", exposures)
    atomic_json(run / "mappings.json", sorted(mappings))
    atomic_json(run / "prior_families.json", prior)
    inputs = {}
    requests = []
    for family in families:
        old = Path(reused["run_dir"]) / (family + ".json")
        row = {
            "family_id": family,
            "filename": family + ".json",
            "url": f"https://rfam.org/family/{family}?content-type=application%2Fjson",
        }
        if old.is_file():
            content = old.read_bytes()
            clan(content, family, config["expected_metadata_release"])
            cached = run / "cache" / old.name
            cached.parent.mkdir(exist_ok=True)
            cached.write_bytes(content)
            row["cache_file"] = "cache/" + old.name
            inputs[str(old)] = digest(content)
        requests.append(row)
    atomic_json(run / "requests.json", requests)
    (run / "driver.py").write_bytes(Path(__file__).read_bytes())
    for directory in (Path(mapping["run_dir"]), Path(reused["run_dir"])):
        for filename in ("manifest.json", "summary.json"):
            p = directory / filename
            inputs[str(p)] = digest(p.read_bytes())
    for filename in ("pdb_full_region.txt", "pdb_full_region_curated.txt"):
        p = source / filename
        inputs[str(p)] = digest(p.read_bytes())
    manifest = {
        "run_dir": str(run),
        "input_sha256": inputs,
        "snapshot_sha256": {
            str(p.relative_to(run)): digest(p.read_bytes())
            for p in run.rglob("*")
            if p.is_file()
        },
        "code_sha256": {
            str(p): digest(p.read_bytes())
            for p in [
                Path(__file__),
                ROOT / "scripts/plan_raw_structure_panel.py",
                *sorted((ROOT / "src/rnastable").glob("*.py")),
            ]
        },
    }
    atomic_json(run / "manifest.json", manifest)
    audit_protocol(run / "manifest.json")
    write_artifact(
        ROOT / "results" / (NAME + "_protocol.json"),
        json.dumps(manifest, indent=2) + "\n",
    )
    print(
        "Frozen family-provenance metadata protocol: " + str(run / "manifest.json"),
        flush=True,
    )
    return manifest


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    require(
        manifest == json.loads((run / "manifest.json").read_text()),
        "Family-data retained protocol differs",
    )
    for field in ("input_sha256", "code_sha256"):
        for name, sha in manifest[field].items():
            require(
                digest(Path(name).read_bytes()) == sha, "Family-data input/code changed"
            )
    config = validate_config(json.loads((run / "config.json").read_text()))
    mappings = {tuple(row) for row in json.loads((run / "mappings.json").read_text())}
    exposures = json.loads((run / "exposure.json").read_text())
    prior = infer_exposed_families(mappings, exposures)
    require(
        prior == json.loads((run / "prior_families.json").read_text()),
        "Family-data prior family inventory differs",
    )
    requests = json.loads((run / "requests.json").read_text())
    require(
        [r["family_id"] for r in requests]
        == sorted(set(config["candidate_families"]) | set(prior)),
        "Family-data request inventory differs",
    )
    expected = {
        "config.json",
        "exposure.json",
        "mappings.json",
        "prior_families.json",
        "requests.json",
        "driver.py",
    }
    for row in requests:
        family = row["family_id"]
        require(
            row["filename"] == family + ".json"
            and row["url"]
            == f"https://rfam.org/family/{family}?content-type=application%2Fjson",
            "Family-data request identity differs",
        )
        if "cache_file" in row:
            require(
                row["cache_file"] == "cache/" + row["filename"],
                "Family-data cache path differs",
            )
            expected.add(row["cache_file"])
            clan(
                (run / row["cache_file"]).read_bytes(),
                family,
                config["expected_metadata_release"],
            )
    require(
        set(manifest["snapshot_sha256"]) == expected,
        "Family-data protocol file inventory differs",
    )
    for name, sha in manifest["snapshot_sha256"].items():
        require(
            digest((run / name).read_bytes()) == sha, "Family-data snapshot changed"
        )
    return manifest


def acquire(protocol_path):
    protocol = audit_protocol(protocol_path)
    directory = Path(protocol["run_dir"])
    config = json.loads((directory / "config.json").read_text())
    mappings = {
        tuple(row) for row in json.loads((directory / "mappings.json").read_text())
    }
    prior = infer_exposed_families(mappings, collect_known_exposures(ROOT))
    require(
        prior == json.loads((directory / "prior_families.json").read_text()),
        "Family exposure changed since metadata freeze",
    )
    run = ROOT / "results" / (NAME + "_metadata_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "protocol.json", protocol)
    attempts = [
        {**r, "status": "not_started"}
        for r in json.loads((directory / "requests.json").read_text())
    ]
    atomic_json(run / "attempts.json", attempts)
    descriptions = {}
    for row in attempts:
        row["status"] = "started"
        atomic_json(run / "attempts.json", attempts)
        try:
            if "cache_file" in row:
                content = (directory / row["cache_file"]).read_bytes()
                row["retrieval"] = "retained_release_bound_metadata"
            else:
                content = bounded_download(
                    row["url"],
                    config["maximum_metadata_bytes"],
                    config["metadata_timeout_seconds"],
                )
                row["retrieval"] = "downloaded_metadata"
            (run / row["filename"]).write_bytes(content)
            row["sha256"] = digest(content)
            clan(content, row["family_id"], config["expected_metadata_release"])
            descriptions[row["family_id"]] = content
            row["status"] = "ok"
        except (OSError, ValueError, KeyError, TypeError) as exc:
            row.update(status="error", error=type(exc).__name__ + ": " + str(exc))
        atomic_json(run / "attempts.json", attempts)
        print(row["family_id"] + ": " + row["status"], flush=True)
    result = (
        split_groups(config, descriptions, prior)
        if set(prior) <= set(descriptions)
        else None
    )
    manifest = {
        "run_dir": str(run),
        "protocol_run": str(directory),
        "snapshot_sha256": {
            p.name: digest(p.read_bytes()) for p in run.iterdir() if p.is_file()
        },
    }
    atomic_json(run / "manifest.json", manifest)
    summary = {
        "complete": True,
        "run_dir": str(run),
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "planned_metadata_requests": len(attempts),
        "successful_metadata_records": sum(a["status"] == "ok" for a in attempts),
        "reused_metadata_records": sum(
            a["status"] == "ok"
            and a.get("retrieval") == "retained_release_bound_metadata"
            for a in attempts
        ),
        "selection": result,
        "new_sequence_or_structure_bytes_read": False,
        "model_training_authorized": False,
    }
    atomic_json(run / "summary.json", summary)
    audit(run / "summary.json")
    write_artifact(
        ROOT / "results" / (NAME + "_metadata_summary.json"),
        json.dumps(summary, indent=2) + "\n",
    )
    return summary


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(
        summary == json.loads((run / "summary.json").read_text()),
        "Family-data metadata summary differs",
    )
    raw = (run / "manifest.json").read_bytes()
    require(
        digest(raw) == summary["manifest_sha256"],
        "Family-data metadata manifest changed",
    )
    manifest = json.loads(raw)
    require(manifest["run_dir"] == str(run), "Family-data metadata run differs")
    protocol = audit_protocol(Path(manifest["protocol_run"]) / "manifest.json")
    directory = Path(protocol["run_dir"])
    require(
        protocol == json.loads((run / "protocol.json").read_text()),
        "Family-data retained protocol differs",
    )
    config = json.loads((directory / "config.json").read_text())
    prior = json.loads((directory / "prior_families.json").read_text())
    requests = json.loads((directory / "requests.json").read_text())
    attempts = json.loads((run / "attempts.json").read_text())
    require(
        len(attempts) == len(requests)
        and all(
            all(a.get(k) == v for k, v in r.items()) and a["status"] in ("ok", "error")
            for a, r in zip(attempts, requests, strict=True)
        ),
        "Family-data attempt inventory differs",
    )
    expected = {"protocol.json", "attempts.json"} | {
        r["filename"] for r in attempts if "sha256" in r
    }
    require(
        set(manifest["snapshot_sha256"]) == expected,
        "Family-data retained-file inventory differs",
    )
    for name, sha in manifest["snapshot_sha256"].items():
        require(
            digest((run / name).read_bytes()) == sha,
            "Family-data metadata response changed",
        )
    descriptions = {}
    for row in attempts:
        if row["status"] == "ok":
            content = (run / row["filename"]).read_bytes()
            require(
                digest(content) == row["sha256"], "Family-data response hash differs"
            )
            if "cache_file" in row:
                require(
                    row["retrieval"] == "retained_release_bound_metadata"
                    and content == (directory / row["cache_file"]).read_bytes(),
                    "Family-data cache reuse differs",
                )
            else:
                require(
                    row["retrieval"] == "downloaded_metadata",
                    "Family-data retrieval identity differs",
                )
            clan(content, row["family_id"], config["expected_metadata_release"])
            descriptions[row["family_id"]] = content
    selection = (
        split_groups(config, descriptions, prior)
        if set(prior) <= set(descriptions)
        else None
    )
    require(
        summary
        == {
            "complete": True,
            "run_dir": str(run),
            "manifest_sha256": digest(raw),
            "planned_metadata_requests": len(attempts),
            "successful_metadata_records": sum(a["status"] == "ok" for a in attempts),
            "reused_metadata_records": sum(
                a["status"] == "ok"
                and a.get("retrieval") == "retained_release_bound_metadata"
                for a in attempts
            ),
            "selection": selection,
            "new_sequence_or_structure_bytes_read": False,
            "model_training_authorized": False,
        },
        "Family-data metadata replay differs",
    )
    print(
        "Family-provenance metadata replay passed; no new labels, inference, fitting or exposure."
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs/family_provenance_dataset_2026-10-14.json",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--acquire", action="store_true")
    mode.add_argument("--verify", type=Path)
    parser.add_argument(
        "--protocol",
        type=Path,
        default=ROOT / "results/family_provenance_dataset_protocol.json",
    )
    args = parser.parse_args()
    if args.verify:
        audit(args.verify)
    elif args.acquire:
        acquire(args.protocol)
    else:
        freeze(args.config)


if __name__ == "__main__":
    main()
