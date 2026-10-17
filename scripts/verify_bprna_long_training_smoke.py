#!/usr/bin/env python3
"""Replay the frozen long bpRNA training-only selection."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.exposures import exposure_records, read_exposure  # noqa: E402
from rnastable.reference import digest  # noqa: E402
from prepare_bprna_training_subset import read_candidate  # noqa: E402
from prepare_bprna_training_subset_v2 import masks, overlap_after_lcs  # noqa: E402
from prepare_bprna_long_training_smoke import audit_protocol  # noqa: E402


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    if summary != json.loads((run / "summary.json").read_text()):
        raise ValueError("Long bpRNA summary identity differs")
    protocol = json.loads((run / "protocol.json").read_text())
    frozen, config, inventory = audit_protocol(Path(protocol["run_dir"]) / "manifest.json")
    if protocol != frozen:
        raise ValueError("Long bpRNA run protocol differs")
    plan = Path(protocol["run_dir"])
    headers = json.loads((plan / "candidates.json").read_text())
    exposed = json.loads((plan / "exposures.json").read_text())
    source = Path(inventory["source_run_dir"]) / "source.zip"
    if digest(source.read_bytes()) != inventory["source_sha256"]:
        raise ValueError("Long bpRNA source changed")
    valid, errors = [], {}
    with zipfile.ZipFile(source) as archive:
        for header in headers:
            try:
                valid.append(read_candidate(archive, header))
            except (ValueError, KeyError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
                errors[header["id"]] = type(exc).__name__ + ": " + str(exc)
    if valid != json.loads((run / "valid_records.json").read_text()):
        raise ValueError("Long bpRNA source record replay differs")
    event = summary["exposure_event"]
    event_path = Path(event["path"])
    if (event["stage"] != "training_started"
            or digest(event_path.read_bytes()) != event["sha256"]
            or read_exposure(event_path)["records"] != exposure_records(
                valid, str(run) + " training_started")):
        raise ValueError("Long bpRNA exposure event differs")
    known = sorted({row["sequence"] for row in exposed})
    known_masks = [(sequence, masks(sequence)) for sequence in known]
    by_id = {row["id"]: row for row in valid}
    selected, decisions = [], []
    for header in headers:
        row = by_id.get(header["id"])
        if row is None:
            reason = "unsupported_source_record"
        elif not row["pairs"] or not row["legal_canonical_pairs"]:
            reason = "no_legal_training_pairs"
        elif any(overlap_after_lcs(row["sequence"], old, old_masks, 0.8)
                 for old, old_masks in known_masks):
            reason = "prior_exposure_overlap"
        elif any(overlap_after_lcs(row["sequence"], old["sequence"],
                                   masks(old["sequence"]), 0.8) for old in selected):
            reason = "within_screen_overlap"
        else:
            reason = "training_only_candidate"
            selected.append(row)
        decisions.append({"id": header["id"], "reason": reason,
                          "error": errors.get(header["id"]),
                          "sequence_sha256": row["sequence_sha256"] if row else None})
    if {"selected": selected, "decisions": decisions} != json.loads(
            (run / "selection.json").read_text()):
        raise ValueError("Long bpRNA sequence selection replay differs")
    expected = {"complete": True, "run_dir": str(run),
                "candidate_count": len(headers), "valid_sequence_count": len(valid),
                "selected_training_only_count": len(selected),
                "selected_length_min_nt": min((len(r["sequence"]) for r in selected), default=None),
                "selected_length_max_nt": max((len(r["sequence"]) for r in selected), default=None),
                "reason_counts": dict(sorted(Counter(r["reason"] for r in decisions).items())),
                "exposure_event": event, "training_only": True,
                "model_training_performed": False, "model_inference_performed": False,
                "independent_test_claim": False}
    if summary != expected:
        raise ValueError("Long bpRNA summary values/policy differ")
    print("Long bpRNA training-only screen replay passed:", len(selected), "selected")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", type=Path)
    audit(parser.parse_args().summary)


if __name__ == "__main__":
    main()
