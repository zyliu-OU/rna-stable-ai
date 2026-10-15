#!/usr/bin/env python3
"""Freeze and acquire pinned per-sequence PDB-derived annotation source files."""
# ruff: noqa: E402 -- standalone source bootstrap.

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp, write_artifact
from rnastable.context_inference import load_checkpoint
from rnastable.exposures import collect_known_exposures
from rnastable.native_journal import atomic_json
from rnastable.reference import digest
from rnastable.reference_audit import require
from audit_reference_readiness import validate_policy

NAME = "structure_derived_source"
REPOSITORY = "Rfam/rfam-3d-seed-alignments"
SUPPORT_FILES = {
    "LICENSE",
    "README.md",
    "add_3d.py",
    "fr3d_2d.py",
    "pdb_full_region.txt",
    "pdb_full_region_curated.txt",
}
POLICY = (
    "Pinned source acquisition only. Retain all requested files and failures. No annotation "
    "pairs parsed, cohort selected, model inference, native folds, or new exposure. "
    "Per-sequence FR3D/PDB-derived annotations are distinct from seed consensus and "
    "direct chemical-probing measurements. Final sequence/provenance binding, declared "
    "coverage minima, exposure events, and evaluation protocol remain required."
)


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def validate_config(config):
    require(
        type(config.get("schema_version")) is int
        and config["schema_version"] == 1
        and config.get("stage") == "structure_derived_source_acquisition_only"
        and config.get("test_inference_authorized") is False,
        "Invalid structure-derived source-only protocol",
    )
    require(
        config.get("repository") == REPOSITORY
        and re.fullmatch(r"[0-9a-f]{40}", config.get("commit", "")),
        "Unrecognized pinned annotation source",
    )
    families = config.get("families")
    require(
        isinstance(families, list)
        and 1 <= len(families) <= 3
        and len(set(families)) == len(families)
        and all(isinstance(f, str) and re.fullmatch(r"RF\d{5}", f) for f in families),
        "Invalid source family inventory",
    )
    expected = SUPPORT_FILES | {f"data/output/{f}.sto" for f in families}
    files = config.get("files")
    require(
        isinstance(files, list)
        and len(files) == len(expected)
        and {f["path"] for f in files} == expected,
        "Source file inventory differs",
    )
    limit, timeout = config.get("maximum_bytes_per_file"), config.get("timeout_seconds")
    require(
        type(limit) is int
        and 1 <= limit <= 10 * 1024 * 1024
        and type(timeout) is int
        and 1 <= timeout <= 30,
        "Invalid source resource bound",
    )
    for f in files:
        require(
            set(f) == {"path", "git_blob", "bytes"}
            and re.fullmatch(r"[0-9a-f]{40}", f["git_blob"])
            and type(f["bytes"]) is int
            and 1 <= f["bytes"] <= limit,
            "Malformed expected source blob",
        )
    require(
        set(config["model_sources"]) == {"baseline", "stack", "helix"}
        and config.get("decoder") == "exact_sparse"
        and config.get("pair_penalty") == 0,
        "Comparison model inventory differs",
    )
    plan = config["future_binding"]
    require(
        type(plan["minimum_length"]) is int
        and type(plan["maximum_length"]) is int
        and 1 <= plan["minimum_length"] <= plan["maximum_length"] <= 1024
        and type(plan["max_records_per_family"]) is int
        and 1 <= plan["max_records_per_family"] <= 5,
        "Invalid future length/cap bound",
    )
    require(
        plan["selection_order"] == "family_pdb_chain_sequence_id"
        and plan["similarity_threshold"] == 0.8
        and plan["reference_format"] == "pair_set_zero_based_v1"
        and plan["reference_source"]
        == "per_sequence_PDB_SS_annotation_only_no_consensus_fallback"
        and plan["include_crossing_pairs"] is True
        and plan["replace_unsupported_records"] is False
        and plan["merge_repeated_pdb_sequences_for_selection"] is True,
        "Declared per-sequence annotation policy differs",
    )
    require(
        plan["readiness_policy"] == "configs/reference_readiness.json",
        "Unknown readiness policy path",
    )
    return config


def source_url(config, entry):
    return f"https://raw.githubusercontent.com/{REPOSITORY}/{config['commit']}/{entry['path']}"


def download_file(url, limit, timeout):
    require(
        url.startswith(f"https://raw.githubusercontent.com/{REPOSITORY}/"),
        "Unexpected source URL",
    )
    request = urllib.request.Request(
        url, headers={"User-Agent": "RNA-StableAI/source-provenance"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        require(response.geturl() == url, "Source download redirected")
        raw = response.read(limit + 1)
    require(len(raw) <= limit, "Source byte bound exceeded")
    return raw


def freeze(config_path):
    raw = Path(config_path).read_bytes()
    config = validate_config(json.loads(raw))
    exposures = collect_known_exposures(ROOT)
    require(
        not set(config["families"]) & {r.get("family_id") for r in exposures},
        "Proposed structure-derived family already consumed",
    )
    readiness = (ROOT / config["future_binding"]["readiness_policy"]).read_bytes()
    validate_policy(json.loads(readiness))
    sources = {}
    for name, relative in config["model_sources"].items():
        source, settings, checkpoint, _ = load_checkpoint(ROOT / relative)
        require(
            settings["seed"] == config["model_seed"]
            and settings["top_k"] == 16
            and settings["inference_decoder"] == config["decoder"]
            and settings.get("pair_features")
            == {
                "baseline": None,
                "stack": "adjacent_stackability",
                "helix": "local_helix_context_v1",
            }[name],
            "Frozen source model identity differs",
        )
        sources[name] = (source, settings, checkpoint.read_bytes())
    run = ROOT / "results" / (NAME + "_protocol_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    (run / "config.json").write_bytes(raw)
    (run / "readiness_policy.json").write_bytes(readiness)
    atomic_json(run / "exposure.json", exposures)
    for name, (source, _, weights) in sources.items():
        (run / (name + "_summary.json")).write_bytes(source)
        (run / (name + "_checkpoint.pt")).write_bytes(weights)
    manifest = {
        "run_dir": str(run),
        "policy": POLICY,
        "models": {
            name: {"config": settings, "checkpoint_sha256": digest(weights)}
            for name, (_, settings, weights) in sources.items()
        },
        "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
        "code_sha256": {
            str(p): digest(p.read_bytes())
            for p in [
                Path(__file__),
                Path(__file__).with_name("audit_reference_readiness.py"),
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
        "Frozen structure-derived source protocol: " + str(run / "manifest.json"),
        flush=True,
    )
    return manifest


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    require(
        manifest == json.loads((run / "manifest.json").read_text())
        and manifest["policy"] == POLICY,
        "Retained source protocol differs",
    )
    expected = {"config.json", "readiness_policy.json", "exposure.json"} | {
        f"{name}_{kind}"
        for name in ("baseline", "stack", "helix")
        for kind in ("summary.json", "checkpoint.pt")
    }
    require(
        set(manifest["snapshot_sha256"]) == expected,
        "Protocol snapshot inventory differs",
    )
    for name, sha in manifest["snapshot_sha256"].items():
        require(
            digest((run / name).read_bytes()) == sha,
            "Protocol snapshot changed: " + name,
        )
    for name, sha in manifest["code_sha256"].items():
        require(
            digest(Path(name).read_bytes()) == sha, "Protocol code changed: " + name
        )
    config = validate_config(json.loads((run / "config.json").read_text()))
    validate_policy(json.loads((run / "readiness_policy.json").read_text()))
    require(
        set(manifest["models"]) == set(config["model_sources"]),
        "Protocol models differ",
    )
    for name, model in manifest["models"].items():
        summary = json.loads((run / (name + "_summary.json")).read_text())
        require(
            summary["complete"] is True
            and summary["config"] == model["config"]
            and summary["config"]["seed"] == config["model_seed"]
            and model["checkpoint_sha256"]
            == manifest["snapshot_sha256"][name + "_checkpoint.pt"]
            == summary["checkpoint_sha256"]["best_context_model.pt"],
            "Protocol checkpoint binding differs",
        )
    return manifest


def acquire(protocol_path):
    protocol = audit_protocol(protocol_path)
    config = json.loads((Path(protocol["run_dir"]) / "config.json").read_text())
    require(
        not set(config["families"])
        & {r.get("family_id") for r in collect_known_exposures(ROOT)},
        "Source family consumed since protocol freeze",
    )
    run = ROOT / "results" / (NAME + "_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "protocol.json", protocol)
    attempts = [
        {**f, "url": source_url(config, f), "status": "not_started"}
        for f in config["files"]
    ]
    atomic_json(run / "attempts.json", attempts)
    for attempt in attempts:
        attempt["status"] = "started"
        atomic_json(run / "attempts.json", attempts)
        try:
            raw = download_file(
                attempt["url"],
                config["maximum_bytes_per_file"],
                config["timeout_seconds"],
            )
            target = run / "source" / attempt["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            attempt["sha256"] = digest(raw)
            require(
                len(raw) == attempt["bytes"] and git_blob(raw) == attempt["git_blob"],
                "Source bytes differ from predeclared Git blob",
            )
            attempt["status"] = "ok"
        except (OSError, ValueError) as exc:
            attempt.update(status="error", error=type(exc).__name__ + ": " + str(exc))
        atomic_json(run / "attempts.json", attempts)
        print(attempt["path"] + ": " + attempt["status"], flush=True)
    files = [
        run / "protocol.json",
        run / "attempts.json",
        *[run / "source" / a["path"] for a in attempts if "sha256" in a],
    ]
    manifest = {
        "run_dir": str(run),
        "protocol_run": protocol["run_dir"],
        "policy": POLICY,
        "snapshot_sha256": {
            str(p.relative_to(run)): digest(p.read_bytes()) for p in files
        },
    }
    atomic_json(run / "manifest.json", manifest)
    summary = {
        "complete": True,
        "run_dir": str(run),
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "sources_complete": all(a["status"] == "ok" for a in attempts),
        "planned_requests": len(attempts),
        "successful_requests": sum(a["status"] == "ok" for a in attempts),
        "annotation_pairs_parsed": False,
        "test_inference_allowed": False,
    }
    atomic_json(run / "summary.json", summary)
    audit(run / "summary.json")
    write_artifact(
        ROOT / "results" / (NAME + "_summary.json"),
        json.dumps(summary, indent=2) + "\n",
    )
    return summary


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(
        summary == json.loads((run / "summary.json").read_text()),
        "Retained source summary differs",
    )
    raw = (run / "manifest.json").read_bytes()
    require(digest(raw) == summary["manifest_sha256"], "Source manifest changed")
    manifest = json.loads(raw)
    require(
        manifest["run_dir"] == str(run) and manifest["policy"] == POLICY,
        "Source identity differs",
    )
    protocol = audit_protocol(Path(manifest["protocol_run"]) / "manifest.json")
    require(
        protocol == json.loads((run / "protocol.json").read_text()),
        "Acquisition protocol differs",
    )
    config = json.loads((Path(protocol["run_dir"]) / "config.json").read_text())
    attempts = json.loads((run / "attempts.json").read_text())
    require(len(attempts) == len(config["files"]), "Source request denominator differs")
    expected_files = {"protocol.json", "attempts.json"}
    for attempt, entry in zip(attempts, config["files"], strict=True):
        require(
            all(attempt[key] == value for key, value in entry.items())
            and attempt["url"] == source_url(config, entry)
            and attempt["status"] in ("ok", "error"),
            "Source request differs from plan",
        )
        if "sha256" in attempt:
            name = "source/" + attempt["path"]
            expected_files.add(name)
            content = (run / name).read_bytes()
            require(digest(content) == attempt["sha256"], "Retained response changed")
            if attempt["status"] == "ok":
                require(
                    len(content) == entry["bytes"]
                    and git_blob(content) == entry["git_blob"],
                    "Retained successful Git blob differs",
                )
        else:
            require(attempt["status"] != "ok", "Successful response bytes missing")
    require(
        set(manifest["snapshot_sha256"]) == expected_files,
        "Source snapshot inventory differs",
    )
    for name, sha in manifest["snapshot_sha256"].items():
        require(digest((run / name).read_bytes()) == sha, "Source snapshot changed")
    expected = {
        "complete": True,
        "run_dir": str(run),
        "manifest_sha256": digest(raw),
        "sources_complete": all(a["status"] == "ok" for a in attempts),
        "planned_requests": len(attempts),
        "successful_requests": sum(a["status"] == "ok" for a in attempts),
        "annotation_pairs_parsed": False,
        "test_inference_allowed": False,
    }
    require(summary == expected, "Source acquisition accounting differs")
    print(
        "Structure-derived source audit passed: exact Git blobs, response ledger and frozen models; no annotation parsing."
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs/structure_derived_source_2026-10-14.json",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--acquire", action="store_true")
    mode.add_argument("--verify", type=Path, metavar="SUMMARY")
    parser.add_argument(
        "--protocol",
        type=Path,
        default=ROOT / "results/structure_derived_source_protocol.json",
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
