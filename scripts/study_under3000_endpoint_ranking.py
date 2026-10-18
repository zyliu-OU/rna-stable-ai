#!/usr/bin/env python3
"""Fixed three-seed endpoint-ranking study on the scoped 103-record training arm."""

import argparse
import copy
import json
from pathlib import Path
import random
import resource
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.artifacts import timestamp
from rnastable.endpoint_ranking import endpoint_ranking_loss
from rnastable.exposures import read_exposure, record_exposure
from rnastable.helix_pairs import make_helix_model
from rnastable.native_journal import atomic_json
from rnastable.pair_set_training import score_predictions
from rnastable.reference import digest
from rnastable.sampled_pair_supervision import sampled_pair_supervision
from rnastable.structure_model import tokens
from evaluate_long_length_checkpoints_v3 import long_predictions
from run_under3000_development import audit as audit_baseline, verify as verify_baseline

BASE = ROOT / "results/under3000_development_runs/20261018T223810.974436Z"
BASE_PROTOCOL = ROOT / "results/under3000_development_protocol_runs/20261018T223802.654756Z/manifest.json"
SEEDS = (7, 1729, 20261015)


def policy():
    return {"active_length_nt": [1, 2999], "training_arm": "extended_103", "seeds": list(SEEDS),
            "epochs": 10, "auxiliary_weight": 0.25, "ranking_margin": 1.0,
            "negative_sampling": "same_frozen_uniform_sample_as_baseline",
            "hard_competitor": "maximum_sampled_negative_logit_at_either_positive_endpoint",
            "checkpoint_selection": "fixed_final_epoch", "decoder": "exact_sparse_top32",
            "validation_used_during_training": False, "development_only": True,
            "independent_test_claim": False, "model_defaults_changed": False,
            "stage3_ready": False}


def freeze():
    import torch

    verify_baseline(BASE / "summary.json")
    baseline, train, validation, config = audit_baseline(BASE_PROTOCOL)
    folder = ROOT / "results/under3000_endpoint_ranking_protocol_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    atomic_json(folder / "train.json", train["extended_103"])
    atomic_json(folder / "validation.json", validation)
    atomic_json(folder / "config.json", config)
    paths = [BASE_PROTOCOL, BASE / "summary.json"]
    for seed in SEEDS:
        paths += [BASE / f"extended_103_seed{seed}" / name for name in
                  ("initial_model.pt", "final_model.pt", "summary.json", "predictions.json")]
    paths += [Path(p) for p in baseline["source_sha256"]]
    code = [Path(p) for p in baseline["code_sha256"]]
    code += [ROOT / "scripts/run_under3000_development.py", ROOT / "src/rnastable/endpoint_ranking.py", Path(__file__).resolve()]
    manifest = {"run_dir": str(folder), "policy": policy(), "torch_version": torch.__version__,
                "source_sha256": {str(p): digest(p.read_bytes()) for p in paths},
                "code_sha256": {str(p): digest(p.read_bytes()) for p in code},
                "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in folder.iterdir()}}
    atomic_json(folder / "manifest.json", manifest)
    print(folder / "manifest.json")


def audit(path):
    import torch

    manifest = json.loads(Path(path).read_text())
    folder = Path(manifest["run_dir"])
    if (manifest != json.loads((folder / "manifest.json").read_text())
            or manifest["policy"] != policy() or manifest["torch_version"] != torch.__version__):
        raise ValueError("Endpoint ranking protocol or runtime differs")
    for group in ("source_sha256", "code_sha256"):
        for name, sha in manifest[group].items():
            if digest(Path(name).read_bytes()) != sha:
                raise ValueError("Endpoint ranking source changed: " + name)
    for name, sha in manifest["snapshot_sha256"].items():
        if digest((folder / name).read_bytes()) != sha:
            raise ValueError("Endpoint ranking snapshot changed")
    _, trains, validation, config = audit_baseline(BASE_PROTOCOL)
    train = trains["extended_103"]
    if any(not 1 <= len(r["sequence"]) < 3000 for r in train + validation["long"] + validation["short"]):
        raise ValueError("Ranking study exceeds active scope")
    if any(json.loads((folder / name).read_text()) != value for name, value in
           (("train.json", train), ("validation.json", validation), ("config.json", config))):
        raise ValueError("Ranking dataset differs from frozen baseline")
    return manifest, train, validation, config


def cohort_scores(predictions, validation):
    offset = 0
    result = {}
    for name, cohort in validation.items():
        score, rows = score_predictions(predictions[offset:offset + len(cohort)], cohort)
        result[name] = {"n": len(cohort), "mean_pair_f1": score,
                        "rows": [{"id": r["id"], "family_id": r["family_id"],
                                  "length_nt": len(r["sequence"]), **s}
                                 for r, s in zip(cohort, rows, strict=True)]}
        offset += len(cohort)
    if offset != len(predictions):
        raise ValueError("Ranking validation inventory differs")
    return result


def fit(train, validation, config, seed, folder):
    import torch

    torch.set_num_threads(config["cpu_threads"])
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    rng = random.Random(seed)
    model = make_helix_model({**config, "seed": seed})
    torch.save(model.state_dict(), folder / "initial_model.pt")
    baseline_initial = torch.load(BASE / f"extended_103_seed{seed}" / "initial_model.pt", map_location="cpu", weights_only=True)
    if any(not torch.equal(v, baseline_initial[k]) for k, v in model.state_dict().items()):
        raise ValueError("Ranking initial weights differ from baseline")
    samples = [sampled_pair_supervision(r, seed=seed + i, max_negatives=8192, negatives_per_positive=4)
               for i, r in enumerate(train)]
    positives = sum(int(labels.sum()) for _, labels, _ in samples)
    negatives = sum(len(labels) - int(labels.sum()) for _, labels, _ in samples)
    if not positives or not negatives:
        raise ValueError("Ranking training requires both classes")
    bce = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(negatives / positives))
    optimizer = torch.optim.Adam(model.parameters(), lr=config["learning_rate"])
    history = []
    started = monotonic()
    for epoch in range(1, 11):
        order = list(range(len(train)))
        rng.shuffle(order)
        total = classification = ranking = 0.0
        ranked = gold = 0
        model.train()
        for i in order:
            indices, labels, _ = samples[i]
            optimizer.zero_grad(set_to_none=True)
            logits = model(tokens(train[i]["sequence"]), indices)
            base_loss = bce(logits, labels)
            rank_loss, counts = endpoint_ranking_loss(logits, indices, labels, len(train[i]["sequence"]), margin=1.0)
            loss = base_loss + 0.25 * rank_loss
            if not bool(torch.isfinite(loss)):
                raise ValueError("Nonfinite ranking objective")
            loss.backward()
            optimizer.step()
            total += loss.item()
            classification += base_loss.item()
            ranking += rank_loss.item()
            ranked += counts["ranked_pairs"]
            gold += counts["positive_pairs"]
        row = {"epoch": epoch, "mean_total_loss": total / len(train),
               "mean_bce_loss": classification / len(train), "mean_ranking_loss": ranking / len(train),
               "ranked_positive_pairs": ranked, "positive_pairs": gold}
        history.append(row)
        print(folder.name, "epoch", epoch, "loss", round(row["mean_total_loss"], 6), flush=True)
    training_seconds = monotonic() - started
    torch.save(model.state_dict(), folder / "final_model.pt")
    model.eval()
    with torch.inference_mode():
        predictions = long_predictions(model, validation["long"] + validation["short"], folder.name, config)
    atomic_json(folder / "predictions.json", predictions)
    return {"seed": seed, "training_records": len(train), "training_seconds": training_seconds,
            "positive_pairs": positives, "negative_pairs": negatives, "history": history,
            "cohorts": cohort_scores(predictions, validation),
            "checkpoint_sha256": {n: digest((folder / n).read_bytes()) for n in ("initial_model.pt", "final_model.pt")},
            "predictions_sha256": digest((folder / "predictions.json").read_bytes())}


def summary_for(components):
    baseline = json.loads((BASE / "summary.json").read_text())["components"]
    comparisons = {}
    for cohort in ("long", "short"):
        previous = [baseline[f"extended_103_seed{s}"][cohort]["mean_pair_f1"] for s in SEEDS]
        current = [components[str(s)]["cohorts"][cohort]["mean_pair_f1"] for s in SEEDS]
        comparisons[cohort] = {"baseline_mean_f1": sum(previous) / 3,
                               "ranking_mean_f1": sum(current) / 3,
                               "paired_differences": {str(s): b - a for s, a, b in zip(SEEDS, previous, current)},
                               "mean_difference": (sum(current) - sum(previous)) / 3}
    return {"complete": True, "policy": policy(), "comparisons": comparisons,
            "peak_process_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def run(path):
    manifest, train, validation, config = audit(path)
    folder = ROOT / "results/under3000_endpoint_ranking_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    atomic_json(folder / "protocol.json", manifest)
    components = {}
    for seed in SEEDS:
        component = folder / f"ranking_seed{seed}"
        component.mkdir()
        events = [record_exposure(component, "training_started", train),
                  record_exposure(component, "validation_started", validation["long"] + validation["short"])]
        result = fit(train, validation, config, seed, component)
        result["exposure_events"] = events
        atomic_json(component / "summary.json", result)
        components[str(seed)] = result
    summary = summary_for(components)
    atomic_json(folder / "summary.json", summary)
    print(folder / "summary.json")
    print(summary["comparisons"])


def verify(path):
    import torch

    folder = Path(path).resolve().parent
    manifest, train, validation, config = audit(folder / "protocol.json")
    torch.set_num_threads(config["cpu_threads"])
    torch.use_deterministic_algorithms(True)
    components = {}
    for seed in SEEDS:
        component = folder / f"ranking_seed{seed}"
        result = json.loads((component / "summary.json").read_text())
        for name, sha in result["checkpoint_sha256"].items():
            if digest((component / name).read_bytes()) != sha:
                raise ValueError("Ranking checkpoint changed")
        if digest((component / "predictions.json").read_bytes()) != result["predictions_sha256"]:
            raise ValueError("Ranking predictions changed")
        initial = torch.load(component / "initial_model.pt", map_location="cpu", weights_only=True)
        previous = torch.load(BASE / f"extended_103_seed{seed}" / "initial_model.pt", map_location="cpu", weights_only=True)
        if any(not torch.equal(v, previous[k]) for k, v in initial.items()):
            raise ValueError("Ranking initial match changed")
        for event, stage, records in zip(result["exposure_events"], ("training_started", "validation_started"),
                                         (train, validation["long"] + validation["short"]), strict=True):
            from rnastable.exposures import exposure_records
            if digest(Path(event["path"]).read_bytes()) != event["sha256"]:
                raise ValueError("Ranking exposure event changed")
            saved = read_exposure(event["path"])
            if saved["stage"] != stage or saved["records"] != exposure_records(records, str(component) + " " + stage):
                raise ValueError("Ranking exposure identity differs")
        model = make_helix_model({**config, "seed": seed})
        model.load_state_dict(torch.load(component / "final_model.pt", map_location="cpu", weights_only=True))
        model.eval()
        with torch.inference_mode():
            replay = long_predictions(model, validation["long"] + validation["short"], component.name, config)
        if replay != json.loads((component / "predictions.json").read_text()) or result["cohorts"] != cohort_scores(replay, validation):
            raise ValueError("Ranking inference or score replay differs")
        components[str(seed)] = result
    saved = json.loads(Path(path).read_text())
    expected = summary_for(components)
    expected["peak_process_rss_kib"] = saved["peak_process_rss_kib"]
    if saved != expected:
        raise ValueError("Ranking summary differs")
    print("Endpoint ranking checkpoint inference and score replay passed (no retraining)")


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
