#!/usr/bin/env python3
"""Freeze, acquire and replay a BGSU RNA 3D Hub metadata-only NR export."""

import argparse
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.reference import digest  # noqa: E402

CONFIG = ROOT / "configs/bgsu_nr_source_2026-10-16.json"
PROTOCOL = ROOT / "results/bgsu_nr_source_protocol.json"
SUMMARY = ROOT / "results/bgsu_nr_source_summary.json"
URL = "https://rna.bgsu.edu/rna3dhub/nrlist/download/NR/4.61/3.5A/json/full"


def validate_config(config):
    if (config.get("schema_version") != 1
            or config.get("stage") != "metadata_only_representative_structure_source"
            or config.get("source_release") != "4.61"
            or config.get("resolution_cutoff") != "3.5A"
            or config.get("format") != "json_full"
            or config.get("url") != URL
            or type(config.get("maximum_response_bytes")) is not int
            or not 1 <= config["maximum_response_bytes"] <= 104857600
            or type(config.get("timeout_seconds")) is not int
            or not 1 <= config["timeout_seconds"] <= 90
            or config.get("candidate_sequences_allowed_at_this_stage") is not False
            or config.get("contact_labels_allowed_at_this_stage") is not False
            or config.get("model_inference_authorized") is not False):
        raise ValueError("Invalid fixed BGSU metadata source protocol")
    return config


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    raw = CONFIG.read_bytes()
    validate_config(json.loads(raw))
    run = ROOT / "results/bgsu_nr_source_protocol_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    (run / "config.json").write_bytes(raw)
    (run / "driver.py").write_bytes(Path(__file__).read_bytes())
    manifest = {"run_dir": str(run),
                "config_sha256": digest(raw),
                "driver_sha256": digest(Path(__file__).read_bytes()),
                "source_url": URL,
                "metadata_only": True}
    atomic_json(run / "manifest.json", manifest)
    audit_protocol(run / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen BGSU metadata source:", run / "manifest.json")


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    if manifest != json.loads((run / "manifest.json").read_text()):
        raise ValueError("BGSU metadata protocol manifest differs")
    raw = (run / "config.json").read_bytes()
    if digest(raw) != manifest["config_sha256"]:
        raise ValueError("BGSU metadata configuration changed")
    config = validate_config(json.loads(raw))
    if (manifest["source_url"] != URL or manifest["metadata_only"] is not True
            or digest((run / "driver.py").read_bytes()) != manifest["driver_sha256"]
            or digest(Path(__file__).read_bytes()) != manifest["driver_sha256"]):
        raise ValueError("BGSU metadata protocol identity changed")
    return manifest, config


def fetch(config):
    request = Request(config["url"], headers={
        "User-Agent": "RNA-StableAI-metadata-source/0.1"})
    with urlopen(request, timeout=config["timeout_seconds"]) as response:
        if response.geturl() != config["url"]:
            raise ValueError("BGSU source redirected away from fixed URL")
        raw = response.read(config["maximum_response_bytes"] + 1)
    if not raw or len(raw) > config["maximum_response_bytes"]:
        raise ValueError("Empty or oversized BGSU metadata response")
    json.loads(raw)
    return raw


def acquire(path):
    protocol, config = audit_protocol(path)
    run = ROOT / "results/bgsu_nr_source_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "protocol.json", protocol)
    attempt = {"url": config["url"], "status": "started"}
    atomic_json(run / "attempt.json", attempt)
    try:
        raw = fetch(config)
        (run / "source.json").write_bytes(raw)
        attempt.update(status="ok", sha256=digest(raw), size_bytes=len(raw))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        attempt.update(status="error", error=type(exc).__name__ + ": " + str(exc))
    atomic_json(run / "attempt.json", attempt)
    manifest = {"run_dir": str(run), "protocol_run": protocol["run_dir"],
                "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()}}
    atomic_json(run / "manifest.json", manifest)
    summary = {"complete": True, "run_dir": str(run),
               "manifest_sha256": digest((run / "manifest.json").read_bytes()),
               "source_status": attempt["status"],
               "source_size_bytes": attempt.get("size_bytes"),
               "candidate_sequences_read": False,
               "contact_labels_read": False,
               "model_inference_performed": False}
    atomic_json(run / "summary.json", summary)
    audit(run / "summary.json")
    if SUMMARY.exists():
        raise FileExistsError(SUMMARY)
    atomic_json(SUMMARY, summary)
    print("BGSU metadata source:", attempt["status"], run / "summary.json")


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    if summary != json.loads((run / "summary.json").read_text()):
        raise ValueError("BGSU metadata summary differs")
    raw_manifest = (run / "manifest.json").read_bytes()
    if digest(raw_manifest) != summary["manifest_sha256"]:
        raise ValueError("BGSU metadata manifest changed")
    manifest = json.loads(raw_manifest)
    protocol, config = audit_protocol(Path(manifest["protocol_run"]) / "manifest.json")
    if json.loads((run / "protocol.json").read_text()) != protocol:
        raise ValueError("BGSU metadata protocol copy changed")
    attempt = json.loads((run / "attempt.json").read_text())
    if attempt.get("url") != config["url"]:
        raise ValueError("BGSU metadata request URL changed")
    expected_files = {"protocol.json", "attempt.json"}
    if attempt["status"] == "ok":
        raw = (run / "source.json").read_bytes()
        if digest(raw) != attempt["sha256"] or len(raw) != attempt["size_bytes"]:
            raise ValueError("BGSU metadata response changed")
        json.loads(raw)
        expected_files.add("source.json")
    elif attempt["status"] != "error" or "error" not in attempt:
        raise ValueError("BGSU metadata request unfinished")
    if set(manifest["snapshot_sha256"]) != expected_files:
        raise ValueError("BGSU metadata acquisition file inventory differs")
    for name, sha in manifest["snapshot_sha256"].items():
        if digest((run / name).read_bytes()) != sha:
            raise ValueError("BGSU metadata acquisition snapshot changed")
    expected = {"complete": True, "run_dir": str(run),
                "manifest_sha256": digest(raw_manifest),
                "source_status": attempt["status"],
                "source_size_bytes": attempt.get("size_bytes"),
                "candidate_sequences_read": False,
                "contact_labels_read": False,
                "model_inference_performed": False}
    if summary != expected:
        raise ValueError("BGSU metadata summary counts differ")
    print("BGSU metadata acquisition replay passed")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--acquire", action="store_true")
    mode.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        audit(args.verify)
    elif args.acquire:
        acquire(PROTOCOL)
    else:
        freeze()


if __name__ == "__main__":
    main()
