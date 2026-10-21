#!/usr/bin/env python3
"""Step 1 of folding_engine_swap_v1: rank the free baselines the source paper ships.

A free per-nucleotide EternaFold score beats this project's fitted calibration on
in-solution half-life. Before installing an engine and refitting anything, the
cheap question is whether that is specific to EternaFold or whether every free
structure score in the same table does as well. The source paper precomputes ten
such columns, so this costs one pass over a workbook.

The decision rule was declared in `configs/folding_engine_swap_v1_2026-10-20.json`
BEFORE this script was run: if several unrelated free scores cluster near +0.42,
the feature family is at its ceiling and refitting cannot be expected to pass it.
If EternaFold stands clearly above the others, the engine is specifically better.

Nothing is fitted here. Nothing is installed here.

Usage:
    python scripts/run_free_baseline_panel.py --archive /path/to/MOESM4.zip
"""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import glob
import hashlib
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_two_axis_comparison import number, read_table, spearman  # noqa: E402

PROTOCOL = ROOT / "configs/folding_engine_swap_v1_2026-10-20.json"
TWO_AXIS = ROOT / "configs/two_axis_comparison_v1_2026-10-20.json"
SUM_COLUMNS = ("SUP DegScore2.1", "SUP Vienna", "SUP EternaFold")
AVG_COLUMNS = ("AUP DegScore 2.1", "AUP Vienna", "AUP EternaFold",
               "dG(MFE) Vienna", "dG(MFE) EternaFold", "CAI", "GC content (CDS)")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--archive", required=True)
    parser.add_argument("--out", default="results/free_baseline_panel_runs")
    args = parser.parse_args(argv)

    protocol = json.loads(PROTOCOL.read_text())
    declared = json.loads(TWO_AXIS.read_text())["test_set"]
    archive = Path(args.archive)
    archive_digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if archive_digest != declared["archive_sha256"]:
        raise SystemExit(f"archive sha256 {archive_digest} does not match the protocol")
    records, table_digest = read_table(archive)
    if table_digest != declared["table_sha256"]:
        raise SystemExit(f"table sha256 {table_digest} does not match the protocol")

    # The test set is defined by the two-axis run, not re-derived here, so the
    # panel is scored on exactly the constructs the comparison used.
    two_axis = json.loads(Path(sorted(glob.glob(
        str(ROOT / "results/two_axis_comparison_runs/*/summary.json")))[-1]).read_text())
    wanted = {r["sequence_id"]: r for r in two_axis["rows"]}
    rows = [r for r in records if r["Sequence ID"] in wanted]
    if len(rows) != len(wanted):
        raise SystemExit(f"matched {len(rows)} of {len(wanted)} test constructs")

    in_solution = [number(r, "In-solution half-life") for r in rows]
    in_cell = [number(r, "In-cell half-life") for r in rows]
    length = [float(r["RNA length"]) for r in rows]

    panel = {}
    for column in SUM_COLUMNS + AVG_COLUMNS:
        values = [number(r, column) for r in rows]
        if any(v is None for v in values):
            panel[column] = {"available": False,
                             "missing": sum(1 for v in values if v is None)}
            continue
        entry = {"available": True, "form": "as given",
                 "spearman_vs_in_solution": spearman(values, in_solution),
                 "spearman_vs_in_cell": spearman(values, in_cell),
                 "spearman_vs_length": spearman(values, length)}
        if column in SUM_COLUMNS:
            per_nt = [v / n for v, n in zip(values, length)]
            entry["per_nucleotide"] = {
                "spearman_vs_in_solution": spearman(per_nt, in_solution),
                "spearman_vs_in_cell": spearman(per_nt, in_cell),
                "spearman_vs_length": spearman(per_nt, length)}
        panel[column] = entry

    def best_magnitude(column):
        """The strongest in-solution |rho| this column reaches in any reported form."""
        entry = panel[column]
        if not entry.get("available"):
            return None
        options = [abs(entry["spearman_vs_in_solution"])]
        if "per_nucleotide" in entry:
            options.append(abs(entry["per_nucleotide"]["spearman_vs_in_solution"]))
        return max(options)

    ranked = sorted((c for c in panel if panel[c].get("available")),
                    key=lambda c: best_magnitude(c), reverse=True)
    eternafold = best_magnitude("SUP EternaFold")
    others = [best_magnitude(c) for c in ranked if c != "SUP EternaFold"]
    runner_up = max(others) if others else None
    gap = eternafold - runner_up if runner_up is not None else None
    # Declared rule: a clear lead means the engine is specifically better.
    clustered = sum(1 for v in others if v >= eternafold - 0.03)

    summary = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": protocol["purpose"],
        "step": "1 of 3: free baseline panel",
        "protocol": str(PROTOCOL.relative_to(ROOT)),
        "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
        "source": {"archive_sha256": archive_digest, "table_sha256": table_digest,
                   "not_redistributed": declared["not_redistributed"]},
        "test_set": {"records": len(rows),
                     "defined_by": "the two-axis comparison run, not re-derived"},
        "fitting_performed": "none",
        "engine_installed": "none",
        "reference_points_from_the_two_axis_run": {
            "ours_fitted_calibration_in_solution": two_axis["ours"]["spearman_vs_in_solution"],
            "ours_fitted_calibration_in_cell": two_axis["ours"]["spearman_vs_in_cell"],
            "transcript_gc_alone_in_solution": two_axis["gc_alone"]["spearman_vs_in_solution"],
        },
        "panel": panel,
        "ranking_by_best_in_solution_magnitude": [
            {"column": c, "best_abs_spearman_vs_in_solution": best_magnitude(c)}
            for c in ranked],
        "decision": {
            "rule_declared_in_advance": protocol["declared_before_any_number_was_seen"][2],
            "eternafold_best_abs": eternafold,
            "runner_up_best_abs": runner_up,
            "gap": gap,
            "other_columns_within_0_03_of_eternafold": clustered,
            "verdict": ("EternaFold stands clearly above the other free scores, so the "
                        "engine is specifically better and steps 2 and 3 are worth building"
                        if clustered == 0 else
                        "several unrelated free scores reach the same level, so this feature "
                        "family is at its ceiling and a refit should not be expected to pass "
                        "it; steps 2 and 3 are diagnostic only"),
            "steps_2_and_3_warranted": clustered == 0,
        },
        "what_this_cannot_establish": protocol["what_this_cannot_establish"],
    }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%f") + "Z"
    out = ROOT / args.out / stamp
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out / 'summary.json'}\n")
    print(f"{'column':<24}{'form':>14}{'in-solution':>13}{'in-cell':>10}{'vs length':>11}")
    for column in ranked:
        entry = panel[column]
        print(f"{column:<24}{'as given':>14}{entry['spearman_vs_in_solution']:>+13.4f}"
              f"{entry['spearman_vs_in_cell']:>+10.4f}{entry['spearman_vs_length']:>+11.4f}")
        if "per_nucleotide" in entry:
            per = entry["per_nucleotide"]
            print(f"{'':<24}{'per nucleotide':>14}{per['spearman_vs_in_solution']:>+13.4f}"
                  f"{per['spearman_vs_in_cell']:>+10.4f}{per['spearman_vs_length']:>+11.4f}")
    print(f"\nEternaFold best |rho| {eternafold:.4f} vs runner-up {runner_up:.4f} "
          f"(gap {gap:+.4f}); {clustered} other columns within 0.03")
    print(f"VERDICT: {summary['decision']['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
