#!/usr/bin/env python3
"""Frozen matched pool-random/hard-mixture study using training-only BCE teachers."""

import argparse
import copy
import json
from pathlib import Path
import random
import resource
import sys
from time import monotonic

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.artifacts import timestamp
from rnastable.exposures import exposure_records, read_exposure, record_exposure
from rnastable.global_sparse_pairs import sparse_candidates
from rnastable.hard_negative_supervision import select_training_pairs
from rnastable.helix_pairs import make_helix_model
from rnastable.native_journal import atomic_json
from rnastable.reference import digest
from rnastable.sampled_pair_supervision import sampled_pair_supervision
from rnastable.structure_model import tokens
from evaluate_long_length_checkpoints_v3 import long_predictions
from run_under3000_development import audit as audit_baseline, verify as verify_baseline
from study_under3000_endpoint_ranking import BASE, BASE_PROTOCOL, SEEDS, cohort_scores

ARMS = ("pool_random", "hard_mixture")


def policy():
    return {"length_nt": [1, 2999], "train_records": 103, "seeds": list(SEEDS), "arms": list(ARMS),
            "teacher": "matching_seed_frozen_103_record_BCE_fixed_final_checkpoint",
            "teacher_pool": "union_original_uniform_negatives_and_positive_logit_top8_per_right_endpoint_minus_gold",
            "mining_schedule": "once_before_student_training", "reserved_uniform_fraction": 0.5,
            "remaining_negative_selection": {"pool_random": "uniform_without_replacement", "hard_mixture": "teacher_logit_descending_then_coordinates"},
            "negative_budget": "exactly_original_uniform_sample_count_per_record", "loss": "BCE_only",
            "epochs": 10, "checkpoint": "fixed_final_epoch", "decoder": "exact_sparse_top32",
            "teacher_compute_shared_between_new_arms": True, "total_compute_equal_to_historical_BCE": False,
            "validation_used_for_mining_or_training": False, "development_only": True,
            "independent_test_claim": False, "model_defaults_changed": False, "stage3_ready": False}


def freeze():
    import torch

    verify_baseline(BASE / "summary.json")
    baseline, trains, validation, config = audit_baseline(BASE_PROTOCOL)
    folder = ROOT / "results/under3000_hard_negative_protocol_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    for name, value in (("train.json", trains["extended_103"]), ("validation.json", validation), ("config.json", config)):
        atomic_json(folder / name, value)
    source = [BASE_PROTOCOL, BASE / "summary.json", *map(Path, baseline["source_sha256"])]
    for seed in SEEDS:
        source += [BASE / f"extended_103_seed{seed}" / name for name in ("initial_model.pt", "final_model.pt", "summary.json", "predictions.json")]
    code = [*map(Path, baseline["code_sha256"]), ROOT / "scripts/run_under3000_development.py",
            ROOT / "scripts/study_under3000_endpoint_ranking.py", ROOT / "src/rnastable/endpoint_ranking.py",
            ROOT / "src/rnastable/hard_negative_supervision.py", Path(__file__).resolve()]
    manifest = {"run_dir": str(folder), "policy": policy(), "torch_version": torch.__version__,
                "source_sha256": {str(p): digest(p.read_bytes()) for p in source},
                "code_sha256": {str(p): digest(p.read_bytes()) for p in code},
                "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in folder.iterdir()}}
    atomic_json(folder / "manifest.json", manifest)
    print(folder / "manifest.json")


def audit(path):
    import torch

    manifest = json.loads(Path(path).read_text())
    folder = Path(manifest["run_dir"])
    if (manifest != json.loads((folder / "manifest.json").read_text()) or manifest["policy"] != policy()
            or manifest["torch_version"] != torch.__version__):
        raise ValueError("Hard-negative protocol differs")
    for group in ("source_sha256", "code_sha256"):
        for name, sha in manifest[group].items():
            if digest(Path(name).read_bytes()) != sha:
                raise ValueError("Hard-negative input changed: " + name)
    for name, sha in manifest["snapshot_sha256"].items():
        if digest((folder / name).read_bytes()) != sha:
            raise ValueError("Hard-negative snapshot differs")
    _, trains, validation, config = audit_baseline(BASE_PROTOCOL)
    train = trains["extended_103"]
    for name, value in (("train.json", train), ("validation.json", validation), ("config.json", config)):
        if json.loads((folder / name).read_text()) != value:
            raise ValueError("Hard-negative data differs from scoped baseline")
    if any(not 1 <= len(r["sequence"]) < 3000 for r in train + validation["long"] + validation["short"]):
        raise ValueError("Hard-negative experiment exceeds active scope")
    return manifest, train, validation, config


def teacher_pool(model, record, seed, config):
    import torch

    indices, labels, _ = sampled_pair_supervision(record, seed=seed, max_negatives=8192, negatives_per_positive=4)
    mined = sparse_candidates(model, record["sequence"], top_k=8, block_size=config["block_size"])
    positive = set(map(tuple, indices[labels.bool()].tolist()))
    uniform = set(map(tuple, indices[~labels.bool()].tolist()))
    pairs = np.array(sorted((uniform | set(map(tuple, mined["pairs"].tolist()))) - positive), dtype=np.int64).reshape(-1, 2)
    with torch.inference_mode():
        scores = model(tokens(record["sequence"]), torch.tensor(pairs, dtype=torch.long)).numpy().copy()
    return {"base_pairs": indices.numpy(), "base_labels": labels.numpy(), "pool_pairs": pairs, "pool_scores": scores}


def teacher(seed, config):
    import torch

    model = make_helix_model({**config, "seed": seed})
    model.load_state_dict(torch.load(BASE / f"extended_103_seed{seed}" / "final_model.pt", map_location="cpu", weights_only=True))
    model.eval()
    return model


def selected(record, pool, seed, arm):
    return select_training_pairs(record["sequence"], pool["base_pairs"], pool["base_labels"],
                                 pool["pool_pairs"], pool["pool_scores"], seed=seed, mode=arm)


def sample_digest(samples):
    return digest(b"".join(edges.numpy().tobytes() + labels.numpy().tobytes() for edges, labels, _ in samples))


def fit(train, validation, config, seed, folder, samples):
    import torch

    torch.manual_seed(seed)
    rng = random.Random(seed)
    model = make_helix_model({**config, "seed": seed})
    initial = copy.deepcopy(model.state_dict())
    previous = torch.load(BASE / f"extended_103_seed{seed}" / "initial_model.pt", map_location="cpu", weights_only=True)
    if any(not torch.equal(v, previous[k]) for k, v in initial.items()):
        raise ValueError("Student initial weights differ from baseline")
    torch.save(initial, folder / "initial_model.pt")
    positives = sum(int(labels.sum()) for _, labels, _ in samples)
    negatives = sum(len(labels) - int(labels.sum()) for _, labels, _ in samples)
    old = json.loads((BASE / f"extended_103_seed{seed}" / "summary.json").read_text())
    if positives != old["sampled_positive_pairs"] or negatives != old["sampled_negative_pairs"]:
        raise ValueError("Student pair-count budget differs from baseline")
    criterion = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(negatives / positives))
    optimizer = torch.optim.Adam(model.parameters(), lr=config["learning_rate"])
    history = []
    started = monotonic()
    for epoch in range(1, 11):
        order = list(range(len(train)))
        rng.shuffle(order)
        total = 0.0
        model.train()
        for i in order:
            edges, labels, _ = samples[i]
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(tokens(train[i]["sequence"]), edges), labels)
            if not bool(torch.isfinite(loss)):
                raise ValueError("Nonfinite hard-negative training loss")
            loss.backward()
            optimizer.step()
            total += loss.item()
        history.append({"epoch": epoch, "mean_train_loss": total / len(train)})
        print(folder.name, "epoch", epoch, "loss", round(total / len(train), 6), flush=True)
    training_seconds = monotonic() - started
    torch.save(model.state_dict(), folder / "final_model.pt")
    model.eval()
    with torch.inference_mode():
        predictions = long_predictions(model, validation["long"] + validation["short"], folder.name, config)
    atomic_json(folder / "predictions.json", predictions)
    return {"seed": seed, "history": history, "training_seconds": training_seconds,
            "positive_pairs": positives, "negative_pairs": negatives, "sample_sha256": sample_digest(samples),
            "sampling_details": [{"id": r["id"], **info} for r, (_, _, info) in zip(train, samples, strict=True)],
            "cohorts": cohort_scores(predictions, validation),
            "checkpoint_sha256": {n: digest((folder / n).read_bytes()) for n in ("initial_model.pt", "final_model.pt")},
            "predictions_sha256": digest((folder / "predictions.json").read_bytes())}


def summarize(parts):
    previous = json.loads((BASE / "summary.json").read_text())["components"]
    result = {}
    for cohort in ("long", "short"):
        values = {arm: [parts[f"{arm}_seed{s}"]["cohorts"][cohort]["mean_pair_f1"] for s in SEEDS] for arm in ARMS}
        base = [previous[f"extended_103_seed{s}"][cohort]["mean_pair_f1"] for s in SEEDS]
        result[cohort] = {"historical_BCE_mean_f1": sum(base) / 3,
                          "arm_mean_f1": {arm: sum(v) / 3 for arm, v in values.items()},
                          "hard_minus_random_per_seed": {str(s): values["hard_mixture"][i] - values["pool_random"][i] for i, s in enumerate(SEEDS)}}
    return {"complete": True, "policy": policy(), "comparisons": result,
            "peak_process_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def run(path):
    import torch

    manifest, train, validation, config = audit(path)
    torch.set_num_threads(config["cpu_threads"])
    torch.use_deterministic_algorithms(True)
    folder = ROOT / "results/under3000_hard_negative_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    atomic_json(folder / "protocol.json", manifest)
    parts = {}
    for seed in SEEDS:
        pool_dir = folder / f"mining_seed{seed}"
        pool_dir.mkdir()
        event = record_exposure(pool_dir, "training_started", train)
        model = teacher(seed, config)
        started = monotonic()
        pools = []
        for i, record in enumerate(train):
            pool = teacher_pool(model, record, seed + i, config)
            np.savez_compressed(pool_dir / f"{i:03d}.npz", **pool)
            pools.append(pool)
        atomic_json(pool_dir / "manifest.json", {"teacher_seed": seed, "mining_seconds": monotonic() - started,
                    "exposure_event": event, "files_sha256": {p.name: digest(p.read_bytes()) for p in pool_dir.glob('*.npz')}})
        samples_by_arm = {arm: [selected(r, pool, seed + i, arm) for i, (r, pool) in enumerate(zip(train, pools, strict=True))] for arm in ARMS}
        for left, right in zip(samples_by_arm["pool_random"], samples_by_arm["hard_mixture"], strict=True):
            if right[2]["mean_selected_pool_logit"] is not None and right[2]["mean_selected_pool_logit"] < left[2]["mean_selected_pool_logit"] - 1e-8:
                raise ValueError("Hard selection is not at least as high-scoring as matched random selection")
        for arm in ARMS:
            component = folder / f"{arm}_seed{seed}"
            component.mkdir()
            events = [record_exposure(component, "training_started", train), record_exposure(component, "validation_started", validation["long"] + validation["short"])]
            result = fit(train, validation, config, seed, component, samples_by_arm[arm])
            result["exposure_events"] = events
            atomic_json(component / "summary.json", result)
            parts[component.name] = result
            atomic_json(folder / "progress.json", {"completed_components": sorted(parts)})
    summary = summarize(parts)
    atomic_json(folder / "summary.json", summary)
    print(folder / "summary.json")
    print(summary["comparisons"])


def verify_event(event, folder, stage, records):
    if digest(Path(event["path"]).read_bytes()) != event["sha256"]:
        raise ValueError("Hard-negative exposure bytes differ")
    saved = read_exposure(event["path"])
    if saved["stage"] != stage or saved["records"] != exposure_records(records, str(folder) + " " + stage):
        raise ValueError("Hard-negative exposure identity differs")


def verify(path):
    import torch

    folder = Path(path).resolve().parent
    _, train, validation, config = audit(folder / "protocol.json")
    torch.set_num_threads(config["cpu_threads"])
    torch.use_deterministic_algorithms(True)
    parts = {}
    for seed in SEEDS:
        pool_dir = folder / f"mining_seed{seed}"
        saved = json.loads((pool_dir / "manifest.json").read_text())
        verify_event(saved["exposure_event"], pool_dir, "training_started", train)
        model = teacher(seed, config)
        pools = []
        for i, record in enumerate(train):
            name = f"{i:03d}.npz"
            if digest((pool_dir / name).read_bytes()) != saved["files_sha256"][name]:
                raise ValueError("Teacher pool archive differs")
            with np.load(pool_dir / name, allow_pickle=False) as archive:
                pool = dict(archive)
            replay = teacher_pool(model, record, seed + i, config)
            if set(pool) != set(replay) or any(not np.array_equal(pool[k], replay[k]) for k in pool):
                raise ValueError("Training-only teacher mining replay differs")
            pools.append(pool)
        for arm in ARMS:
            component = folder / f"{arm}_seed{seed}"
            result = json.loads((component / "summary.json").read_text())
            samples = [selected(r, pool, seed + i, arm) for i, (r, pool) in enumerate(zip(train, pools, strict=True))]
            if sample_digest(samples) != result["sample_sha256"] or result["sampling_details"] != [{"id": r["id"], **info} for r, (_, _, info) in zip(train, samples, strict=True)]:
                raise ValueError("Student selection replay differs")
            for name, sha in result["checkpoint_sha256"].items():
                if digest((component / name).read_bytes()) != sha:
                    raise ValueError("Student checkpoint differs")
            initial = torch.load(component / "initial_model.pt", map_location="cpu", weights_only=True)
            baseline_initial = torch.load(BASE / f"extended_103_seed{seed}" / "initial_model.pt", map_location="cpu", weights_only=True)
            if any(not torch.equal(v, baseline_initial[k]) for k, v in initial.items()):
                raise ValueError("Student matched initialization differs")
            for event, stage, rows in zip(result["exposure_events"], ("training_started", "validation_started"), (train, validation["long"] + validation["short"]), strict=True):
                verify_event(event, component, stage, rows)
            student = make_helix_model({**config, "seed": seed})
            student.load_state_dict(torch.load(component / "final_model.pt", map_location="cpu", weights_only=True))
            student.eval()
            with torch.inference_mode():
                predictions = long_predictions(student, validation["long"] + validation["short"], component.name, config)
            if (digest((component / "predictions.json").read_bytes()) != result["predictions_sha256"]
                    or predictions != json.loads((component / "predictions.json").read_text())
                    or result["cohorts"] != cohort_scores(predictions, validation)):
                raise ValueError("Student inference or score replay differs")
            parts[component.name] = result
    expected = summarize(parts)
    saved = json.loads(Path(path).read_text())
    expected["peak_process_rss_kib"] = saved["peak_process_rss_kib"]
    if saved != expected:
        raise ValueError("Hard-negative aggregate replay differs")
    print("Teacher mining, sample selection, checkpoint inference and score replay passed (no retraining)")


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
