#!/usr/bin/env python3
"""Audit the complete matched family pair-set development study."""
# ruff: noqa: E402 -- standalone source bootstrap.

import argparse
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import write_artifact
from rnastable.native_journal import atomic_json
from rnastable.reference import digest
from rnastable.reference_audit import require
from run_family_pair_set_training import SEEDS, audit_component, audit_protocol, component_name
from rnastable.pair_head_study import HEADS


def matched_initialization(study):
    import torch

    for seed in SEEDS:
        states = {head: torch.load(study / component_name(head, seed) / "initial_model.pt",
                                   map_location="cpu", weights_only=True)
                  for head in HEADS}
        for head in ("stack", "helix"):
            require(all(torch.equal(value, states[head]["base." + key])
                        for key, value in states["baseline"].items()),
                    "Matched base initialization differs")
            feature = "stack_weights.weight" if head == "stack" else "helix_weights.weight"
            require(bool((states[head][feature] == 0).all()),
                    "Extra head features do not start at zero")
    return True


def collect(study):
    protocol = audit_protocol(study / "manifest.json")
    rows, component_hashes = [], {}
    for head in HEADS:
        for seed in SEEDS:
            path = study / component_name(head, seed) / "summary.json"
            component = audit_component(path, verify_protocol=False)
            training = component["training"]
            component_hashes[str(path.relative_to(study))] = digest(path.read_bytes())
            rows.append({"head": head, "seed": seed,
                         "initial_validation_full_pair_f1": training["initial_validation_full_pair_f1"],
                         "selected_validation_full_pair_f1": training["selected_validation_full_pair_f1"],
                         "selected_epoch": training["selected_epoch"],
                         "unlearnable_train_gold_pairs": training["unlearnable_train_gold_pairs"],
                         "unlearnable_validation_gold_pairs": training["unlearnable_validation_gold_pairs"],
                         "full_train_gold_pairs": training["full_train_gold_pairs"],
                         "full_validation_gold_pairs": training["full_validation_gold_pairs"]})
    require(matched_initialization(study), "Matched initializations differ")
    means = {head: statistics.mean(r["selected_validation_full_pair_f1"]
                                   for r in rows if r["head"] == head) for head in HEADS}
    return protocol, rows, component_hashes, means


def build(study):
    protocol, rows, hashes, means = collect(study)
    summary = {"complete": True, "run_dir": str(study),
               "study_manifest_sha256": digest((study / "manifest.json").read_bytes()),
               "summary_code_sha256": digest(Path(__file__).read_bytes()),
               "component_summary_sha256": hashes,
               "rows": rows, "mean_selected_validation_full_pair_f1_by_head": means,
               "matched_initialization": True,
               "train_records": 61, "validation_records": 22,
               "development_only": True, "test_evaluated": False,
               "independent_test_claim": False,
               "limitations": [
                   "Validation records select checkpoints; selected F1 is development performance, not independent test accuracy.",
                   "The training dataset used label-informed coverage selection after two failed frozen source runs.",
                   "Unlearnable noncanonical or short-loop gold contacts remain in full-reference validation scoring.",
                   "No biological stability, mutation benefit, retained function or broad structure accuracy claim.",
               ]}
    require(protocol["run_dir"] == str(study), "Study directory differs")
    atomic_json(study / "summary.json", summary)
    audit(study / "summary.json")
    write_artifact(ROOT / "results/family_pair_set_training_summary.json",
                   json.dumps(summary, indent=2) + "\n")
    return summary


def audit(path):
    summary = json.loads(Path(path).read_text())
    study = Path(summary["run_dir"])
    require(summary == json.loads((study / "summary.json").read_text())
            and digest(Path(__file__).read_bytes()) == summary["summary_code_sha256"],
            "Study summary/code changed")
    protocol, rows, hashes, means = collect(study)
    require(protocol["run_dir"] == str(study)
            and digest((study / "manifest.json").read_bytes()) == summary["study_manifest_sha256"]
            and summary["component_summary_sha256"] == hashes
            and summary["rows"] == rows
            and summary["mean_selected_validation_full_pair_f1_by_head"] == means
            and summary["matched_initialization"] is True
            and summary["train_records"] == 61
            and summary["validation_records"] == 22
            and summary["development_only"] is True
            and summary["test_evaluated"] is False
            and summary["independent_test_claim"] is False,
            "Matched training study replay differs")
    print("Nine-component pair-set development study audit passed; no independent test.")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--protocol", type=Path,
                        default=ROOT / "results/family_pair_set_training_protocol.json")
    args = parser.parse_args()
    if args.verify:
        audit(args.verify)
    else:
        plan = json.loads(args.protocol.read_text())
        build(Path(plan["run_dir"]))


if __name__ == "__main__":
    main()
