#!/usr/bin/env python3
"""Single-seed matched helix fit with 27 longer training-only bpRNA records."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.exposures import exposure_records, read_exposure, record_exposure  # noqa: E402
from rnastable.helix_pairs import make_helix_model  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.pair_head_study import head_config, predictions  # noqa: E402
from rnastable.pair_set_training import (  # noqa: E402
    pair_set_supervision, score_predictions, train_component,
)
from rnastable.reference import digest  # noqa: E402
from prepare_bprna_training_subset_v2 import audit as audit_subset  # noqa: E402

SOURCE = ROOT / "results/bprna_training_subset_v2_runs/20261016T174219.360435Z/summary.json"
CONTROL = ROOT / "results/family_pair_set_training_runs/20261016T012741.486402Z"
PROTOCOL = ROOT / "results/bprna_length_pilot_protocol.json"
SEED = 1729
CODE = [Path(__file__), *(ROOT / "src/rnastable" / name for name in (
    "pair_set_training.py", "pair_head_study.py", "helix_pairs.py",
    "global_sparse_pairs.py", "context_pairs.py", "exact_sparse_pairs.py",
    "exposures.py", "pair_reference.py", "scoring.py", "structure_model.py"))]


def inputs():
    source = audit_subset(SOURCE)
    source_run = Path(source["run_dir"])
    extension = json.loads((source_run / "selection.json").read_text())["selected"]
    if len(extension) != 27 or any(not 400 <= len(row["sequence"]) <= 1024 for row in extension):
        raise ValueError("Screened longer training extension differs")
    old_train = json.loads((CONTROL / "train.json").read_text())["records"]
    validation = json.loads((CONTROL / "validation.json").read_text())["records"]
    if len(old_train) != 61 or len(validation) != 22:
        raise ValueError("Matched source training/validation cohorts differ")
    new_records = [{"id": row["id"], "sequence": row["sequence"],
                    "pairs": row["pairs"], "reference_kind": "computational",
                    "source": "bpRNA-1m version 1.0 dot-bracket training-only; " + row["source_group"]}
                   for row in extension]
    if len({row["id"] for row in old_train + new_records + validation}) != 110:
        raise ValueError("Matched training/validation IDs overlap")
    for row in new_records:
        pair_set_supervision(row, 1024)
    control_run = CONTROL / f"helix_seed{SEED}"
    control_summary = json.loads((control_run / "summary.json").read_text())
    config = control_summary["config"]
    if (control_summary["head"] != "helix" or control_summary["seed"] != SEED
            or config["top_k"] != 16 or config["epochs"] != 10):
        raise ValueError("Matched helix control differs")
    base = {key: value for key, value in config.items()
            if key not in ("seed", "pair_features")}
    if head_config(base, "helix", SEED) != config:
        raise ValueError("Matched helix configuration differs")
    return old_train + new_records, validation, base, control_summary, source


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    train, validation, base, control, source = inputs()
    run = ROOT / "results/bprna_length_pilot_protocol_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "train.json", {"records": train, "role": "training_only"})
    atomic_json(run / "validation.json", {"records": validation, "role": "reused_development_validation"})
    atomic_json(run / "base_config.json", base)
    atomic_json(run / "control_summary.json", control)
    atomic_json(run / "source_summary.json", source)
    policy = {"schema_version": 1,
              "stage": "matched_single_seed_length_expansion_development",
              "head": "helix", "seed": SEED,
              "old_train_records": 61, "new_bpRNA_training_records": 27,
              "validation_records": 22, "epochs": 10,
              "checkpoint_selection": "reused_validation_full_pair_f1_then_BCE",
              "candidate_decoder": "exact_sparse_top16_zero_penalty",
              "model_defaults_changed": False,
              "test_evaluated": False, "independent_accuracy_claim": False}
    atomic_json(run / "policy.json", policy)
    manifest = {"run_dir": str(run),
                "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
                "code_sha256": {str(p): digest(p.read_bytes()) for p in CODE},
                "control_initial_sha256": digest((CONTROL / f"helix_seed{SEED}" / "initial_model.pt").read_bytes())}
    atomic_json(run / "manifest.json", manifest)
    audit_protocol(run / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen bpRNA length-extension pilot:", run / "manifest.json")


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    if manifest != json.loads((run / "manifest.json").read_text()):
        raise ValueError("Length-pilot protocol manifest differs")
    expected = {"train.json", "validation.json", "base_config.json",
                "control_summary.json", "source_summary.json", "policy.json"}
    if set(manifest["snapshot_sha256"]) != expected:
        raise ValueError("Length-pilot snapshot inventory differs")
    for name, sha in manifest["snapshot_sha256"].items():
        if digest((run / name).read_bytes()) != sha:
            raise ValueError("Length-pilot snapshot changed")
    for name, sha in manifest["code_sha256"].items():
        if digest(Path(name).read_bytes()) != sha:
            raise ValueError("Length-pilot execution code changed")
    if digest((CONTROL / f"helix_seed{SEED}" / "initial_model.pt").read_bytes()) != manifest["control_initial_sha256"]:
        raise ValueError("Matched control initial checkpoint changed")
    policy = json.loads((run / "policy.json").read_text())
    if (policy["head"] != "helix" or policy["seed"] != SEED
            or policy["new_bpRNA_training_records"] != 27
            or policy["validation_records"] != 22
            or policy["test_evaluated"] is not False
            or policy["independent_accuracy_claim"] is not False):
        raise ValueError("Length-pilot policy differs")
    train = json.loads((run / "train.json").read_text())["records"]
    validation = json.loads((run / "validation.json").read_text())["records"]
    if len(train) != 88 or len(validation) != 22:
        raise ValueError("Length-pilot frozen cohort differs")
    return manifest


def execute():
    import torch

    protocol = audit_protocol(PROTOCOL)
    plan = Path(protocol["run_dir"])
    train = json.loads((plan / "train.json").read_text())["records"]
    validation = json.loads((plan / "validation.json").read_text())["records"]
    base = json.loads((plan / "base_config.json").read_text())
    control = json.loads((plan / "control_summary.json").read_text())
    run = ROOT / "results/bprna_length_pilot_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "protocol.json", protocol)
    events = [record_exposure(run, "training_started", train),
              record_exposure(run, "validation_started", validation)]
    training, rows = train_component(train, validation, base, "helix", SEED, run)
    atomic_json(run / "training.json", training)
    atomic_json(run / "predictions.json", rows)
    old_initial = torch.load(CONTROL / f"helix_seed{SEED}" / "initial_model.pt",
                             map_location="cpu", weights_only=True)
    new_initial = torch.load(run / "initial_model.pt", map_location="cpu", weights_only=True)
    matched = all(torch.equal(value, new_initial[key]) for key, value in old_initial.items())
    if not matched:
        raise ValueError("Length-pilot initial weights differ from control")
    manifest = {"run_dir": str(run), "protocol_run": protocol["run_dir"],
                "exposure_events": events,
                "snapshot_sha256": {str(p.relative_to(run)): digest(p.read_bytes())
                                    for p in run.rglob("*") if p.is_file()}}
    atomic_json(run / "manifest.json", manifest)
    summary = expected_summary(run, (run / "manifest.json").read_bytes(),
                               train, validation, training, control)
    atomic_json(run / "summary.json", summary)
    audit(run / "summary.json")
    print("Length-extension pilot:", run / "summary.json")
    print("Extended F1:", summary["extended_validation_full_pair_f1"],
          "control F1:", summary["control_validation_full_pair_f1"])


def expected_summary(run, manifest_raw, train, validation, training, control):
    old_f1 = control["training"]["selected_validation_full_pair_f1"]
    new_f1 = training["selected_validation_full_pair_f1"]
    return {"complete": True, "run_dir": str(run),
            "manifest_sha256": digest(manifest_raw),
            "train_records": len(train), "validation_records": len(validation),
            "new_longer_train_records": len(train) - 61,
            "train_max_length_nt": max(len(row["sequence"]) for row in train),
            "validation_max_length_nt": max(len(row["sequence"]) for row in validation),
            "selected_epoch": training["selected_epoch"],
            "extended_validation_full_pair_f1": new_f1,
            "control_validation_full_pair_f1": old_f1,
            "development_f1_difference": new_f1 - old_f1,
            "matched_initial_weights": True,
            "test_evaluated": False, "independent_accuracy_claim": False,
            "model_defaults_changed": False}


def audit(path):
    import torch

    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    if summary != json.loads((run / "summary.json").read_text()):
        raise ValueError("Length-pilot summary differs")
    raw_manifest = (run / "manifest.json").read_bytes()
    if digest(raw_manifest) != summary["manifest_sha256"]:
        raise ValueError("Length-pilot manifest changed")
    manifest = json.loads(raw_manifest)
    protocol = audit_protocol(Path(manifest["protocol_run"]) / "manifest.json")
    if protocol != json.loads((run / "protocol.json").read_text()):
        raise ValueError("Length-pilot protocol copy differs")
    plan = Path(protocol["run_dir"])
    train = json.loads((plan / "train.json").read_text())["records"]
    validation = json.loads((plan / "validation.json").read_text())["records"]
    for event, records, stage in zip(manifest["exposure_events"],
                                     (train, validation),
                                     ("training_started", "validation_started"), strict=True):
        ep = Path(event["path"])
        if (digest(ep.read_bytes()) != event["sha256"]
                or read_exposure(ep)["records"] != exposure_records(
                    records, str(run) + " " + stage)):
            raise ValueError("Length-pilot exposure event differs")
    expected_files = {"protocol.json", "training.json", "predictions.json",
                      "initial_model.pt", "best_model.pt", "epochs.jsonl"}
    expected_files |= {str(Path(event["path"]).relative_to(run))
                       for event in manifest["exposure_events"]}
    if set(manifest["snapshot_sha256"]) != expected_files:
        raise ValueError("Length-pilot run file inventory differs")
    for name, sha in manifest["snapshot_sha256"].items():
        if digest((run / name).read_bytes()) != sha:
            raise ValueError("Length-pilot run snapshot changed")
    training = json.loads((run / "training.json").read_text())
    if training["history"] != [json.loads(line) for line in (run / "epochs.jsonl").read_text().splitlines()]:
        raise ValueError("Length-pilot epoch history differs")
    if any(digest((run / name).read_bytes()) != sha
           for name, sha in training["checkpoint_sha256"].items()):
        raise ValueError("Length-pilot checkpoint changed")
    old_initial = torch.load(CONTROL / f"helix_seed{SEED}" / "initial_model.pt",
                             map_location="cpu", weights_only=True)
    new_initial = torch.load(run / "initial_model.pt", map_location="cpu", weights_only=True)
    if not all(torch.equal(value, new_initial[key]) for key, value in old_initial.items()):
        raise ValueError("Length-pilot initial weights differ")
    config = head_config(json.loads((plan / "base_config.json").read_text()), "helix", SEED)
    model = make_helix_model(config)
    model.load_state_dict(torch.load(run / "best_model.pt", map_location="cpu", weights_only=True))
    model.eval()
    torch.set_num_threads(config["cpu_threads"])
    with torch.inference_mode():
        replayed = predictions(model, validation, "trained", config)
    if replayed != json.loads((run / "predictions.json").read_text())["trained"]:
        raise ValueError("Length-pilot checkpoint predictions differ")
    f1, _ = score_predictions(replayed, validation)
    if f1 != training["selected_validation_full_pair_f1"]:
        raise ValueError("Length-pilot validation score differs")
    control = json.loads((plan / "control_summary.json").read_text())
    if summary != expected_summary(run, raw_manifest, train, validation, training, control):
        raise ValueError("Length-pilot summary values differ")
    print("bpRNA length-extension pilot replay passed")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.freeze:
        freeze()
    elif args.run:
        execute()
    else:
        audit(args.verify)


if __name__ == "__main__":
    main()
