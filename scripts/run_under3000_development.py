#!/usr/bin/env python3
"""Matched Stage 2 development fits restricted to 1-2999 nt; no promotion."""

import argparse
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.artifacts import timestamp
from rnastable.exposures import record_exposure
from rnastable.native_journal import atomic_json
from rnastable.pair_set_training import score_predictions
from rnastable.reference import digest
from train_sampled_long_development import fit_one, inputs, CODE, SEEDS
from audit_stage2_under3000 import SHORT_REFS, GATE

SCOPE = ROOT / "configs/project_scope_2026-10-18.json"
SOURCES = [ROOT / "results/bprna_length_pilot_protocol_runs/20261016T174446.305367Z/train.json",
           ROOT / "results/bprna_long_training_smoke_runs/20261017T033749.792816Z/selection.json",
           ROOT / "results/long_validation_coverage_runs/20261017T033935.363253Z/selection.json",
           ROOT / "results/family_pair_set_training_runs/20261016T012741.486402Z/helix_seed1729/summary.json",
           SHORT_REFS, GATE, SCOPE]


def datasets():
    old, extra, long, config = inputs()
    if any(len(r["sequence"]) >= 3000 for r in old):
        raise ValueError("Historical control exceeds new active scope")
    extra = [r for r in extra if len(r["sequence"]) < 3000]
    long = [r for r in long if len(r["sequence"]) < 3000]
    short = json.loads(SHORT_REFS.read_text())
    if len(old) != 88 or len(extra) != 15 or len(long) != 6 or len(short) != 13:
        raise ValueError("Scoped development inventory differs")
    return {"control_88": old, "extended_103": old + extra}, {"long": long, "short": short}, {
        **config, "training_max_length": 2999, "top_k": 32}


def freeze():
    train, validation, config = datasets()
    folder = ROOT / "results/under3000_development_protocol_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    for name, value in (("train.json", train), ("validation.json", validation), ("config.json", config)):
        atomic_json(folder / name, value)
    manifest = {"run_dir": str(folder), "seeds": list(SEEDS), "epochs": 10,
                "checkpoint": "fixed_final_epoch", "decoder": "exact_sparse_top32",
                "top32_choice_basis": "previous_exposed_development_diagnostic",
                "validation_used_during_fit": False, "independent_test_claim": False,
                "model_defaults_changed": False, "stage3_target": "cell_free_expression",
                "source_sha256": {str(p): digest(p.read_bytes()) for p in SOURCES},
                "code_sha256": {str(p): digest(p.read_bytes()) for p in [*CODE, Path(__file__).resolve()]},
                "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in folder.iterdir()}}
    atomic_json(folder / "manifest.json", manifest)
    print(folder / "manifest.json")


def audit(path):
    manifest = json.loads(Path(path).read_text())
    folder = Path(manifest["run_dir"])
    if manifest != json.loads((folder / "manifest.json").read_text()):
        raise ValueError("Scoped protocol manifest differs")
    for group in ("source_sha256", "code_sha256"):
        for name, sha in manifest[group].items():
            if digest(Path(name).read_bytes()) != sha:
                raise ValueError("Scoped input or code changed: " + name)
    for name, sha in manifest["snapshot_sha256"].items():
        if digest((folder / name).read_bytes()) != sha:
            raise ValueError("Scoped snapshot changed")
    train, validation, config = datasets()
    if (train != json.loads((folder / "train.json").read_text())
            or validation != json.loads((folder / "validation.json").read_text())
            or config != json.loads((folder / "config.json").read_text())):
        raise ValueError("Scoped dataset differs")
    return manifest, train, validation, config


def run(path):
    import torch

    manifest, train, validation, config = audit(path)
    folder = ROOT / "results/under3000_development_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    atomic_json(folder / "protocol.json", manifest)
    records = validation["long"] + validation["short"]
    result = {}
    for seed in SEEDS:
        initial = {}
        for arm, training in train.items():
            component = folder / f"{arm}_seed{seed}"
            component.mkdir()
            events = [record_exposure(component, "training_started", training),
                      record_exposure(component, "validation_started", records)]
            metrics = fit_one(training, records, copy.deepcopy(config), seed, component)
            predictions = json.loads((component / "predictions.json").read_text())
            offset = 0
            by_cohort = {}
            for name, cohort in validation.items():
                f1, _ = score_predictions(predictions[offset:offset + len(cohort)], cohort)
                by_cohort[name] = {"n": len(cohort), "mean_pair_f1": f1}
                offset += len(cohort)
            metrics.update(cohorts=by_cohort, exposure_events=events)
            atomic_json(component / "summary.json", metrics)
            result[component.name] = by_cohort
            initial[arm] = torch.load(component / "initial_model.pt", map_location="cpu", weights_only=True)
        if any(not torch.equal(initial["control_88"][k], initial["extended_103"][k]) for k in initial["control_88"]):
            raise ValueError("Matched initial weights differ")
    summary = {"complete": True, "components": result, "development_only": True,
               "independent_test_claim": False, "model_defaults_changed": False,
               "ready_for_stage3": False, "matched_initial_weights": True}
    atomic_json(folder / "summary.json", summary)
    print(folder / "summary.json")


def verify(path):
    from rnastable.exposures import read_exposure

    folder = Path(path).parent
    manifest, train, validation, config = audit(folder / "protocol.json")
    summary = json.loads(Path(path).read_text())
    expected = {}
    for seed in SEEDS:
        initial = {}
        for arm in train:
            component = folder / f"{arm}_seed{seed}"
            saved = json.loads((component / "summary.json").read_text())
            predictions = json.loads((component / "predictions.json").read_text())
            if any(digest((component / name).read_bytes()) != sha for name, sha in saved["checkpoint_sha256"].items()):
                raise ValueError("Scoped checkpoint bytes differ")
            if digest((component / "predictions.json").read_bytes()) != saved["predictions_sha256"]:
                raise ValueError("Scoped predictions differ")
            if saved["train_records"] != len(train[arm]) or saved["train_max_length_nt"] >= 3000:
                raise ValueError("Scoped training bound differs")
            for event in saved["exposure_events"]:
                if digest(Path(event["path"]).read_bytes()) != event["sha256"]:
                    raise ValueError("Scoped exposure event differs")
                read_exposure(event["path"])
            offset = 0
            by_cohort = {}
            for name, cohort in validation.items():
                score, _ = score_predictions(predictions[offset:offset + len(cohort)], cohort)
                by_cohort[name] = {"n": len(cohort), "mean_pair_f1": score}
                offset += len(cohort)
            if offset != len(predictions) or saved["cohorts"] != by_cohort:
                raise ValueError("Scoped scores differ")
            expected[component.name] = by_cohort
            import torch
            initial[arm] = torch.load(component / "initial_model.pt", map_location="cpu", weights_only=True)
        if any(not torch.equal(initial["control_88"][k], initial["extended_103"][k]) for k in initial["control_88"]):
            raise ValueError("Scoped matched initial weights differ")
    if summary != {"complete": True, "components": expected, "development_only": True,
                   "independent_test_claim": False, "model_defaults_changed": False,
                   "ready_for_stage3": False, "matched_initial_weights": True}:
        raise ValueError("Scoped summary differs")
    print("Under-3000 development artifact and score replay passed (no retraining)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--run", type=Path)
    mode.add_argument("--verify-run", type=Path)
    args = parser.parse_args()
    if args.freeze:
        freeze()
    elif args.run:
        run(args.run)
    else:
        verify(args.verify_run)


if __name__ == "__main__":
    main()
