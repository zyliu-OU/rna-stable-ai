"""Derive per-task accuracy and training-overlap evidence for RiboNN tasks.

Reads the pinned released supplementary tables from a directory the caller
supplies, verifies their hashes, pairs measured against predicted TE per task,
and cross-checks the result against the authors' own pooled test metrics.
Selects no task, freezes no floor and amends no gate.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

from rnastable.ribonn_task_evidence import (
    agreement, overlap_check, per_task_metrics, rank_tasks, read_sheet_columns,
    MEASURED_PREFIX, PREDICTED_PREFIX,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT/"configs/ribonn_task_evidence_v1_2026-10-19.json"
ASSAY_TASKS = ["A549", "Primary_CD4+_T-cells", "HSB2", "Molt-3", "HEK293T"]
REPORTER_NEEDLES = ["luc", "luciferase", "GFP", "nanoluc", "renilla"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, obj):
    with Path(path).open("x") as f:
        f.write(json.dumps(obj, indent=2, allow_nan=False)+"\n")


def source(config, role, sources_dir):
    for entry in config["sources"]:
        if entry["role"] != role:
            continue
        path = Path(sources_dir)/entry["file"]
        if not path.exists():
            raise ValueError(
                f"Missing pinned source {entry['file']}. Fetch it from {entry['url']} "
                f"into the directory passed as --sources-dir.")
        if path.stat().st_size != entry["bytes"] or sha(path) != entry["sha256"]:
            raise ValueError(f"Pinned source does not match its recorded hash: {entry['file']}")
        return path, entry
    raise ValueError(f"Config declares no source for role {role}")


def author_pooled_metrics():
    """The authors' own pooled test metrics from the retained weight archive."""
    runs = ROOT/"results/ribonn_weight_acquisition_runs/20261019T044334.430330Z/extracted/human/runs.csv"
    if not runs.exists():
        return None
    pearson, r2 = [], []
    for row in csv.DictReader(runs.open()):
        if row.get("metrics.test_pearson"):
            pearson.append(float(row["metrics.test_pearson"]))
        if row.get("metrics.test_r2"):
            r2.append(float(row["metrics.test_r2"]))
    if not pearson:
        return None
    return {"runs": len(pearson),
            "test_pearson_mean": sum(pearson)/len(pearson),
            "test_r2_mean": sum(r2)/len(r2) if r2 else None,
            "note": "Pooled over tasks per training run, not per task."}


def verify(run):
    """Re-check artifact hashes and replay the derived summary statistics."""
    manifest = json.loads((run/"manifest.json").read_text())
    for name, expected in manifest["artifacts"].items():
        path = run/name
        if not path.resolve().is_relative_to(run.resolve()) or sha(path) != expected:
            raise ValueError(f"Artifact checksum mismatch: {name}")
    rows = json.loads((run/"per_task_metrics.json").read_text())
    summary = json.loads((run/"summary.json").read_text())
    replayed = rank_tasks(rows, ASSAY_TASKS)
    if replayed != summary["assay_relevant_tasks"]:
        raise ValueError("Stored task ranking does not replay from stored metrics")
    if summary["task_selected"] or summary["gate_amended"]:
        raise ValueError("Stored run claims a task selection or gate amendment")
    result = {"artifacts_verified": len(manifest["artifacts"]),
              "tasks_evaluated": len(rows),
              "task_selected": False,
              "mode": "artifact and stored-metric audit; no re-derivation"}
    print(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT)
    parser.add_argument("--sources-dir", type=Path,
                        help="directory holding the pinned supplementary files")
    parser.add_argument("--verify-run", type=Path)
    args = parser.parse_args()
    if args.verify_run:
        verify(args.verify_run.resolve())
        return
    config = json.loads(args.config.read_text())
    for flag in ("task_selected", "floors_frozen", "gate_amended",
                 "new_sequence_scoring_enabled", "expression_candidate_design_enabled",
                 "stage3_ready"):
        if config[flag]:
            raise ValueError(f"Evidence audit must not set {flag}")
    if not args.sources_dir:
        raise SystemExit("--sources-dir is required; the pinned supplementary files are not "
                         "retained in this repository. See the config for URLs and hashes.")

    measured_path, measured_entry = source(config, "measured_te_human", args.sources_dir)
    predicted_path, predicted_entry = source(config, "predicted_te_human", args.sources_dir)
    method = config["method"]

    measured, measured_rows = read_sheet_columns(
        measured_path, measured_entry["sheet"],
        lambda n: n == "tx_id" or n == "SYMBOL" or n.startswith(MEASURED_PREFIX))
    predicted, predicted_rows = read_sheet_columns(
        predicted_path, predicted_entry["sheet"],
        lambda n: n == "tx_id" or n.startswith(PREDICTED_PREFIX))

    symbols = list(measured.get("SYMBOL", {}).values())
    overlap = overlap_check(symbols, REPORTER_NEEDLES)
    rows = per_task_metrics(measured, predicted, method["minimum_n"])
    ranked = rank_tasks(rows, ASSAY_TASKS)
    authors = author_pooled_metrics()

    pearson = sorted(r["pearson"] for r in rows)
    r2 = sorted(r["r2"] for r in rows)
    derived_mean_pearson = sum(pearson)/len(pearson)
    consistency = None
    if authors:
        consistency = {
            "authors_pooled_test_pearson_mean": authors["test_pearson_mean"],
            "derived_per_task_pearson_mean": derived_mean_pearson,
            "derived_at_or_below_authors": derived_mean_pearson <= authors["test_pearson_mean"],
            "verdict": ("consistent with out-of-fold predictions"
                        if derived_mean_pearson <= authors["test_pearson_mean"]
                        else "derived accuracy EXCEEDS the authors' pooled test metrics; the "
                             "held-out assumption is in doubt and the figures must be discarded "
                             "rather than adjusted")}

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out = ROOT/"results/ribonn_task_evidence_runs"/stamp
    out.mkdir(parents=True, exist_ok=False)
    print(out, flush=True)
    write(out/"protocol.json", config)
    write(out/"per_task_metrics.json", rows)
    write(out/"training_overlap.json", overlap)

    implementations = [Path(__file__), ROOT/"src/rnastable/ribonn_task_evidence.py"]
    identities = {}
    for path in implementations:
        target = out/"source"/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        identities[str(path.relative_to(ROOT))] = sha(path)
    write(out/"identity.json",
          {"implementation": identities, "config_sha256": sha(args.config),
           "sources": {e["role"]: {"file": e["file"], "sha256": e["sha256"], "url": e["url"]}
                       for e in config["sources"]},
           "sources_retained_in_repo": False})

    summary = {
        "measured_transcripts": measured_rows, "predicted_transcripts": predicted_rows,
        "transcripts_without_predictions": measured_rows-predicted_rows,
        "tasks_evaluated": len(rows),
        "pearson": {"min": pearson[0], "median": pearson[len(pearson)//2],
                    "max": pearson[-1], "mean": derived_mean_pearson},
        "r2": {"min": r2[0], "median": r2[len(r2)//2], "max": r2[-1],
               "mean": sum(r2)/len(r2)},
        "assay_relevant_tasks": ranked,
        "authors_pooled_metrics": authors,
        "held_out_consistency_check": consistency,
        "held_out_assumption": method["held_out_assumption"],
        "training_overlap": overlap,
        "interpretation_rules": config["interpretation_rules"],
        "no_claim_permitted": config["no_claim_permitted"],
        "task_selected": False, "floors_frozen": False, "gate_amended": False,
        "new_sequence_scoring_enabled": False, "stage3_ready": False,
        "interpretation": "Per-task accuracy of the released model on endogenous human "
                          "transcripts, recomputed from released tables. Not an independent "
                          "evaluation, and not applicable to a designed reporter construct."}
    write(out/"summary.json", summary)
    artifacts = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob("*")) if p.is_file()}
    write(out/"manifest.json", {"run": stamp, "artifacts": artifacts})
    print(json.dumps({k: summary[k] for k in
                      ("tasks_evaluated", "pearson", "r2", "assay_relevant_tasks",
                       "held_out_consistency_check")}, indent=2))


if __name__ == "__main__":
    main()
