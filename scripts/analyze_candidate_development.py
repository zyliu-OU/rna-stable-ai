#!/usr/bin/env python3
"""Diagnose fixed sparse pools for nine already selected development checkpoints."""

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from analyze_development_slices import replay
from rnastable.artifacts import timestamp, publish
from rnastable.candidate_diagnostics import CATEGORIES, diagnose
from rnastable.context_inference import load_checkpoint
from rnastable.development_slices import source_group
from rnastable.exposures import record_exposure, read_exposure, exposure_records
from rnastable.global_sparse_pairs import sparse_candidates
from rnastable.native_journal import atomic_json
from rnastable.pair_model import CANONICAL
from rnastable.reference import digest
from rnastable.reference_audit import require
from rnastable.scoring import base_pairs
from rnastable.structure_model import tokens

NAME = "candidate_development"
LIMITATIONS = [
    "Reused development labels and nine already selected checkpoints; no independent accuracy claim.",
    "No fitting, checkpoint/decoder selection, native folds or prospective-panel access.",
    "Legal reference pairs require canonical chemistry and endpoint distance >=4; excluded labels remain in the denominator.",
    "Positive pairs outside the retained pool describe top-k pruning at the fixed original settings, not a new tuned candidate count.",
    "Retained but unselected contacts describe scoring/structure competition; they do not establish a decoder error.",
]


def run_analysis(records, components):
    import torch
    torch.set_num_threads(2)
    rows = []
    for component in components:
        _, config, _, model = load_checkpoint(Path(component["summary"]))
        source = json.loads(Path(component["summary"]).read_text())
        stored = json.loads((Path(source["run_dir"]) / "predictions.json").read_text())
        predictions = {r["id"]: r for r in stored["records"] if r["method"].startswith("trained_")}
        for record in records:
            sequence = record["sequence"]
            pool = sparse_candidates(model, sequence, config["top_k"], config["block_size"])
            gold = sorted(p for p in base_pairs(record["structure"])
                          if p[1]-p[0] >= 4 and sequence[p[0]]+sequence[p[1]] in CANONICAL)
            with torch.inference_mode():
                indices = torch.tensor(gold, dtype=torch.long).reshape(-1, 2)
                logits = model(tokens(sequence), indices).tolist()
            row = diagnose(record, pool["pairs"].tolist(), pool["scores"].tolist(),
                           dict(zip(gold, logits)), predictions[record["id"]]["structure"])
            rows.append({"seed": source["seed"], "head": source["head"],
                         "source_group": source_group(record), **row})
        print(f"Diagnosed {source['seed']} {source['head']}: {len(records)} development records", flush=True)
    aggregates = []
    for seed, head in sorted({(r["seed"], r["head"]) for r in rows}):
        for group in ["all", "PDB-derived", "Rfam-comparative", "CRW-comparative"]:
            selected = [r for r in rows if (r["seed"], r["head"]) == (seed, head)
                        and (group == "all" or r["source_group"] == group)]
            aggregates.append({"seed": seed, "head": head, "source_group": group,
                               "records": len(selected),
                               **{key: sum(r[key] for r in selected) for key in
                                  ("reference_pairs", "false_positive_pairs", *CATEGORIES)},
                               "mean_pair_f1": statistics.mean(r["pair_f1"] for r in selected) if selected else None})
    return {"rows": rows, "aggregates": aggregates, "planned_predictions": 9*len(records),
            "measured_predictions": len(rows), "test_evaluated": False,
            "checkpoint_selected": False, "model_fitted": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    source_path = ROOT / "results/pair_head_development_study_summary.json"
    records, _, sources = replay(source_path)
    source = json.loads(source_path.read_text())
    # Bind every checkpoint before inference, in addition to stored prediction hashes.
    for component in source["components"]:
        _, _, checkpoint, _ = load_checkpoint(Path(component["summary"]))
        sources[str(checkpoint)] = digest(checkpoint.read_bytes())
    paths = [Path(__file__), ROOT / "scripts/analyze_development_slices.py",
             *sorted((ROOT / "src/rnastable").glob("*.py"))]
    code = {str(p): digest(p.read_bytes()) for p in paths}
    if args.verify:
        summary = json.loads((ROOT / "results" / (NAME + "_summary.json")).read_text())
        run = Path(summary["run_dir"])
        require(summary == json.loads((run / "summary.json").read_text()), "Retained summary differs")
        manifest = json.loads((run / "manifest.json").read_text())
        require(digest((run / "manifest.json").read_bytes()) == summary["manifest_sha256"]
                and manifest["source_sha256"] == sources and manifest["code_sha256"] == code
                and manifest["limitations"] == LIMITATIONS, "Frozen diagnostic bindings differ")
        require(json.loads((run / "validation.json").read_text()) == records
                and digest((run / "validation.json").read_bytes()) == manifest["validation_sha256"],
                "Frozen diagnostic records differ")
        event = summary["exposure_event"]
        path = Path(event["path"])
        require(path.resolve().parent == (run / "exposures").resolve()
                and digest(path.read_bytes()) == event["sha256"], "Exposure binding differs")
        exposed = read_exposure(path)
        require(exposed["stage"] == "validation_started" and exposed["records"] ==
                exposure_records(records, str(run) + " validation_started"), "Exposure inventory differs")
    else:
        run = ROOT / "results" / (NAME + "_runs") / timestamp()
        run.mkdir(parents=True, exist_ok=False)
        atomic_json(run / "validation.json", records)
        manifest = {"run_dir": str(run), "source_sha256": sources, "code_sha256": code,
                    "validation_sha256": digest((run / "validation.json").read_bytes()),
                    "limitations": LIMITATIONS}
        atomic_json(run / "manifest.json", manifest)
        event = record_exposure(run, "validation_started", records)
    analysis = run_analysis(records, source["components"])
    require(analysis["planned_predictions"] == analysis["measured_predictions"] == 423,
            "Development prediction denominator changed")
    if args.verify:
        require(analysis == summary["analysis"], "Candidate diagnostic replay differs")
        print("Candidate diagnostics audit passed:423 development predictions, complete contact partitions; no fitting, test or native folds.")
        return summary
    summary = {"complete": True, "run_dir": str(run), "manifest_sha256": digest((run / "manifest.json").read_bytes()),
               "exposure_event": event, "analysis": analysis}
    atomic_json(run / "summary.json", summary)
    report = ["# Sparse candidate development diagnostics", "", *LIMITATIONS, "",
              "Contact counts are summed over records; F1 is a mean over records. Each reference contact appears in exactly one category.", "",
              "| Seed | Head | Group | Records | Gold pairs | Illegal | Nonpositive | Positive pruned | Retained missed | Recovered | False positives | Mean F1 |",
              "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    fields = ["seed", "head", "source_group", "records", "reference_pairs", *CATEGORIES,
              "false_positive_pairs", "mean_pair_f1"]
    for row in analysis["aggregates"]:
        report.append("| " + " | ".join(str(row[k]) for k in fields) + " |")
    publish(ROOT, NAME, summary, analysis["rows"], list(analysis["rows"][0]), "\n".join(report)+"\n")
    return summary


if __name__ == "__main__":
    main()
