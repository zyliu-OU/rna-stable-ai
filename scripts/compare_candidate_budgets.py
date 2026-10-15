#!/usr/bin/env python3
"""Fixed, posthoc development comparison of top-16/32/64 candidate pools."""
# ruff: noqa: E402 -- CLI bootstrap locates the local source tree.

import argparse
import json
import math
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from analyze_development_slices import replay
from rnastable.artifacts import timestamp, publish
from rnastable.candidate_diagnostics import CATEGORIES, diagnose
from rnastable.context_inference import load_checkpoint
from rnastable.development_slices import HEADS, SEEDS, source_group, length_group
from rnastable.exact_sparse_pairs import decode_exact_sparse
from rnastable.exposures import record_exposure, read_exposure, exposure_records
from rnastable.global_sparse_pairs import sparse_candidates
from rnastable.native_journal import atomic_json
from rnastable.pair_model import CANONICAL
from rnastable.reference import digest
from rnastable.reference_audit import require
from rnastable.scoring import base_pairs
from rnastable.structure_model import tokens

NAME = "candidate_budget_development"
BUDGETS = (16, 32, 64)
TIMINGS = ("score_seconds", "decode_seconds")
COUNTS = ("reference_pairs", "candidate_pairs", "false_positive_pairs", *CATEGORIES)
COSTS = ("candidate_array_bytes", "dp_array_bytes", "peak_score_tile_elements")
LIMITATIONS = [
    "Posthoc development tuning: all nine checkpoints were selected using top-16; no joint epoch/budget selection.",
    "All 47 reused validation records and all three initialization seeds retained; no independent biological uncertainty claim.",
    "Larger pools can improve gold retention while introducing incorrect competitors and reducing F1.",
    "No fitting, checkpoint selection, default changes, native folds or prospective-panel access.",
    "Timings are single CPU observations with two Torch threads, including pool construction; no speed significance claim.",
    "Array bytes describe candidate and DP arrays, not total process memory; tile elements exclude temporary feature arrays.",
]


def aggregate(rows):
    """Retain fixed, empty slices and paired per-record changes versus top-16."""
    require(len(rows) == 1269, "Expected all 1269 planned predictions")
    ids = {r["id"] for r in rows}
    require(len(ids) == 47, "Expected 47 development records")
    by_key = {(r["seed"], r["head"], r["id"], r["top_k"]): r for r in rows}
    require(
        len(by_key) == len(rows)
        and set(by_key)
        == {(s, h, i, k) for s in SEEDS for h in HEADS for i in ids for k in BUDGETS},
        "Budget prediction inventory differs",
    )
    definitions = [
        ("all", "all"),
        *[
            ("source_group", x)
            for x in ("PDB-derived", "Rfam-comparative", "CRW-comparative")
        ],
        *[("length_group", x) for x in ("1..64", "65..128", "129..256", "257..1024")],
        *[("reference_kind", x) for x in ("experimental", "computational")],
    ]
    result = []
    for seed in SEEDS:
        for head in HEADS:
            for top_k in BUDGETS:
                for dimension, group in definitions:
                    selected = [
                        r
                        for r in rows
                        if (r["seed"], r["head"], r["top_k"]) == (seed, head, top_k)
                        and (dimension == "all" or r[dimension] == group)
                    ]
                    changes = [
                        r["pair_f1"] - by_key[(seed, head, r["id"], 16)]["pair_f1"]
                        for r in selected
                    ]
                    result.append(
                        {
                            "seed": seed,
                            "head": head,
                            "top_k": top_k,
                            "dimension": dimension,
                            "group": group,
                            "records": len(selected),
                            **{c: sum(r[c] for r in selected) for c in COUNTS},
                            "mean_pair_f1": statistics.mean(
                                r["pair_f1"] for r in selected
                            )
                            if selected
                            else None,
                            "mean_f1_change_from_16": statistics.mean(changes)
                            if selected
                            else None,
                            "improved_records": sum(d > 0 for d in changes),
                            "regressed_records": sum(d < 0 for d in changes),
                            "unchanged_records": sum(d == 0 for d in changes),
                            **{t: sum(r[t] for r in selected) for t in TIMINGS},
                            **{
                                c: max((r[c] for r in selected), default=0)
                                for c in COSTS
                            },
                        }
                    )
    return result


def validate_costs(row):
    for key in TIMINGS:
        require(
            type(row[key]) in (int, float)
            and math.isfinite(row[key])
            and row[key] >= 0,
            "Invalid measured timing",
        )
    for key in COSTS:
        require(type(row[key]) is int and row[key] >= 0, "Invalid array/tile cost")
    require(
        row["candidate_array_bytes"] == row["candidate_pairs"] * 16
        and row["dp_array_bytes"] == row["length"] ** 2 * 12,
        "Array accounting differs",
    )


def evaluate(records, components, run, stored=None):
    import torch

    torch.set_num_threads(2)
    rows = []
    if stored is not None:
        require(len(stored) == 1269, "Stored outcome denominator differs")
    for component in components:
        _, config, _, model = load_checkpoint(Path(component["summary"]))
        require(
            config["top_k"] == 16 and config["inference_decoder"] == "exact_sparse",
            "Expected original top-16 exact decoder",
        )
        source = json.loads(Path(component["summary"]).read_text())
        predictions = json.loads(
            (Path(source["run_dir"]) / "predictions.json").read_text()
        )
        original = {
            r["id"]: r["structure"]
            for r in predictions["records"]
            if r["method"].startswith("trained_")
        }
        for record in records:
            sequence = record["sequence"]
            gold = sorted(
                p
                for p in base_pairs(record["structure"])
                if p[1] - p[0] >= 4 and sequence[p[0]] + sequence[p[1]] in CANONICAL
            )
            with torch.inference_mode():
                logits = model(
                    tokens(sequence),
                    torch.tensor(gold, dtype=torch.long).reshape(-1, 2),
                ).tolist()
            previous = set()
            previous_objective = 0.0
            for top_k in BUDGETS:
                identity = {
                    "seed": source["seed"],
                    "head": source["head"],
                    "id": record["id"],
                    "top_k": top_k,
                }
                try:
                    start = time.monotonic()
                    pool = sparse_candidates(
                        model, sequence, top_k, config["block_size"]
                    )
                    score_seconds = time.monotonic() - start
                    retained = set(map(tuple, pool["pairs"].tolist()))
                    require(previous <= retained, "Larger candidate pool is not nested")
                    previous = retained
                    start = time.monotonic()
                    decoded = decode_exact_sparse(
                        sequence, pool["pairs"], pool["scores"]
                    )
                    decode_seconds = time.monotonic() - start
                    require(
                        decoded["objective"] + 1e-9 >= previous_objective,
                        "Exact objective decreased with nested candidates",
                    )
                    previous_objective = decoded["objective"]
                    require(
                        top_k != 16 or decoded["structure"] == original[record["id"]],
                        "Top-16 no longer reproduces stored prediction",
                    )
                    row = {
                        **identity,
                        "source_group": source_group(record),
                        "length_group": length_group(len(sequence)),
                        "reference_kind": record["reference_kind"],
                        "structure": decoded["structure"],
                        "objective": decoded["objective"],
                        **diagnose(
                            record,
                            pool["pairs"].tolist(),
                            pool["scores"].tolist(),
                            dict(zip(gold, logits)),
                            decoded["structure"],
                        ),
                        **{c: pool[c] if c in pool else decoded[c] for c in COSTS},
                        "score_seconds": score_seconds,
                        "decode_seconds": decode_seconds,
                    }
                    validate_costs(row)
                    if stored is not None:
                        expected = stored[len(rows)]
                        validate_costs(expected)
                        require(
                            {k: v for k, v in row.items() if k not in TIMINGS}
                            == {k: v for k, v in expected.items() if k not in TIMINGS},
                            "Budget outcome replay differs",
                        )
                        row = expected  # Historical wall times cannot be replayed.
                    rows.append(row)
                except Exception as exc:
                    if stored is None:
                        atomic_json(run / "outcomes.json", rows)
                        atomic_json(
                            run / "failure.json",
                            {
                                **identity,
                                "error": str(exc),
                                "completed_predictions": len(rows),
                                "complete": False,
                            },
                        )
                    raise
            if stored is None:
                atomic_json(run / "outcomes.json", rows)
        print(
            f"{'Verified' if stored is not None else 'Measured'} {source['seed']} {source['head']}: 141 budget predictions",
            flush=True,
        )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    source_path = ROOT / "results/pair_head_development_study_summary.json"
    records, _, sources = replay(source_path)
    source = json.loads(source_path.read_text())
    require(len(records) == 47, "Development cohort differs")
    for component in source["components"]:
        _, _, checkpoint, _ = load_checkpoint(Path(component["summary"]))
        sources[str(checkpoint)] = digest(checkpoint.read_bytes())
    paths = [
        Path(__file__),
        ROOT / "scripts/analyze_development_slices.py",
        *sorted((ROOT / "src/rnastable").glob("*.py")),
    ]
    bindings = {
        "source_sha256": sources,
        "code_sha256": {str(p): digest(p.read_bytes()) for p in paths},
        "budgets": list(BUDGETS),
        "planned_predictions": 1269,
        "limitations": LIMITATIONS,
        "decoder": "exact_sparse",
        "cpu_threads": 2,
        "budget_order": "16,32,64 within each checkpoint-record",
    }
    if args.verify:
        summary = json.loads((ROOT / "results" / (NAME + "_summary.json")).read_text())
        run = Path(summary["run_dir"])
        require(
            summary == json.loads((run / "summary.json").read_text()),
            "Retained summary differs",
        )
        manifest = json.loads((run / "manifest.json").read_text())
        require(
            digest((run / "manifest.json").read_bytes()) == summary["manifest_sha256"]
            and all(manifest[k] == v for k, v in bindings.items()),
            "Frozen budget bindings differ",
        )
        require(
            json.loads((run / "validation.json").read_text()) == records
            and digest((run / "validation.json").read_bytes())
            == manifest["validation_sha256"],
            "Frozen validation differs",
        )
        event = summary["exposure_event"]
        path = Path(event["path"])
        require(
            path.resolve().parent == (run / "exposures").resolve()
            and digest(path.read_bytes()) == event["sha256"],
            "Exposure binding differs",
        )
        exposure = read_exposure(path)
        require(
            exposure["stage"] == event["stage"] == "validation_started"
            and exposure["records"]
            == exposure_records(records, str(run) + " validation_started"),
            "Exposure inventory differs",
        )
        require(
            digest((run / "outcomes.json").read_bytes()) == summary["outcomes_sha256"],
            "Outcomes changed",
        )
        stored = json.loads((run / "outcomes.json").read_text())
    else:
        run = ROOT / "results" / (NAME + "_runs") / timestamp()
        run.mkdir(parents=True, exist_ok=False)
        atomic_json(run / "validation.json", records)
        atomic_json(
            run / "manifest.json",
            {
                **bindings,
                "run_dir": str(run),
                "validation_sha256": digest((run / "validation.json").read_bytes()),
            },
        )
        event = record_exposure(run, "validation_started", records)
        stored = None
    rows = evaluate(records, source["components"], run, stored)
    aggregates = aggregate(rows)
    flags = {
        "complete": True,
        "development_only": True,
        "test_evaluated": False,
        "model_fitted": False,
        "checkpoint_selected": False,
        "defaults_changed": False,
        "measured_predictions": len(rows),
        "top16_reproduced_predictions": 423,
    }
    if args.verify:
        require(
            summary["aggregates"] == aggregates
            and all(summary[k] == v for k, v in flags.items()),
            "Budget aggregates/identity differ",
        )
        print(
            "Budget replay passed:1269 predictions,423 original top-16 reproductions; historical costs bound and validated."
        )
        return summary
    summary = {
        **flags,
        "run_dir": str(run),
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "outcomes_sha256": digest((run / "outcomes.json").read_bytes()),
        "exposure_event": event,
        "aggregates": aggregates,
    }
    atomic_json(run / "summary.json", summary)
    fields = [
        "seed",
        "head",
        "top_k",
        "dimension",
        "group",
        "records",
        "mean_pair_f1",
        "mean_f1_change_from_16",
        "positive_not_retained",
        "regressed_records",
        *TIMINGS,
        *COSTS,
    ]
    report = [
        "# Candidate budget development comparison",
        "",
        *LIMITATIONS,
        "",
        "All1269 outcomes retained; all423 top-16 structures exactly reproduce stored predictions.",
        "Coverage counts sum contacts; F1 averages records. Costs sum wall times and report maximum array bytes/tile elements.",
        "",
        "| " + " | ".join(fields) + " |",
        "|" + "---|" * len(fields),
    ]
    report.extend(
        "| " + " | ".join(str(r[k]) for k in fields) + " |" for r in aggregates
    )
    publish(ROOT, NAME, summary, rows, list(rows[0]), "\n".join(report) + "\n")
    return summary


if __name__ == "__main__":
    main()
