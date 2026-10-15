#!/usr/bin/env python3
"""Acquire predeclared raw PDB contact graphs and bind a fixed feasibility cohort."""
# ruff: noqa: E402 -- standalone source bootstrap.

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import publish, timestamp, write_artifact
from rnastable.exposures import (
    collect_known_exposures,
    record_exposure,
    read_exposure,
    exposure_records,
)
from rnastable.native_journal import atomic_json
from rnastable.pair_reference import validate_pairs, has_crossing_pairs
from rnastable.prospective_data import sequence_overlap
from rnastable.reference import digest
from rnastable.reference_audit import require
from audit_structure_contact_provenance import (
    download,
    sequence_from_response,
    compare as parse_graph,
)
from plan_raw_structure_panel import audit as audit_metadata, infer_exposed_families

NAME = "raw_structure_references"
LIMITATIONS = [
    "A six-family structure-derived feasibility cohort, not a completion of broad independent biological validation.",
    "Raw FR3D cWW contacts are retained as returned, including noncanonical chemistry and crossing contacts. Multiple-partner graphs remain unsupported rather than projected.",
    "Current source responses are frozen by bytes, request identity and acquisition time; complete tool-training independence and annotation correctness are not certified.",
    "Known PDB/family/clan and heuristic sequence overlap are screened. Unknown training provenance remains unresolved.",
    "All source failures, sequence-screening exclusions and selected unsupported references remain explicit. No replacement or model selection from source outcomes.",
]


def freeze(metadata_path):
    metadata = audit_metadata(metadata_path)
    require(
        metadata["metadata_complete"] and metadata["screening"]["metadata_candidates"],
        "Complete nonempty raw-panel metadata screen required",
    )
    metadata_run = Path(metadata["run_dir"])
    metadata_manifest = json.loads((metadata_run / "manifest.json").read_text())
    planning_run = Path(metadata_manifest["protocol_run"])
    config = json.loads((planning_run / "config.json").read_text())
    mappings = {
        tuple(row) for row in json.loads((planning_run / "mappings.json").read_text())
    }
    exposures = collect_known_exposures(ROOT)
    require(
        not set(config["families"]) & set(infer_exposed_families(mappings, exposures)),
        "Raw source family exposed since metadata planning",
    )
    run = ROOT / "results" / (NAME + "_protocol_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "metadata.json", metadata)
    atomic_json(run / "config.json", config)
    atomic_json(run / "exposure.json", exposures)
    plan = [
        {**row, "filename": f"record_{i:03d}.json"}
        for i, row in enumerate(metadata["screening"]["metadata_candidates"])
    ]
    atomic_json(run / "requests.json", plan)
    (run / "driver.py").write_bytes(Path(__file__).read_bytes())
    inputs = {
        str(metadata_run / "summary.json"): digest(
            (metadata_run / "summary.json").read_bytes()
        )
    }
    for directory in (metadata_run, planning_run):
        path = directory / "manifest.json"
        inputs[str(path)] = digest(path.read_bytes())
        manifest = json.loads(path.read_text())
        inputs.update(
            {
                str(directory / name): sha
                for name, sha in manifest["snapshot_sha256"].items()
            }
        )
        inputs.update(manifest.get("code_sha256", {}))
        inputs.update(manifest.get("input_sha256", {}))
    manifest = {
        "run_dir": str(run),
        "planning_run": str(planning_run),
        "input_sha256": inputs,
        "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
        "code_sha256": {
            str(p): digest(p.read_bytes())
            for p in [
                Path(__file__),
                Path(__file__).with_name("audit_structure_contact_provenance.py"),
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
        "Frozen raw reference acquisition protocol: " + str(run / "manifest.json"),
        flush=True,
    )
    return manifest


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    require(
        manifest == json.loads((run / "manifest.json").read_text()),
        "Raw-reference protocol differs",
    )
    require(
        set(manifest["snapshot_sha256"])
        == {
            "metadata.json",
            "config.json",
            "exposure.json",
            "requests.json",
            "driver.py",
        },
        "Raw-reference protocol snapshot inventory differs",
    )
    for field in ("input_sha256", "code_sha256"):
        for name, sha in manifest[field].items():
            require(
                digest(Path(name).read_bytes()) == sha,
                "Raw-reference input/code changed: " + name,
            )
    for name, sha in manifest["snapshot_sha256"].items():
        require(
            digest((run / name).read_bytes()) == sha, "Raw-reference snapshot changed"
        )
    metadata = json.loads((run / "metadata.json").read_text())
    expected = [
        {**r, "filename": f"record_{i:03d}.json"}
        for i, r in enumerate(metadata["screening"]["metadata_candidates"])
    ]
    require(
        json.loads((run / "requests.json").read_text()) == expected,
        "Raw-reference request plan differs",
    )
    return manifest


def valid_source_sequences(run, attempts):
    output, failures = {}, {}
    for attempt in attempts:
        if attempt["status"] != "ok":
            failures[attempt["id"]] = "source_unavailable"
            continue
        try:
            sequence, _ = sequence_from_response(
                (run / attempt["filename"]).read_bytes()
            )
            output[attempt["id"]] = sequence
        except (ValueError, KeyError, TypeError) as exc:
            failures[attempt["id"]] = "unsupported_source_sequence: " + str(exc)
    return output, failures


def select_sequences(attempts, sequences, failures, exposures, plan):
    require(
        len({a["id"] for a in attempts}) == len(attempts),
        "Duplicate raw-reference identity",
    )
    prior = sorted({r["sequence"] for r in exposures})
    accepted_sequences, counts = [], Counter()
    selected, decisions = [], []
    for row in attempts:
        identity, family = row["id"], row["family_id"]
        sequence = sequences.get(identity)
        if identity in failures:
            reason = failures[identity]
        elif not plan["minimum_length"] <= len(sequence) <= plan["maximum_length"]:
            reason = "outside_declared_length_range"
        elif any(sequence_overlap(sequence, old) for old in prior):
            reason = "prior_sequence_exposure"
        elif any(sequence_overlap(sequence, old) for old in accepted_sequences):
            reason = "panel_sequence_redundancy"
        elif counts[family] >= plan["max_records_per_family"]:
            reason = "fixed_final_family_cap"
        else:
            reason = "selected_before_contact_parsing"
            counts[family] += 1
            accepted_sequences.append(sequence)
            selected.append(
                {
                    key: row[key]
                    for key in (
                        "id",
                        "family_id",
                        "pdb_accession",
                        "chain_id",
                        "filename",
                    )
                }
                | {"sequence": sequence, "sequence_sha256": digest(sequence.encode())}
            )
        decisions.append(
            {
                "id": identity,
                "family_id": family,
                "reason": reason,
                "sequence_sha256": digest(sequence.encode()) if sequence else None,
            }
        )
    return selected, decisions


def bind_graphs(run, selected, families):
    output = []
    for record in selected:
        row = {key: value for key, value in record.items() if key != "filename"}
        row.update(
            reference_kind="computational",
            reference_basis="raw_FR3D_PDB_cWW_graph",
            source="BGSU RNA 3D Hub; exact frozen PDB-chain cWW contacts",
            sequence_bound=True,
        )
        try:
            graph = parse_graph(
                (run / record["filename"]).read_bytes(), {**record, "pairs": []}
            )
            require(graph["sequence_bound"], "Frozen raw reference sequence differs")
            row["raw_cww_pairs"] = graph["raw_cww_pairs"]
            row["raw_cww_rows"] = graph["raw_cww_rows"]
            row["other_annotation_rows"] = graph["other_annotation_rows"]
            row["raw_nucleotides_with_multiple_cww_partners"] = graph[
                "raw_nucleotides_with_multiple_cww_partners"
            ]
            require(
                not graph["raw_nucleotides_with_multiple_cww_partners"],
                "Raw cWW graph has multiple partners; projection forbidden",
            )
            contacts = validate_pairs(graph["raw_cww_pairs"], len(record["sequence"]))
            row.update(
                reference_status="ok",
                pairs=graph["raw_cww_pairs"],
                reference_has_crossing_pairs=has_crossing_pairs(contacts),
            )
        except (ValueError, KeyError, TypeError) as exc:
            row.update(reference_status="unsupported_reference", error=str(exc))
        output.append(row)
    groups = []
    for family in families:
        subset = [r for r in output if r["family_id"] == family]
        groups.append(
            {
                "family_id": family,
                "planned_records": len(subset),
                "supported_references": sum(
                    r["reference_status"] == "ok" for r in subset
                ),
            }
        )
    return {
        "records": output,
        "families": groups,
        "planned_records": len(output),
        "supported_references": sum(r["reference_status"] == "ok" for r in output),
        "sequence_bindings_complete": True,
        "known_provenance_overlap": False,
    }


def feasibility(binding, plan):
    qualified = sum(
        f["supported_references"] >= plan["feasibility_minimum_per_family"]
        for f in binding["families"]
    )
    ready = (
        qualified >= plan["feasibility_minimum_supported_families"]
        and binding["supported_references"] >= plan["feasibility_minimum_total"]
    )
    return {
        "scope": plan["study_scope"],
        "families_meeting_feasibility_minimum": qualified,
        "feasibility_coverage_met": ready,
        "broad_validation_gate_satisfied": False,
        "model_inference_authorized_by_this_stage": False,
        "independent_training_tool_provenance_certified": False,
    }


def acquire(protocol_path):
    protocol = audit_protocol(protocol_path)
    directory = Path(protocol["run_dir"])
    config = json.loads((directory / "config.json").read_text())
    planning = Path(protocol["planning_run"])
    mappings = {
        tuple(row) for row in json.loads((planning / "mappings.json").read_text())
    }
    exposures = collect_known_exposures(ROOT)
    require(
        not set(config["families"]) & set(infer_exposed_families(mappings, exposures)),
        "Raw source family exposed since request freeze",
    )
    run = ROOT / "results" / (NAME + "_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "protocol.json", protocol)
    atomic_json(run / "exposure_before.json", exposures)
    attempts = [
        {**row, "status": "not_started"}
        for row in json.loads((directory / "requests.json").read_text())
    ]
    atomic_json(run / "attempts.json", attempts)
    for a in attempts:
        a["status"] = "started"
        atomic_json(run / "attempts.json", attempts)
        try:
            raw = download(a["url"])
            (run / a["filename"]).write_bytes(raw)
            a.update(status="ok", sha256=digest(raw))
        except (OSError, ValueError) as exc:
            a.update(status="error", error=type(exc).__name__ + ": " + str(exc))
        atomic_json(run / "attempts.json", attempts)
        print(a["id"] + ": " + a["status"], flush=True)
    sequences, failures = valid_source_sequences(run, attempts)
    selected, decisions = select_sequences(
        attempts, sequences, failures, exposures, config["future_binding"]
    )
    atomic_json(run / "selection.json", decisions)
    exposed = [
        {
            "sequence": sequences[a["id"]],
            "family_id": a["family_id"],
            "pdb_accession": a["pdb_accession"],
        }
        for a in attempts
        if a["id"] in sequences
    ]
    event = record_exposure(run, "validation_started", exposed) if exposed else None
    binding = bind_graphs(run, selected, config["families"])
    manifest = {
        "run_dir": str(run),
        "protocol_run": str(directory),
        "exposure_event": event,
        "snapshot_sha256": {
            str(p.relative_to(run)): digest(p.read_bytes())
            for p in run.rglob("*")
            if p.is_file()
        },
    }
    atomic_json(run / "manifest.json", manifest)
    summary = {
        "complete": True,
        "run_dir": str(run),
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "planned_source_requests": len(attempts),
        "successful_source_requests": sum(a["status"] == "ok" for a in attempts),
        "selection_decisions": decisions,
        "binding": binding,
        "readiness": feasibility(binding, config["future_binding"]),
        "limitations": LIMITATIONS,
        "inference_performed": False,
    }
    atomic_json(run / "summary.json", summary)
    audit(run / "summary.json")
    rows = binding["families"]
    report = [
        "# Raw structure-derived feasibility references",
        "",
        f"Fixed source requests: {len(attempts)}. Selected records: {binding['planned_records']}; supported: {binding['supported_references']}.",
        "",
        "| Family | Selected | Supported |",
        "|---|---:|---:|",
    ]
    report += [
        f"| {r['family_id']} | {r['planned_records']} | {r['supported_references']} |"
        for r in rows
    ]
    report += [
        "",
        "Feasibility coverage met: "
        + str(summary["readiness"]["feasibility_coverage_met"]),
        "",
        *LIMITATIONS,
        "",
    ]
    publish(ROOT, NAME, summary, rows, list(rows[0]), "\n".join(report))
    return summary


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(
        summary == json.loads((run / "summary.json").read_text()),
        "Raw-reference retained summary differs",
    )
    raw = (run / "manifest.json").read_bytes()
    require(digest(raw) == summary["manifest_sha256"], "Raw-reference manifest changed")
    manifest = json.loads(raw)
    require(manifest["run_dir"] == str(run), "Raw-reference run identity differs")
    protocol = audit_protocol(Path(manifest["protocol_run"]) / "manifest.json")
    require(
        protocol == json.loads((run / "protocol.json").read_text()),
        "Raw-reference retained protocol differs",
    )
    directory = Path(protocol["run_dir"])
    config = json.loads((directory / "config.json").read_text())
    plan = json.loads((directory / "requests.json").read_text())
    attempts = json.loads((run / "attempts.json").read_text())
    require(
        len(attempts) == len(plan)
        and all(
            all(a.get(k) == value for k, value in row.items())
            and a["status"] in ("ok", "error")
            for a, row in zip(attempts, plan, strict=True)
        ),
        "Raw-reference request inventory differs",
    )
    expected = {
        "protocol.json",
        "exposure_before.json",
        "attempts.json",
        "selection.json",
    }
    for a in attempts:
        if a["status"] == "ok":
            require(
                "sha256" in a
                and digest((run / a["filename"]).read_bytes()) == a["sha256"],
                "Raw-reference response changed",
            )
        if "sha256" in a:
            expected.add(a["filename"])
    sequences, failures = valid_source_sequences(run, attempts)
    exposed = [
        {
            "sequence": sequences[a["id"]],
            "family_id": a["family_id"],
            "pdb_accession": a["pdb_accession"],
        }
        for a in attempts
        if a["id"] in sequences
    ]
    event = manifest["exposure_event"]
    require(
        bool(event) == bool(exposed), "Raw-reference source exposure inventory differs"
    )
    if event:
        event_path = Path(event["path"])
        expected.add(str(event_path.relative_to(run)))
        require(
            digest(event_path.read_bytes()) == event["sha256"]
            and read_exposure(event_path)["records"]
            == exposure_records(exposed, str(run) + " validation_started"),
            "Raw-reference source exposure differs",
        )
    require(
        set(manifest["snapshot_sha256"]) == expected,
        "Raw-reference file inventory differs",
    )
    for name, sha in manifest["snapshot_sha256"].items():
        require(
            digest((run / name).read_bytes()) == sha, "Raw-reference snapshot changed"
        )
    exposures = json.loads((run / "exposure_before.json").read_text())
    selected, decisions = select_sequences(
        attempts, sequences, failures, exposures, config["future_binding"]
    )
    binding = bind_graphs(run, selected, config["families"])
    require(
        summary
        == {
            "complete": True,
            "run_dir": str(run),
            "manifest_sha256": digest(raw),
            "planned_source_requests": len(plan),
            "successful_source_requests": sum(a["status"] == "ok" for a in attempts),
            "selection_decisions": decisions,
            "binding": binding,
            "readiness": feasibility(binding, config["future_binding"]),
            "limitations": LIMITATIONS,
            "inference_performed": False,
        }
        and decisions == json.loads((run / "selection.json").read_text()),
        "Raw-reference binding replay differs",
    )
    print(
        "Raw-reference replay passed: fixed source requests, complete cWW graphs, selection and exposure; no new network or inference."
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metadata",
        type=Path,
        default=ROOT / "results/raw_structure_panel_metadata_summary.json",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--acquire", action="store_true")
    mode.add_argument("--verify", type=Path)
    parser.add_argument(
        "--protocol",
        type=Path,
        default=ROOT / "results/raw_structure_references_protocol.json",
    )
    args = parser.parse_args()
    if args.verify:
        audit(args.verify)
    elif args.acquire:
        acquire(args.protocol)
    else:
        freeze(args.metadata)


if __name__ == "__main__":
    main()
