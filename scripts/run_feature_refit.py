#!/usr/bin/env python3
"""Step 3 of folding_engine_swap_v1, redirected by what step 1 found.

Step 1 killed the engine-swap hypothesis. The apparent EternaFold advantage was
not EternaFold and was not structure: in the PERSIST-seq table, SUP is summed
over a sub-region (median 673 nt) and not over the molecule (median 1034 nt), so
dividing it by RNA length produced AUP multiplied by a region-length ratio, and
the ratio was the dominant factor (-0.3850 against the structure term's -0.2648).
All three engines clustered near 0.42 because all three shared that one artifact.

Step 2, installing EternaFold, is therefore skipped: the engines agree once
properly normalised (AUP EternaFold -0.2648, AUP Vienna -0.2589, AUP DegScore
-0.2170) and there is nothing to gain by swapping.

What survives is a different and cleaner finding: GC content (CDS), a single free
column with no normalisation ambiguity, reaches +0.3651 against the frozen
calibration's +0.3200. So this step asks whether refitting on the paper's own
free columns beats the frozen arm AND beats the best single free column.

Fitted on the same 69 records as the frozen arm. No held-out and no in-cell label
touches a coefficient. The frozen arm is retained, never replaced.

Usage:
    python scripts/run_feature_refit.py --archive /path/to/MOESM4.zip
"""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import csv
import glob
import hashlib
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_two_axis_comparison import concordance, number, read_table, spearman  # noqa: E402

PROTOCOL = ROOT / "configs/folding_engine_swap_v1_2026-10-20.json"
TWO_AXIS = ROOT / "configs/two_axis_comparison_v1_2026-10-20.json"
CALIBRATION = ROOT / "results/strand_rnafold_calibration_runs/20261019T174049.053308Z"

# EternaFold-based arms are RETIRED at the user's direction (2026-10-20: "remove the
# test result for EternaFold-based refit, we dont do that"). The engine swap was a dead
# hypothesis and is not part of the plan, which stays RNAfold + STRAND + RiboNN + BoTorch.
# The arms kept here are ViennaRNA- and composition-based and are retained for one reason
# only: they carry the overfitting finding, which is about training-set size rather than
# about any engine, and that finding constrains every future model in this project.
ARMS = {
    "gc_cds_only": ["GC content (CDS)"],
    "frozen_form_from_table": ["dG(MFE) Vienna", "GC content (CDS)", "AUP Vienna"],
    "vienna_plus_composition": ["GC content (CDS)", "AUP Vienna", "dG(MFE) Vienna", "CAI"],
}


def ols(design, target):
    """Least squares with an intercept, via normal equations and Gaussian elimination.

    No numpy dependency is introduced for a 69-row fit of at most eight columns.
    """
    rows = [[1.0] + list(x) for x in design]
    width = len(rows[0])
    normal = [[sum(r[i] * r[j] for r in rows) for j in range(width)] + [
        sum(r[i] * y for r, y in zip(rows, target))] for i in range(width)]
    for col in range(width):
        pivot = max(range(col, width), key=lambda r: abs(normal[r][col]))
        if abs(normal[pivot][col]) < 1e-12:
            raise SystemExit("singular design matrix")
        normal[col], normal[pivot] = normal[pivot], normal[col]
        scale = normal[col][col]
        normal[col] = [v / scale for v in normal[col]]
        for other in range(width):
            if other == col:
                continue
            factor = normal[other][col]
            normal[other] = [v - factor * p for v, p in zip(normal[other], normal[col])]
    return [normal[i][width] for i in range(width)]


def predict(coefficients, design):
    return [coefficients[0] + sum(c * x for c, x in zip(coefficients[1:], row))
            for row in design]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--archive", required=True)
    parser.add_argument("--out", default="results/feature_refit_runs")
    args = parser.parse_args(argv)

    declared = json.loads(TWO_AXIS.read_text())["test_set"]
    archive = Path(args.archive)
    archive_digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if archive_digest != declared["archive_sha256"]:
        raise SystemExit("archive sha256 does not match the protocol")
    records, table_digest = read_table(archive)
    if table_digest != declared["table_sha256"]:
        raise SystemExit("table sha256 does not match the protocol")

    two_axis = json.loads(Path(sorted(glob.glob(
        str(ROOT / "results/two_axis_comparison_runs/*/summary.json")))[-1]).read_text())
    test_ids = {r["sequence_id"]: r for r in two_axis["rows"]}
    training_values = {round(float(r["in_solution_half_life"]), 4) for r in csv.DictReader(
        (CALIBRATION / "features/train_features.csv").open())}

    train, test = [], []
    for record in records:
        in_solution = number(record, "In-solution half-life")
        if in_solution is None:
            continue
        if record["Sequence ID"] in test_ids:
            test.append(record)
        elif round(in_solution, 4) in training_values:
            train.append(record)
    print(f"train {len(train)}  test {len(test)}", flush=True)
    if len(train) != 69 or len(test) != 122:
        raise SystemExit(f"expected 69 train and 122 test, got {len(train)} and {len(test)}")

    train_target = [number(r, "In-solution half-life") for r in train]
    test_solution = [number(r, "In-solution half-life") for r in test]
    test_cell = [number(r, "In-cell half-life") for r in test]

    results = {}
    for name, columns in ARMS.items():
        usable = all(number(r, c) is not None for r in train + test for c in columns)
        if not usable:
            results[name] = {"available": False, "columns": columns}
            continue
        design_train = [[number(r, c) for c in columns] for r in train]
        design_test = [[number(r, c) for c in columns] for r in test]
        coefficients = ols(design_train, train_target)
        fitted = predict(coefficients, design_train)
        predicted = predict(coefficients, design_test)
        results[name] = {
            "available": True,
            "columns": columns,
            "n_features": len(columns),
            "coefficients": dict(zip(["intercept"] + columns, coefficients)),
            "train_spearman": spearman(fitted, train_target),
            "test_spearman_vs_in_solution": spearman(predicted, test_solution),
            "test_spearman_vs_in_cell": spearman(predicted, test_cell),
            "test_concordance_vs_in_solution": concordance(predicted, test_solution),
        }

    frozen = two_axis["ours"]["spearman_vs_in_solution"]
    gc_cds = spearman([number(r, "GC content (CDS)") for r in test], test_solution)
    best_valid_free = max(
        abs(spearman([number(r, c) for r in test], test_solution))
        for c in ("GC content (CDS)", "AUP EternaFold", "AUP Vienna", "AUP DegScore 2.1"))
    best_arm = max((n for n in results if results[n]["available"]),
                   key=lambda n: results[n]["test_spearman_vs_in_solution"])
    best_value = results[best_arm]["test_spearman_vs_in_solution"]

    summary = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "step": "3 of 3: refit on the source paper's free columns",
        "protocol": str(PROTOCOL.relative_to(ROOT)),
        "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
        "source": {"archive_sha256": archive_digest, "table_sha256": table_digest,
                   "not_redistributed": declared["not_redistributed"]},
        "counts": {"train": len(train), "test": len(test)},
        "estimator": {
            "method": "ordinary least squares",
            "why_not_pls": "The frozen model is a one-component PLS fitted in R and cannot "
                           "be reproduced exactly here. OLS is used for every arm so the "
                           "comparison is internally apples-to-apples, and the frozen PLS "
                           "arm is reported alongside as a labelled reference.",
            "target": "measured in-solution half-life in hours",
            "no_in_cell_label_used": True,
        },
        "step_2_skipped": {
            "what_was_skipped": "installing EternaFold and reproducing its column locally",
            "why": "Step 1 showed the engines agree once properly normalised (AUP "
                   "EternaFold -0.2648, AUP Vienna -0.2589, AUP DegScore -0.2170) and that "
                   "the apparent EternaFold advantage was an artifact of dividing a "
                   "sub-region sum by full RNA length. There is nothing for an engine swap "
                   "to gain, so installing one would spend effort on a dead hypothesis.",
        },
        "the_defective_baseline_that_prompted_this": {
            "what_was_reported": "gate v14 recorded a free per-nucleotide EternaFold score "
                                 "at +0.4190 beating the frozen calibration at +0.3200, as "
                                 "the most adverse finding in any gate version",
            "what_it_actually_was": "AUP multiplied by a region-length ratio. In this table "
                                    "SUP is summed over a sub-region whose implied length is "
                                    "median 673 nt, not the RNA length of median 1034 nt, so "
                                    "dividing by RNA length does not yield a per-nucleotide "
                                    "structure score.",
            "decomposition_on_the_122": {"aup_alone": -0.2648, "region_fraction_alone": -0.3850,
                                         "the_product_as_reported": -0.4190},
            "why_all_three_engines_clustered": "They share the one artifact, not a common "
                                               "ceiling. That inference in the step 1 verdict "
                                               "was wrong for the right numbers.",
            "scope_of_the_error": "Confined to two_axis_comparison_v1. On the 123-record "
                                  "Fig_S8a sheet the SUP columns are labelled FULL and "
                                  "SUP/length equals AUP FULL exactly on 123 of 123 records, "
                                  "so the post-hoc correction recorded in "
                                  "external_validation_leppek_v1 was correct and its -0.3248 "
                                  "figure stands.",
            "corrected_comparison": "Against properly normalised free structure scores the "
                                    "frozen calibration (+0.3200) WINS; the best is AUP "
                                    "EternaFold at -0.2648. The adverse finding survives in a "
                                    "different form: GC content (CDS), a single free column "
                                    f"with no normalisation ambiguity, reaches {gc_cds:+.4f}.",
        },
        "reference_points": {
            "frozen_vienna_arm_in_solution": frozen,
            "frozen_vienna_arm_in_cell": two_axis["ours"]["spearman_vs_in_cell"],
            "gc_content_cds_alone": gc_cds,
            "best_valid_free_single_column_abs": best_valid_free,
        },
        "arms": results,
        "verdict": {
            "success_criterion_declared_in_advance": (
                "the refit must beat BOTH the frozen arm and the best free single column; "
                "beating only the frozen arm is not success"),
            "criterion_amended": (
                "The protocol named the free EternaFold score at +0.4190 as the bar. That "
                "score is defective, so the bar is restated as the best VALID free single "
                f"column, GC content (CDS) at {gc_cds:+.4f}. The amendment is recorded rather "
                "than applied silently, and it lowers the bar, so it is stated explicitly."),
            "best_arm": best_arm,
            "best_arm_test_spearman": best_value,
            "beats_frozen_arm": best_value > frozen,
            "beats_best_free_single_column": best_value > abs(gc_cds),
            "success": bool(best_value > frozen and best_value > abs(gc_cds)),
        },
        "what_this_cannot_establish": json.loads(
            PROTOCOL.read_text())["what_this_cannot_establish"],
    }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%f") + "Z"
    out = ROOT / args.out / stamp
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out / 'summary.json'}\n")
    print(f"{'arm':<38}{'feats':>6}{'train':>9}{'test in-sol':>13}{'test in-cell':>14}")
    for name, entry in results.items():
        if not entry["available"]:
            print(f"{name:<38}{'--':>6}  unavailable")
            continue
        print(f"{name:<38}{entry['n_features']:>6}{entry['train_spearman']:>+9.4f}"
              f"{entry['test_spearman_vs_in_solution']:>+13.4f}"
              f"{entry['test_spearman_vs_in_cell']:>+14.4f}")
    print(f"\n{'frozen ViennaRNA arm (reference)':<38}{3:>6}{'':>9}{frozen:>+13.4f}"
          f"{two_axis['ours']['spearman_vs_in_cell']:>+14.4f}")
    print(f"{'GC content (CDS) alone (reference)':<38}{1:>6}{'':>9}{gc_cds:>+13.4f}")
    print(f"\nbest arm: {best_arm} at {best_value:+.4f}")
    print(f"  beats frozen arm ({frozen:+.4f})?           {summary['verdict']['beats_frozen_arm']}")
    print(f"  beats GC content (CDS) ({gc_cds:+.4f})?      "
          f"{summary['verdict']['beats_best_free_single_column']}")
    print(f"  SUCCESS by the declared criterion:        {summary['verdict']['success']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
