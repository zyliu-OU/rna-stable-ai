#!/usr/bin/env python3
"""Recompute descriptive precision/recall from saved ranking-study predictions."""

import argparse
import json
from pathlib import Path

from study_under3000_endpoint_ranking import cohort_scores, BASE, BASE_PROTOCOL, digest
from run_under3000_development import audit


def compute(folder):
    _, _, validation, _ = audit(BASE_PROTOCOL)
    result = {"source_run": str(folder.resolve()),
              "summary_sha256": digest((folder / "summary.json").read_bytes()),
              "interpretation": "Descriptive reused-development prediction diagnostics; no inference or selection performed",
              "cohorts": {}}
    for cohort in ("long", "short"):
        result["cohorts"][cohort] = {}
        for arm in ("baseline", "ranking"):
            rows = []
            for seed in (7, 1729, 20261015):
                if arm == "baseline":
                    predictions = json.loads((BASE / f"extended_103_seed{seed}" / "predictions.json").read_text())
                else:
                    predictions = json.loads((folder / f"ranking_seed{seed}" / "predictions.json").read_text())
                rows.extend(cohort_scores(predictions, validation)[cohort]["rows"])
            result["cohorts"][cohort][arm] = {
                "record_seed_rows": len(rows),
                **{key: sum(r[key] for r in rows) / len(rows)
                   for key in ("pair_precision", "pair_recall", "predicted_pairs")}}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-run", required=True, type=Path)
    folder = parser.parse_args().verify_run.resolve()
    if json.loads((folder / "descriptive_diagnostics.json").read_text()) != compute(folder):
        raise ValueError("Descriptive ranking diagnostics differ")
    print("Descriptive ranking precision/recall replay passed")


if __name__ == "__main__":
    main()
