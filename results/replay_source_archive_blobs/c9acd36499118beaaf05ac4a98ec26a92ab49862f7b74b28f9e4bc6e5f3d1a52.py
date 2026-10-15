#!/usr/bin/env python3
"""Prove pair-set scoring matches all 423 stored development structure predictions."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import publish, timestamp
from rnastable.native_journal import atomic_json
from rnastable.pair_reference import FORMAT, audit, run_evaluation
from rnastable.reference import digest, METRICS
from rnastable.reference_audit import require
from rnastable.scoring import base_pairs, structure_agreement
from analyze_development_slices import replay


def inputs():
    source_path = ROOT / "results/pair_head_development_study_summary.json"
    records, analysis, sources = replay(source_path)
    source = json.loads(source_path.read_text())
    refs = {
        "schema_version": 1,
        "format": FORMAT,
        "dataset_id": "reused_47_record_pair_score_equivalence",
        "records": [
            {**r, "pairs": [list(p) for p in sorted(base_pairs(r["structure"]))]}
            for r in records
        ],
    }
    for r in refs["records"]:
        del r["structure"]
    predictions, methods, expected = [], [], {}
    by_id = {r["id"]: r for r in records}
    for item in source["components"]:
        component = json.loads(Path(item["summary"]).read_text())
        method = component["head"] + "_seed" + str(component["seed"])
        methods.append(method)
        bundle = json.loads(
            (Path(component["run_dir"]) / "predictions.json").read_text()
        )
        trained = next(m for m in bundle["methods"] if m.startswith("trained_"))
        for p in bundle["records"]:
            if p["method"] != trained:
                continue
            predictions.append(
                {
                    "id": p["id"],
                    "sequence": p["sequence"],
                    "method": method,
                    "status": "ok",
                    "pairs": [
                        list(pair) for pair in sorted(base_pairs(p["structure"]))
                    ],
                }
            )
            expected[(p["id"], method)] = structure_agreement(
                p["structure"], by_id[p["id"]]["structure"]
            )
    return (
        refs,
        {
            "schema_version": 1,
            "format": FORMAT,
            "methods": methods,
            "records": predictions,
        },
        expected,
        sources,
    )


def check(result, expected):
    require(
        len(result["rows"]) == len(expected) == 423,
        "Development score denominator differs",
    )
    for row in result["rows"]:
        require(
            row["status"] == "ok"
            and {k: row[k] for k in METRICS}
            == expected[(row["reference_id"], row["method"])],
            "Pair-set and dot-bracket metrics differ",
        )
    require(
        result["crossing_reference_records"] == 0,
        "Nested development references changed",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    refs, pred, expected, sources = inputs()
    if args.verify:
        summary = json.loads(
            (ROOT / "results/pair_reference_development_summary.json").read_text()
        )
        run = Path(summary["run_dir"])
        require(
            summary == json.loads((run / "summary.json").read_text()),
            "Retained equivalence study differs",
        )
        require(
            summary["source_sha256"] == sources, "Development source binding differs"
        )
        require(
            json.loads((run / "references.json").read_text()) == refs
            and json.loads((run / "predictions.json").read_text()) == pred,
            "Generated pair inputs differ",
        )
        result = audit(Path(summary["pair_evaluation_run"]) / "summary.json")
        require(
            digest((Path(result["run_dir"]) / "summary.json").read_bytes())
            == summary["pair_evaluation_sha256"],
            "Pair evaluation result changed",
        )
        check(result, expected)
        require(
            summary["matched_predictions"] == 423
            and summary["development_only"] is True
            and summary["new_inference"] is False
            and summary["test_evaluated"] is False,
            "Equivalence interpretation differs",
        )
        print(
            "Development pair-score equivalence passed: all seven metrics for 423 stored predictions; no fitting, inference or test evaluation."
        )
        return summary
    run = ROOT / "results/pair_reference_development_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "references.json", refs)
    atomic_json(run / "predictions.json", pred)
    result = run_evaluation(ROOT, run / "references.json", run / "predictions.json")
    check(result, expected)
    audit(Path(result["run_dir"]) / "summary.json")
    summary = {
        "complete": True,
        "run_dir": str(run),
        "source_sha256": sources,
        "pair_evaluation_run": result["run_dir"],
        "pair_evaluation_sha256": digest(
            (Path(result["run_dir"]) / "summary.json").read_bytes()
        ),
        "matched_predictions": 423,
        "records": 47,
        "checkpoints": 9,
        "development_only": True,
        "new_inference": False,
        "test_evaluated": False,
        "aggregates": result["aggregates"],
    }
    atomic_json(run / "summary.json", summary)
    report = [
        "# Pair-set scoring equivalence on reused development",
        "",
        "All seven exact pair metrics match legacy dot-bracket scoring for 423 stored predictions (nine checkpoints × 47 records). No new inference, fitting, model selection or test evaluation.",
        "",
        "Crossing-contact capability is verified separately with synthetic fixtures; these development references are nested.",
        "",
        "| Checkpoint | Reference kind | Planned | Measured | Mean pair F1 |",
        "|---|---|---:|---:|---:|",
    ]
    for a in result["aggregates"]:
        report.append(
            f"| {a['method']} | {a['reference_kind']} | {a['planned_inputs']} | {a['measured_inputs']} | {a['mean_pair_f1']} |"
        )
    publish(
        ROOT,
        "pair_reference_development",
        summary,
        result["aggregates"],
        list(result["aggregates"][0]),
        "\n".join(report) + "\n",
    )
    return summary


if __name__ == "__main__":
    main()
