#!/usr/bin/env python3
"""Replay both frozen longer-family screens without downloads or inference."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.exposures import exposure_records, read_exposure  # noqa: E402
from rnastable.pair_model import CANONICAL  # noqa: E402
from rnastable.pair_reference import validate_pairs  # noqa: E402
from rnastable.prospective_binding import bind_pair_reference, parse_stockholm  # noqa: E402
from rnastable.reference import digest  # noqa: E402
import prepare_long_validation_family as v1  # noqa: E402
import prepare_long_validation_family_v2 as v2  # noqa: E402


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    if summary != json.loads((run / "summary.json").read_text()):
        raise ValueError("Summary identity differs")
    module = v2 if "_v2_runs" in str(run) else v1
    protocol = json.loads((run / "protocol.json").read_text())
    frozen, config, exposed = module.audit_protocol(
        Path(protocol["run_dir"]) / "manifest.json")
    if protocol != frozen:
        raise ValueError("Run protocol binding differs")
    attempts = json.loads((run / "attempts.json").read_text())
    if [row["family_id"] for row in attempts] != config["families"]:
        raise ValueError("Attempt family inventory differs")
    alignments = {}
    for row in attempts:
        source = run / (row["family_id"] + ".sto")
        if row["status"] == "ok":
            if digest(source.read_bytes()) != row["sha256"]:
                raise ValueError("Source hash differs")
            alignment = parse_stockholm(source.read_bytes(), row["family_id"])
            if len(alignment["sequences"]) != row["alignment_sequences"]:
                raise ValueError("Source sequence count differs")
            alignments[row["family_id"]] = alignment
        elif row["status"] != "failed" or source.exists():
            raise ValueError("Attempt status/source inventory differs")
    selected, decisions = module.select_candidates(alignments, config, exposed)
    if {"selected": selected, "decisions": decisions} != json.loads(
            (run / "selection.json").read_text()):
        raise ValueError("Frozen sequence selection replay differs")
    event = summary["exposure_event"]
    if bool(event) != bool(selected):
        raise ValueError("Selection exposure inventory differs")
    if event:
        event_path = Path(event["path"])
        if (digest(event_path.read_bytes()) != event["sha256"]
                or read_exposure(event_path)["records"] != exposure_records(
                    selected, str(run) + " validation_started")):
            raise ValueError("Selection exposure event differs")
    bound = []
    for row in selected:
        try:
            result = bind_pair_reference(row, alignments[row["family_id"]])
            validate_pairs(result["pairs"], len(result["sequence"]))
            if not any(j - i >= 4 and result["sequence"][i] + result["sequence"][j]
                       in CANONICAL for i, j in result["pairs"]):
                raise ValueError("No legal canonical reference pairs")
            bound.append({**result, "reference_status": "ok"})
        except (ValueError, KeyError, TypeError) as exc:
            bound.append({**row, "reference_status": "unsupported_reference",
                          "error": type(exc).__name__ + ": " + str(exc)})
    if bound != json.loads((run / "binding.json").read_text()):
        raise ValueError("Pair binding replay differs")
    counts = Counter(row["family_id"] for row in bound if row["reference_status"] == "ok")
    ready = (all(counts[family] >= config["minimum_complete_per_family"]
                 for family in config["families"])
             and sum(counts.values()) >= config["minimum_complete_total"])
    expected = {"complete": True, "run_dir": str(run),
                "ready_for_development_validation": ready,
                "family_complete_counts": dict(sorted(counts.items())),
                "selected_sequence_count": len(selected),
                "complete_reference_count": sum(counts.values()),
                "decision_counts": dict(sorted(Counter(d["reason"] for d in decisions).items())),
                "attempt_statuses": {row["family_id"]: row["status"] for row in attempts},
                "development_validation_only": True, "model_inference_performed": False,
                "independent_test_claim": False,
                "known_bpRNA_family_lineage_complete": False,
                "exposure_event": event}
    if summary != expected:
        raise ValueError("Summary metrics/policy differ")
    print(f"Longer family replay passed: {run}; complete={sum(counts.values())}, ready={ready}")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", type=Path)
    audit(parser.parse_args().summary)


if __name__ == "__main__":
    main()
