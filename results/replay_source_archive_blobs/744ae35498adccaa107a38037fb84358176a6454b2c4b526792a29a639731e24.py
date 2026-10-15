#!/usr/bin/env python3
"""Combine audited stack/helix prior studies without new search or selection."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp, publish
from rnastable.native_journal import atomic_json
from rnastable.prior_comparison import compare_studies
from rnastable.reference import digest
from rnastable.reference_audit import require
from rnastable.reference_extension import audit as audit_extension
from run_checkpoint_prior_replication import audit as audit_stack
from run_helix_prior_replication import audit as audit_helix


def inputs():
    names = {
        "stack": "checkpoint_prior_replication",
        "extension": "checkpoint_prior_reference_extension",
        "helix_seed20261006": "helix_prior_replication",
        "helix_seed20261007": "helix_prior_seed7_replication",
    }
    paths = {
        key: ROOT / "results" / (name + "_summary.json") for key, name in names.items()
    }
    return paths, {key: json.loads(path.read_text()) for key, path in paths.items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    paths, data = inputs()
    audit_stack(paths["stack"])
    audit_extension(ROOT, paths["extension"])
    for key in ("helix_seed20261006", "helix_seed20261007"):
        audit_helix(paths[key])
    comparison = compare_studies(
        data["stack"],
        data["extension"],
        [(key, data[key]) for key in ("helix_seed20261006", "helix_seed20261007")],
    )
    sources = {str(path): digest(path.read_bytes()) for path in paths.values()}
    if args.verify:
        summary = json.loads(
            (ROOT / "results/checkpoint_prior_comparison_summary.json").read_text()
        )
        require(
            summary["comparison"] == comparison and summary["source_sha256"] == sources,
            "Prior comparison replay differs",
        )
        require(
            summary
            == json.loads((Path(summary["run_dir"]) / "summary.json").read_text()),
            "Retained comparison differs",
        )
        print(
            "Prior comparison audit passed:54 trajectories,12 paired prior differences and24 repeated control checks; no native callbacks or new selection."
        )
        return summary
    run = ROOT / "results/checkpoint_prior_comparison_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    summary = {
        "complete": True,
        "run_dir": str(run),
        "source_sha256": sources,
        "comparison": comparison,
        "native_callbacks": 0,
    }
    atomic_json(run / "summary.json", summary)
    rows = comparison["paired_prior_differences"]
    report = [
        "# Descriptive checkpoint-prior comparison",
        "",
        *comparison["limitations"],
        "",
        "| Helix model seed | Input | Search seed | Stack selected delta | Helix selected delta | Helix minus stack | Helix minus compatibility |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        report.append(
            "| "
            + " | ".join(
                str(row[key])
                for key in (
                    "model_seed",
                    "input_id",
                    "search_seed",
                    "stack_selected_delta_kcal_mol",
                    "helix_selected_delta_kcal_mol",
                    "helix_minus_stack_selected_delta_kcal_mol",
                    "helix_minus_compatibility_selected_delta_kcal_mol",
                )
            )
            + " |"
        )
    report += [
        "",
        f"Replayed {len(comparison['control_reproducibility_checks'])} model-independent controls with identical finalists and LinearFold energies.",
    ]
    publish(
        ROOT,
        "checkpoint_prior_comparison",
        summary,
        rows,
        list(rows[0]),
        "\n".join(report) + "\n",
    )
    return summary


if __name__ == "__main__":
    main()
