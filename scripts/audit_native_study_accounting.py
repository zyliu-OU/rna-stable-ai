#!/usr/bin/env python3
"""Publish/replay stopped helix replication request denominators without native callbacks."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp, publish
from rnastable.native_journal import exclusive_driver, atomic_json
from rnastable.native_study_accounting import study_accounting
from rnastable.reference_audit import require


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        summary = json.loads(
            (ROOT / "results/helix_prior_execution_summary.json").read_text()
        )
        run = Path(summary["run_dir"])
        require(
            summary == json.loads((run / "summary.json").read_text()),
            "Retained ledger differs",
        )
        with exclusive_driver(Path(summary["accounting"]["run_dir"]) / ".driver.lock"):
            expected = study_accounting(summary["accounting"]["run_dir"])
        require(
            summary["accounting"] == expected, "Full study accounting replay differs"
        )
        print(
            "Native study accounting audit passed: every planned component and request denominator; zero native callbacks."
        )
        return summary
    study = args.study or Path(
        json.loads((ROOT / "results/helix_prior_replication_summary.json").read_text())[
            "run_dir"
        ]
    )
    with exclusive_driver(study / ".driver.lock"):
        accounting = study_accounting(study)
    run = ROOT / "results/helix_prior_execution_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    summary = {
        "complete": True,
        "run_dir": str(run),
        "accounting": accounting,
        "native_callbacks": 0,
        "model_fitted": False,
        "test_accuracy_evaluated": False,
    }
    atomic_json(run / "summary.json", summary)
    report = [
        "# Full native study execution accounting",
        "",
        accounting["policy"],
        "",
        f"Totals: `{json.dumps(accounting['totals'], sort_keys=True)}`",
        "",
        "| Component | Input index | Seed | Planned | Started | Complete | Unknown | Not started |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in accounting["rows"]:
        report.append(
            "| "
            + " | ".join(
                str(row[key])
                for key in (
                    "component_index",
                    "input_index",
                    "seed",
                    "planned_native_requests",
                    "started_native_requests",
                    "completed_native_requests",
                    "unknown_native_requests",
                    "not_started_native_requests",
                )
            )
            + " |"
        )
    publish(
        ROOT,
        "helix_prior_execution",
        summary,
        accounting["rows"],
        list(accounting["rows"][0]),
        "\n".join(report) + "\n",
    )
    print(json.dumps(accounting["totals"], indent=2))
    return summary


if __name__ == "__main__":
    main()
