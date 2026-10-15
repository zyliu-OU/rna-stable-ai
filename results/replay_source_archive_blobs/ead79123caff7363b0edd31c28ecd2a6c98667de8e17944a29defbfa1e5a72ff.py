#!/usr/bin/env python3
"""Freeze and acquire a pinned, public author dataset without assay inference."""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp, write_artifact
from rnastable.context_inference import load_checkpoint
from rnastable.exposures import collect_known_exposures
from rnastable.native_journal import atomic_json
from rnastable.reference import digest
from rnastable.reference_audit import require

NAME = "degradation_source"
POLICY = (
    "Pinned author-source acquisition only. No assay labels parsed, sequence selection, "
    "inference, training or native folds. Supplied predicted structures are not experimental gold. "
    "Public short-construct chemical-degradation measurements do not establish mutation effects, "
    "long-RNA stability, in-cell half-life or retained function. A final exposure-aware assay "
    "evaluation protocol remains required before predictions."
)


def validate_config(config):
    require(
        config["schema_version"] == 1
        and type(config["schema_version"]) is int
        and config["stage"] == "source_acquisition_only"
        and config["test_inference_authorized"] is False,
        "Invalid source-only protocol",
    )
    require(
        config["repository"] == "https://github.com/eternagame/KaggleOpenVaccine"
        and re.fullmatch(r"[0-9a-f]{40}", config["commit"])
        and config["source_path"] == "data/Kaggle_RYOS_data/Kaggle_RYOS_trainset.json",
        "Unrecognized author source",
    )
    require(
        type(config["maximum_bytes"]) is int
        and 1 <= config["maximum_bytes"] <= 64 * 1024 * 1024
        and type(config["timeout_seconds"]) is int
        and 1 <= config["timeout_seconds"] <= 30,
        "Invalid download resource bounds",
    )
    require(
        config["future_pilot_record_cap"] == 64
        and config["future_selection_order"] == "sequence_id_lexicographic"
        and config["quality_filter_for_selection"] is False
        and config["reference_structures_are_experimental_gold"] is False,
        "Declared future pilot rules differ",
    )
    require(
        config["measured_targets"]
        == ["reactivity", "deg_Mg_pH10", "deg_pH10", "deg_Mg_50C", "deg_50C"],
        "Assay target inventory differs",
    )
    require(
        set(config["model_sources"]) == {"baseline", "stack", "helix"}
        and config["decoder"] == "exact_sparse"
        and config["pair_penalty"] == 0,
        "Model/decoder inventory differs",
    )
    return config


def urls(config):
    suffix = (
        "eternagame/KaggleOpenVaccine/" + config["commit"] + "/" + config["source_path"]
    )
    return [
        "https://raw.githubusercontent.com/" + suffix,
        "https://media.githubusercontent.com/media/" + suffix,
    ]


def freeze(config_path):
    raw = Path(config_path).read_bytes()
    config = validate_config(json.loads(raw))
    run = ROOT / "results" / (NAME + "_protocol_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    (run / "config.json").write_bytes(raw)
    atomic_json(run / "exposure.json", collect_known_exposures(ROOT))
    models = {}
    for name, relative in config["model_sources"].items():
        source, settings, checkpoint, _ = load_checkpoint(ROOT / relative)
        feature = {
            "baseline": None,
            "stack": "adjacent_stackability",
            "helix": "local_helix_context_v1",
        }[name]
        require(
            settings["seed"] == config["model_seed"]
            and settings["top_k"] == 16
            and settings["inference_decoder"] == config["decoder"]
            and settings.get("pair_features") == feature,
            "Frozen source model differs",
        )
        (run / (name + "_summary.json")).write_bytes(source)
        (run / (name + "_checkpoint.pt")).write_bytes(checkpoint.read_bytes())
        models[name] = settings
    paths = [Path(__file__), *sorted((ROOT / "src/rnastable").glob("*.py"))]
    manifest = {
        "run_dir": str(run),
        "models": models,
        "urls": urls(config),
        "policy": POLICY,
        "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
        "code_sha256": {str(p): digest(p.read_bytes()) for p in paths},
    }
    atomic_json(run / "manifest.json", manifest)
    audit_protocol(run / "manifest.json")
    write_artifact(
        ROOT / "results" / (NAME + "_protocol.json"),
        json.dumps(manifest, indent=2) + "\n",
    )
    print(
        "Frozen measured-degradation source protocol: " + str(run / "manifest.json"),
        flush=True,
    )
    return manifest


def audit_protocol(path):
    plan = json.loads(Path(path).read_text())
    run = Path(plan["run_dir"])
    require(
        plan == json.loads((run / "manifest.json").read_text()),
        "Protocol pointer differs",
    )
    config = validate_config(json.loads((run / "config.json").read_text()))
    require(
        plan["urls"] == urls(config)
        and plan["policy"] == POLICY
        and set(plan["models"]) == set(config["model_sources"]),
        "Protocol scope differs",
    )
    require(
        set(plan["snapshot_sha256"])
        == {"config.json", "exposure.json"}
        | {
            name + suffix
            for name in plan["models"]
            for suffix in ("_summary.json", "_checkpoint.pt")
        },
        "Protocol snapshot inventory differs",
    )
    for name, sha in plan["snapshot_sha256"].items():
        require(
            Path(name).name == name and digest((run / name).read_bytes()) == sha,
            "Protocol input changed",
        )
    for name, settings in plan["models"].items():
        source = json.loads((run / (name + "_summary.json")).read_text())
        require(
            source["complete"] is True
            and source["config"] == settings
            and settings["seed"] == config["model_seed"]
            and source["checkpoint_sha256"]["best_context_model.pt"]
            == plan["snapshot_sha256"][name + "_checkpoint.pt"],
            "Protocol checkpoint binding differs",
        )
    for name, sha in plan["code_sha256"].items():
        require(digest(Path(name).read_bytes()) == sha, "Source protocol code changed")
    return plan


def fetch(url, maximum, timeout):
    request = urllib.request.Request(
        url, headers={"User-Agent": "RNA-StableAI-measured-source/0.1"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        require(
            response.geturl().startswith(
                (
                    "https://raw.githubusercontent.com/",
                    "https://media.githubusercontent.com/",
                )
            ),
            "Author source redirected to an unapproved host",
        )
        raw = response.read(maximum + 1)
    require(0 < len(raw) <= maximum, "Empty or oversized author source")
    require(
        not raw.startswith(b"version https://git-lfs.github.com/spec/"),
        "Git LFS pointer requires the declared media endpoint",
    )
    # Do not inspect any assay values here. Parsing belongs to a separately frozen binding step.
    return raw


def acquire(protocol_path):
    plan = audit_protocol(protocol_path)
    protocol = Path(plan["run_dir"])
    config = json.loads((protocol / "config.json").read_text())
    run = ROOT / "results" / (NAME + "_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "protocol.json", plan)
    attempts = []
    source = None
    for url in plan["urls"]:
        attempt = {"url": url, "status": "started"}
        attempts.append(attempt)
        atomic_json(run / "attempts.json", attempts)
        try:
            raw = fetch(url, config["maximum_bytes"], config["timeout_seconds"])
            (run / "author_trainset.json").write_bytes(raw)
            source = {
                "filename": "author_trainset.json",
                "url": url,
                "sha256": digest(raw),
                "bytes": len(raw),
            }
            attempt.update(status="ok", **source)
        except (OSError, ValueError) as exc:
            attempt.update(status="error", error=type(exc).__name__ + ": " + str(exc))
        atomic_json(run / "attempts.json", attempts)
        print("Measured-source download: " + attempt["status"], flush=True)
        if source:
            break
    summary = {
        "complete": True,
        "run_dir": str(run),
        "sources_complete": source is not None,
        "protocol_sha256": digest((run / "protocol.json").read_bytes()),
        "attempts_sha256": digest((run / "attempts.json").read_bytes()),
        "source": source,
        "assay_labels_parsed": False,
        "test_inference_allowed": False,
    }
    atomic_json(run / "summary.json", summary)
    write_artifact(
        ROOT / "results" / (NAME + "_summary.json"),
        json.dumps(summary, indent=2) + "\n",
    )
    return summary


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(
        summary == json.loads((run / "summary.json").read_text())
        and summary["complete"] is True
        and summary["assay_labels_parsed"] is False
        and summary["test_inference_allowed"] is False,
        "Source acquisition identity differs",
    )
    require(
        digest((run / "protocol.json").read_bytes()) == summary["protocol_sha256"]
        and digest((run / "attempts.json").read_bytes()) == summary["attempts_sha256"],
        "Source ledger changed",
    )
    plan = json.loads((run / "protocol.json").read_text())
    require(
        plan == audit_protocol(Path(plan["run_dir"]) / "manifest.json"),
        "Source protocol differs",
    )
    attempts = json.loads((run / "attempts.json").read_text())
    require(
        1 <= len(attempts) <= len(plan["urls"])
        and [a["url"] for a in attempts] == plan["urls"][: len(attempts)]
        and all(a["status"] in ("ok", "error") for a in attempts),
        "Source request inventory differs",
    )
    successful = [a for a in attempts if a["status"] == "ok"]
    require(
        summary["sources_complete"] == bool(successful) and len(successful) <= 1,
        "Source denominator differs",
    )
    require(
        (successful and attempts[-1]["status"] == "ok")
        or (not successful and len(attempts) == len(plan["urls"])),
        "Source fallback ledger is incomplete",
    )
    if successful:
        source = summary["source"]
        require(
            source
            == {k: successful[0][k] for k in ("filename", "url", "sha256", "bytes")}
            and source["filename"] == "author_trainset.json",
            "Source file binding differs",
        )
        raw = (run / source["filename"]).read_bytes()
        require(
            digest(raw) == source["sha256"] and len(raw) == source["bytes"],
            "Author dataset changed",
        )
    else:
        require(summary["source"] is None, "Failed acquisition retained a source")
    print(
        "Measured-source audit passed: bound bytes and failure ledger; no assay parsing or inference."
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs/degradation_source_pilot_2026-10-13.json",
    )
    parser.add_argument("--protocol", type=Path)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--acquire", action="store_true")
    group.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        return audit(ROOT / "results" / (NAME + "_summary.json"))
    if args.acquire:
        protocol = (
            args.protocol
            or Path(
                json.loads((ROOT / "results" / (NAME + "_protocol.json")).read_text())[
                    "run_dir"
                ]
            )
            / "manifest.json"
        )
        return acquire(protocol)
    return freeze(args.config)


if __name__ == "__main__":
    main()
