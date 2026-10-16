#!/usr/bin/env python3
"""Acquire and bind the frozen eight-family raw-contact candidate panel."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.exposures import (  # noqa: E402
    collect_known_exposures, exposure_records, read_exposure, record_exposure,
)
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.reference import digest  # noqa: E402
from audit_structure_contact_provenance import download  # noqa: E402
from freeze_fresh_structure_panel import audit as audit_panel  # noqa: E402
from prepare_raw_structure_references import (  # noqa: E402
    bind_graphs, select_sequences, valid_source_sequences,
)

PANEL = ROOT / "results/fresh_structure_panel_protocol.json"
PROTOCOL = ROOT / "results/fresh_structure_references_protocol.json"
SUMMARY = ROOT / "results/fresh_structure_references_summary.json"


def request_plan(panel):
    run = Path(panel["run_dir"])
    selected = json.loads((run / "selection.json").read_text())["candidates"]
    return [{**row, "id": row["family_id"] + ":" + row["pdb_accession"] + "_" + row["chain_id"],
             "filename": f"record_{i:03d}.json"} for i, row in enumerate(selected)]


def freeze():
    panel = audit_panel(PANEL)
    requests = request_plan(panel)
    if len(requests) != 56 or len({r["pdb_accession"] for r in requests}) != 56:
        raise ValueError("Frozen panel request count/identity differs")
    exposures = collect_known_exposures(ROOT)
    original = json.loads((Path(panel["run_dir"]) / "exposures.json").read_text())
    if exposures != original:
        raise ValueError("Exposure changed after panel freeze")
    run = ROOT / "results/fresh_structure_references_protocol_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "panel.json", panel)
    atomic_json(run / "requests.json", requests)
    atomic_json(run / "exposure.json", exposures)
    (run / "driver.py").write_bytes(Path(__file__).read_bytes())
    sources = [Path(__file__), Path(__file__).with_name("prepare_raw_structure_references.py"),
               Path(__file__).with_name("audit_structure_contact_provenance.py")]
    manifest = {"run_dir": str(run), "panel_run": panel["run_dir"],
                "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
                "code_sha256": {str(p): digest(p.read_bytes()) for p in sources},
                "source_labels_read_at_freeze": False,
                "model_inference_authorized": False}
    atomic_json(run / "manifest.json", manifest)
    audit_protocol(run / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen raw-contact acquisition:", run / "manifest.json")


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    if (manifest != json.loads((run / "manifest.json").read_text())
            or manifest["source_labels_read_at_freeze"] is not False
            or manifest["model_inference_authorized"] is not False):
        raise ValueError("Raw-contact acquisition protocol differs")
    for name, sha in manifest["snapshot_sha256"].items():
        if digest((run / name).read_bytes()) != sha:
            raise ValueError("Protocol snapshot changed")
    for name, sha in manifest["code_sha256"].items():
        if digest(Path(name).read_bytes()) != sha:
            raise ValueError("Protocol code changed")
    panel = audit_panel(Path(manifest["panel_run"]) / "manifest.json")
    if panel != json.loads((run / "panel.json").read_text()):
        raise ValueError("Panel copy changed")
    if request_plan(panel) != json.loads((run / "requests.json").read_text()):
        raise ValueError("Request list differs from frozen panel")
    if json.loads((run / "exposure.json").read_text()) != json.loads(
            (Path(panel["run_dir"]) / "exposures.json").read_text()):
        raise ValueError("Exposure snapshot differs")
    return manifest


def future_plan(protocol):
    config = json.loads((Path(protocol["panel_run"]) / "config.json").read_text())
    source = config["future_binding"]
    return config["families"], {
        "minimum_length": source["minimum_length"],
        "maximum_length": source["maximum_length"],
        "max_records_per_family": source["maximum_supported_records_per_family"],
    }, source


def evaluate(run, attempts, exposure_before, protocol):
    families, plan, policy = future_plan(protocol)
    sequences, failures = valid_source_sequences(run, attempts)
    selected, decisions = select_sequences(
        attempts, sequences, failures, exposure_before, plan)
    binding = bind_graphs(run, selected, families)
    qualified = sum(r["supported_references"] >= policy["minimum_supported_per_family"]
                    for r in binding["families"])
    coverage = (binding["supported_references"] >= policy["minimum_supported_total"]
                and qualified >= policy["minimum_supported_families"])
    return sequences, decisions, binding, {
        "supported_references": binding["supported_references"],
        "families_meeting_three_references": qualified,
        "coverage_thresholds_met": coverage,
        "independent_experimental_panel_ready": False,
        "training_tool_independence_certified": False,
        "model_inference_authorized_by_this_stage": False,
    }


def acquire(path):
    protocol = audit_protocol(path)
    directory = Path(protocol["run_dir"])
    exposures = collect_known_exposures(ROOT)
    exposure_before = json.loads((directory / "exposure.json").read_text())
    if exposures != exposure_before:
        raise ValueError("Exposure changed before contact acquisition")
    run = ROOT / "results/fresh_structure_references_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "protocol.json", protocol)
    atomic_json(run / "exposure_before.json", exposures)
    attempts = [{**row, "status": "not_started"} for row in
                json.loads((directory / "requests.json").read_text())]
    atomic_json(run / "attempts.json", attempts)
    for attempt in attempts:
        attempt["status"] = "started"
        atomic_json(run / "attempts.json", attempts)
        try:
            raw = download(attempt["url"])
            (run / attempt["filename"]).write_bytes(raw)
            attempt.update(status="ok", sha256=digest(raw))
        except (OSError, ValueError) as exc:
            attempt.update(status="error", error=type(exc).__name__ + ": " + str(exc))
        atomic_json(run / "attempts.json", attempts)
        print(attempt["id"] + ": " + attempt["status"], flush=True)
    sequences, _ = valid_source_sequences(run, attempts)
    exposed = [{"sequence": sequences[a["id"]], "family_id": a["family_id"],
                "pdb_accession": a["pdb_accession"]} for a in attempts if a["id"] in sequences]
    event = record_exposure(run, "validation_started", exposed) if exposed else None
    sequences, decisions, binding, readiness = evaluate(run, attempts, exposures, protocol)
    atomic_json(run / "selection.json", decisions)
    manifest = {"run_dir": str(run), "protocol_run": str(directory),
                "exposure_event": event,
                "snapshot_sha256": {str(p.relative_to(run)): digest(p.read_bytes())
                                    for p in run.rglob("*") if p.is_file()}}
    atomic_json(run / "manifest.json", manifest)
    summary = {"complete": True, "run_dir": str(run),
               "manifest_sha256": digest((run / "manifest.json").read_bytes()),
               "planned_source_requests": len(attempts),
               "successful_source_requests": sum(a["status"] == "ok" for a in attempts),
               "selection_decisions": decisions, "binding": binding,
               "readiness": readiness, "inference_performed": False}
    atomic_json(run / "summary.json", summary)
    audit(run / "summary.json")
    atomic_json(SUMMARY, summary)
    print("Reference summary:", run / "summary.json")


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    if summary != json.loads((run / "summary.json").read_text()):
        raise ValueError("Reference summary differs")
    raw = (run / "manifest.json").read_bytes()
    if digest(raw) != summary["manifest_sha256"]:
        raise ValueError("Reference manifest changed")
    manifest = json.loads(raw)
    protocol = audit_protocol(Path(manifest["protocol_run"]) / "manifest.json")
    if protocol != json.loads((run / "protocol.json").read_text()):
        raise ValueError("Retained reference protocol changed")
    requests = json.loads((Path(protocol["run_dir"]) / "requests.json").read_text())
    attempts = json.loads((run / "attempts.json").read_text())
    if len(attempts) != len(requests):
        raise ValueError("Reference request count changed")
    expected_files = {"protocol.json", "exposure_before.json", "attempts.json", "selection.json"}
    for attempt, request in zip(attempts, requests, strict=True):
        if any(attempt.get(k) != v for k, v in request.items()):
            raise ValueError("Reference request identity changed")
        if attempt["status"] == "ok":
            if digest((run / attempt["filename"]).read_bytes()) != attempt["sha256"]:
                raise ValueError("Contact response changed")
            expected_files.add(attempt["filename"])
        elif attempt["status"] != "error" or "error" not in attempt:
            raise ValueError("Unfinished contact request")
    exposures = json.loads((run / "exposure_before.json").read_text())
    if exposures != json.loads((Path(protocol["run_dir"]) / "exposure.json").read_text()):
        raise ValueError("Pre-acquisition exposure changed")
    sequences, decisions, binding, readiness = evaluate(run, attempts, exposures, protocol)
    exposed = [{"sequence": sequences[a["id"]], "family_id": a["family_id"],
                "pdb_accession": a["pdb_accession"]} for a in attempts if a["id"] in sequences]
    event = manifest["exposure_event"]
    if bool(event) != bool(exposed):
        raise ValueError("Reference exposure event missing")
    if event:
        event_path = Path(event["path"])
        if (digest(event_path.read_bytes()) != event["sha256"]
                or read_exposure(event_path)["records"] !=
                exposure_records(exposed, str(run) + " validation_started")):
            raise ValueError("Reference exposure event changed")
        expected_files.add(str(event_path.relative_to(run)))
    if set(manifest["snapshot_sha256"]) != expected_files:
        raise ValueError("Reference file inventory changed")
    for name, sha in manifest["snapshot_sha256"].items():
        if digest((run / name).read_bytes()) != sha:
            raise ValueError("Reference snapshot changed")
    if summary != {"complete": True, "run_dir": str(run),
                   "manifest_sha256": digest(raw),
                   "planned_source_requests": len(attempts),
                   "successful_source_requests": sum(a["status"] == "ok" for a in attempts),
                   "selection_decisions": decisions, "binding": binding,
                   "readiness": readiness, "inference_performed": False}:
        raise ValueError("Reference binding replay differs")
    if decisions != json.loads((run / "selection.json").read_text()):
        raise ValueError("Reference selection changed")
    print("Fresh reference replay passed; no network or model inference")
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
