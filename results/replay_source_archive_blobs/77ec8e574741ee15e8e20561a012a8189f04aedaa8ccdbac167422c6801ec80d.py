#!/usr/bin/env python3
"""Verify response PDB/chain and contact nucleotide identities without inference."""
# ruff: noqa: E402 -- standalone source bootstrap.

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp, publish
from rnastable.native_journal import atomic_json
from rnastable.reference import digest
from rnastable.reference_audit import require
from audit_structure_contact_provenance import sequence_from_response
from prepare_raw_structure_references import audit as audit_references

NAME = "raw_structure_identity"


def validate_identity(raw, request):
    sequence, data = sequence_from_response(raw)
    require(
        isinstance(data.get("pdb_id"), str)
        and data["pdb_id"].lower() == request["pdb_accession"].lower(),
        "Returned PDB identity differs from request",
    )
    require(
        data.get("chain_id") == request["chain_id"],
        "Returned chain identity differs from request",
    )
    annotations = data.get("annotations")
    require(isinstance(annotations, list), "Returned contact inventory missing")
    for annotation in annotations:
        require(
            isinstance(annotation, dict) and isinstance(annotation.get("bp"), str),
            "Malformed returned contact",
        )
        for suffix in ("1", "2"):
            index = annotation.get("seq_id" + suffix)
            require(
                (type(index) is int or isinstance(index, str) and index.isdigit())
                and 1 <= int(index) <= len(sequence),
                "Returned contact coordinate invalid",
            )
            nucleotide = annotation.get("nt" + suffix)
            require(
                isinstance(nucleotide, str)
                and len(nucleotide) == 1
                and nucleotide.upper().replace("T", "U") == sequence[int(index) - 1],
                "Returned contact nucleotide differs from sequence coordinate",
            )
    return {
        "pdb_accession": request["pdb_accession"],
        "chain_id": request["chain_id"],
        "sequence_sha256": digest(sequence.encode()),
        "validated_annotation_rows": len(annotations),
        "validated_cww_rows": sum(a["bp"] == "cWW" for a in annotations),
    }


def outcomes(source):
    run = Path(source["run_dir"])
    attempts = json.loads((run / "attempts.json").read_text())
    rows = []
    for request in attempts:
        row = {
            "id": request["id"],
            "status": "source_unavailable",
            "identity_verified": False,
        }
        if request["status"] == "ok":
            try:
                row.update(
                    validate_identity(
                        (run / request["filename"]).read_bytes(), request
                    ),
                    status="ok",
                    identity_verified=True,
                )
            except (ValueError, KeyError, TypeError) as exc:
                row.update(status="identity_or_coordinate_rejected", error=str(exc))
        rows.append(row)
    lookup = {r["id"]: r for r in rows}
    supported = [
        r for r in source["binding"]["records"] if r["reference_status"] == "ok"
    ]
    selected_ok = bool(supported) and all(
        lookup[r["id"]]["identity_verified"]
        and lookup[r["id"]]["sequence_sha256"] == r["sequence_sha256"]
        for r in supported
    )
    return rows, selected_ok


def build(path):
    source = audit_references(path)
    source_path = Path(source["run_dir"]) / "summary.json"
    rows, accepted = outcomes(source)
    run = ROOT / "results" / (NAME + "_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "source.json", source)
    (run / "driver.py").write_bytes(Path(__file__).read_bytes())
    manifest = {
        "run_dir": str(run),
        "source_summary": str(source_path),
        "source_sha256": digest(source_path.read_bytes()),
        "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
        "code_sha256": {str(Path(__file__)): digest(Path(__file__).read_bytes())},
    }
    atomic_json(run / "manifest.json", manifest)
    summary = {
        "complete": True,
        "run_dir": str(run),
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "rows": rows,
        "selected_supported_identity_verified": accepted,
        "selected_supported_references": source["binding"]["supported_references"],
        "inference_authorized": False,
        "broad_validation_gate_satisfied": False,
    }
    atomic_json(run / "summary.json", summary)
    audit(run / "summary.json")
    report = [
        "# Raw structure response identity audit",
        "",
        "Exact returned PDB/chain and contact nucleotide/coordinate checks. No prediction or source replacement.",
        "",
        "| Record | Status | Identity verified |",
        "|---|---|---|",
    ]
    report += [
        f"| {r['id']} | {r['status']} | {r['identity_verified']} |" for r in rows
    ]
    report += [
        "",
        "All selected supported source identities verified: " + str(accepted),
        "",
    ]
    publish(
        ROOT,
        NAME,
        summary,
        rows,
        [
            "id",
            "status",
            "identity_verified",
            "sequence_sha256",
            "validated_annotation_rows",
        ],
        "\n".join(report),
    )
    return summary


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(
        summary == json.loads((run / "summary.json").read_text()),
        "Retained identity summary differs",
    )
    raw = (run / "manifest.json").read_bytes()
    require(digest(raw) == summary["manifest_sha256"], "Identity manifest changed")
    manifest = json.loads(raw)
    require(manifest["run_dir"] == str(run), "Identity run differs")
    require(
        set(manifest["snapshot_sha256"]) == {"source.json", "driver.py"},
        "Identity snapshot inventory differs",
    )
    for name, sha in manifest["snapshot_sha256"].items():
        require(digest((run / name).read_bytes()) == sha, "Identity snapshot changed")
    for name, sha in manifest["code_sha256"].items():
        require(digest(Path(name).read_bytes()) == sha, "Identity code changed")
    require(
        digest(Path(manifest["source_summary"]).read_bytes())
        == manifest["source_sha256"],
        "Identity source changed",
    )
    source = audit_references(manifest["source_summary"])
    require(
        source == json.loads((run / "source.json").read_text()),
        "Identity source binding differs",
    )
    rows, accepted = outcomes(source)
    require(
        summary
        == {
            "complete": True,
            "run_dir": str(run),
            "manifest_sha256": digest(raw),
            "rows": rows,
            "selected_supported_identity_verified": accepted,
            "selected_supported_references": source["binding"]["supported_references"],
            "inference_authorized": False,
            "broad_validation_gate_satisfied": False,
        },
        "Identity replay differs",
    )
    print("Raw structure identity replay passed; no new network requests or inference.")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=ROOT / "results/raw_structure_references_summary.json",
    )
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        audit(args.verify)
    else:
        build(args.source)


if __name__ == "__main__":
    main()
