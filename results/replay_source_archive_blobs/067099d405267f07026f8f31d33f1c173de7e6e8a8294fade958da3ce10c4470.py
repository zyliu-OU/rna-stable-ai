#!/usr/bin/env python3
"""Replay metrics from all nine measured checkpoints on the same frozen47 records."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp, publish
from rnastable.development_slices import analyze
from rnastable.exposures import record_exposure, read_exposure, exposure_records
from rnastable.native_journal import atomic_json
from rnastable.reference import digest
from rnastable.reference_audit import require


def replay(source_path, before_analysis=None):
    source_path = Path(source_path)
    source = json.loads(source_path.read_text())
    parent = Path(source["run_dir"])
    require(
        source["completed_fits"] == source["planned_fits"] == 9
        and source["test_evaluated"] is False
        and source["development_only"] is True,
        "Expected completed development head study",
    )
    require(
        source == json.loads((parent / "summary.json").read_text())
        and digest((parent / "manifest.json").read_bytes())
        == source["manifest_sha256"],
        "Head study binding differs",
    )
    plan = json.loads((parent / "manifest.json").read_text())
    path = parent / "validation.json"
    require(
        digest(path.read_bytes()) == plan["snapshot_sha256"]["validation.json"],
        "Frozen validation changed",
    )
    records = json.loads(path.read_text())["records"]
    components = []
    sources = {
        str(source_path): digest(source_path.read_bytes()),
        str(path): digest(path.read_bytes()),
    }
    for item in source["components"]:
        path = Path(item["summary"])
        require(digest(path.read_bytes()) == item["sha256"], "Component changed")
        component = json.loads(path.read_text())
        child = Path(component["run_dir"])
        require(
            (child / "validation.json").read_bytes()
            == (parent / "validation.json").read_bytes(),
            "Component validation differs",
        )
        pred = child / "predictions.json"
        require(
            digest(pred.read_bytes()) == component["predictions_sha256"],
            "Checkpoint predictions changed",
        )
        bundle = json.loads(pred.read_text())
        methods = [
            method for method in bundle["methods"] if method.startswith("trained_")
        ]
        require(len(methods) == 1, "Trained method inventory differs")
        components.append(
            (
                component,
                [row for row in bundle["records"] if row["method"] == methods[0]],
            )
        )
        sources[str(path)] = digest(path.read_bytes())
        sources[str(pred)] = digest(pred.read_bytes())
    if before_analysis is not None:
        before_analysis(records)
    return records, analyze(records, components), sources


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    source = ROOT / "results/pair_head_development_study_summary.json"
    run = (
        None if args.verify else ROOT / "results/development_slices_runs" / timestamp()
    )
    events = []
    if run is not None:
        run.mkdir(parents=True, exist_ok=False)
    records, analysis, sources = replay(
        source,
        None
        if args.verify
        else lambda records: events.append(
            record_exposure(run, "validation_started", records)
        ),
    )
    if args.verify:
        summary = json.loads(
            (ROOT / "results/development_slices_summary.json").read_text()
        )
        run = Path(summary["run_dir"])
        require(
            summary == json.loads((run / "summary.json").read_text())
            and summary["analysis"] == analysis
            and summary["source_sha256"] == sources,
            "Development slice replay differs",
        )
        event = summary["exposure_event"]
        path = Path(event["path"])
        require(
            path.resolve().parent == (run / "exposures").resolve()
            and digest(path.read_bytes()) == event["sha256"],
            "Diagnostic exposure changed",
        )
        data = read_exposure(path)
        require(
            data["stage"] == "validation_started"
            and data["records"]
            == exposure_records(records, str(run) + " validation_started"),
            "Diagnostic exposure records differ",
        )
        print(
            "Development slices audit passed:423 stored checkpoint predictions, fixed source/length slices and all47 per-record differences; no new inference, fitting or test."
        )
        return summary
    event = events[0]
    summary = {
        "complete": True,
        "run_dir": str(run),
        "source_sha256": sources,
        "analysis": analysis,
        "exposure_event": event,
    }
    atomic_json(run / "summary.json", summary)
    rows = analysis["slices"]
    report = [
        "# Reused development checkpoint diagnostics",
        "",
        *analysis["limitations"],
        "",
        "| Slice | Group | Seed | Head | Records | Precision | Recall | F1 |",
        "|---|---|---:|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        report.append(
            "| "
            + " | ".join(
                str(row[key])
                for key in (
                    "dimension",
                    "group",
                    "model_seed",
                    "head",
                    "planned_records",
                    "pair_precision",
                    "pair_recall",
                    "pair_f1",
                )
            )
            + " |"
        )
    report += [
        "",
        "## All per-record mean differences",
        "",
        "| ID | Length | Source | Baseline F1 | Stack F1 | Helix F1 | Helix minus baseline |",
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    for row in analysis["per_record_mean_across_model_seeds"]:
        report.append(
            "| "
            + " | ".join(
                str(row[key])
                for key in (
                    "id",
                    "length",
                    "source_group",
                    "baseline_mean_f1",
                    "stack_mean_f1",
                    "helix_mean_f1",
                    "helix_minus_baseline_mean_f1",
                )
            )
            + " |"
        )
    publish(
        ROOT,
        "development_slices",
        summary,
        rows,
        list(rows[0]),
        "\n".join(report) + "\n",
    )
    return summary


if __name__ == "__main__":
    main()
