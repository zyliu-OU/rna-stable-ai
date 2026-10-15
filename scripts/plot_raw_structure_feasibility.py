#!/usr/bin/env python3
"""Export a source-bound family/method figure without new model/native requests."""
# ruff: noqa: E402 -- standalone source bootstrap.

import argparse
import json
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp, write_artifact
from rnastable.native_journal import atomic_json
from rnastable.reference import digest
from rnastable.reference_audit import require
from evaluate_raw_structure_feasibility import audit

NAMES = {
    "RF00379": "c-di-AMP",
    "RF00380": "Mbox",
    "RF00442": "Guanidine-I",
    "RF01054": "preQ1-II",
    "RF01750": "ZMP/ZTP",
    "RF01786": "c-di-GMP-II",
}
METHODS = ["baseline", "stack", "helix", "all_unpaired", "ViennaRNA", "LinearFold"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summary",
        type=Path,
        default=ROOT / "results/raw_structure_feasibility_summary.json",
    )
    args = parser.parse_args()
    summary = audit(args.summary)
    source = Path(summary["run_dir"]) / "summary.json"
    lookup = {(row["family_id"], row["method"]): row for row in summary["by_family"]}
    families = sorted({key[0] for key in lookup})
    require(set(families) == set(NAMES), "Figure requires the six declared families")
    overall = {row["method"]: row for row in summary["aggregates"]}
    values, labels = [], []
    for family in families:
        count = lookup[(family, METHODS[0])]["planned_inputs"]
        labels.append(f"{NAMES[family]} · {family}  (n={count})")
        values.append([lookup[(family, method)]["mean_pair_f1"] for method in METHODS])
    labels.append("All references  (n=10)")
    values.append([overall[method]["mean_pair_f1"] for method in METHODS])
    data = np.array([[np.nan if v is None else v for v in row] for row in values])
    plt.rcParams.update({"font.size": 11, "svg.fonttype": "none"})
    fig, ax = plt.subplots(figsize=(11.4, 6.8), layout="constrained")
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad("#eeeeee")
    display = ax.imshow(
        np.ma.masked_invalid(data), vmin=0, vmax=1, cmap=cmap, aspect="auto"
    )
    ax.set_xticks(
        range(len(METHODS)),
        ["Baseline", "Stack", "Helix", "All unpaired", "ViennaRNA", "LinearFold"],
    )
    ax.set_yticks(range(len(labels)), labels)
    ax.tick_params(axis="both", length=0, pad=9)
    ax.axhline(len(families) - 0.5, color="white", linewidth=3)
    for y in range(data.shape[0]):
        for x in range(data.shape[1]):
            value = data[y, x]
            ax.text(
                x,
                y,
                "null" if np.isnan(value) else f"{value:.3f}",
                ha="center",
                va="center",
                color="white" if np.isfinite(value) and value < 0.55 else "#18212b",
                fontsize=11,
            )
    fig.colorbar(display, ax=ax, label="Mean pair F1", shrink=0.82)
    ax.set_title(
        "Six-family raw-contact feasibility\nFrozen models · 10 references · all 60 outcomes retained",
        loc="left",
        fontsize=15,
        pad=16,
    )
    fig.supxlabel(
        "Descriptive per-record macro scores. Small selected cohort; broad validation and stability/function remain open.",
        fontsize=10,
    )
    run = ROOT / "results/raw_structure_feasibility_figures" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    for extension in ("png", "svg"):
        fig.savefig(run / ("family_pair_f1." + extension), dpi=220, bbox_inches="tight")
    plt.close(fig)
    (run / "driver.py").write_bytes(Path(__file__).read_bytes())
    manifest = {
        "source_summary": str(source),
        "source_sha256": digest(source.read_bytes()),
        "code_sha256": {str(Path(__file__)): digest(Path(__file__).read_bytes())},
        "files_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
        "methods": METHODS,
        "families": families,
        "values": values,
        "native_requests_added": 0,
        "model_fitted": False,
    }
    atomic_json(run / "manifest.json", manifest)
    write_artifact(
        ROOT / "results/raw_structure_feasibility_figure_summary.json",
        json.dumps({"run_dir": str(run), **manifest}, indent=2) + "\n",
    )
    print("Saved raw structure feasibility figure: " + str(run), flush=True)


if __name__ == "__main__":
    main()
