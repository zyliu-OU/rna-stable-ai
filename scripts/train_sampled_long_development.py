#!/usr/bin/env python3
"""Matched sampled-pair fits with and without 17 longer training-only RNAs."""

import argparse
import copy
import json
from pathlib import Path
import random
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.exposures import record_exposure  # noqa: E402
from rnastable.helix_pairs import make_helix_model  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.pair_set_training import score_predictions  # noqa: E402
from rnastable.reference import digest  # noqa: E402
from rnastable.sampled_pair_supervision import sampled_pair_supervision  # noqa: E402
from rnastable.structure_model import tokens  # noqa: E402
from evaluate_long_length_checkpoints_v3 import aggregate, long_predictions  # noqa: E402

OLD_TRAIN = ROOT / "results/bprna_length_pilot_protocol_runs/20261016T174446.305367Z/train.json"
NEW_SOURCE = ROOT / "results/bprna_long_training_smoke_runs/20261017T033749.792816Z/selection.json"
VALIDATION = ROOT / "results/long_validation_coverage_runs/20261017T033935.363253Z/selection.json"
BASE = ROOT / "results/family_pair_set_training_runs/20261016T012741.486402Z/helix_seed1729/summary.json"
PROTOCOL = ROOT / "results/sampled_long_development_protocol.json"
SEEDS = (7, 1729, 20261015)
ARMS = ("control_88", "extended_105")
CODE = [Path(__file__), ROOT / "scripts/evaluate_long_length_checkpoints_v3.py",
        *(ROOT / "src/rnastable" / name for name in (
            "sampled_pair_supervision.py", "helix_pairs.py", "global_sparse_pairs.py",
            "context_pairs.py", "long_exact_sparse_pairs.py", "structure_model.py",
            "pair_set_training.py", "pair_reference.py", "scoring.py"))]


def inputs():
    old = json.loads(OLD_TRAIN.read_text())["records"]
    extra = json.loads(NEW_SOURCE.read_text())["selected"]
    validation = json.loads(VALIDATION.read_text())["selected"]
    base = json.loads(BASE.read_text())["config"]
    if (len(old) != 88 or len(extra) != 17 or len(validation) != 11
            or len({row["id"] for row in old + extra + validation}) != 116
            or max(len(row["sequence"]) for row in extra) != 3995
            or base["pair_features"] != "local_helix_context_v1"
            or base["learning_rate"] != 0.001 or base["cpu_threads"] != 2):
        raise ValueError("Sampled long development inputs differ")
    config = {**base, "training_max_length": 4999}
    return old, extra, validation, config


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    old, extra, validation, config = inputs()
    run = ROOT / "results/sampled_long_development_protocol_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "old_train.json", old)
    atomic_json(run / "extra_train.json", extra)
    atomic_json(run / "validation.json", validation)
    atomic_json(run / "config.json", config)
    atomic_json(run / "policy.json", {
        "schema_version": 1, "stage": "matched_sampled_long_development",
        "seeds": list(SEEDS), "arms": list(ARMS), "epochs": 10,
        "max_negatives": 8192, "negatives_per_positive": 4,
        "negative_sample_seed": "fit_seed_plus_record_index",
        "checkpoint_selection": "fixed_final_epoch",
        "validation_used_during_training": False,
        "decoder": "bounded_exact_sparse_top16",
        "cohort_label_informed": True,
        "bpRNA_training_family_lineage_complete": False,
        "development_only": True, "independent_test_claim": False,
        "model_defaults_changed": False})
    manifest = {"run_dir": str(run),
                "source_sha256": {str(path): digest(path.read_bytes()) for path in
                                  (OLD_TRAIN, NEW_SOURCE, VALIDATION, BASE)},
                "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
                "code_sha256": {str(path): digest(path.read_bytes()) for path in CODE}}
    atomic_json(run / "manifest.json", manifest)
    audit_protocol(run / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen sampled long development comparison:", run / "manifest.json")


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    if manifest != json.loads((run / "manifest.json").read_text()):
        raise ValueError("Sampled-long manifest changed")
    if set(manifest["snapshot_sha256"]) != {
            "old_train.json", "extra_train.json", "validation.json", "config.json", "policy.json"}:
        raise ValueError("Sampled-long snapshot inventory changed")
    for name, sha in manifest["snapshot_sha256"].items():
        if digest((run / name).read_bytes()) != sha:
            raise ValueError("Sampled-long snapshot changed")
    for name, sha in manifest["code_sha256"].items():
        if digest(Path(name).read_bytes()) != sha:
            raise ValueError("Sampled-long execution code changed")
    for name, sha in manifest["source_sha256"].items():
        if digest(Path(name).read_bytes()) != sha:
            raise ValueError("Sampled-long source changed")
    old, extra, validation, config = inputs()
    if (old != json.loads((run / "old_train.json").read_text())
            or extra != json.loads((run / "extra_train.json").read_text())
            or validation != json.loads((run / "validation.json").read_text())
            or config != json.loads((run / "config.json").read_text())):
        raise ValueError("Sampled-long frozen inputs changed")
    policy = json.loads((run / "policy.json").read_text())
    if (policy["seeds"] != list(SEEDS) or policy["arms"] != list(ARMS)
            or policy["epochs"] != 10 or policy["max_negatives"] != 8192
            or policy["negatives_per_positive"] != 4
            or policy["validation_used_during_training"] is not False
            or policy["checkpoint_selection"] != "fixed_final_epoch"
            or policy["independent_test_claim"] is not False):
        raise ValueError("Sampled-long policy changed")
    return manifest, old, extra, validation, config


def fit_one(train, validation, config, seed, run):
    import torch

    torch.set_num_threads(config["cpu_threads"])
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    rng = random.Random(seed)
    model = make_helix_model({**config, "seed": seed})
    initial = copy.deepcopy(model.state_dict())
    torch.save(initial, run / "initial_model.pt")
    samples = [sampled_pair_supervision(row, seed=seed + index,
                                         max_negatives=8192, negatives_per_positive=4)
               for index, row in enumerate(train)]
    positive = sum(int(labels.sum()) for _, labels, _ in samples)
    negative = sum(len(labels) - int(labels.sum()) for _, labels, _ in samples)
    if not positive or not negative or any(not len(labels) for _, labels, _ in samples):
        raise ValueError("Sampled-long training classes differ")
    loss_fn = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(negative / positive))
    optimizer = torch.optim.Adam(model.parameters(), lr=config["learning_rate"])
    history = []
    started = monotonic()
    for epoch in range(1, 11):
        order = list(range(len(train)))
        rng.shuffle(order)
        losses = []
        model.train()
        for index in order:
            edges, labels, _ = samples[index]
            optimizer.zero_grad(set_to_none=True)
            logits = model(tokens(train[index]["sequence"]), edges)
            loss = loss_fn(logits, labels)
            if not bool(torch.isfinite(loss)):
                raise ValueError("Nonfinite sampled-long training loss")
            loss.backward()
            optimizer.step()
            losses.append(loss.item())
        row = {"epoch": epoch, "mean_train_loss": sum(losses) / len(losses)}
        history.append(row)
        print(run.name, "epoch", epoch, "loss", row["mean_train_loss"], flush=True)
    training_seconds = monotonic() - started
    torch.save(model.state_dict(), run / "final_model.pt")
    model.eval()
    with torch.inference_mode():
        rows = long_predictions(model, validation, run.name, config)
    f1, scored = score_predictions(rows, validation)
    atomic_json(run / "predictions.json", rows)
    return {"seed": seed, "train_records": len(train),
            "train_max_length_nt": max(len(row["sequence"]) for row in train),
            "sampled_positive_pairs": positive, "sampled_negative_pairs": negative,
            "unsupported_train_gold_pairs": sum(item[2] for item in samples),
            "positive_weight": negative / positive,
            "history": history, "training_seconds": training_seconds,
            "validation_mean_pair_f1": f1,
            "validation_scores": [{"id": record["id"], "family_id": record["family_id"],
                                   "length_nt": len(record["sequence"]), **score}
                                  for record, score in zip(validation, scored, strict=True)],
            **aggregate(scored, validation),
            "checkpoint_sha256": {
                name: digest((run / name).read_bytes())
                for name in ("initial_model.pt", "final_model.pt")},
            "predictions_sha256": digest((run / "predictions.json").read_bytes()),
            "checkpoint_selection": "fixed_final_epoch",
            "independent_test_claim": False}


def execute():
    import torch

    protocol, old, extra, validation, config = audit_protocol(PROTOCOL)
    run = ROOT / "results/sampled_long_development_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "protocol.json", protocol)
    components = {}
    for seed in SEEDS:
        initial_states = {}
        for arm in ARMS:
            component = run / f"{arm}_seed{seed}"
            component.mkdir()
            train = old if arm == "control_88" else old + extra
            events = [record_exposure(component, "training_started", train),
                      record_exposure(component, "validation_started", validation)]
            metrics = fit_one(train, validation, config, seed, component)
            metrics.update(arm=arm, run_dir=str(component), exposure_events=events)
            atomic_json(component / "summary.json", metrics)
            components[f"{arm}_seed{seed}"] = metrics
            initial_states[arm] = torch.load(component / "initial_model.pt",
                                             map_location="cpu", weights_only=True)
        if not all(torch.equal(value, initial_states["extended_105"][name])
                   for name, value in initial_states["control_88"].items()):
            raise ValueError("Matched arms started from different weights")
        atomic_json(run / "progress.json", {"completed_seeds": seed,
                                             "components": sorted(components)})
    differences = {str(seed): components[f"extended_105_seed{seed}"]["validation_mean_pair_f1"]
                   - components[f"control_88_seed{seed}"]["validation_mean_pair_f1"]
                   for seed in SEEDS}
    summary = {"complete": True, "run_dir": str(run),
               "component_paths": {name: value["run_dir"] for name, value in components.items()},
               "paired_f1_differences": differences,
               "mean_paired_f1_difference": sum(differences.values()) / len(differences),
               "matched_initial_weights": True,
               "cohort_label_informed": True, "development_only": True,
               "bpRNA_training_family_lineage_complete": False,
               "independent_test_claim": False, "model_defaults_changed": False}
    atomic_json(run / "summary.json", summary)
    print("Sampled long matched development:", run / "summary.json")
    print("Paired differences:", differences)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--verify-protocol", type=Path)
    args = parser.parse_args()
    if args.freeze:
        freeze()
    elif args.run:
        execute()
    else:
        audit_protocol(args.verify_protocol)
        print("Sampled long development protocol replay passed")


if __name__ == "__main__":
    main()
