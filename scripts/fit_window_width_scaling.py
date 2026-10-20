"""How predicted objective spread scales with synonymous window width.

The 30 and 50 codon runs gave a two-point power law, spread proportional to
window^0.372, which predicted that a whole-ORF window would leave the predicted
half-life spanning about 7.8 percent of the calibration's training target range.
A two-point fit cannot be tested against itself, so this does two things:

  1. fits on the first two widths and PREDICTS the third, then reports the
     measured value beside the prediction and the ratio between them;
  2. refits across all widths and reports the exponent that uses every point.

The prediction is made from the earlier runs only, so the third run can refute
it. If it does, that is the result and it is reported as such.

Spread is measured as standard deviation, not range, because a range is set by
two members and a 512-member sample's extremes are the least stable statistic
it has.

Nothing here is a measurement of any molecule. Every spread is a spread of
predictions from an unvalidated model, and a scaling law over such predictions
describes the model's sensitivity, not biology.
"""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import csv
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

CALIBRATION = ROOT / "results/strand_rnafold_calibration_runs/20261019T174049.053308Z"
HOURS = "predicted_in_solution_half_life_hours"


def training_target_range():
    rows = list(csv.DictReader((CALIBRATION / "features/train_features.csv").open()))
    values = [float(row["in_solution_half_life"]) for row in rows]
    return min(values), max(values)


def load(run_dir):
    path = ROOT / run_dir if not Path(run_dir).is_absolute() else Path(run_dir)
    summary = json.loads((path / "summary.json").read_text())
    members = json.loads((path / "scored_members.json").read_text())
    complete = [m for m in members if m.get("stability") and m.get("translation")]
    hours = [m["stability"][HOURS] for m in complete]
    translation = [m["translation"]["value"] for m in complete]
    low, high = training_target_range()
    return {
        "run": str(path.relative_to(ROOT)),
        "design_space": summary["design_space"],
        "window_codons": summary["pool"]["window_codons"],
        "window_nt": summary["pool"]["window_codons"] * 3,
        "window_fraction_of_transcript": summary["pool"]["window_codons"] * 3
        / summary["assembly"]["transcript_length_nt"],
        "substitutable_positions": summary["pool"]["substitutable_positions"],
        "gc_mode": summary["gc_mode"],
        "pool_size": summary["pool"]["size"],
        "seed": summary["pool"]["seed"],
        "n": len(complete),
        "half_life_stdev": statistics.stdev(hours),
        "half_life_range": max(hours) - min(hours),
        "half_life_range_fraction_of_training_range": (max(hours) - min(hours)) / (high - low),
        "translation_stdev": statistics.stdev(translation),
        "edit_count_max": max(m["substitution_count"] for m in complete),
        "pareto_front_size": summary["selection"]["pareto_front_size"],
        "bo_front_found": (summary.get("bo_replay") or {}).get("front_members_found"),
        "bo_random_front_found": (summary.get("bo_replay") or {}).get(
            "random_front_members_found"),
    }


def power_fit(widths, values):
    """Least-squares fit of log(value) against log(width).

    Returns the exponent, the prefactor and R-squared. With two points R-squared
    is 1 by construction and is reported as None rather than as a fit quality.
    """
    xs = [math.log(w) for w in widths]
    ys = [math.log(v) for v in values]
    n = len(xs)
    mean_x, mean_y = statistics.fmean(xs), statistics.fmean(ys)
    sxx = sum((x - mean_x) ** 2 for x in xs)
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    exponent = sxy / sxx
    intercept = mean_y - exponent * mean_x
    if n <= 2:
        r_squared = None
    else:
        predicted = [intercept + exponent * x for x in xs]
        ss_res = sum((y - p) ** 2 for y, p in zip(ys, predicted))
        ss_tot = sum((y - mean_y) ** 2 for y in ys)
        r_squared = 1 - ss_res / ss_tot if ss_tot else None
    return {"exponent": exponent, "prefactor": math.exp(intercept), "r_squared": r_squared,
            "points": n}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--run", action="append", required=True,
                        help="a design-workflow run directory; repeat, narrowest first")
    parser.add_argument("--out", default="results/window_scaling_runs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    runs = sorted((load(r) for r in args.run), key=lambda r: r["window_codons"])
    if len(runs) < 3:
        raise SystemExit("At least three widths are needed to test a two-point fit")
    for key in ("gc_mode", "pool_size", "seed"):
        if len({run[key] for run in runs}) != 1:
            raise SystemExit(f"Runs differ in {key}; the comparison would be confounded")

    widths = [run["window_nt"] for run in runs]
    stdevs = [run["half_life_stdev"] for run in runs]
    fractions = [run["half_life_range_fraction_of_training_range"] for run in runs]

    # Fit on everything except the widest, then predict the widest. This is the
    # only honest way to test a fit that was made before the third run existed.
    held_out = runs[-1]
    fit_prior = power_fit(widths[:-1], fractions[:-1])
    predicted = fit_prior["prefactor"] * held_out["window_nt"] ** fit_prior["exponent"]
    measured = held_out["half_life_range_fraction_of_training_range"]

    fit_all_stdev = power_fit(widths, stdevs)
    fit_all_fraction = power_fit(widths, fractions)

    payload = {
        "purpose": ("Test the two-point window-width scaling against a third, wider run, "
                    "and refit across every width."),
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "spread_statistic": ("standard deviation, and range expressed as a fraction of the "
                             "calibration's training target range; not range alone, which "
                             "is set by two members"),
        "runs": runs,
        "held_out_prediction": {
            "fitted_on_widths_nt": widths[:-1],
            "exponent_used": fit_prior["exponent"],
            "prefactor_used": fit_prior["prefactor"],
            "predicted_for_width_nt": held_out["window_nt"],
            "predicted_fraction_of_training_range": predicted,
            "measured_fraction_of_training_range": measured,
            "measured_over_predicted": measured / predicted if predicted else None,
            "basis": ("the fit was made from the earlier runs only, so the widest run can "
                      "refute it"),
        },
        "fit_all_widths": {
            "half_life_stdev": fit_all_stdev,
            "half_life_range_fraction": fit_all_fraction,
        },
        "window_axis_ceiling": {
            "widest_window_codons": held_out["window_codons"],
            "widest_window_fraction_of_transcript": held_out["window_fraction_of_transcript"],
            "note": ("This is the widest window the constraints permit for this construct, "
                     "so it is the ceiling of the window axis, not an arbitrary largest "
                     "case."),
            "measured_fraction_of_training_range_at_the_ceiling": measured,
        },
        "no_claim": [
            "Every spread is a spread of PREDICTIONS from an unvalidated model. A scaling "
            "law over them describes the model's sensitivity to sequence, not biology.",
            "No molecule in this project has been measured.",
            "A power law over three points is a description of three points.",
            "The widest run is a diagnostic probe, not a campaign design space; editing "
            "90.9 percent of the transcript destroys regional attribution.",
            "Whether the measured spread at the ceiling is acceptable is a judgement.",
        ],
    }

    print("widths and measured spread:")
    for run in runs:
        print(f"  {run['window_codons']:>3} codons = {run['window_nt']:>4} nt "
              f"({run['window_fraction_of_transcript'] * 100:>4.1f}% of transcript)  "
              f"subst {run['substitutable_positions']:>3}  "
              f"half-life stdev {run['half_life_stdev']:.5f}  "
              f"range {run['half_life_range_fraction_of_training_range'] * 100:>5.2f}% of training  "
              f"TE stdev {run['translation_stdev']:.5f}  front {run['pareto_front_size']:>2}")
    print(f"\nfit on widths {widths[:-1]} nt -> exponent {fit_prior['exponent']:.3f}")
    print(f"  predicted at {held_out['window_nt']} nt: {predicted * 100:.2f}% of training range")
    print(f"  measured                     : {measured * 100:.2f}%")
    print(f"  measured/predicted           : {measured / predicted:.2f}x")
    print(f"\nrefit across all {len(runs)} widths:")
    print(f"  half-life stdev    exponent {fit_all_stdev['exponent']:.3f}  "
          f"R2 {fit_all_stdev['r_squared']:.4f}")
    print(f"  half-life range    exponent {fit_all_fraction['exponent']:.3f}  "
          f"R2 {fit_all_fraction['r_squared']:.4f}")

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
