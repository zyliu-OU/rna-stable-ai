#!/usr/bin/env python3
"""Frozen candidate-budget pilot on one sampled-long development checkpoint."""

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
ARM = SOURCE / "extended_105_seed1729"
CHECKPOINT = ARM / "final_model.pt"
BASELINE = ARM / "predictions.json"
PROTOCOL = ROOT / "results/long_candidate_budget_pilot_v2_protocol.json"
BUDGETS = (16, 32, 64)
CODE = [Path(__file__), *(ROOT / "src/rnastable" / name for name in (
    "global_sparse_pairs.py", "helix_pairs.py", "context_pairs.py",
    "long_exact_sparse_pairs.py", "pair_reference.py", "pair_set_training.py",
    "scoring.py", "structure_model.py"))]


def source_paths():
    return [COHORT, CONFIG, CHECKPOINT, BASELINE, ARM / "summary.json", SOURCE / "summary.json"]


def audit(path):
    manifest = json.loads(Path(path).read_text())
    folder = Path(manifest["run_dir"])
    if manifest != json.loads((folder / "manifest.json").read_text()):
        raise ValueError("Pilot manifest changed")
    for group in ("source_sha256", "code_sha256"):
        for name, sha in manifest[group].items():
            if digest(Path(name).read_bytes()) != sha:
                raise ValueError(f"Pilot {group} changed: {name}")
    if manifest["policy"] != {
        "checkpoint": "extended_105_seed1729_fixed_final_epoch",
        "budgets": list(BUDGETS), "decoder": "bounded_exact_sparse",
        "cohort_label_informed": True, "development_only": True,
        "independent_test_claim": False, "model_defaults_changed": False,
    }:
        raise ValueError("Pilot policy changed")
    records = json.loads(COHORT.read_text())["selected"]
    config = json.loads(CONFIG.read_text())
    baseline = json.loads(BASELINE.read_text())
    if (len(records) != 11 or len(baseline) != 11 or config["top_k"] != 16
            or config["cpu_threads"] != 2 or max(map(lambda r: len(r["sequence"]), records)) != 3100):
        raise ValueError("Pilot source inventory changed")
    return manifest, records, config, baseline


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    folder = ROOT / "results/long_candidate_budget_pilot_v2_protocol_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {
        "run_dir": str(folder),
        "policy": {"checkpoint": "extended_105_seed1729_fixed_final_epoch",
                   "budgets": list(BUDGETS), "decoder": "bounded_exact_sparse",
                   "cohort_label_informed": True, "development_only": True,
                   "independent_test_claim": False, "model_defaults_changed": False},
        "source_sha256": {str(p): digest(p.read_bytes()) for p in source_paths()},
        "code_sha256": {str(p): digest(p.read_bytes()) for p in CODE},
    }
    atomic_json(folder / "manifest.json", manifest)
    audit(folder / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen candidate-budget pilot:", folder / "manifest.json")


def execute():
    import numpy as np
    import torch

    manifest, records, config, baseline = audit(PROTOCOL)
    torch.set_num_threads(config["cpu_threads"])
    model = make_helix_model(config)
    model.load_state_dict(torch.load(CHECKPOINT, map_location="cpu", weights_only=True))
    model.eval()
    folder = ROOT / "results/long_candidate_budget_pilot_v2_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    atomic_json(folder / "protocol.json", manifest)
    predictions = {str(k): [] for k in BUDGETS}
    diagnostics = {str(k): [] for k in BUDGETS}
    for record in records:
        sequence = record["sequence"]
        started = monotonic()
        candidates = sparse_candidates(model, sequence, 64, config["block_size"])
        scoring_seconds = monotonic() - started
        gold = validate_pairs(record["pairs"], len(sequence))
        legal = {(i, j) for i, j in gold
                 if j - i >= 4 and sequence[i] + sequence[j] in {"AU", "UA", "CG", "GC", "GU", "UG"}}
        rank = np.zeros(len(sequence), dtype=np.int32)
        for budget in BUDGETS:
            indices = []
            for index, (_, right) in enumerate(candidates["pairs"]):
                if rank[right] < budget:
                    indices.append(index)
                rank[right] += 1
            rank.fill(0)
            pairs = candidates["pairs"][indices]
            scores = candidates["scores"][indices]
            started = monotonic()
            decoded = decode_long_exact_sparse(sequence, pairs, scores)
            decode_seconds = monotonic() - started
            retained = set(map(tuple, pairs.tolist()))
            row = {"id": record["id"], "sequence": sequence, "method": f"top{budget}",
                   "status": "ok", "structure": decoded["structure"]}
            predictions[str(budget)].append(row)
            diagnostics[str(budget)].append({
                "id": record["id"], "family_id": record["family_id"],
                "length_nt": len(sequence), "gold_pairs": len(gold),
                "legal_gold_pairs": len(legal), "candidate_count": len(retained),
                "legal_gold_in_candidates": len(legal & retained),
                "scoring_seconds": scoring_seconds, "decode_seconds": decode_seconds,
                "candidate_array_bytes": pairs.nbytes + scores.nbytes,
                "dp_array_bytes": decoded["dp_array_bytes"],
            })
        print(record["id"], "complete", flush=True)
    if [r["structure"] for r in predictions["16"]] != [r["structure"] for r in baseline]:
        raise ValueError("Top-16 pilot differs from frozen checkpoint predictions")
    summaries = {}
    for budget in BUDGETS:
        key = str(budget)
        mean_f1, scored = score_predictions(predictions[key], records)
        for row, score in zip(diagnostics[key], scored, strict=True):
            row.update(score)
        total_legal = sum(r["legal_gold_pairs"] for r in diagnostics[key])
        total_hit = sum(r["legal_gold_in_candidates"] for r in diagnostics[key])
        summaries[key] = {
            "mean_record_pair_f1": mean_f1,
            "weighted_legal_gold_candidate_recall": total_hit / total_legal,
            "legal_gold_pairs": total_legal, "legal_gold_in_candidates": total_hit,
            "total_candidates": sum(r["candidate_count"] for r in diagnostics[key]),
            "total_decode_seconds": sum(r["decode_seconds"] for r in diagnostics[key]),
            "rows": diagnostics[key],
        }
    atomic_json(folder / "predictions.json", predictions)
    result = {"complete": True, "run_dir": str(folder), "candidate_budgets": summaries,
              "top16_matches_frozen_predictions": True,
              "prediction_sha256": digest((folder / "predictions.json").read_bytes()),
              "peak_process_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              **manifest["policy"]}
    atomic_json(folder / "summary.json", result)
    print("Candidate-budget pilot:", folder / "summary.json")
    for key, row in summaries.items():
        print(key, "F1", row["mean_record_pair_f1"], "legal recall",
              row["weighted_legal_gold_candidate_recall"], flush=True)


def verify_run(path):
    folder = Path(path).resolve().parent
    summary = json.loads(Path(path).read_text())
    manifest, records, _, baseline = audit(folder / "protocol.json")
    predictions = json.loads((folder / "predictions.json").read_text())
    if (summary["run_dir"] != str(folder) or summary["complete"] is not True
            or summary["prediction_sha256"] != digest((folder / "predictions.json").read_bytes())
            or set(summary["candidate_budgets"]) != set(map(str, BUDGETS))
            or not summary["top16_matches_frozen_predictions"]
            or any(summary[key] != value for key, value in manifest["policy"].items())):
        raise ValueError("Candidate-budget run inventory changed")
    if [r["structure"] for r in predictions["16"]] != [r["structure"] for r in baseline]:
        raise ValueError("Frozen top-16 predictions changed")
    for budget in BUDGETS:
        key = str(budget)
        rows = summary["candidate_budgets"][key]["rows"]
        if len(rows) != len(records):
            raise ValueError("Candidate-budget record count changed")
        mean, scored = score_predictions(predictions[key], records)
        item = summary["candidate_budgets"][key]
        if abs(mean - item["mean_record_pair_f1"]) > 1e-12:
            raise ValueError("Candidate-budget score changed")
        for row, score, record in zip(rows, scored, records, strict=True):
            if (row["id"] != record["id"] or row["family_id"] != record["family_id"]
                    or any(row[name] != value for name, value in score.items())):
                raise ValueError("Candidate-budget row changed")
        legal = sum(row["legal_gold_pairs"] for row in rows)
        hit = sum(row["legal_gold_in_candidates"] for row in rows)
        if (item["legal_gold_pairs"] != legal or item["legal_gold_in_candidates"] != hit
                or item["total_candidates"] != sum(row["candidate_count"] for row in rows)
                or abs(item["weighted_legal_gold_candidate_recall"] - hit / legal) > 1e-12):
            raise ValueError("Candidate-budget aggregate changed")
    print("Candidate-budget pilot run replay passed")


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
        print("Candidate-budget pilot protocol replay passed")


if __name__ == "__main__":
    main()
