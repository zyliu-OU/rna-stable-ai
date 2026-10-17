#!/usr/bin/env python3
"""Bounded native baselines on the frozen longer development cohort."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.exposures import record_exposure  # noqa: E402
from rnastable.folding import fold_sequence  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.pair_reference import pair_agreement, validate_pairs  # noqa: E402
from rnastable.reference import digest  # noqa: E402
from rnastable.scoring import base_pairs  # noqa: E402

COHORT = ROOT / "results/long_validation_coverage_runs/20261017T033935.363253Z"
PROTOCOL = ROOT / "results/long_native_controls_protocol.json"
METHODS = ("LinearFold", "ViennaRNA")
CONFIG = {"temperature_c": 37, "beam_size": 100,
          "timeout_seconds": 30, "memory_limit_gib": 4}
CODE = [Path(__file__), *(ROOT / "src/rnastable" / name for name in (
    "folding.py", "vienna_worker.py", "pair_reference.py", "scoring.py"))]


def inputs():
    summary = json.loads((COHORT / "summary.json").read_text())
    if (summary["ready_for_development_validation"] is not True
            or summary["selected_complete_reference_count"] != 11
            or summary["label_informed_selection"] is not True):
        raise ValueError("Long native development cohort differs")
    records = json.loads((COHORT / "selection.json").read_text())["selected"]
    if len(records) != 11:
        raise ValueError("Long native reference inventory differs")
    return records


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    records = inputs()
    run = ROOT / "results/long_native_controls_protocol_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "records.json", records)
    atomic_json(run / "config.json", CONFIG)
    atomic_json(run / "policy.json", {
        "schema_version": 1, "stage": "longer_development_native_comparison",
        "methods": list(METHODS), "maximum_seconds_per_record_method": 30,
        "cohort_label_informed": True, "development_validation_only": True,
        "failed_folds_remain_unknown": True, "independent_test_claim": False})
    manifest = {"run_dir": str(run),
                "cohort_summary_sha256": digest((COHORT / "summary.json").read_bytes()),
                "cohort_selection_sha256": digest((COHORT / "selection.json").read_bytes()),
                "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
                "code_sha256": {str(path): digest(path.read_bytes()) for path in CODE}}
    atomic_json(run / "manifest.json", manifest)
    audit_protocol(run / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen longer native control study:", run / "manifest.json")


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    if manifest != json.loads((run / "manifest.json").read_text()):
        raise ValueError("Long native protocol manifest differs")
    if set(manifest["snapshot_sha256"]) != {"records.json", "config.json", "policy.json"}:
        raise ValueError("Long native snapshot inventory differs")
    for name, sha in manifest["snapshot_sha256"].items():
        if digest((run / name).read_bytes()) != sha:
            raise ValueError("Long native snapshot changed")
    for name, sha in manifest["code_sha256"].items():
        if digest(Path(name).read_bytes()) != sha:
            raise ValueError("Long native code changed")
    if (digest((COHORT / "summary.json").read_bytes()) != manifest["cohort_summary_sha256"]
            or digest((COHORT / "selection.json").read_bytes()) != manifest["cohort_selection_sha256"]
            or inputs() != json.loads((run / "records.json").read_text())
            or json.loads((run / "config.json").read_text()) != CONFIG):
        raise ValueError("Long native input/source differs")
    policy = json.loads((run / "policy.json").read_text())
    if (policy["methods"] != list(METHODS)
            or policy["failed_folds_remain_unknown"] is not True
            or policy["independent_test_claim"] is not False):
        raise ValueError("Long native policy differs")
    return manifest, inputs()


def score(result, record):
    if result["status"] != "ok":
        return None
    predicted = base_pairs(result["structure"])
    gold = validate_pairs(record["pairs"], len(record["sequence"]))
    return pair_agreement(predicted, gold)


def execute():
    protocol, records = audit_protocol(PROTOCOL)
    run = ROOT / "results/long_native_controls_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "protocol.json", protocol)
    event = record_exposure(run, "validation_started", records)
    rows = []
    for record in records:
        for method in METHODS:
            print(method, record["id"], len(record["sequence"]), flush=True)
            result = fold_sequence(ROOT, record["sequence"], CONFIG, method,
                                   run / "raw" / (record["id"].replace("/", "_")
                                                   + "_" + method + ".txt"))
            metrics = score(result, record)
            rows.append({"id": record["id"], "family_id": record["family_id"],
                         "length_nt": len(record["sequence"]), "method": method,
                         "fold": result, "metrics": metrics})
            atomic_json(run / "rows.json", rows)
    groups = defaultdict(list)
    status = defaultdict(lambda: defaultdict(int))
    for row in rows:
        status[row["method"]][row["fold"]["status"]] += 1
        if row["metrics"] is not None:
            groups[row["method"]].append(row["metrics"]["pair_f1"])
    summary = {"complete": True, "run_dir": str(run),
               "record_count": len(records), "method_count": len(METHODS),
               "status_counts": {m: dict(sorted(status[m].items())) for m in METHODS},
               "successful_mean_pair_f1": {m: (sum(groups[m]) / len(groups[m]) if groups[m] else None)
                                           for m in METHODS},
               "cohort_label_informed": True, "development_validation_only": True,
               "failed_folds_remain_unknown": True, "independent_test_claim": False,
               "exposure_event": event}
    atomic_json(run / "summary.json", summary)
    print("Longer native comparison:", run / "summary.json")
    print(summary["status_counts"], summary["successful_mean_pair_f1"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--verify-protocol", type=Path)
    args = parser.parse_args()
    if args.freeze:
        freeze()
    elif args.run:
        execute()
    else:
        audit_protocol(args.verify_protocol)
        print("Long native control protocol replay passed")


if __name__ == "__main__":
    main()
