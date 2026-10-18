#!/usr/bin/env python3
"""Audit saved Stage 2 accuracy under the current scope without new inference."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.artifacts import timestamp
from rnastable.native_journal import atomic_json
from rnastable.project_scope import load_policy, DEFAULT_POLICY
from rnastable.reference import digest
from study_long_candidate_budget_matched import verify_run as verify_budgets
from verify_long_native_controls import audit as verify_native
from evaluate_bprna_five_clan_feasibility import verify as verify_short, score_rows

BUDGET = ROOT / "results/long_candidate_budget_matched_runs/20261017T183356.669629Z"
NATIVE = ROOT / "results/long_native_controls_runs/20261017T034318.804594Z"
SHORT = ROOT / "results/bprna_five_clan_feasibility_evaluation_runs/20261017T191445.852927Z"
LONG_SELECTION = ROOT / "results/long_validation_coverage_runs/20261017T033935.363253Z/selection.json"
SHORT_REFS = ROOT / "results/bprna_five_clan_reference_screen_runs/20261017T191404.643416Z/references.json"
EXTRA = ROOT / "results/bprna_long_training_smoke_runs/20261017T033749.792816Z/selection.json"
GATE = ROOT / "configs/stage2_to_stage3_gate_2026-10-18.json"
SEEDS = (7, 1729, 20261015)


def aggregate(rows):
    if any(not 1 <= r["length_nt"] < 3000 for r in rows):
        raise ValueError("Scope audit aggregates only lengths 1-2999 nt")
    values = [r["pair_f1"] for r in rows]
    families = sorted({r["family_id"] for r in rows})
    by_family = {family: sum(r["pair_f1"] for r in rows if r["family_id"] == family)
                 / sum(r["family_id"] == family for r in rows) for family in families}
    return {"n": len(values), "mean_record_pair_f1": sum(values) / len(values) if values else None,
            "family_means": by_family,
            "mean_family_pair_f1": sum(by_family.values()) / len(by_family) if by_family else None,
            "bands": {name: {"n": len(selected), "mean_pair_f1":
                              sum(r["pair_f1"] for r in selected) / len(selected) if selected else None}
                      for name, lo, hi in (("1_999", 1, 1000), ("1000_1999", 1000, 2000), ("2000_2999", 2000, 3000))
                      for selected in [[r for r in rows if lo <= r["length_nt"] < hi]]}}


def compute():
    policy = load_policy()
    boundary = policy["active_sequence_length_nt"]["maximum_exclusive"]
    gate = json.loads(GATE.read_text())
    if boundary != 3000 or gate["active_length_nt"]["maximum_exclusive"] != boundary:
        raise ValueError("Stage 2 audit requires the current exclusive 3000-nt scope")
    verify_budgets(BUDGET / "summary.json")
    verify_native(NATIVE / "summary.json")
    verify_short(SHORT / "summary.json")
    records = json.loads(LONG_SELECTION.read_text())["selected"]
    active = [r for r in records if len(r["sequence"]) < boundary]
    excluded = [{"id": r["id"], "length_nt": len(r["sequence"])} for r in records if len(r["sequence"]) >= boundary]
    paths = [GATE, DEFAULT_POLICY, LONG_SELECTION, SHORT_REFS, EXTRA]
    results = {}
    for arm in ("control_88", "extended_105"):
        for budget in (16, 32, 64):
            per_seed = {}
            for seed in SEEDS:
                path = BUDGET / f"{arm}_seed{seed}" / "summary.json"
                paths.append(path)
                data = json.loads(path.read_text())["budgets"][str(budget)]["rows"]
                per_seed[str(seed)] = aggregate([r for r in data if r["length_nt"] < boundary])
            results[f"{arm}_top{budget}"] = {
                "mean_seed_record_pair_f1": sum(r["mean_record_pair_f1"] for r in per_seed.values()) / len(SEEDS),
                "per_seed": per_seed}
    path = NATIVE / "rows.json"
    paths.append(path)
    natives = {}
    for method in ("LinearFold", "ViennaRNA"):
        rows = [r for r in json.loads(path.read_text()) if r["method"] == method and r["length_nt"] < boundary]
        ok = [{**r, **r["metrics"]} for r in rows if r["metrics"] is not None]
        natives[method] = {**aggregate(ok), "failed_count": len(rows) - len(ok)}
    short_records = json.loads(SHORT_REFS.read_text())
    short_results = {}
    for name in [f"{arm}_seed{seed}" for arm in ("control_88", "extended_105") for seed in SEEDS] + ["LinearFold", "ViennaRNA"]:
        path = SHORT / (name + "_predictions.json")
        paths.append(path)
        predictions = json.loads(path.read_text())
        short_results[name] = score_rows(predictions, short_records)
    extras = json.loads(EXTRA.read_text())["selected"]
    return {"scope": gate["active_length_nt"], "stage3_target": gate["stage3_target"],
            "ready_for_stage3": False,
            "reasons": ["Learned model remains below both native controls on development references",
                        "Only one long development reference lies in 2000-2999 nt",
                        "Independent complete-reference validation remains unestablished",
                        "Existing checkpoints were trained with some now-deferred sequences"],
            "long_development_reference_count": len(active),
            "long_reference_band_counts": dict(Counter("1000_1999" if len(r["sequence"]) < 2000 else "2000_2999" for r in active)),
            "excluded_deferred_references": excluded, "long_model_results": results,
            "long_native_results": natives, "short_feasibility_results": short_results,
            "historical_extended_training_above_scope": [{"id": r["id"], "length_nt": len(r["sequence"])}
                                                        for r in extras if len(r["sequence"]) >= boundary],
            "development_only": True, "independent_test_claim": False,
            "model_defaults_changed": False, "new_inference_performed": False,
            "inputs_sha256": {str(p): digest(p.read_bytes()) for p in paths}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--verify-run", type=Path)
    args = parser.parse_args()
    result = compute()
    if args.run:
        folder = ROOT / "results/stage2_under3000_audit_runs" / timestamp()
        folder.mkdir(parents=True, exist_ok=False)
        atomic_json(folder / "manifest.json", {"driver_sha256": digest(Path(__file__).read_bytes())})
        atomic_json(folder / "summary.json", result)
        print(folder / "summary.json")
    else:
        manifest = json.loads((args.verify_run.parent / "manifest.json").read_text())
        if manifest != {"driver_sha256": digest(Path(__file__).read_bytes())} or json.loads(args.verify_run.read_text()) != result:
            raise ValueError("Stage 2 scope audit replay differs")
        print("Stage 2 under-3000 audit replay passed")


if __name__ == "__main__":
    main()
