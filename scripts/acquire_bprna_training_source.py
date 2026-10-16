#!/usr/bin/env python3
"""Freeze and acquire an official bpRNA dot-bracket training-source archive."""

import argparse
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.reference import digest  # noqa: E402

CONFIG = ROOT / "configs/bprna_training_source_2026-10-16.json"
PROTOCOL = ROOT / "results/bprna_training_source_protocol.json"
URL = "https://bprna.cgrb.oregonstate.edu/bpRNA_1m/dbnFiles.zip"


def validate_config(config):
    if (config.get("schema_version") != 1
            or config.get("stage") != "training_only_length_expansion_source"
            or config.get("url") != URL
            or config.get("active_maximum_length_exclusive") != 5000
            or config.get("maximum_response_bytes") != 62914560
            or config.get("timeout_seconds") != 120
            or config.get("training_only") is not True
            or config.get("independent_test_use_authorized") is not False
            or config.get("model_training_authorized_at_acquisition") is not False
            or config.get("model_inference_authorized_at_acquisition") is not False):
        raise ValueError("Invalid bpRNA training-source configuration")
    return config


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    raw = CONFIG.read_bytes()
    validate_config(json.loads(raw))
    run = ROOT / "results/bprna_training_source_protocol_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    (run / "config.json").write_bytes(raw)
    (run / "driver.py").write_bytes(Path(__file__).read_bytes())
    manifest = {"run_dir": str(run), "config_sha256": digest(raw),
                "driver_sha256": digest(Path(__file__).read_bytes()),
                "source_url": URL, "training_only": True}
    atomic_json(run / "manifest.json", manifest)
    audit_protocol(run / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen bpRNA training source:", run / "manifest.json")


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    if manifest != json.loads((run / "manifest.json").read_text()):
        raise ValueError("bpRNA protocol manifest differs")
    raw = (run / "config.json").read_bytes()
    if digest(raw) != manifest["config_sha256"]:
        raise ValueError("bpRNA source configuration changed")
    config = validate_config(json.loads(raw))
    if (manifest["source_url"] != URL or manifest["training_only"] is not True
            or digest((run / "driver.py").read_bytes()) != manifest["driver_sha256"]
            or digest(Path(__file__).read_bytes()) != manifest["driver_sha256"]):
        raise ValueError("bpRNA protocol driver/source differs")
    return manifest, config


def fetch(config):
    request = Request(config["url"], headers={
        "User-Agent": "RNA-StableAI-training-source/0.1"})
    with urlopen(request, timeout=config["timeout_seconds"]) as response:
        if response.geturl() != config["url"]:
            raise ValueError("bpRNA source redirected from fixed URL")
        raw = response.read(config["maximum_response_bytes"] + 1)
    if not raw or len(raw) > config["maximum_response_bytes"]:
        raise ValueError("Empty or oversized bpRNA source")
    return raw


def acquire(path):
    protocol, config = audit_protocol(path)
    run = ROOT / "results/bprna_training_source_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "protocol.json", protocol)
    attempt = {"url": config["url"], "status": "started"}
    atomic_json(run / "attempt.json", attempt)
    try:
        raw = fetch(config)
        (run / "source.zip").write_bytes(raw)
        if not zipfile.is_zipfile(run / "source.zip"):
            raise ValueError("bpRNA response is not ZIP")
        with zipfile.ZipFile(run / "source.zip") as archive:
            entries = len(archive.infolist())
        attempt.update(status="ok", sha256=digest(raw), size_bytes=len(raw),
                       zip_entries=entries)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        attempt.update(status="error", error=type(exc).__name__ + ": " + str(exc))
    atomic_json(run / "attempt.json", attempt)
    manifest = {"run_dir": str(run), "protocol_run": protocol["run_dir"],
                "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()}}
    atomic_json(run / "manifest.json", manifest)
    summary = {"complete": True, "run_dir": str(run),
               "manifest_sha256": digest((run / "manifest.json").read_bytes()),
               "source_status": attempt["status"],
               "source_size_bytes": attempt.get("size_bytes"),
               "zip_entries": attempt.get("zip_entries"),
               "training_only": True, "labels_parsed": False,
               "model_training_performed": False,
               "model_inference_performed": False}
    atomic_json(run / "summary.json", summary)
    audit(run / "summary.json")
    print("bpRNA source:", attempt["status"], run / "summary.json")


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    if summary != json.loads((run / "summary.json").read_text()):
        raise ValueError("bpRNA source summary differs")
    raw_manifest = (run / "manifest.json").read_bytes()
    if digest(raw_manifest) != summary["manifest_sha256"]:
        raise ValueError("bpRNA source manifest changed")
    manifest = json.loads(raw_manifest)
    protocol, config = audit_protocol(Path(manifest["protocol_run"]) / "manifest.json")
    if json.loads((run / "protocol.json").read_text()) != protocol:
        raise ValueError("bpRNA source protocol copy differs")
    attempt = json.loads((run / "attempt.json").read_text())
    if attempt.get("url") != config["url"]:
        raise ValueError("bpRNA source request differs")
    expected_files = {"protocol.json", "attempt.json"}
    if attempt["status"] == "ok":
        raw = (run / "source.zip").read_bytes()
        if digest(raw) != attempt["sha256"] or len(raw) != attempt["size_bytes"]:
            raise ValueError("bpRNA source bytes changed")
        with zipfile.ZipFile(run / "source.zip") as archive:
            if len(archive.infolist()) != attempt["zip_entries"]:
                raise ValueError("bpRNA ZIP entry count changed")
        expected_files.add("source.zip")
    elif attempt["status"] != "error" or "error" not in attempt:
        raise ValueError("bpRNA source attempt incomplete")
    if set(manifest["snapshot_sha256"]) != expected_files:
        raise ValueError("bpRNA source file inventory differs")
    for name, sha in manifest["snapshot_sha256"].items():
        if digest((run / name).read_bytes()) != sha:
            raise ValueError("bpRNA source snapshot changed")
    expected = {"complete": True, "run_dir": str(run),
                "manifest_sha256": digest(raw_manifest),
                "source_status": attempt["status"],
                "source_size_bytes": attempt.get("size_bytes"),
                "zip_entries": attempt.get("zip_entries"),
                "training_only": True, "labels_parsed": False,
                "model_training_performed": False,
                "model_inference_performed": False}
    if summary != expected:
        raise ValueError("bpRNA source summary values differ")
    print("bpRNA training-source replay passed")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--acquire", action="store_true")
    mode.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.freeze:
        freeze()
    elif args.acquire:
        acquire(PROTOCOL)
    else:
        audit(args.verify)


if __name__ == "__main__":
    main()
