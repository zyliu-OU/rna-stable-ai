#!/usr/bin/env python3
"""Bind measured assay vectors and reserve a fixed external proxy-assessment pilot."""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from prepare_degradation_source import audit as audit_source
from rnastable.artifacts import timestamp, write_artifact
from rnastable.exposures import (
    collect_known_exposures,
    record_exposure,
    read_exposure,
    exposure_records,
)
from rnastable.native_journal import atomic_json
from rnastable.prospective_data import sequence_overlap
from rnastable.reference import digest
from rnastable.reference_audit import require
from rnastable.sequences import validate_sequence

NAME = "degradation_binding"
ERROR_FIELDS = {
    "reactivity": "reactivity_error",
    "deg_Mg_pH10": "deg_error_Mg_pH10",
    "deg_pH10": "deg_error_pH10",
    "deg_Mg_50C": "deg_error_Mg_50C",
    "deg_50C": "deg_error_50C",
}
PLAN = {
    "record_cap": 64,
    "selection": "sequence_id_lexicographic_first64_no_quality_filter",
    "target_coordinate_mapping": "array_index_equals_zero_based_prefix_sequence_position",
    "measurement_summary": "arithmetic_mean_of_all_seq_scored_values_only_when_complete",
    "targets": list(ERROR_FIELDS),
    "methods": [
        "baseline",
        "stack",
        "helix",
        "all_unpaired",
        "ViennaRNA",
        "LinearFold",
    ],
    "proxies": [
        "unpaired_fraction_of_scored_prefix",
        "gc_fraction_of_scored_prefix",
        "native_mfe_per_nt",
    ],
    "correlation": "descriptive_spearman_rho",
    "minimum_complete_records": 3,
    "quality_slices": ["all", "SN_filter_0", "SN_filter_1", "SN_filter_unknown"],
    "native_temperature_c": 37,
    "native_timeout_seconds": 30,
    "native_memory_limit_gib": 4,
    "native_beam_size": 100,
    "model_fitted": False,
    "checkpoint_selected": False,
}
LIMITATIONS = [
    "External public short-construct proxy assessment, not an independent clinical or long-biological-RNA validation.",
    "Chemical reactivity and degradation are distinct assays; conditions differ from37C native folding and the model's structural training.",
    "Per-position normalized measurements may be negative; no clipping or partial-vector averaging. Provided structures/derived half-lives are not used as truth.",
    "Shared construct flanks, laboratory batches and correlated bases preclude independent-replicate uncertainty claims; descriptive rho only.",
    "No causal mutation stabilization or retained-function claim. All source sequences are conservatively marked as validation exposure before binding assays.",
]


def read_records(raw):
    require(0 < len(raw) <= 64 * 1024 * 1024, "Invalid assay source size")
    text = raw.decode()
    try:
        container = json.loads(text)
    except json.JSONDecodeError:
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        if isinstance(container, dict) and isinstance(container.get("id"), dict):
            indices = set(container["id"])
            require(
                indices
                and all(
                    isinstance(k, str) and k.isdecimal() and str(int(k)) == k
                    for k in indices
                ),
                "Invalid columnar source indices",
            )
            require(
                all(
                    isinstance(column, dict) and set(column) == indices
                    for column in container.values()
                ),
                "Columnar source inventory differs",
            )
            rows = [
                {key: column[index] for key, column in container.items()}
                for index in sorted(indices, key=int)
            ]
        else:
            rows = container if isinstance(container, list) else [container]
    require(
        1 <= len(rows) <= 10000 and all(isinstance(r, dict) for r in rows),
        "Expected bounded JSON assay records",
    )
    ids = [r.get("id") for r in rows]
    require(
        all(isinstance(i, str) and i.strip() == i and i for i in ids)
        and len(set(ids)) == len(ids),
        "Missing or duplicate assay identity",
    )
    return rows


def headers(rows):
    inventory = []
    for r in rows:
        sequence = validate_sequence(r.get("sequence"))
        require(
            1 <= len(sequence) <= 1024
            and type(r.get("seq_length")) is int
            and r["seq_length"] == len(sequence)
            and type(r.get("seq_scored")) is int
            and 1 <= r["seq_scored"] <= len(sequence),
            "Assay length/coordinate inventory differs",
        )
        inventory.append({"id": r["id"], "sequence": sequence})
    return inventory


def numeric_vector(value, length, nonnegative=False):
    return (
        isinstance(value, list)
        and len(value) == length
        and all(
            type(v) in (int, float) and math.isfinite(v) and (not nonnegative or v >= 0)
            for v in value
        )
    )


def bind_row(row, overlaps):
    scored = row["seq_scored"]
    assays = {}
    for target, error_field in ERROR_FIELDS.items():
        values, errors = row.get(target), row.get(error_field)
        reason = (
            "invalid_or_incomplete_measurement_vector"
            if not numeric_vector(values, scored)
            else (
                "invalid_or_incomplete_error_vector"
                if not numeric_vector(errors, scored, nonnegative=True)
                else None
            )
        )
        assays[target] = {
            "status": "unsupported" if reason else "ok",
            "reason": reason,
            "values": None if reason else values,
            "errors": None if reason else errors,
            "mean": None if reason else sum(values) / len(values),
        }
    quality = row.get("SN_filter")
    if type(quality) is not int or quality not in (0, 1):
        quality = None
    return {
        "id": row["id"],
        "sequence": row["sequence"],
        "sequence_sha256": digest(row["sequence"].encode()),
        "seq_length": row["seq_length"],
        "seq_scored": scored,
        "SN_filter": quality,
        "prior_sequence_overlap": overlaps,
        "prediction_allowed": not overlaps,
        "assays": assays,
    }


def compute(rows, prior):
    selected = sorted(rows, key=lambda r: r["id"])[: PLAN["record_cap"]]
    sequences = sorted({r["sequence"] for r in prior})
    result = [
        bind_row(r, any(sequence_overlap(r["sequence"], s) for s in sequences))
        for r in selected
    ]
    return {
        "records": result,
        "source_records": len(rows),
        "planned_records": len(selected),
        "planned_assay_outcomes": len(selected) * len(ERROR_FIELDS),
        "supported_assay_outcomes": sum(
            a["status"] == "ok" for r in result for a in r["assays"].values()
        ),
        "overlap_records": sum(r["prior_sequence_overlap"] for r in result),
        "test_inference_allowed": False,
        "reference_structures_used_as_gold": False,
    }


def prepare():
    source = audit_source(ROOT / "results/degradation_source_summary.json")
    require(
        source["sources_complete"] is True,
        "Complete measured-source acquisition required",
    )
    source_path = Path(source["run_dir"]) / source["source"]["filename"]
    run = ROOT / "results" / (NAME + "_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    prior = collect_known_exposures(ROOT)
    atomic_json(run / "source.json", source)
    atomic_json(run / "prior_exposure.json", prior)
    project = Path(__file__).resolve().parents[1]
    paths = [
        Path(__file__),
        project / "scripts/prepare_degradation_source.py",
        *sorted((project / "src/rnastable").glob("*.py")),
    ]
    manifest = {
        "run_dir": str(run),
        "source_path": str(source_path),
        "source_sha256": digest(source_path.read_bytes()),
        "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
        "code_sha256": {str(p): digest(p.read_bytes()) for p in paths},
        "analysis_plan": PLAN,
        "limitations": LIMITATIONS,
    }
    atomic_json(run / "manifest.json", manifest)
    rows = read_records(source_path.read_bytes())
    inventory = headers(rows)
    event = record_exposure(run, "validation_started", inventory)
    binding = compute(rows, prior)
    atomic_json(run / "binding.json", binding)
    summary = {
        "complete": True,
        "run_dir": str(run),
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "binding_sha256": digest((run / "binding.json").read_bytes()),
        "exposure_event": event,
        **binding,
    }
    atomic_json(run / "summary.json", summary)
    write_artifact(
        ROOT / "results" / (NAME + "_summary.json"),
        json.dumps(summary, indent=2, allow_nan=False) + "\n",
    )
    print(
        f"Bound measured pilot:{binding['planned_records']} records, {binding['supported_assay_outcomes']}/{binding['planned_assay_outcomes']} assay outcomes; {binding['overlap_records']} overlaps. No predictions."
    )
    return summary


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(
        summary == json.loads((run / "summary.json").read_text())
        and summary["complete"] is True,
        "Binding pointer differs",
    )
    manifest = json.loads((run / "manifest.json").read_text())
    require(
        digest((run / "manifest.json").read_bytes()) == summary["manifest_sha256"]
        and manifest["analysis_plan"] == PLAN
        and manifest["limitations"] == LIMITATIONS,
        "Assay plan changed",
    )
    source = json.loads((run / "source.json").read_text())
    require(
        source == audit_source(Path(source["run_dir"]) / "summary.json"),
        "Assay source changed",
    )
    for name, sha in manifest["snapshot_sha256"].items():
        require(
            Path(name).name == name and digest((run / name).read_bytes()) == sha,
            "Binding input changed",
        )
    for name, sha in manifest["code_sha256"].items():
        require(digest(Path(name).read_bytes()) == sha, "Binding code changed")
    source_path = Path(manifest["source_path"])
    require(
        source_path == Path(source["run_dir"]) / source["source"]["filename"]
        and digest(source_path.read_bytes())
        == manifest["source_sha256"]
        == source["source"]["sha256"],
        "Assay payload changed",
    )
    rows = read_records(source_path.read_bytes())
    inventory = headers(rows)
    event = summary["exposure_event"]
    p = Path(event["path"])
    exposure = read_exposure(p)
    require(
        p.resolve().parent == (run / "exposures").resolve()
        and set((run / "exposures").glob("*.json")) == {p}
        and digest(p.read_bytes()) == event["sha256"]
        and exposure["stage"] == event["stage"] == "validation_started"
        and exposure["records"]
        == exposure_records(inventory, str(run) + " validation_started"),
        "Assay exposure differs",
    )
    binding = compute(rows, json.loads((run / "prior_exposure.json").read_text()))
    require(
        digest((run / "binding.json").read_bytes()) == summary["binding_sha256"]
        and json.loads((run / "binding.json").read_text()) == binding
        and all(summary[k] == v for k, v in binding.items()),
        "Assay binding replay differs",
    )
    print(
        "Measured assay binding replay passed: exact coordinates, values/errors, selection, prior overlaps and exposure; no model or native calls."
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    return (
        audit(ROOT / "results" / (NAME + "_summary.json")) if args.verify else prepare()
    )


if __name__ == "__main__":
    main()
