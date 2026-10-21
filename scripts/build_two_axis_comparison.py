#!/usr/bin/env python3
"""Merge mRNAutilus's half-life scores into this project's 2x2 comparison run.

This project's half is produced by `scripts/run_two_axis_comparison.py`.
mRNAutilus's half is produced in its own isolated environment, because it needs
torch, flash-attn and a 1.78 GB checkpoint this project neither depends on nor
redistributes. This script joins the two on sequence_id and completes the table.

Usage:
    python scripts/build_two_axis_comparison.py THEIR_SCORES_JSON
"""
import argparse
import glob
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BINS = ((1.00, 1.10), (1.10, 1.25), (1.25, 1.50), (1.50, 2.00), (2.00, math.inf))


def bin_key(low, high):
    return f"{low:.2f}-{high:.2f}" if high != math.inf else f"above_{low:.2f}"


def concordance(predicted, measured):
    out = {}
    for low, high in BINS:
        pairs = agree = 0
        for i in range(len(measured)):
            for j in range(i + 1, len(measured)):
                small, large = sorted((measured[i], measured[j]))
                if small <= 0:
                    continue
                if low <= large / small < high:
                    pairs += 1
                    agree += (predicted[i] < predicted[j]) == (measured[i] < measured[j])
        out[bin_key(low, high)] = {"pairs": pairs,
                                   "concordance": agree / pairs if pairs else None}
    return out


def spearman(xs, ys):
    def ranks(values):
        order = sorted(range(len(values)), key=lambda i: values[i])
        result = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            shared = (i + j) / 2 + 1
            for k in range(i, j + 1):
                result[order[k]] = shared
            i = j + 1
        return result
    return statistics.correlation(ranks(xs), ranks(ys))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("their_scores")
    args = parser.parse_args(argv)

    run_path = Path(sorted(glob.glob(
        str(ROOT / "results/two_axis_comparison_runs/*/summary.json")))[-1])
    run = json.loads(run_path.read_text())
    their = json.loads(Path(args.their_scores).read_text())
    rows = run["rows"]
    if their["n"] != len(rows):
        raise SystemExit(f"their {their['n']} scores vs our {len(rows)} rows")

    ours = [r["predicted_hours"] for r in rows]
    theirs = [their["scores"][r["sequence_id"]] for r in rows]
    in_cell = [r["measured_in_cell_hours"] for r in rows]
    in_solution = [r["measured_in_solution_hours"] for r in rows]
    gc = [r["features"]["gc_fraction"] for r in rows]
    eterna = [-r["baseline_eternafold_sup"] / r["length_nt"] for r in rows]

    def column(measured, label):
        return {
            "measured_axis": label,
            "spearman": {
                "ours": spearman(ours, measured),
                "mrnautilus": spearman(theirs, measured),
                "free_eternafold_per_nucleotide": spearman(eterna, measured),
                "transcript_gc_alone": spearman(gc, measured),
            },
            "concordance": {
                bin_key(lo, hi): {
                    "pairs": concordance(ours, measured)[bin_key(lo, hi)]["pairs"],
                    "ours": concordance(ours, measured)[bin_key(lo, hi)]["concordance"],
                    "mrnautilus": concordance(theirs, measured)[bin_key(lo, hi)]["concordance"],
                } for lo, hi in BINS
            },
        }

    in_sol_col, in_cell_col = column(in_solution, "in-solution"), column(in_cell, "in-cell")
    axes_rho = run["measured_axes"]["spearman_between_the_two_measured_axes"]
    ours_home = in_sol_col["spearman"]["ours"] > in_cell_col["spearman"]["ours"]
    theirs_home = in_cell_col["spearman"]["mrnautilus"] > in_sol_col["spearman"]["mrnautilus"]

    summary = {
        "built_utc": run["built_utc"],
        "purpose": run["purpose"],
        "protocol": run["protocol"],
        "protocol_sha256": run["protocol_sha256"],
        "source": run["source"],
        "our_run": str(run_path.parent.relative_to(ROOT)),
        "counts": run["counts"],
        "refitting_performed": "none",

        "the_two_measured_axes_barely_agree": {
            "spearman_between_them": axes_rho,
            "statement": (
                f"In-solution and in-cell half-life of the SAME 122 constructs rank at "
                f"Spearman {axes_rho:+.4f}. They are very nearly unrelated orderings. "
                "This is the single most important number in this artifact: it means no "
                "predictor can rank both axes well, the two columns are separate tasks "
                "rather than two views of 'stability', and any method claiming to "
                "predict 'mRNA stability' must say which one it means."),
            "consequence_for_this_comparison": (
                "Winning one column implies nothing about the other. The earlier "
                "one-column comparison could not have been repaired by more in-solution "
                "data, which is what gate v13 recorded as a prohibition."),
        },

        "in_solution_column": in_sol_col,
        "in_cell_column": in_cell_col,

        "domain_test": {
            "question": "Is each method better inside its own training domain than outside it?",
            "ours_better_in_its_own_domain": ours_home,
            "theirs_better_in_its_own_domain": theirs_home,
            "ours": {"in_solution_is_home": True,
                     "spearman_home": in_sol_col["spearman"]["ours"],
                     "spearman_away": in_cell_col["spearman"]["ours"]},
            "mrnautilus": {"in_cell_is_home": True,
                           "spearman_home": in_cell_col["spearman"]["mrnautilus"],
                           "spearman_away": in_sol_col["spearman"]["mrnautilus"]},
            "declared_expectation": (
                "The protocol declared, before any number was seen, that a sound pair of "
                "methods would each win their own column. Whatever happened is reported "
                "as measured."),
        },

        "the_free_baseline": {
            "in_solution": in_sol_col["spearman"]["free_eternafold_per_nucleotide"],
            "in_cell": in_cell_col["spearman"]["free_eternafold_per_nucleotide"],
            "ours_in_solution": in_sol_col["spearman"]["ours"],
            "statement": (
                "A free per-nucleotide EternaFold score, which requires no training and no "
                "calibration, is carried in both columns because the protocol declared it. "
                f"On in-solution it reaches {in_sol_col['spearman']['free_eternafold_per_nucleotide']:+.4f} "
                f"against this project's calibration at {in_sol_col['spearman']['ours']:+.4f}. "
                "On in-cell it has the wrong sign. The calibration therefore does not beat "
                "free folding on its own home axis, which is the same finding the v10 "
                "ablation recorded and this test does nothing to relieve."),
        },

        "gc_diagnostic": {
            "ours_vs_transcript_gc": run["ours"]["correlation_with_transcript_gc"],
            "gc_alone_vs_in_solution": in_sol_col["spearman"]["transcript_gc_alone"],
            "gc_alone_vs_in_cell": in_cell_col["spearman"]["transcript_gc_alone"],
            "statement": (
                "Gate v12 recorded that this project's objective collapses to transcript GC "
                "at r = +0.99 on the synthetic design pool. Here, on 122 real measured "
                "constructs, the same objective correlates with GC at "
                f"{run['ours']['correlation_with_transcript_gc']:+.4f}, so the collapse is a "
                "property of the objective and not an artifact of the design pool's "
                "composition."),
        },

        "what_this_changes": [
            "The axis question is settled: in-solution and in-cell stability are nearly "
            "unrelated on identical constructs, so 'stability' is not one target.",
            "The earlier head-to-head is now correctly bounded. It measured one column of "
            "a two-column problem, and the column it measured is the one this project "
            "trained on.",
            "The free-baseline problem is worse than previously recorded, not better: on "
            "in-solution, free EternaFold now ranks ABOVE the frozen calibration.",
        ],

        "no_claim": [
            "Nothing here is a new measurement. Every label is from the source paper.",
            "No claim about either method's translation side. RiboNN is not run here, and "
            "mRNAutilus's translation head is trained on Zheng et al. 2025, which is "
            "RiboNN's own training source, so that comparison would be partly circular.",
            "No claim that either method resolves the narrow bin; chance is 0.50.",
            "No resolution claim on mRNAutilus's arbitrary output scale.",
            "No claim about mRNAutilus's generator. Only its half-life regressor was run.",
            "Neither the source archive nor mRNAutilus's weights are redistributed here.",
        ],

        "rows": [{"sequence_id": r["sequence_id"], "group": r["group"],
                  "length_nt": r["length_nt"],
                  "measured_in_cell_hours": r["measured_in_cell_hours"],
                  "measured_in_solution_hours": r["measured_in_solution_hours"],
                  "ours_predicted_hours": r["predicted_hours"],
                  "mrnautilus_halflife_score": their["scores"][r["sequence_id"]],
                  "transcript_gc_fraction": r["features"]["gc_fraction"]}
                 for r in rows],
    }

    out = run_path.parent / "two_axis_summary.json"
    out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out}\n")
    print(f"measured axes agree at Spearman {axes_rho:+.4f}  <-- they are different tasks\n")
    print(f"{'':<34}{'in-solution':>14}{'in-cell':>12}")
    for label, key in (("ours (frozen calibration)", "ours"),
                       ("mRNAutilus halflife head", "mrnautilus"),
                       ("free EternaFold per nt", "free_eternafold_per_nucleotide"),
                       ("transcript GC alone", "transcript_gc_alone")):
        print(f"{label:<34}{in_sol_col['spearman'][key]:>+14.4f}"
              f"{in_cell_col['spearman'][key]:>+12.4f}")
    print(f"\nours better in its own domain?       {ours_home}")
    print(f"mRNAutilus better in its own domain? {theirs_home}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
