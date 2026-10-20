#!/usr/bin/env python3
"""Multi-objective optimizer mechanics under the Pareto formulation.

The user chose on 2026-10-20 that the optimizer is asked for a Pareto front over
the two incommensurable score sides rather than for a single best candidate. This
verifies the mechanics of that formulation on toy objectives, across the
project's three seeds, and records the run.

It designs, proposes and scores **no RNA**. Expression candidate design is
disabled by `configs/stage2_to_stage3_gate_v5_2026-10-20.json` and this script
does not open it: the objectives are mathematical functions over a finite pool,
chosen to conflict so that a trade-off is actually exercised.

Each seed is also run with the same budget spent on random selection, because a
hypervolume figure on its own says nothing about the optimizer.
"""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import json
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.multi_objective_bo import run_toy_pareto
from rnastable.pareto import dominates

FORMULATION = ROOT / "configs/pareto_objective_formulation_v1_2026-10-20.json"
GATE = ROOT / "configs/stage2_to_stage3_gate_v5_2026-10-20.json"
SEEDS = (7, 1729, 20261015)
BUDGET = 8
REFERENCE_POINT = (0.0, 0.0)
PINNED = ("botorch", "gpytorch", "linear_operator", "torch")


def check_front(front):
    """A front that contains a dominated member is not a front."""
    points = [tuple(point) for point in front]
    return not any(dominates(other, point)
                   for point in points for other in points if other != point)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", default="results/pareto_mechanics_runs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    formulation = json.loads(FORMULATION.read_text())
    gate = json.loads(GATE.read_text())
    # The formulation explicitly does not open the campaign switches. If a later
    # gate opens them, that is a decision this script must not be able to make.
    if gate["expression_candidate_design_enabled"] or gate["new_sequence_scoring_enabled"]:
        raise SystemExit("Gate opened a campaign switch; this mechanics driver is "
                         "not the right entry point for a real campaign")
    if formulation["objectives"][0]["direction"] != "maximize" or \
            formulation["objectives"][1]["direction"] != "maximize":
        raise SystemExit("This driver assumes both objectives are maximized")

    seeds = {}
    for seed in SEEDS:
        result = run_toy_pareto(seed=seed, budget=BUDGET, reference_point=REFERENCE_POINT)
        resumed = run_toy_pareto(seed=seed, budget=BUDGET, reference_point=REFERENCE_POINT,
                                 state={"protocol": result["protocol"],
                                        "history": result["history"][:5]})
        seeds[str(seed)] = {
            "pareto_indices": result["pareto_indices"],
            "pareto_front": result["pareto_front"],
            "front_is_non_dominated": check_front(result["pareto_front"]),
            "front_size": len(result["pareto_front"]),
            "hypervolume": result["hypervolume"],
            "random_hypervolume": result["random_hypervolume"],
            "hypervolume_exceeds_random": result["hypervolume"] > result["random_hypervolume"],
            "random_front_size": len(result["random_pareto_indices"]),
            "unique_evaluations": result["unique_evaluations"],
            "history": result["history"],
            "resume_reproduces_the_run": resumed["history"] == result["history"],
            "protocol": result["protocol"],
        }
        print(f"seed {seed:>9}  front {len(result['pareto_front'])}  "
              f"hv {result['hypervolume']:.6f}  random hv {result['random_hypervolume']:.6f}  "
              f"{'optimizer ahead' if result['hypervolume'] > result['random_hypervolume'] else 'RANDOM AHEAD'}",
              flush=True)

    payload = {
        "purpose": ("Mechanics of the Pareto objective formulation: a front rather than a "
                    "single best candidate, over two deliberately conflicting toy objectives."),
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "formulation": str(FORMULATION.relative_to(ROOT)),
        "gate": str(GATE.relative_to(ROOT)),
        "seeds": seeds,
        "budget": BUDGET,
        "reference_point": list(REFERENCE_POINT),
        "versions": {name: metadata.version(name) for name in PINNED},
        "rna_designed": False,
        "rna_scored": False,
        "composite_score_emitted": False,
        "all_fronts_non_dominated": all(s["front_is_non_dominated"] for s in seeds.values()),
        "all_resumes_reproduced": all(s["resume_reproduces_the_run"] for s in seeds.values()),
        "optimizer_ahead_of_random_on_every_seed": all(
            s["hypervolume_exceeds_random"] for s in seeds.values()),
        "seed_sensitivity": {
            "distinct_optimizer_hypervolumes": len({s["hypervolume"] for s in seeds.values()}),
            "distinct_optimizer_histories": len(
                {tuple(row["index"] for row in s["history"]) for s in seeds.values()}),
            "interpretation": (
                "The optimizer selects the same points on every seed, so the three runs are "
                "NOT three independent confirmations. The pool is 31 members with 25 feasible "
                "and a fixed 3-point initial design, so the acquisition ordering is "
                "effectively determined and the fit seed does not change it. Only the random "
                "baseline varies with the seed. This says the mechanics are stable on this "
                "pool; it does not demonstrate robustness to seed on a larger domain."),
        },
        "no_claim": [
            "This is software verification of the optimizer mechanics, not biological evidence.",
            "A hypervolume improvement on a toy objective says nothing about RNA.",
            "No RNA sequence was designed, proposed or scored.",
            "No single best candidate is reported; with two incommensurable objectives there "
            "is none, and inventing one would be the composite score_record_schema_v1 forbids.",
            "Hypervolume is a diagnostic of a set and must not be attached to a candidate as "
            "its score.",
            "The reference point (0.0, 0.0) is meaningful for the toy objectives only. No "
            "reference point has been selected for the real scales.",
        ],
    }

    print(f"\nfronts non-dominated: {payload['all_fronts_non_dominated']}   "
          f"resumes reproduced: {payload['all_resumes_reproduced']}   "
          f"optimizer ahead on every seed: {payload['optimizer_ahead_of_random_on_every_seed']}")

    if args.dry_run:
        print("\nDry run: nothing written.", file=sys.stderr)
        return 0
    out = ROOT / args.out / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True, exist_ok=False)
    (out / "summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(f"\nWrote {out}/summary.json", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
