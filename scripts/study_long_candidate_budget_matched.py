#!/usr/bin/env python3
"""Frozen candidate-budget comparison across all matched sampled-long fits."""

import argparse
import json
from pathlib import Path
import resource
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.global_sparse_pairs import sparse_candidates  # noqa: E402
from rnastable.helix_pairs import make_helix_model  # noqa: E402
from rnastable.long_exact_sparse_pairs import decode_long_exact_sparse  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.pair_reference import validate_pairs  # noqa: E402
from rnastable.pair_set_training import score_predictions  # noqa: E402
from rnastable.reference import digest  # noqa: E402

SOURCE = ROOT / "results/sampled_long_development_runs/20261017T034847.147062Z"
COHORT = ROOT / "results/long_validation_coverage_runs/20261017T033935.363253Z/selection.json"
CONFIG = ROOT / "results/sampled_long_development_protocol_runs/20261017T034843.520152Z/config.json"
PROTOCOL = ROOT / "results/long_candidate_budget_matched_protocol.json"
SEEDS = (7, 1729, 20261015)
ARMS = ("control_88", "extended_105")
BUDGETS = (16, 32, 64)
CODE = [Path(__file__), *(ROOT / "src/rnastable" / name for name in (
    "global_sparse_pairs.py", "helix_pairs.py", "context_pairs.py",
    "long_exact_sparse_pairs.py", "pair_reference.py", "pair_set_training.py",
    "scoring.py", "structure_model.py"))]
CANONICAL = {"AU", "UA", "CG", "GC", "GU", "UG"}


def components():
    return {f"{arm}_seed{seed}": SOURCE / f"{arm}_seed{seed}"
            for seed in SEEDS for arm in ARMS}


def sources():
    paths = [COHORT, CONFIG, SOURCE / "summary.json"]
    for folder in components().values():
        paths.extend((folder / "final_model.pt", folder / "predictions.json", folder / "summary.json"))
    return paths


def policy():
    return {"arms": list(ARMS), "seeds": list(SEEDS), "budgets": list(BUDGETS),
            "checkpoint": "fixed_final_epoch", "decoder": "bounded_exact_sparse",
            "cohort_label_informed": True, "development_only": True,
            "independent_test_claim": False, "model_defaults_changed": False}


def audit(path):
    manifest = json.loads(Path(path).read_text())
    folder = Path(manifest["run_dir"])
    if manifest != json.loads((folder / "manifest.json").read_text()) or manifest["policy"] != policy():
        raise ValueError("Matched budget manifest or policy changed")
    for group in ("source_sha256", "code_sha256"):
        for name, sha in manifest[group].items():
            if digest(Path(name).read_bytes()) != sha:
                raise ValueError(f"Matched budget {group} changed: {name}")
    records = json.loads(COHORT.read_text())["selected"]
    config = json.loads(CONFIG.read_text())
    if (len(records) != 11 or config["top_k"] != 16 or config["cpu_threads"] != 2
            or max(len(r["sequence"]) for r in records) != 3100):
        raise ValueError("Matched budget input inventory changed")
    for folder in components().values():
        baseline = json.loads((folder / "predictions.json").read_text())
        summary = json.loads((folder / "summary.json").read_text())
        if (len(baseline) != 11 or summary["checkpoint_selection"] != "fixed_final_epoch"
                or summary["train_records"] not in (88, 105)):
            raise ValueError("Matched budget component inventory changed")
    return manifest, records, config


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    folder = ROOT / "results/long_candidate_budget_matched_protocol_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {"run_dir": str(folder), "policy": policy(),
                "source_sha256": {str(p): digest(p.read_bytes()) for p in sources()},
                "code_sha256": {str(p): digest(p.read_bytes()) for p in CODE}}
    atomic_json(folder / "manifest.json", manifest)
    audit(folder / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen matched candidate budgets:", folder / "manifest.json")


def evaluate_component(model, records, config, name):
    import numpy as np

    predictions = {str(k): [] for k in BUDGETS}
    diagnostics = {str(k): [] for k in BUDGETS}
    for record in records:
        sequence = record["sequence"]
        started = monotonic()
        candidates = sparse_candidates(model, sequence, 64, config["block_size"])
        scoring_seconds = monotonic() - started
        gold = validate_pairs(record["pairs"], len(sequence))
        legal = {(i, j) for i, j in gold if j - i >= 4 and sequence[i] + sequence[j] in CANONICAL}
        rank = np.zeros(len(sequence), dtype=np.int32)
        for budget in BUDGETS:
            indices = []
            for index, (_, right) in enumerate(candidates["pairs"]):
                if rank[right] < budget:
                    indices.append(index)
                rank[right] += 1
            rank.fill(0)
            pairs, scores = candidates["pairs"][indices], candidates["scores"][indices]
            started = monotonic()
            decoded = decode_long_exact_sparse(sequence, pairs, scores)
            retained = set(map(tuple, pairs.tolist()))
            predictions[str(budget)].append({
                "id": record["id"], "sequence": sequence, "method": name,
                "status": "ok", "structure": decoded["structure"]})
            diagnostics[str(budget)].append({
                "id": record["id"], "family_id": record["family_id"],
                "length_nt": len(sequence), "gold_pairs": len(gold),
                "legal_gold_pairs": len(legal), "candidate_count": len(retained),
                "legal_gold_in_candidates": len(legal & retained),
                "scoring_seconds": scoring_seconds, "decode_seconds": monotonic() - started,
                "candidate_array_bytes": pairs.nbytes + scores.nbytes,
                "dp_array_bytes": decoded["dp_array_bytes"]})
    baseline = json.loads((components()[name] / "predictions.json").read_text())
    if [r["structure"] for r in predictions["16"]] != [r["structure"] for r in baseline]:
        raise ValueError(f"{name}: top-16 structures differ from frozen predictions")
    summaries = {}
    for budget in BUDGETS:
        key = str(budget)
        mean, scored = score_predictions(predictions[key], records)
        for row, score in zip(diagnostics[key], scored, strict=True):
            row.update(score)
        legal = sum(row["legal_gold_pairs"] for row in diagnostics[key])
        hit = sum(row["legal_gold_in_candidates"] for row in diagnostics[key])
        summaries[key] = {
            "mean_record_pair_f1": mean,
            "weighted_legal_gold_candidate_recall": hit / legal,
            "legal_gold_pairs": legal, "legal_gold_in_candidates": hit,
            "total_candidates": sum(row["candidate_count"] for row in diagnostics[key]),
            "total_decode_seconds": sum(row["decode_seconds"] for row in diagnostics[key]),
            "rows": diagnostics[key]}
    return predictions, summaries


def execute():
    import torch

    manifest, records, config = audit(PROTOCOL)
    torch.set_num_threads(config["cpu_threads"])
    folder = ROOT / "results/long_candidate_budget_matched_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    atomic_json(folder / "protocol.json", manifest)
    summaries = {}
    for name, component in components().items():
        model = make_helix_model(config)
        model.load_state_dict(torch.load(component / "final_model.pt", map_location="cpu", weights_only=True))
        model.eval()
        predictions, budgets = evaluate_component(model, records, config, name)
        part = folder / name
        part.mkdir()
        atomic_json(part / "predictions.json", predictions)
        atomic_json(part / "summary.json", {"name": name, "budgets": budgets,
                                            "top16_matches_frozen_predictions": True,
                                            "predictions_sha256": digest((part / "predictions.json").read_bytes())})
        summaries[name] = {key: {k: v for k, v in value.items() if k != "rows"}
                           for key, value in budgets.items()}
        print(name, {key: round(value["mean_record_pair_f1"], 4)
                     for key, value in budgets.items()}, flush=True)
    paired = {}
    for seed in SEEDS:
        paired[str(seed)] = {str(k): summaries[f"extended_105_seed{seed}"][str(k)]["mean_record_pair_f1"]
                             - summaries[f"control_88_seed{seed}"][str(k)]["mean_record_pair_f1"]
                             for k in BUDGETS}
    result = {"complete": True, "run_dir": str(folder), "component_summaries": summaries,
              "paired_extended_minus_control_f1": paired,
              "peak_process_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              **policy()}
    atomic_json(folder / "summary.json", result)
    print("Matched candidate budget study:", folder / "summary.json")


def verify_run(path):
    folder = Path(path).resolve().parent
    summary = json.loads(Path(path).read_text())
    manifest, records, _ = audit(folder / "protocol.json")
    if (summary["run_dir"] != str(folder) or summary["complete"] is not True
            or any(summary[k] != v for k, v in manifest["policy"].items())
            or set(summary["component_summaries"]) != set(components())):
        raise ValueError("Matched candidate run inventory changed")
    for name, component in components().items():
        part = folder / name
        result = json.loads((part / "summary.json").read_text())
        predictions = json.loads((part / "predictions.json").read_text())
        baseline = json.loads((component / "predictions.json").read_text())
        if (result["name"] != name or not result["top16_matches_frozen_predictions"]
                or result["predictions_sha256"] != digest((part / "predictions.json").read_bytes())
                or [r["structure"] for r in predictions["16"]] != [r["structure"] for r in baseline]):
            raise ValueError(f"{name}: prediction inventory changed")
        for budget in BUDGETS:
            key = str(budget)
            item = result["budgets"][key]
            rows = item["rows"]
            mean, scored = score_predictions(predictions[key], records)
            if len(rows) != 11 or abs(mean - item["mean_record_pair_f1"]) > 1e-12:
                raise ValueError(f"{name}: F1 changed")
            for row, score, record in zip(rows, scored, records, strict=True):
                if row["id"] != record["id"] or any(row[k] != v for k, v in score.items()):
                    raise ValueError(f"{name}: record score changed")
            legal = sum(row["legal_gold_pairs"] for row in rows)
            hit = sum(row["legal_gold_in_candidates"] for row in rows)
            if (item["legal_gold_pairs"] != legal or item["legal_gold_in_candidates"] != hit
                    or item["total_candidates"] != sum(row["candidate_count"] for row in rows)
                    or abs(item["weighted_legal_gold_candidate_recall"] - hit / legal) > 1e-12
                    or summary["component_summaries"][name][key] != {k: v for k, v in item.items() if k != "rows"}):
                raise ValueError(f"{name}: aggregate changed")
    for seed in SEEDS:
        for budget in BUDGETS:
            key = str(budget)
            difference = (summary["component_summaries"][f"extended_105_seed{seed}"][key]["mean_record_pair_f1"]
                          - summary["component_summaries"][f"control_88_seed{seed}"][key]["mean_record_pair_f1"])
            if abs(summary["paired_extended_minus_control_f1"][str(seed)][key] - difference) > 1e-12:
                raise ValueError("Paired F1 changed")
    print("Matched candidate budget run replay passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--verify-protocol", type=Path)
    mode.add_argument("--verify-run", type=Path)
    args = parser.parse_args()
    if args.freeze:
        freeze()
    elif args.run:
        execute()
    elif args.verify_run:
        verify_run(args.verify_run)
    else:
        audit(args.verify_protocol)
        print("Matched candidate budget protocol replay passed")


if __name__ == "__main__":
    main()
