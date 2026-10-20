#!/usr/bin/env python3
"""Compare objective spread between two design-workflow runs.

The window widened from 30 to 50 codons because the 30-codon objective
landscape was nearly flat. Design-space v2 recorded that as a falsifiable
expectation: a wider window should widen the spread. This measures it.

The two runs are otherwise matched -- same GC mode, same pool size, same seed,
same folding settings, same calibration, same RiboNN checkpoints -- so the
window width is the only deliberate difference. The number of substitutable
positions differs (13 against 24) because that IS the change, not a confound.

Spread is reported four ways, because range alone is driven by two members:
range, standard deviation, interquartile range, and the fraction of the
calibration's training target range that the predicted half-life spans. The
per-feature spreads are reported too, so a flat objective can be attributed to
the feature that is not moving rather than left unexplained.

Nothing here is a measurement of any molecule. Both runs are predictions from
an unvalidated model, and a wider spread of predictions is not evidence that
the predictions are right.
"""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import csv
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

CALIBRATION = ROOT / "results/strand_rnafold_calibration_runs/20261019T174049.053308Z"
HOURS = "predicted_in_solution_half_life_hours"
FEATURES = ("energy_per_length", "GC", "aup")


def training_target_range():
    rows = list(csv.DictReader((CALIBRATION / "features/train_features.csv").open()))
    values = [float(row["in_solution_half_life"]) for row in rows]
    return min(values), max(values)


def spread(values):
    ordered = sorted(values)
    if len(ordered) < 4:
        iqr = None
    else:
        quartiles = statistics.quantiles(ordered, n=4, method="inclusive")
        iqr = quartiles[2] - quartiles[0]
    return {
        "n": len(ordered),
        "min": ordered[0],
        "max": ordered[-1],
        "range": ordered[-1] - ordered[0],
        "stdev": statistics.stdev(ordered) if len(ordered) > 1 else None,
        "iqr": iqr,
        "median": statistics.median(ordered),
    }


def load(run_dir):
    run_dir = ROOT / run_dir if not Path(run_dir).is_absolute() else Path(run_dir)
    summary = json.loads((run_dir / "summary.json").read_text())
    members = json.loads((run_dir / "scored_members.json").read_text())
    complete = [m for m in members if m.get("stability") and m.get("translation")]
    low, high = training_target_range()
    hours = [m["stability"][HOURS] for m in complete]
    report = {
        "run": str(run_dir.relative_to(ROOT)),
        "design_space": summary["design_space"],
        "window_codons": summary["pool"]["window_codons"],
        "window_nt": summary["pool"]["window_codons"] * 3,
        "transcript_length_nt": summary["assembly"]["transcript_length_nt"],
        "window_fraction_of_transcript": summary["pool"]["window_codons"] * 3
        / summary["assembly"]["transcript_length_nt"],
        "gc_mode": summary["gc_mode"],
        "pool_size": summary["pool"]["size"],
        "substitutable_positions": summary["pool"]["substitutable_positions"],
        "seed": summary["pool"]["seed"],
        "complete_members": len(complete),
        "folds_ok": summary["folding"]["ok"],
        "extrapolating": summary["stability"]["extrapolating"],
        "half_life_hours": spread(hours),
        "translation": spread([m["translation"]["value"] for m in complete]),
        "substitution_count": spread([m["substitution_count"] for m in complete]),
        "features": {name: spread([m["stability"]["features"][name] for m in complete])
                     for name in FEATURES},
        "pareto_front_size": summary["selection"]["pareto_front_size"],
        "panel_members": summary["selection"]["panel_members"],
        "bo_replay": summary.get("bo_replay"),
    }
    report["half_life_hours"]["range_as_fraction_of_training_target_range"] = (
        report["half_life_hours"]["range"] / (high - low))
    report["calibration_training_target_range_hours"] = [low, high]
    return report


def ratio(wide, narrow):
    if not narrow:
        return None
    return wide / narrow


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--narrow", required=True, help="the 30-codon run directory")
    parser.add_argument("--wide", required=True, help="the 50-codon run directory")
    parser.add_argument("--out", default="results/window_width_comparison_runs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    narrow, wide = load(args.narrow), load(args.wide)
    if narrow["window_codons"] >= wide["window_codons"]:
        raise SystemExit("--narrow must have the smaller window")
    for key in ("gc_mode", "pool_size", "seed", "transcript_length_nt"):
        if narrow[key] != wide[key]:
            raise SystemExit(f"Runs differ in {key}; the comparison would be confounded")

    comparison = {
        "half_life_range_ratio": ratio(wide["half_life_hours"]["range"],
                                       narrow["half_life_hours"]["range"]),
        "half_life_stdev_ratio": ratio(wide["half_life_hours"]["stdev"],
                                       narrow["half_life_hours"]["stdev"]),
        "half_life_iqr_ratio": ratio(wide["half_life_hours"]["iqr"],
                                     narrow["half_life_hours"]["iqr"]),
        "translation_range_ratio": ratio(wide["translation"]["range"],
                                         narrow["translation"]["range"]),
        "translation_stdev_ratio": ratio(wide["translation"]["stdev"],
                                         narrow["translation"]["stdev"]),
        "window_nt_ratio": wide["window_nt"] / narrow["window_nt"],
        "substitutable_position_ratio": (wide["substitutable_positions"]
                                         / narrow["substitutable_positions"]),
        "feature_stdev_ratio": {
            name: ratio(wide["features"][name]["stdev"], narrow["features"][name]["stdev"])
            for name in FEATURES},
    }
    widened = (comparison["half_life_stdev_ratio"] or 0) > 1.0
    payload = {
        "purpose": ("Did widening the synonymous window from 30 to 50 codons widen the "
                    "predicted objective spread? Design-space v2 recorded this as a "
                    "falsifiable expectation; this is the measurement."),
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "expectation_under_test": ("A wider window should widen the objective spread, "
                                   "because more of the transcript varies."),
        "narrow": narrow,
        "wide": wide,
        "comparison": comparison,
        "expectation_held": widened,
        "matched_on": ["gc_mode", "pool_size", "seed", "transcript_length_nt",
                       "folding settings", "calibration run", "RiboNN checkpoints"],
        "deliberate_difference": ("window width, and therefore the number of substitutable "
                                  "positions: 13 at 30 codons against 24 at 50"),
        "no_claim": [
            "Both runs are predictions from an unvalidated model. A wider spread of "
            "predictions is NOT evidence that the predictions are right.",
            "No molecule in this project has been measured, so neither run can be scored "
            "against reality.",
            "A spread is not an effect. Nothing here says a variant differs in stability or "
            "translation, only that the model's output differs.",
            "The stability side extrapolates on GC in both runs, because the construct is "
            "more GC-rich than the calibration's training set.",
            "Whether the remaining flatness is acceptable is a judgement, not an output.",
        ],
    }

    def show(report):
        half, trans = report["half_life_hours"], report["translation"]
        print(f"  window {report['window_codons']:>2} codons = {report['window_nt']:>3} nt "
              f"({report['window_fraction_of_transcript'] * 100:.1f}% of the transcript), "
              f"{report['substitutable_positions']} substitutable positions")
        print(f"    half-life  {half['min']:.4f} .. {half['max']:.4f} h   "
              f"range {half['range']:.5f}  stdev {half['stdev']:.5f}  iqr {half['iqr']:.5f}  "
              f"({half['range_as_fraction_of_training_target_range'] * 100:.2f}% of training range)")
        print(f"    TE         {trans['min']:.4f} .. {trans['max']:.4f}     "
              f"range {trans['range']:.5f}  stdev {trans['stdev']:.5f}  iqr {trans['iqr']:.5f}")
        print(f"    edits      {report['substitution_count']['min']}"
              f"..{report['substitution_count']['max']}   front "
              f"{report['pareto_front_size']} of {report['complete_members']}")
        for name in FEATURES:
            feature = report["features"][name]
            print(f"      {name:<17} stdev {feature['stdev']:.6g}  range {feature['range']:.6g}")

    print("narrow:")
    show(narrow)
    print("wide:")
    show(wide)
    print("\nratios wide/narrow:")
    print(f"  window nt              {comparison['window_nt_ratio']:.2f}x")
    print(f"  substitutable positions {comparison['substitutable_position_ratio']:.2f}x")
    print(f"  half-life range        {comparison['half_life_range_ratio']:.2f}x")
    print(f"  half-life stdev        {comparison['half_life_stdev_ratio']:.2f}x")
    print(f"  half-life iqr          {comparison['half_life_iqr_ratio']:.2f}x")
    print(f"  TE range               {comparison['translation_range_ratio']:.2f}x")
    print(f"  TE stdev               {comparison['translation_stdev_ratio']:.2f}x")
    for name, value in comparison["feature_stdev_ratio"].items():
        print(f"  feature {name:<17} stdev {value if value is None else format(value, '.2f') + 'x'}")
    print(f"\nexpectation held: {widened}")

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
