"""Exact pair-set scoring, including crossing contacts; no contact projection."""

import csv
import json
from pathlib import Path

from .artifacts import publish, timestamp
from .exposures import exposure_records, read_exposure, record_exposure
from .native_journal import atomic_json
from .reference import (
    digest,
    METRICS,
    PREDICTION_STATUSES,
    REFERENCE_KINDS,
    aggregate_rows,
    text_field,
)
from .reference_audit import require
from .scoring import base_pairs
from .sequences import validate_sequence

FORMAT = "pair_set_zero_based_v1"
NAME = "pair_reference"
FIELDS = [
    "reference_id",
    "method",
    "reference_kind",
    "source",
    "length",
    "sequence_sha256",
    "reference_has_crossing_pairs",
    "status",
    "error",
    *METRICS,
]
LIMITATIONS = [
    "Exact zero-based contacts; crossing reference/predicted pairs are scored without removal, flattening or replacement.",
    "Each nucleotide has at most one partner. Reference pair chemistry and minimum loop size are not inferred or filtered.",
    "Missing/failed predictions retain unknown metrics. Means describe measured inputs only, with one vote per reference.",
    "Source labels/provenance are supplied annotations, not independent biological evidence. Pair agreement does not establish stability or retained function.",
    "This evaluator performs no inference, native folding, training or checkpoint selection; supplied records are conservatively registered as validation exposure.",
]


def validate_pairs(pairs, length):
    if type(length) is not int or not 1 <= length <= 10000:
        raise ValueError("Pair references require length in 1..10000")
    if not isinstance(pairs, list):
        raise ValueError("Pairs must be explicit [left,right] lists")
    occupied, result = set(), set()
    for pair in pairs:
        if (
            not isinstance(pair, list)
            or len(pair) != 2
            or any(type(i) is not int for i in pair)
        ):
            raise ValueError("Each pair requires two integer coordinates")
        left, right = pair
        if not 0 <= left < right < length:
            raise ValueError(
                "Pair coordinates must be zero-based, ordered and in range"
            )
        if left in occupied or right in occupied:
            raise ValueError("Duplicate contact or multiple partners for a nucleotide")
        occupied.update(pair)
        result.add((left, right))
    return result


def has_crossing_pairs(pairs):
    ends = []
    for left, right in sorted(pairs):
        while ends and ends[-1] < left:
            ends.pop()
        if ends and right > ends[-1]:
            return True
        ends.append(right)
    return False


def pair_agreement(predicted, reference):
    common = len(predicted & reference)
    both_empty = not predicted and not reference
    return {
        "reference_pairs": len(reference),
        "predicted_pairs": len(predicted),
        "shared_pairs": common,
        "pair_precision": common / len(predicted) if predicted else float(both_empty),
        "pair_recall": common / len(reference) if reference else float(both_empty),
        "pair_f1": 2 * common / (len(predicted) + len(reference))
        if predicted or reference
        else 1.0,
        "pair_jaccard": common / len(predicted | reference)
        if predicted or reference
        else 1.0,
        "base_pair_distance": len(predicted ^ reference),
    }


def validate_inputs(references, predictions):
    for name, data in (("references", references), ("predictions", predictions)):
        if (
            not isinstance(data, dict)
            or type(data.get("schema_version")) is not int
            or data["schema_version"] != 1
        ):
            raise ValueError(name + " requires schema_version=1")
        if data.get("format") != FORMAT or not isinstance(data.get("records"), list):
            raise ValueError(
                name + " requires explicit pair_set_zero_based_v1 format and records"
            )
    text_field(references.get("dataset_id"), "dataset ID")
    if not references["records"]:
        raise ValueError("At least one pair reference is required")
    inventory = {}
    for r in references["records"]:
        if not isinstance(r, dict):
            raise ValueError("Reference must be an object")
        identity = text_field(r.get("id"), "reference ID")
        if identity in inventory:
            raise ValueError("Duplicate reference ID")
        sequence = validate_sequence(r.get("sequence"))
        validate_pairs(r.get("pairs"), len(sequence))
        if "structure" in r:
            raise ValueError(
                "Pair references must use one explicit contact representation"
            )
        if (
            not isinstance(r.get("reference_kind"), str)
            or r["reference_kind"] not in REFERENCE_KINDS
        ):
            raise ValueError("Invalid reference kind")
        text_field(r.get("source"), "reference source")
        inventory[identity] = r
    # Validate optional provenance before any output or scoring.
    exposure_records(references["records"], "pair-reference validation")
    methods = predictions.get("methods")
    if not isinstance(methods, list) or not methods:
        raise ValueError("Prediction methods must be a nonempty list")
    for method in methods:
        text_field(method, "method")
    if len(set(methods)) != len(methods):
        raise ValueError("Duplicate prediction method")
    seen = set()
    for p in predictions["records"]:
        if not isinstance(p, dict):
            raise ValueError("Prediction must be an object")
        text_field(p.get("id"), "prediction ID")
        text_field(p.get("method"), "prediction method")
        if p["id"] not in inventory or p["method"] not in methods:
            raise ValueError("Unknown prediction reference/method")
        key = (p["id"], p["method"])
        if key in seen:
            raise ValueError("Duplicate prediction")
        seen.add(key)
        sequence = inventory[p["id"]]["sequence"]
        if p.get("sequence") != sequence:
            raise ValueError("Prediction sequence differs from exact reference")
        if (
            not isinstance(p.get("status"), str)
            or p["status"] not in PREDICTION_STATUSES
        ):
            raise ValueError("Invalid prediction status")
        representations = sum(key in p for key in ("pairs", "structure"))
        if p["status"] == "ok":
            if representations != 1:
                raise ValueError(
                    "Successful prediction requires exactly one pairs/structure representation"
                )
            if "pairs" in p:
                validate_pairs(p["pairs"], len(sequence))
            elif not isinstance(p["structure"], str) or len(p["structure"]) != len(
                sequence
            ):
                raise ValueError("Prediction structure length differs")
            else:
                base_pairs(p["structure"])
        else:
            if representations:
                raise ValueError("Failed prediction must not contain contacts")
            text_field(p.get("error"), "prediction failure reason")


def evaluate_rows(references, predictions):
    validate_inputs(references, predictions)
    lookup = {(p["id"], p["method"]): p for p in predictions["records"]}
    rows = []
    for r in references["records"]:
        actual = validate_pairs(r["pairs"], len(r["sequence"]))
        for method in predictions["methods"]:
            p = lookup.get((r["id"], method))
            row = dict.fromkeys(METRICS)
            row.update(
                reference_id=r["id"],
                method=method,
                reference_kind=r["reference_kind"],
                source=r["source"],
                length=len(r["sequence"]),
                sequence_sha256=digest(r["sequence"].encode()),
                reference_has_crossing_pairs=has_crossing_pairs(actual),
                status=p["status"] if p else "missing",
                error=p.get("error", "") if p else "No prediction supplied",
            )
            if row["status"] == "ok":
                proposed = (
                    validate_pairs(p["pairs"], len(r["sequence"]))
                    if "pairs" in p
                    else base_pairs(p["structure"])
                )
                row.update(pair_agreement(proposed, actual))
            rows.append(row)
    return rows


def render_report(summary):
    lines = [
        "# Supplied pair-set reference evaluation",
        "",
        f"Dataset: {summary['dataset_id']}",
        "",
        *LIMITATIONS,
        "",
        "| Method | Kind | Planned | Measured | Mean pair F1 |",
        "|---|---|---:|---:|---:|",
    ]
    for a in summary["aggregates"]:
        lines.append(
            f"| {a['method']} | {a['reference_kind']} | {a['planned_inputs']} | {a['measured_inputs']} | {a['mean_pair_f1']} |"
        )
    return "\n".join(lines) + "\n"


def run_evaluation(root, reference_path, prediction_path):
    contents = [Path(p).read_bytes() for p in (reference_path, prediction_path)]
    references, predictions = [json.loads(raw) for raw in contents]
    validate_inputs(references, predictions)
    run = Path(root).resolve() / "results/pair_reference_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    for name, raw in zip(("references.json", "predictions.json"), contents):
        (run / name).write_bytes(raw)
    event = record_exposure(run, "validation_started", references["records"])
    manifest = {
        "run_dir": str(run),
        "format": FORMAT,
        "snapshot_sha256": {
            name: digest(raw)
            for name, raw in zip(("references.json", "predictions.json"), contents)
        },
        "exposure_event": event,
        "policy": "complete_exact_pair_sets_no_projection_v1",
    }
    atomic_json(run / "manifest.json", manifest)
    rows = evaluate_rows(references, predictions)
    summary = {
        "complete": True,
        "run_dir": str(run),
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "dataset_id": references["dataset_id"],
        "planned_predictions": len(rows),
        "crossing_reference_records": sum(
            has_crossing_pairs(validate_pairs(r["pairs"], len(r["sequence"])))
            for r in references["records"]
        ),
        "rows": rows,
        "aggregates": aggregate_rows(rows),
        "limitations": LIMITATIONS,
        "inference_performed": False,
        "model_fitted": False,
    }
    atomic_json(run / "summary.json", summary)
    publish(run, NAME, summary, rows, FIELDS, render_report(summary))
    publish(root, NAME, summary, rows, FIELDS, render_report(summary))
    return summary


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(
        summary == json.loads((run / "summary.json").read_text()),
        "Retained pair evaluation differs",
    )
    raw = (run / "manifest.json").read_bytes()
    require(
        digest(raw) == summary["manifest_sha256"], "Pair evaluation manifest changed"
    )
    manifest = json.loads(raw)
    require(
        manifest["run_dir"] == str(run)
        and manifest["format"] == FORMAT
        and manifest["policy"] == "complete_exact_pair_sets_no_projection_v1",
        "Pair scoring policy differs",
    )
    require(
        set(manifest["snapshot_sha256"]) == {"references.json", "predictions.json"},
        "Pair snapshot inventory differs",
    )
    for name, sha in manifest["snapshot_sha256"].items():
        require(digest((run / name).read_bytes()) == sha, "Frozen pair input changed")
    references, predictions = [
        json.loads((run / name).read_text())
        for name in ("references.json", "predictions.json")
    ]
    event = manifest["exposure_event"]
    event_path = Path(event["path"])
    require(
        event_path.resolve().parent == (run / "exposures").resolve()
        and digest(event_path.read_bytes()) == event["sha256"],
        "Pair exposure changed",
    )
    exposed = read_exposure(event_path)
    require(
        exposed["stage"] == event["stage"] == "validation_started"
        and exposed["records"]
        == exposure_records(references["records"], str(run) + " validation_started"),
        "Pair exposure records differ",
    )
    rows = evaluate_rows(references, predictions)
    require(
        summary["rows"] == rows
        and summary["aggregates"] == aggregate_rows(rows)
        and summary["planned_predictions"] == len(rows),
        "Pair metrics/coverage replay differs",
    )
    require(
        summary["complete"] is True
        and summary["inference_performed"] is False
        and summary["model_fitted"] is False
        and summary["limitations"] == LIMITATIONS
        and summary["dataset_id"] == references["dataset_id"],
        "Pair evaluation interpretation differs",
    )
    require(
        summary["crossing_reference_records"]
        == sum(
            has_crossing_pairs(validate_pairs(r["pairs"], len(r["sequence"])))
            for r in references["records"]
        ),
        "Crossing reference inventory differs",
    )
    require(
        json.loads((run / "results/pair_reference_summary.json").read_text())
        == summary,
        "Pair per-run summary export differs",
    )
    with (run / "results/pair_reference.csv").open(newline="") as stream:
        reader = csv.DictReader(stream)
        require(
            reader.fieldnames == FIELDS
            and list(reader)
            == [{k: "" if r[k] is None else str(r[k]) for k in FIELDS} for r in rows],
            "Pair CSV export differs",
        )
    require(
        (run / "reports/pair_reference_report.md").read_text()
        == render_report(summary),
        "Pair report export differs",
    )
    print(
        f"Pair-set evaluation audit passed: {len(rows)} planned outcomes; exact crossing contacts, frozen inputs, coverage and exposure replayed; no inference."
    )
    return summary
