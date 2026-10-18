#!/usr/bin/env python3
"""Recompute descriptive hard-negative diagnostics from saved predictions."""

import argparse
import json
from pathlib import Path

from study_under3000_hard_negatives import BASE, BASE_PROTOCOL, ARMS, SEEDS, cohort_scores, digest
from run_under3000_development import audit


def compute(folder):
    _, _, validation, _ = audit(BASE_PROTOCOL)
    inputs = [folder / "summary.json"]
    results = {}
    for cohort in ("long", "short"):
        results[cohort] = {}
        for arm in ("historical_BCE", *ARMS):
            rows = []
            for seed in SEEDS:
                path = (BASE / f"extended_103_seed{seed}" / "predictions.json" if arm == "historical_BCE"
                        else folder / f"{arm}_seed{seed}" / "predictions.json")
                inputs.append(path)
                rows.extend(cohort_scores(json.loads(path.read_text()), validation)[cohort]["rows"])
            results[cohort][arm] = {"record_seed_rows": len(rows),
                                   **{k: sum(r[k] for r in rows) / len(rows) for k in
                                      ("pair_f1", "pair_precision", "pair_recall", "predicted_pairs")}}
    return {"run_dir": str(folder.resolve()), "development_only": True,
            "new_inference_performed": False, "metrics": results,
            "driver_sha256": digest(Path(__file__).read_bytes()),
            "inputs_sha256": {str(p.resolve()): digest(p.read_bytes()) for p in inputs}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run", type=Path)
    mode.add_argument("--verify-run", type=Path)
    args = parser.parse_args()
    folder = (args.run or args.verify_run).resolve()
    result = compute(folder)
    path = folder / "descriptive_diagnostics.json"
    if args.run:
        with path.open("x") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
        print(path)
    elif result != json.loads(path.read_text()):
        raise ValueError("Hard-negative descriptive diagnostics differ")
    else:
        print("Hard-negative descriptive diagnostics replay passed")


if __name__ == "__main__":
    main()
