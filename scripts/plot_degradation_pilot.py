#!/usr/bin/env python3
"""Export all declared assay-proxy correlations with source-bound provenance."""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from evaluate_degradation_pilot import FEATURES, PLAN, audit
from rnastable.artifacts import timestamp
from rnastable.native_journal import atomic_json
from rnastable.reference import digest


def main():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    source = ROOT / "results/degradation_pilot_summary.json"
    summary = audit(source)
    rows = [r for r in summary["aggregates"] if r["quality_slice"] == "all"]
    lookup = {(r["method"], r["proxy_name"], r["target"]): r for r in rows}
    matrix = np.array(
        [
            [
                lookup[method, feature, target]["spearman_rho"]
                if lookup[method, feature, target]["spearman_rho"] is not None
                else np.nan
                for target in PLAN["targets"]
            ]
            for method, feature in FEATURES
        ]
    )
    labels = [
        (method + " · unpaired")
        if feature == "unpaired_fraction_of_scored_prefix"
        else (method + " · energy/nt")
        if feature == "native_mfe_per_nt"
        else "Sequence only · GC"
        for method, feature in FEATURES
    ]
    columns = [
        "Reactivity",
        "Degradation\nMg, pH 10",
        "Degradation\npH 10",
        "Degradation\nMg, 50°C",
        "Degradation\n50°C",
    ]
    figure, axis = plt.subplots(figsize=(11.2, 7.6))
    color = plt.get_cmap("coolwarm").copy()
    color.set_bad("#e6e9ef")
    heatmap = axis.imshow(
        np.ma.masked_invalid(matrix), cmap=color, vmin=-1, vmax=1, aspect="auto"
    )
    axis.set_xticks(range(len(columns)), columns, fontsize=10)
    axis.set_yticks(range(len(labels)), labels, fontsize=10)
    for i in range(len(labels)):
        for j in range(len(columns)):
            value = matrix[i, j]
            axis.text(
                j,
                i,
                "—" if np.isnan(value) else f"{value:.3f}",
                ha="center",
                va="center",
                color="white"
                if not np.isnan(value) and abs(value) >= 0.65
                else "#172033",
                fontsize=10,
            )
    for spine in axis.spines.values():
        spine.set_visible(False)
    figure.colorbar(
        heatmap,
        ax=axis,
        label="Descriptive Spearman rho",
        ticks=[-1, -0.5, 0, 0.5, 1],
        shrink=0.85,
    )
    figure.suptitle("RNA-StableAI · measured-assay proxy pilot", fontsize=16, y=0.975)
    axis.set_title(
        "64 short constructs; every selected quality flag = 1", fontsize=11, pad=18
    )
    figure.text(
        0.02,
        0.025,
        "Native folding: 37°C; chemical assay conditions differ. Shared flanks/source processing limit interpretation.\n"
        "Gray cells: undefined correlation. No p-values, independent intervals, causal mutation or function claims.",
        fontsize=9,
    )
    figure.tight_layout(rect=(0, 0.09, 1, 0.93))
    run = ROOT / "results/degradation_pilot_figures" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    for extension in ("png", "svg"):
        figure.savefig(run / ("assay_proxy_correlations." + extension), dpi=180)
    plt.close(figure)
    atomic_json(
        run / "manifest.json",
        {
            "source": str(source),
            "source_run": summary["run_dir"],
            "summary_sha256": digest(source.read_bytes()),
            "code_sha256": digest(Path(__file__).read_bytes()),
            "quality_slice": "all",
            "features": FEATURES,
            "targets": PLAN["targets"],
            "correlations": rows,
            "figure_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
        },
    )
    print("Exported complete correlation figure: " + str(run))
    return run


if __name__ == "__main__":
    main()
