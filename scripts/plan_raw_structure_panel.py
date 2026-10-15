#!/usr/bin/env python3
"""Freeze a raw-contact feasibility panel using PDB/family/clan metadata only."""
# ruff: noqa: E402 -- standalone source bootstrap.

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import sys
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp, write_artifact
from rnastable.exposures import collect_known_exposures
from rnastable.native_journal import atomic_json
from rnastable.prospective_data import bounded_download, validate_description
from rnastable.reference import digest
from rnastable.reference_audit import require
from prepare_structure_derived_source import (
    audit as audit_source,
    audit_protocol as audit_models,
)
from prepare_structure_derived_binding import mapping_rows

NAME = "raw_structure_panel"
BASE = "https://rna.bgsu.edu/rna3dhub/rest/getSequenceBasePairs"


def validate_config(config):
    require(
        type(config.get("schema_version")) is int
        and config["schema_version"] == 1
        and config.get("stage") == "metadata_only_raw_structure_panel"
        and config.get("model_inference_authorized") is False,
        "Raw-panel protocol must remain metadata-only",
    )
    families = config["families"]
    require(
        isinstance(families, list)
        and len(families) == 6
        and len(set(families)) == len(families)
        and all(re.fullmatch(r"RF\d{5}", f) for f in families),
        "Expected six distinct source families",
    )
    require(
        config["expected_metadata_release"] == "15.1",
        "Unrecognized declared metadata release",
    )
    require(
        type(config["metadata_pdb_chain_cap_per_family"]) is int
        and 1 <= config["metadata_pdb_chain_cap_per_family"] <= 5,
        "Invalid metadata candidate cap",
    )
    require(
        type(config["maximum_metadata_bytes"]) is int
        and 1 <= config["maximum_metadata_bytes"] <= 2 * 1024 * 1024
        and type(config["metadata_timeout_seconds"]) is int
        and 1 <= config["metadata_timeout_seconds"] <= 30,
        "Invalid metadata resource bound",
    )
    plan = config["future_binding"]
    require(
        type(plan["minimum_length"]) is int
        and type(plan["maximum_length"]) is int
        and 1 <= plan["minimum_length"] <= plan["maximum_length"] <= 1024
        and type(plan["max_records_per_family"]) is int
        and 1 <= plan["max_records_per_family"] <= 3,
        "Invalid declared final length/cap",
    )
    require(
        plan["sequence_similarity_threshold"] == 0.8
        and plan["source_target"] == "all_returned_cWW_contacts_without_projection"
        and plan["raw_graph_multiple_partners"] == "unsupported_do_not_delete_contacts"
        and plan["selection_order"] == "family_pdb_chain_then_sequence_redundancy"
        and plan["replace_unsupported_records"] is False
        and plan["reference_kind"] == "computational"
        and plan["study_scope"] == "six_family_structure_derived_feasibility_only"
        and plan["feasibility_minimum_supported_families"] == 6
        and plan["feasibility_minimum_per_family"] == 1
        and plan["feasibility_minimum_total"] == 6
        and plan["broad_validation_gate_satisfied"] is False,
        "Raw-contact target or feasibility scope differs",
    )
    return config


def infer_exposed_families(mappings, exposures):
    pdbs = {r["pdb_accession"].lower() for r in exposures if r.get("pdb_accession")}
    return sorted(
        {r["family_id"] for r in exposures if r.get("family_id")}
        | {f for f, pdb, chain in mappings if pdb in pdbs}
    )


def metadata_plan(families, exposed_families):
    names = sorted(set(families) | set(exposed_families))
    require(len(names) <= 40, "Metadata provenance request cap exceeded")
    return [
        {
            "family_id": family,
            "filename": family + ".json",
            "url": f"https://rfam.org/family/{family}?content-type=application%2Fjson",
        }
        for family in names
    ]


def freeze(config_path):
    raw = Path(config_path).read_bytes()
    config = validate_config(json.loads(raw))
    source = audit_source(ROOT / config["mapping_source_summary"])
    require(source["sources_complete"], "Complete pinned PDB metadata required")
    model = audit_models(ROOT / config["model_protocol"])
    source_dir = Path(source["run_dir"]) / "source"
    mappings = mapping_rows(
        (source_dir / "pdb_full_region.txt").read_bytes()
    ) | mapping_rows(
        (source_dir / "pdb_full_region_curated.txt").read_bytes(), curated=True
    )
    exposed = collect_known_exposures(ROOT)
    prior_families = infer_exposed_families(mappings, exposed)
    require(
        not set(config["families"]) & set(prior_families),
        "Proposed raw-panel family already exposed",
    )
    plan = metadata_plan(config["families"], prior_families)
    run = ROOT / "results" / (NAME + "_protocol_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    (run / "config.json").write_bytes(raw)
    atomic_json(run / "exposure.json", exposed)
    atomic_json(run / "mappings.json", sorted(mappings))
    atomic_json(run / "metadata_requests.json", plan)
    atomic_json(run / "prior_families.json", prior_families)
    atomic_json(run / "model_protocol.json", model)
    for name in model["models"]:
        for kind in ("checkpoint.pt", "summary.json"):
            filename = name + "_" + kind
            (run / filename).write_bytes(
                (Path(model["run_dir"]) / filename).read_bytes()
            )
    (run / "driver.py").write_bytes(Path(__file__).read_bytes())
    inputs = [
        Path(source["run_dir"]) / "summary.json",
        Path(source["run_dir"]) / "manifest.json",
        source_dir / "pdb_full_region.txt",
        source_dir / "pdb_full_region_curated.txt",
        ROOT / config["model_protocol"],
    ]
    manifest = {
        "run_dir": str(run),
        "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
        "input_sha256": {str(p): digest(p.read_bytes()) for p in inputs},
        "code_sha256": {
            str(p): digest(p.read_bytes())
            for p in [
                Path(__file__),
                Path(__file__).with_name("prepare_structure_derived_source.py"),
                Path(__file__).with_name("prepare_structure_derived_binding.py"),
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
        "Frozen raw-structure metadata protocol: " + str(run / "manifest.json"),
        flush=True,
    )
    return manifest


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    require(
        manifest == json.loads((run / "manifest.json").read_text()),
        "Raw-panel protocol differs",
    )
    expected = {
        "config.json",
        "exposure.json",
        "mappings.json",
        "metadata_requests.json",
        "prior_families.json",
        "model_protocol.json",
        "driver.py",
    }
    expected |= {
        f"{name}_{kind}"
        for name in ("baseline", "stack", "helix")
        for kind in ("summary.json", "checkpoint.pt")
    }
    require(
        set(manifest["snapshot_sha256"]) == expected,
        "Raw-panel protocol inventory differs",
    )
    for name, sha in manifest["snapshot_sha256"].items():
        require(digest((run / name).read_bytes()) == sha, "Raw-panel snapshot changed")
    for field in ("input_sha256", "code_sha256"):
        for name, sha in manifest[field].items():
            require(
                digest(Path(name).read_bytes()) == sha, "Raw-panel input/code changed"
            )
    config = validate_config(json.loads((run / "config.json").read_text()))
    mappings = {tuple(row) for row in json.loads((run / "mappings.json").read_text())}
    exposed = json.loads((run / "exposure.json").read_text())
    prior = infer_exposed_families(mappings, exposed)
    require(
        prior == json.loads((run / "prior_families.json").read_text())
        and metadata_plan(config["families"], prior)
        == json.loads((run / "metadata_requests.json").read_text()),
        "Raw-panel frozen metadata plan differs",
    )
    models = json.loads((run / "model_protocol.json").read_text())["models"]
    require(
        set(models) == {"baseline", "stack", "helix"},
        "Raw-panel comparison models differ",
    )
    for name, model in models.items():
        require(
            digest((run / (name + "_checkpoint.pt")).read_bytes())
            == model["checkpoint_sha256"],
            "Raw-panel checkpoint bytes differ",
        )
    return manifest


def clan(raw, family, release):
    data = validate_description(raw, family)["rfam"]
    require(
        data["release"]["number"] == release,
        "Metadata release differs from declared release",
    )
    require(
        isinstance(data.get("clan"), dict) and "acc" in data["clan"],
        "Missing clan provenance",
    )
    result = data["clan"]["acc"]
    require(
        result is None or isinstance(result, str) and re.fullmatch(r"CL\d{5}", result),
        "Invalid metadata clan",
    )
    return result


def screen(config, mappings, exposures, descriptions):
    prior = set(infer_exposed_families(mappings, exposures))
    expected = set(prior) | set(config["families"])
    require(set(descriptions) == expected, "Clan metadata inventory differs")
    clans = {
        family: clan(raw, family, config["expected_metadata_release"])
        for family, raw in descriptions.items()
    }
    prior_clans = {clans[f] for f in prior if clans[f] is not None}
    exposed_pdb = {
        r["pdb_accession"].lower() for r in exposures if r.get("pdb_accession")
    }
    candidates, decisions = [], []
    counts = defaultdict(int)
    seen_chains = set()
    for family, pdb, chain in sorted(mappings):
        if family not in config["families"]:
            continue
        if family in prior or pdb in exposed_pdb:
            reason = "prior_family_or_pdb_exposure"
        elif clans[family] is not None and clans[family] in prior_clans:
            reason = "prior_clan_exposure"
        elif (pdb, chain) in seen_chains:
            reason = "cross_family_pdb_chain_redundancy"
        elif counts[family] >= config["metadata_pdb_chain_cap_per_family"]:
            reason = "fixed_metadata_family_cap"
        else:
            reason = "metadata_candidate_only"
            seen_chains.add((pdb, chain))
            counts[family] += 1
            url = (
                BASE
                + "?"
                + urllib.parse.urlencode(
                    {"pdb_id": pdb.upper(), "chain": chain, "only_nested": "False"}
                )
            )
            candidates.append(
                {
                    "id": family + ":" + pdb + "_" + chain,
                    "family_id": family,
                    "pdb_accession": pdb,
                    "chain_id": chain,
                    "url": url,
                }
            )
        decisions.append(
            {
                "family_id": family,
                "pdb_accession": pdb,
                "chain_id": chain,
                "reason": reason,
            }
        )
    return {
        "metadata_candidates": candidates,
        "decisions": decisions,
        "clans": clans,
        "known_exposed_clans": sorted(prior_clans),
        "candidate_counts": {f: counts[f] for f in config["families"]},
        "sequence_or_annotation_bytes_read": False,
        "inference_allowed": False,
        "unknown_training_tool_provenance_resolved": False,
        "broad_validation_gate_satisfied": False,
    }


def acquire(protocol_path):
    protocol = audit_protocol(protocol_path)
    directory = Path(protocol["run_dir"])
    config = json.loads((directory / "config.json").read_text())
    mappings = {
        tuple(row) for row in json.loads((directory / "mappings.json").read_text())
    }
    exposures = collect_known_exposures(ROOT)
    require(
        infer_exposed_families(mappings, exposures)
        == json.loads((directory / "prior_families.json").read_text()),
        "Family exposure changed since metadata freeze",
    )
    run = ROOT / "results" / (NAME + "_metadata_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "protocol.json", protocol)
    atomic_json(run / "exposure.json", exposures)
    attempts = [
        {**r, "status": "not_started"}
        for r in json.loads((directory / "metadata_requests.json").read_text())
    ]
    atomic_json(run / "attempts.json", attempts)
    descriptions = {}
    for a in attempts:
        a["status"] = "started"
        atomic_json(run / "attempts.json", attempts)
        try:
            raw = bounded_download(
                a["url"],
                config["maximum_metadata_bytes"],
                config["metadata_timeout_seconds"],
            )
            (run / a["filename"]).write_bytes(raw)
            a["sha256"] = digest(raw)
            clan(raw, a["family_id"], config["expected_metadata_release"])
            descriptions[a["family_id"]] = raw
            a["status"] = "ok"
        except (OSError, ValueError, KeyError) as exc:
            a.update(status="error", error=type(exc).__name__ + ": " + str(exc))
        atomic_json(run / "attempts.json", attempts)
        print(a["family_id"] + ": " + a["status"], flush=True)
    result = (
        screen(config, mappings, exposures, descriptions)
        if all(a["status"] == "ok" for a in attempts)
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
        "metadata_complete": result is not None,
        "planned_requests": len(attempts),
        "successful_requests": sum(a["status"] == "ok" for a in attempts),
        "screening": result,
        "new_structure_labels_read": False,
        "model_inference_authorized": False,
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
        "Raw-panel metadata summary differs",
    )
    raw = (run / "manifest.json").read_bytes()
    require(
        digest(raw) == summary["manifest_sha256"], "Raw-panel metadata manifest changed"
    )
    manifest = json.loads(raw)
    require(manifest["run_dir"] == str(run), "Raw-panel metadata run identity differs")
    protocol = audit_protocol(Path(manifest["protocol_run"]) / "manifest.json")
    require(
        protocol == json.loads((run / "protocol.json").read_text()),
        "Raw-panel retained protocol differs",
    )
    directory = Path(protocol["run_dir"])
    config = json.loads((directory / "config.json").read_text())
    attempts = json.loads((run / "attempts.json").read_text())
    planned = json.loads((directory / "metadata_requests.json").read_text())
    require(
        len(attempts) == len(planned)
        and all(
            all(a.get(k) == v for k, v in p.items()) and a["status"] in ("ok", "error")
            for a, p in zip(attempts, planned, strict=True)
        ),
        "Raw-panel metadata request inventory differs",
    )
    expected = {"protocol.json", "exposure.json", "attempts.json"} | {
        a["filename"] for a in attempts if "sha256" in a
    }
    require(
        set(manifest["snapshot_sha256"]) == expected,
        "Raw-panel metadata file inventory differs",
    )
    for name, sha in manifest["snapshot_sha256"].items():
        require(
            digest((run / name).read_bytes()) == sha,
            "Raw-panel retained metadata changed",
        )
    descriptions = {}
    for a in attempts:
        if a["status"] == "ok":
            content = (run / a["filename"]).read_bytes()
            require(digest(content) == a["sha256"], "Raw-panel response hash differs")
            clan(content, a["family_id"], config["expected_metadata_release"])
            descriptions[a["family_id"]] = content
    result = None
    if all(a["status"] == "ok" for a in attempts):
        mappings = {
            tuple(row) for row in json.loads((directory / "mappings.json").read_text())
        }
        result = screen(
            config,
            mappings,
            json.loads((run / "exposure.json").read_text()),
            descriptions,
        )
    require(
        summary
        == {
            "complete": True,
            "run_dir": str(run),
            "manifest_sha256": digest(raw),
            "metadata_complete": result is not None,
            "planned_requests": len(attempts),
            "successful_requests": sum(a["status"] == "ok" for a in attempts),
            "screening": result,
            "new_structure_labels_read": False,
            "model_inference_authorized": False,
        },
        "Raw-panel metadata replay differs",
    )
    print(
        "Raw-structure metadata replay passed; no sequence/structure labels, predictions or exposure."
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs/raw_structure_panel_2026-10-14.json",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--acquire", action="store_true")
    mode.add_argument("--verify", type=Path)
    parser.add_argument(
        "--protocol",
        type=Path,
        default=ROOT / "results/raw_structure_panel_protocol.json",
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
