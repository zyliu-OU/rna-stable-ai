#!/usr/bin/env python3
"""Run or verify fixed-draw population sampling on reused development data."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp, publish
from rnastable.native_journal import atomic_json
from rnastable.population_development import (
    SAMPLING_POLICY,
    fit_component,
    audit_component,
)
from rnastable.reference import digest
from rnastable.reference_audit import require
from train_helix_comparative_development import predictions
from train_sampled_comparative_development import frozen_inputs


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(
        summary == json.loads((run / "summary.json").read_text()),
        "Retained aggregate differs",
    )
    require(
        summary["complete"] is True and summary["test_evaluated"] is False,
        "Not complete development-only",
    )
    require(
        digest((run / "manifest.json").read_bytes()) == summary["manifest_sha256"],
        "Aggregate manifest changed",
    )
    manifest = json.loads((run / "manifest.json").read_text())
    require(
        manifest["sampling_seeds"] == [20261006, 20261007, 20261008]
        and manifest["run_dir"] == str(run),
        "Fixed study identity differs",
    )
    require(len(summary["components"]) == 3, "Component inventory differs")
    rows = []
    for seed, item in zip(manifest["sampling_seeds"], summary["components"]):
        path = Path(item["path"])
        require(
            path.resolve()
            == (run / ("sampling_" + str(seed)) / "summary.json").resolve(),
            "Component path differs",
        )
        require(
            digest(path.read_bytes()) == item["sha256"], "Component summary changed"
        )
        component = audit_component(path, frozen_inputs, predictions)
        require(
            component["config"]["population_sampling"]["seed"] == seed,
            "Sampling seed differs",
        )
        rows.append(row_for(component))
    require(rows == summary["rows"], "Aggregate rows differ")
    require(summary["all_model_seeds"] == [20261006] * 3, "Model seed control differs")
    control = summary["full_supervision_control"]
    control_path = Path(control["path"])
    require(
        digest(control_path.read_bytes()) == control["sha256"], "Full control changed"
    )
    full = json.loads(control_path.read_text())
    require(
        full["config"] == manifest["base_config"]
        and full["selected_validation_pair_f1"] == control["validation_mean_pair_f1"],
        "Full control identity differs",
    )
    require(
        all(
            json.loads(Path(item["path"]).read_text())["config"]["seed"]
            == manifest["base_config"]["seed"]
            for item in summary["components"]
        ),
        "Model initialization seed differs",
    )
    return summary


def row_for(component):
    return {
        "sampling_seed": component["config"]["population_sampling"]["seed"],
        "model_seed": component["config"]["seed"],
        "selected_epoch": component["selected_epoch"],
        "validation_mean_pair_f1": component["selected_validation_pair_f1"],
        "sampled_negative": component["train_negative_pairs"],
        "full_negative_population": component["train_population_negative_pairs"],
        "sample_tensor_bytes": component["sample_tensor_bytes"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    parser.add_argument(
        "--summary",
        type=Path,
        default=ROOT / "results/population_development_summary.json",
    )
    args = parser.parse_args()
    if args.verify:
        summary = audit(args.summary)
        print(
            "Population study audit passed: three fixed draws, full training-population weights and full validation labels; no test."
        )
        return summary
    source_bytes, source, snapshots, splits = frozen_inputs(
        ROOT / "results/exact_comparative_development_summary.json"
    )
    base = json.loads((ROOT / "configs/helix_comparative_development.json").read_text())
    run = ROOT / "results/population_development_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    code_paths = [
        Path(__file__),
        ROOT / "scripts/train_helix_comparative_development.py",
        ROOT / "scripts/train_sampled_comparative_development.py",
        *[
            ROOT / "src/rnastable" / name
            for name in (
                "population_development.py",
                "population_sampling.py",
                "context_training.py",
                "helix_pairs.py",
                "context_pairs.py",
                "global_sparse_pairs.py",
                "full_pair_supervision.py",
                "exact_sparse_pairs.py",
                "exposures.py",
                "reference.py",
                "scoring.py",
            )
        ],
    ]
    manifest = {
        "run_dir": str(run),
        "sampling_seeds": [20261006, 20261007, 20261008],
        "base_config": base,
        "source_summary_sha256": digest(source_bytes),
        "code_sha256": {str(p): digest(p.read_bytes()) for p in code_paths},
        "policy": "Three fixed sampling draws; same model initialization and train/validation data. Sampling replicates are not new model seeds or independent biological data.",
    }
    atomic_json(run / "manifest.json", manifest)
    components = []
    rows = []
    for seed in manifest["sampling_seeds"]:
        config = {
            **base,
            "population_sampling": {
                "seed": seed,
                "negatives_per_positive": 32,
                "minimum_negatives": 128,
                "max_length": 1024,
                "policy": SAMPLING_POLICY,
            },
        }
        component = fit_component(
            run / ("sampling_" + str(seed)),
            source_bytes,
            source,
            snapshots,
            splits,
            config,
            predictions,
            code_paths,
        )
        path = Path(component["run_dir"]) / "summary.json"
        components.append({"path": str(path), "sha256": digest(path.read_bytes())})
        rows.append(row_for(component))
    full = json.loads(
        (ROOT / "results/helix_comparative_development_summary.json").read_text()
    )
    require(full["config"] == base, "Full-supervision control configuration differs")
    summary = {
        "complete": True,
        "test_evaluated": False,
        "run_dir": str(run),
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "components": components,
        "rows": rows,
        "all_model_seeds": [base["seed"]] * 3,
        "full_supervision_control": {
            "path": str(ROOT / "results/helix_comparative_development_summary.json"),
            "sha256": digest(
                (
                    ROOT / "results/helix_comparative_development_summary.json"
                ).read_bytes()
            ),
            "validation_mean_pair_f1": full["selected_validation_pair_f1"],
        },
        "limitations": [
            "Reused frozen89 train/47 validation records; no fresh test or generalization claim.",
            "Each fit reuses one draw across10 epochs; expectation-unbiased sampled loss does not imply equivalent optimization.",
            "Sampling seeds vary while model initialization remains fixed. No selection over sampling seeds is performed.",
            "Exact decoding/full validation remain bounded to1024nt; long synthetic sampling does not establish long biological accuracy.",
        ],
    }
    atomic_json(run / "summary.json", summary)
    report = [
        "# Population-sampled helix development comparison",
        "",
        "Full-supervision control F1: " + str(full["selected_validation_pair_f1"]),
        "",
        "| Sampling seed | Model seed | Selected epoch | Reused validation F1 | Sampled negatives | Full negatives | Retained tensor bytes |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        report.append("| " + " | ".join(str(value) for value in row.values()) + " |")
    report += ["", *summary["limitations"]]
    publish(
        ROOT,
        "population_development",
        summary,
        rows,
        list(rows[0]),
        "\n".join(report) + "\n",
    )
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    main()
