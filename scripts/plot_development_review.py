#!/usr/bin/env python3
"""Export static scientific plots from completed, reused development artifacts."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.native_journal import atomic_json
from rnastable.reference import digest
from rnastable.reference_audit import require


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    paths = [
        ROOT / "results/development_slices_summary.json",
        ROOT / "results/population_resource_summary.json",
    ]
    output = ROOT / "reports/figures"
    manifest_path = output / "development_2026-10-06_manifest.json"
    if args.verify:
        manifest = json.loads(manifest_path.read_text())
        for path, sha in {
            **manifest["source_sha256"],
            **manifest["figure_sha256"],
        }.items():
            require(
                digest(Path(path).read_bytes()) == sha,
                "Scientific figure/source changed: " + path,
            )
        print(
            "Development figure audit passed: bound existing metrics and static PNG/SVG; no inference or new evaluation."
        )
        return manifest
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    data = [json.loads(path.read_text()) for path in paths]
    rows = data[0]["analysis"]["slices"]
    resource = data[1]["rows"]
    require(
        data[0]["analysis"]["test_evaluated"] is False
        and data[1]["accuracy_evaluated"] is False,
        "Plot scope changed",
    )
    groups = ("PDB-derived", "Rfam-comparative", "CRW-comparative")
    heads = ("baseline", "stack", "helix")
    colors = ("#758599", "#2875ae", "#22885c")
    fig, (left, right) = plt.subplots(1, 2, figsize=(12, 5))
    x = np.arange(3)
    width = 0.23
    for index, (head, color) in enumerate(zip(heads, colors)):
        values = [
            [
                row["pair_f1"]
                for row in rows
                if row["dimension"] == "source_group"
                and row["group"] == group
                and row["head"] == head
            ]
            for group in groups
        ]
        means = np.array([np.mean(value) for value in values])
        error = np.array(
            [
                [mean - min(value) for mean, value in zip(means, values)],
                [max(value) - mean for mean, value in zip(means, values)],
            ]
        )
        left.bar(
            x + (index - 1) * width,
            means,
            width,
            label=head.capitalize(),
            color=color,
            yerr=error,
            capsize=3,
            error_kw={"linewidth": 1},
        )
    counts = [
        next(
            row["planned_records"]
            for row in rows
            if row["dimension"] == "source_group" and row["group"] == group
        )
        for group in groups
    ]
    left.set_xticks(
        x, [group + "\n(n=" + str(count) + ")" for group, count in zip(groups, counts)]
    )
    left.set_ylabel("Pair F1 on reused validation")
    left.set_ylim(0, 1)
    left.set_title("47 reused records; three model seeds", fontsize=11)
    left.legend(frameon=False, fontsize=9)
    left.text(
        0.5,
        -0.22,
        "Bars: seed mean. Whiskers: observed seed range.\nSelected checkpoints; no independent test.",
        transform=left.transAxes,
        ha="center",
        va="top",
        fontsize=9,
        color="#444444",
    )
    measured = np.array([row["retained_sample_tensor_bytes"] / 1e6 for row in resource])
    theoretical = np.array(
        [row["full_label_tensor_bytes_if_materialized"] / 1e6 for row in resource]
    )
    right.bar(
        x - 0.17, measured, 0.34, color=colors[2], label="Primary sampled tensors"
    )
    right.bar(
        x + 0.17, theoretical, 0.34, color="#cb9d4b", label="Full layout (theoretical)"
    )
    right.set_xticks(x, [f"{row['length']:,} nt" for row in resource])
    right.set_yscale("log")
    right.set_ylabel("Index + label tensor layout (decimal MB)")
    right.set_title("Synthetic sampled training: one update per length", fontsize=11)
    right.legend(frameon=False, fontsize=9)
    for position, value in zip(x - 0.17, measured):
        right.text(position, value * 1.15, f"{value:.2f}", ha="center", fontsize=8)
    for position, value in zip(x + 0.17, theoretical):
        right.text(position, value * 1.15, f"{value:.1f}", ha="center", fontsize=8)
    right.set_ylim(0.1, 1000)
    right.text(
        0.5,
        -0.22,
        "Constructed toy labels; no biological accuracy.\nLayouts exclude copies/model/optimizer/Python allocations.",
        transform=right.transAxes,
        ha="center",
        va="top",
        fontsize=9,
        color="#444444",
    )
    for axis in (left, right):
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", alpha=0.18)
        axis.set_axisbelow(True)
    fig.suptitle(
        "RNA-StableAI: development diagnostics and label-storage feasibility",
        fontsize=13,
        y=0.98,
    )
    fig.subplots_adjust(left=0.07, right=0.98, top=0.85, bottom=0.28, wspace=0.35)
    output.mkdir(parents=True, exist_ok=True)
    figures = [
        output / "development_2026-10-06.png",
        output / "development_2026-10-06.svg",
    ]
    for path in figures:
        fig.savefig(path, dpi=180)
    plt.close(fig)
    manifest = {
        "source_sha256": {str(path): digest(path.read_bytes()) for path in paths},
        "figure_sha256": {str(path): digest(path.read_bytes()) for path in figures},
        "plot_script_sha256": digest(Path(__file__).read_bytes()),
        "purpose": "Static descriptive development/source slices and synthetic primary label layouts; no independent test, biological stability or empirical total-memory saving claim.",
    }
    atomic_json(manifest_path, manifest)
    return manifest


if __name__ == "__main__":
    main()
