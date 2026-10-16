#!/usr/bin/env python3
"""Freeze and run matched pair-set development fits without a test cohort."""
# ruff: noqa: E402 -- standalone source bootstrap.

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp, write_artifact
from rnastable.exposures import exposure_records, read_exposure, record_exposure
from rnastable.native_journal import atomic_json
from rnastable.pair_head_study import FACTORIES, HEADS, head_config, predictions
from rnastable.pair_reference import validate_inputs
from rnastable.pair_set_training import pair_set_supervision, score_predictions, train_component
from rnastable.reference import digest
from rnastable.reference_audit import require
from derive_coverage_development_dataset import audit as audit_dataset

NAME = "family_pair_set_training"
SEEDS = (20261015, 7, 1729)


def training_config(dataset_run):
    coverage_protocol = json.loads((dataset_run / "protocol.json").read_text())
    coverage_dir = Path(coverage_protocol["run_dir"])
    frozen = json.loads((coverage_dir / "config.json").read_text())["future_training"]
    base = json.loads((ROOT / "configs/helix_comparative_development.json").read_text())
    base = {k: v for k, v in base.items() if k not in ("seed", "pair_features")}
    base["mode"] = "family_coverage_development_only"
    require(frozen["initialization"] == "declared_random_seeds_no_pretrained_weights"
            and frozen["heads"] == list(HEADS)
            and frozen["model_seeds"] == list(SEEDS)
            and frozen["checkpoint_selection"]
            == "declared_validation_only_not_completed_test_cohorts"
            and frozen["training_contact_policy"]
            == "retain_full_gold_and_report_unlearnable_contacts"
            and base["epochs"] == frozen["epochs"] == 10
            and base["learning_rate"] == frozen["learning_rate"] == 0.001
            and base["cpu_threads"] == frozen["cpu_threads"] == 2
            and base["top_k"] == frozen["top_k"] == 16
            and base["inference_decoder"] == frozen["decoder"] == "exact_sparse"
            and frozen["pair_penalty"] == 0
            and frozen["device"] == "cpu"
            and base["training_max_length"] == 1024
            and base["positive_weight_exponent"] == 1.0,
            "New training settings differ from declared development design")
    return base


def validate_splits(dataset_run):
    raw = {name: (dataset_run / (name + ".json")).read_bytes()
           for name in ("train", "validation")}
    splits = {name: json.loads(content)["records"] for name, content in raw.items()}
    for name, content in raw.items():
        data = json.loads(content)
        validate_inputs(data, {"schema_version": 1, "format": "pair_set_zero_based_v1",
                               "methods": ["audit"], "records": []})
        require(data["role"] == name and data["development_only"] is True
                and data["label_informed_selection"] is True,
                "Training split provenance differs")
    binding = json.loads((dataset_run / "binding.json").read_text())
    require(binding["dataset_ready"] is True and len(splits["train"]) == 61
            and len(splits["validation"]) == 22,
            "Training requires the ready declared dataset")
    groups = {}
    for name, records in splits.items():
        for record in records:
            bound = next((r for r in binding["records"] if r["id"] == record["id"]), None)
            require(bound is not None and bound["reference_status"] == "ok"
                    and all(record[k] == bound[k] for k in
                            ("sequence", "pairs", "family_id", "source", "reference_kind"))
                    and bound["role"] == name,
                    "Training row differs from source binding")
            groups.setdefault(name, set()).add(bound["group"])
            pair_set_supervision(record, 1024)
    require(len(groups["train"]) == 12 and len(groups["validation"]) == 4
            and not groups["train"] & groups["validation"],
            "Training family/clan split differs")
    return raw, splits


def freeze(dataset_path):
    dataset = audit_dataset(dataset_path)
    require(dataset["dataset_ready"] is True and dataset["model_training_performed"] is False,
            "Ready untrained dataset required")
    dataset_run = Path(dataset["run_dir"])
    raw, _ = validate_splits(dataset_run)
    base = training_config(dataset_run)
    run = ROOT / "results" / (NAME + "_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "dataset_summary.json", dataset)
    atomic_json(run / "base_config.json", base)
    for name, content in raw.items():
        (run / (name + ".json")).write_bytes(content)
    (run / "driver.py").write_bytes(Path(__file__).read_bytes())
    manifest = {"run_dir": str(run), "dataset_manifest_sha256": dataset["manifest_sha256"],
                "heads": list(HEADS), "seeds": list(SEEDS),
                "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
                "code_sha256": {str(p): digest(p.read_bytes()) for p in
                                [Path(__file__), *sorted((ROOT / "src/rnastable").glob("*.py"))]},
                "training_only": True, "independent_test_claim": False}
    atomic_json(run / "manifest.json", manifest)
    audit_protocol(run / "manifest.json")
    write_artifact(ROOT / "results" / (NAME + "_protocol.json"),
                   json.dumps(manifest, indent=2) + "\n")
    return manifest


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    require(manifest == json.loads((run / "manifest.json").read_text()),
            "Training protocol differs")
    require(set(manifest["snapshot_sha256"]) ==
            {"dataset_summary.json", "base_config.json", "train.json",
             "validation.json", "driver.py"}, "Training snapshot inventory differs")
    for name, sha in manifest["snapshot_sha256"].items():
        require(digest((run / name).read_bytes()) == sha,
                "Training snapshot changed: " + name)
    for name, sha in manifest["code_sha256"].items():
        require(digest(Path(name).read_bytes()) == sha,
                "Training code changed: " + name)
    require(manifest["heads"] == list(HEADS) and manifest["seeds"] == list(SEEDS)
            and manifest["training_only"] is True
            and manifest["independent_test_claim"] is False,
            "Training matrix/policy differs")
    dataset = audit_dataset(Path(json.loads((run / "dataset_summary.json").read_text())["run_dir"])
                            / "summary.json")
    require(dataset == json.loads((run / "dataset_summary.json").read_text())
            and dataset["manifest_sha256"] == manifest["dataset_manifest_sha256"],
            "Training source dataset changed")
    source = Path(dataset["run_dir"])
    raw, _ = validate_splits(source)
    require(all(raw[name] == (run / (name + ".json")).read_bytes() for name in raw)
            and training_config(source) == json.loads((run / "base_config.json").read_text()),
            "Training split/config differs")
    return manifest


def component_name(head, seed):
    require(head in HEADS and seed in SEEDS, "Unknown training component")
    return f"{head}_seed{seed}"


def run_component(protocol_path, head, seed):
    import torch

    plan = audit_protocol(protocol_path)
    study = Path(plan["run_dir"])
    name = component_name(head, seed)
    run = study / name
    require(not run.exists(), "Training component already exists: " + name)
    run.mkdir()
    config = head_config(json.loads((study / "base_config.json").read_text()), head, seed)
    manifest = {"run_dir": str(run), "study_manifest_sha256": digest((study / "manifest.json").read_bytes()),
                "head": head, "seed": seed, "config": config,
                "snapshot_sha256": {role + ".json": digest((study / (role + ".json")).read_bytes())
                                    for role in ("train", "validation")}}
    atomic_json(run / "manifest.json", manifest)
    for role in ("train", "validation"):
        (run / (role + ".json")).write_bytes((study / (role + ".json")).read_bytes())
    splits = {role: json.loads((run / (role + ".json")).read_text())["records"]
              for role in ("train", "validation")}
    events = [record_exposure(run, "training_started", splits["train"]),
              record_exposure(run, "validation_started", splits["validation"])]
    training, rows = train_component(splits["train"], splits["validation"],
                                     json.loads((study / "base_config.json").read_text()),
                                     head, seed, run)
    atomic_json(run / "training.json", training)
    atomic_json(run / "predictions.json", rows)
    summary = {"complete": True, "run_dir": str(run), "head": head, "seed": seed,
               "config": config, "manifest_sha256": digest((run / "manifest.json").read_bytes()),
               "train_records": len(splits["train"]), "validation_records": len(splits["validation"]),
               "training": training, "exposure_events": events,
               "predictions_sha256": digest((run / "predictions.json").read_bytes()),
               "test_evaluated": False, "independent_test_claim": False}
    atomic_json(run / "summary.json", summary)
    audit_component(run / "summary.json", verify_protocol=False)
    return summary


def audit_component(path, *, verify_protocol=True):
    import torch

    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    study = run.parent
    if verify_protocol:
        audit_protocol(study / "manifest.json")
    manifest = json.loads((run / "manifest.json").read_text())
    require(summary == json.loads((run / "summary.json").read_text())
            and summary["complete"] is True and summary["test_evaluated"] is False,
            "Training component summary differs")
    require(digest((run / "manifest.json").read_bytes()) == summary["manifest_sha256"]
            and digest((study / "manifest.json").read_bytes())
            == manifest["study_manifest_sha256"],
            "Training component manifest changed")
    head, seed = manifest["head"], manifest["seed"]
    config = head_config(json.loads((study / "base_config.json").read_text()), head, seed)
    require(manifest["config"] == summary["config"] == config,
            "Training component config changed")
    splits = {}
    for role in ("train", "validation"):
        content = (run / (role + ".json")).read_bytes()
        require(content == (study / (role + ".json")).read_bytes()
                and digest(content) == manifest["snapshot_sha256"][role + ".json"],
                "Training component split changed")
        splits[role] = json.loads(content)["records"]
    require((summary["train_records"], summary["validation_records"])
            == (len(splits["train"]), len(splits["validation"])),
            "Training component counts differ")
    events = summary["exposure_events"]
    require(len(events) == 2 and {Path(e["path"]) for e in events}
            == set((run / "exposures").glob("*.json")),
            "Training exposure inventory differs")
    for event, role, stage in zip(events, ("train", "validation"),
                                  ("training_started", "validation_started"), strict=True):
        p = Path(event["path"])
        require(digest(p.read_bytes()) == event["sha256"]
                and read_exposure(p)["records"] == exposure_records(splits[role], str(run) + " " + stage),
                "Training exposure event changed")
    training = summary["training"]
    history = [json.loads(line) for line in (run / "epochs.jsonl").read_text().splitlines()]
    require(training == json.loads((run / "training.json").read_text())
            and training["history"] == history
            and [r["epoch"] for r in history] == list(range(1, 11)),
            "Training epoch history differs")
    chosen = max(history, key=lambda r: (r["validation_mean_full_pair_f1"],
                                          -r["mean_validation_loss"]))
    require(chosen["epoch"] == training["selected_epoch"]
            and chosen["validation_mean_full_pair_f1"]
            == training["selected_validation_full_pair_f1"],
            "Training checkpoint selection differs")
    labels = [pair_set_supervision(r, 1024) for r in splits["train"]]
    val_labels = [pair_set_supervision(r, 1024) for r in splits["validation"]]
    positive = sum(int(y.sum()) for _, y, _ in labels)
    negative = sum(len(y) - int(y.sum()) for _, y, _ in labels)
    require(training["train_positive_pairs"] == positive
            and training["train_negative_pairs"] == negative
            and training["unlearnable_train_gold_pairs"] == sum(s[2] for s in labels)
            and training["unlearnable_validation_gold_pairs"] == sum(s[2] for s in val_labels)
            and training["full_train_gold_pairs"] == sum(len(r["pairs"]) for r in splits["train"])
            and training["full_validation_gold_pairs"] == sum(len(r["pairs"]) for r in splits["validation"]),
            "Training full-gold accounting differs")
    rows = json.loads((run / "predictions.json").read_text())
    require(digest((run / "predictions.json").read_bytes()) == summary["predictions_sha256"],
            "Training predictions changed")
    torch.set_num_threads(config["cpu_threads"])
    for filename, method in (("initial_model.pt", "untrained"),
                             ("best_model.pt", "trained")):
        checkpoint = run / filename
        require(digest(checkpoint.read_bytes()) == training["checkpoint_sha256"][filename],
                "Training checkpoint changed")
        torch.manual_seed(seed)
        model = FACTORIES[head](config)
        state = torch.load(checkpoint, map_location="cpu", weights_only=True)
        if filename == "initial_model.pt":
            require(all(torch.equal(v, state[k]) for k, v in model.state_dict().items()),
                    "Training initial weights differ from declared seed")
        model.load_state_dict(state)
        model.eval()
        with torch.inference_mode():
            replayed = predictions(model, splits["validation"], method, config)
        require(replayed == rows[method], "Training checkpoint predictions differ")
        f1, details = score_predictions(replayed, splits["validation"])
        expected = (training["initial_validation_full_pair_f1"] if method == "untrained"
                    else training["selected_validation_full_pair_f1"])
        require(f1 == expected, "Training full-reference validation score differs")
        if method == "trained":
            require(training["validation_record_scores"] ==
                    [{"id": r["id"], **score}
                     for r, score in zip(splits["validation"], details, strict=True)],
                    "Training per-record scores differ")
    print(f"Training component audit passed: {head} seed {seed}.")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--run-component", nargs=2, metavar=("HEAD", "SEED"))
    mode.add_argument("--verify-component", type=Path)
    mode.add_argument("--verify-protocol", type=Path)
    parser.add_argument("--dataset", type=Path,
                        default=ROOT / "results/family_coverage_development_summary.json")
    parser.add_argument("--protocol", type=Path,
                        default=ROOT / "results/family_pair_set_training_protocol.json")
    args = parser.parse_args()
    if args.verify_component:
        audit_component(args.verify_component)
    elif args.verify_protocol:
        audit_protocol(args.verify_protocol)
    elif args.run_component:
        run_component(args.protocol, args.run_component[0], int(args.run_component[1]))
    else:
        freeze(args.dataset)


if __name__ == "__main__":
    main()
