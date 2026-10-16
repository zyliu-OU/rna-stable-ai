#!/usr/bin/env python3
"""Freeze and acquire missing Rfam clan descriptions without structure labels."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.prospective_data import bounded_download, family_urls  # noqa: E402
from rnastable.reference import digest  # noqa: E402
from plan_raw_structure_panel import clan  # noqa: E402

INVENTORY = ROOT / "results/fresh_structure_inventory_2026-10-15.json"
PROTOCOL_POINTER = ROOT / "results/fresh_structure_metadata_protocol.json"
SUMMARY_POINTER = ROOT / "results/fresh_structure_metadata_summary.json"


def planned_families(inventory):
    if (inventory["stage"] != "metadata_only_inventory"
            or inventory["annotation_labels_read"] is not False
            or inventory["model_inference_authorized"] is not False):
        raise ValueError("Source inventory is not metadata-only")
    families = sorted(row["family_id"] for row in inventory["families"]
                      if row["status"] == "clan_unresolved")
    if len(families) != 92:
        raise ValueError("Expected 92 unresolved mapped families")
    return families


def freeze():
    original = INVENTORY.read_bytes()
    inventory = json.loads(original)
    families = planned_families(inventory)
    run = ROOT / "results/fresh_structure_metadata_protocol_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    (run / "inventory.json").write_bytes(original)
    atomic_json(run / "requests.json", [
        {"family_id": f, "filename": f + ".json", "url": family_urls(f)["description"]}
        for f in families
    ])
    manifest = {
        "run_dir": str(run),
        "source_inventory_sha256": digest(original),
        "snapshot_sha256": {
            name: digest((run / name).read_bytes())
            for name in ("inventory.json", "requests.json")
        },
        "maximum_metadata_bytes": 2 * 1024 * 1024,
        "metadata_timeout_seconds": 30,
        "metadata_release": "15.1",
        "structure_labels_allowed": False,
        "model_inference_allowed": False,
    }
    atomic_json(run / "manifest.json", manifest)
    audit_protocol(run / "manifest.json")
    atomic_json(PROTOCOL_POINTER, manifest)
    print("Frozen metadata protocol:", run / "manifest.json")


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    if manifest != json.loads((run / "manifest.json").read_text()):
        raise ValueError("Metadata protocol differs")
    if manifest["structure_labels_allowed"] or manifest["model_inference_allowed"]:
        raise ValueError("Protocol permits labels or inference")
    for name, expected in manifest["snapshot_sha256"].items():
        if digest((run / name).read_bytes()) != expected:
            raise ValueError("Frozen protocol snapshot changed")
    inventory = json.loads((run / "inventory.json").read_text())
    if digest((run / "inventory.json").read_bytes()) != manifest["source_inventory_sha256"]:
        raise ValueError("Source inventory changed")
    families = planned_families(inventory)
    expected = [{"family_id": f, "filename": f + ".json",
                 "url": family_urls(f)["description"]} for f in families]
    if json.loads((run / "requests.json").read_text()) != expected:
        raise ValueError("Metadata requests changed")
    return manifest, expected


def acquire(path):
    protocol, requests = audit_protocol(path)
    run = ROOT / "results/fresh_structure_metadata_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "protocol.json", protocol)
    attempts = [{**request, "status": "not_started"} for request in requests]
    atomic_json(run / "attempts.json", attempts)
    for attempt in attempts:
        attempt["status"] = "started"
        atomic_json(run / "attempts.json", attempts)
        try:
            raw = bounded_download(attempt["url"],
                                   protocol["maximum_metadata_bytes"],
                                   protocol["metadata_timeout_seconds"])
            clan(raw, attempt["family_id"], protocol["metadata_release"])
            (run / attempt["filename"]).write_bytes(raw)
            attempt["sha256"] = digest(raw)
            attempt["status"] = "ok"
        except (OSError, ValueError, KeyError, TypeError) as exc:
            attempt["status"] = "error"
            attempt["error"] = type(exc).__name__ + ": " + str(exc)
        atomic_json(run / "attempts.json", attempts)
        print(attempt["family_id"] + ": " + attempt["status"], flush=True)
    manifest = {"run_dir": str(run), "protocol_run": protocol["run_dir"],
                "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()}}
    atomic_json(run / "manifest.json", manifest)
    summary = {"complete": True, "run_dir": str(run),
               "manifest_sha256": digest((run / "manifest.json").read_bytes()),
               "requested": len(attempts),
               "successful": sum(a["status"] == "ok" for a in attempts),
               "failed": sum(a["status"] == "error" for a in attempts),
               "structure_labels_read": False,
               "model_inference_performed": False}
    atomic_json(run / "summary.json", summary)
    audit(run / "summary.json")
    atomic_json(SUMMARY_POINTER, summary)
    print("Metadata summary:", run / "summary.json")


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    if summary != json.loads((run / "summary.json").read_text()):
        raise ValueError("Metadata summary differs")
    raw_manifest = (run / "manifest.json").read_bytes()
    if digest(raw_manifest) != summary["manifest_sha256"]:
        raise ValueError("Metadata manifest changed")
    manifest = json.loads(raw_manifest)
    protocol, requests = audit_protocol(Path(manifest["protocol_run"]) / "manifest.json")
    if json.loads((run / "protocol.json").read_text()) != protocol:
        raise ValueError("Retained protocol changed")
    attempts = json.loads((run / "attempts.json").read_text())
    if len(attempts) != len(requests):
        raise ValueError("Request count changed")
    expected_files = {"protocol.json", "attempts.json"}
    for attempt, request in zip(attempts, requests, strict=True):
        if any(attempt.get(k) != value for k, value in request.items()):
            raise ValueError("Request identity changed")
        if attempt["status"] == "ok":
            content = (run / attempt["filename"]).read_bytes()
            if digest(content) != attempt["sha256"]:
                raise ValueError("Response hash changed")
            clan(content, attempt["family_id"], protocol["metadata_release"])
            expected_files.add(attempt["filename"])
        elif attempt["status"] != "error" or "error" not in attempt:
            raise ValueError("Unfinished or invalid request")
    if set(manifest["snapshot_sha256"]) != expected_files:
        raise ValueError("Acquisition file inventory changed")
    for name, sha in manifest["snapshot_sha256"].items():
        if digest((run / name).read_bytes()) != sha:
            raise ValueError("Acquisition snapshot changed")
    if summary != {"complete": True, "run_dir": str(run),
                   "manifest_sha256": digest(raw_manifest),
                   "requested": len(attempts),
                   "successful": sum(a["status"] == "ok" for a in attempts),
                   "failed": sum(a["status"] == "error" for a in attempts),
                   "structure_labels_read": False,
                   "model_inference_performed": False}:
        raise ValueError("Acquisition summary counts changed")
    print("Metadata acquisition replay passed")
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
        acquire(PROTOCOL_POINTER)
    else:
        freeze()


if __name__ == "__main__":
    main()
