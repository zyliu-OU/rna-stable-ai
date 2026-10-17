#!/usr/bin/env python3
"""Audit bounded native outputs against saved complete pair references."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.exposures import exposure_records, read_exposure  # noqa: E402
from rnastable.folding import parse_output  # noqa: E402
from rnastable.reference import digest  # noqa: E402
from evaluate_long_native_controls import (  # noqa: E402
    COHORT, METHODS, audit_protocol, score,
)
from verify_long_validation_coverage import audit as audit_cohort  # noqa: E402


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    if summary != json.loads((run / "summary.json").read_text()):
        raise ValueError("Long native summary identity differs")
    audit_cohort(COHORT / "summary.json")
    protocol = json.loads((run / "protocol.json").read_text())
    frozen, records = audit_protocol(Path(protocol["run_dir"]) / "manifest.json")
    if protocol != frozen:
        raise ValueError("Long native protocol binding differs")
    event = summary["exposure_event"]
    event_path = Path(event["path"])
    if (event["stage"] != "validation_started"
            or digest(event_path.read_bytes()) != event["sha256"]
            or read_exposure(event_path)["records"] != exposure_records(
                records, str(run) + " validation_started")):
        raise ValueError("Long native exposure event differs")
    rows = json.loads((run / "rows.json").read_text())
    if [(row["id"], row["method"]) for row in rows] != [
            (record["id"], method) for record in records for method in METHODS]:
        raise ValueError("Long native row order/inventory differs")
    status = defaultdict(lambda: defaultdict(int))
    values = defaultdict(list)
    for row, record in zip(rows, (r for r in records for _ in METHODS), strict=True):
        if row["family_id"] != record["family_id"] or row["length_nt"] != len(record["sequence"]):
            raise ValueError("Long native sequence identity differs")
        fold = row["fold"]
        status[row["method"]][fold["status"]] += 1
        if fold["status"] == "ok":
            raw = Path(fold["raw_output"])
            if not raw.is_file() or run not in raw.parents:
                raise ValueError("Long native raw output missing")
            replay = parse_output(row["method"], raw.read_text(), len(record["sequence"]))
            if any(fold[key] != value for key, value in replay.items()):
                raise ValueError("Long native raw fold parse differs")
        metrics = score(fold, record)
        if row["metrics"] != metrics:
            raise ValueError("Long native pair-score replay differs")
        if metrics is not None:
            values[row["method"]].append(metrics["pair_f1"])
    expected_status = {m: dict(sorted(status[m].items())) for m in METHODS}
    expected_means = {m: (sum(values[m]) / len(values[m]) if values[m] else None)
                      for m in METHODS}
    if (summary["record_count"] != len(records)
            or summary["method_count"] != len(METHODS)
            or summary["status_counts"] != expected_status
            or summary["successful_mean_pair_f1"] != expected_means
            or summary["failed_folds_remain_unknown"] is not True
            or summary["independent_test_claim"] is not False):
        raise ValueError("Long native summary values/policy differ")
    print("Long native control replay passed:", expected_status, expected_means)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", type=Path)
    audit(parser.parse_args().summary)


if __name__ == "__main__":
    main()
