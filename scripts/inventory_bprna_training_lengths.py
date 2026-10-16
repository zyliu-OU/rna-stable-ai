#!/usr/bin/env python3
"""Inventory bpRNA dot-bracket header lengths without reading sequences/labels."""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.reference import digest  # noqa: E402
from acquire_bprna_training_source import audit as audit_source  # noqa: E402

SOURCE_SUMMARY = ROOT / "results/bprna_training_source_runs/20261016T173354.858608Z/summary.json"
OUTPUT = ROOT / "results/bprna_training_length_inventory_2026-10-16.json"
NAME = re.compile(r"dbnFiles/(bpRNA_([A-Za-z0-9]+)_\d+)\.dbn\Z")
LENGTH = re.compile(r"#Length:\s*(\d+)\s*\Z")


def length_band(length):
    if length < 1:
        return "invalid"
    if length < 400:
        return "1_399"
    if length <= 1024:
        return "400_1024"
    if length < 5000:
        return "1025_4999"
    return "5000_plus_deferred"


def header_from(archive, info):
    match = NAME.fullmatch(info.filename)
    if match is None:
        raise ValueError("Unexpected bpRNA DBN path")
    with archive.open(info) as stream:
        name = stream.readline(256).decode("ascii").strip()
        length = stream.readline(256).decode("ascii").strip()
        page = stream.readline(256).decode("ascii").strip()
    if name != "#Name: " + match.group(1):
        raise ValueError("bpRNA DBN name/header differs")
    found = LENGTH.fullmatch(length)
    if found is None or not page.startswith("#PageNumber:"):
        raise ValueError("bpRNA DBN header is incomplete")
    number = int(found.group(1))
    if number < 1 or number > 100000:
        raise ValueError("bpRNA stated length out of bounds")
    return {"id": match.group(1), "source_group": match.group(2),
            "stated_length_nt": number, "zip_path": info.filename}


def inventory(archive):
    bands = Counter()
    groups = defaultdict(Counter)
    eligible, errors = [], []
    seen = set()
    for info in archive.infolist():
        if info.is_dir():
            continue
        try:
            row = header_from(archive, info)
            if row["id"] in seen:
                raise ValueError("Duplicate bpRNA ID")
            seen.add(row["id"])
            band = length_band(row["stated_length_nt"])
            bands[band] += 1
            groups[row["source_group"]][band] += 1
            if band in ("400_1024", "1025_4999"):
                eligible.append(row)
        except (UnicodeDecodeError, ValueError, OSError, zipfile.BadZipFile) as exc:
            errors.append({"zip_path": info.filename, "reason": type(exc).__name__})
    return {"all_file_count": len(archive.infolist()),
            "parsed_record_count": sum(bands.values()),
            "invalid_header_count": len(errors),
            "length_band_counts": dict(sorted(bands.items())),
            "source_group_length_band_counts": {
                group: dict(sorted(counts.items())) for group, counts in sorted(groups.items())},
            "eligible_400_4999_metadata_count": len(eligible),
            "eligible_400_4999_headers": sorted(eligible, key=lambda r: r["id"]),
            "invalid_headers": errors}


def compute():
    summary = audit_source(SOURCE_SUMMARY)
    if summary["source_status"] != "ok":
        raise ValueError("bpRNA training source not acquired")
    source = Path(summary["run_dir"]) / "source.zip"
    with zipfile.ZipFile(source) as archive:
        result = inventory(archive)
    result.update({
        "schema_version": 1,
        "stage": "training_source_header_length_inventory",
        "source_run_dir": summary["run_dir"],
        "source_sha256": digest(source.read_bytes()),
        "source_summary_sha256": digest(SOURCE_SUMMARY.read_bytes()),
        "training_only": True,
        "candidate_sequences_read": False,
        "structure_labels_read": False,
        "independent_test_use_authorized": False,
        "model_training_authorized": False,
        "model_inference_authorized": False,
        "limitations": [
            "Stated header lengths are not verified against sequence/structure strings.",
            "Source group is filename metadata, not independent provenance or family identity.",
            "All selected training sequences require exact validation, overlap screening, and durable exposure events before fitting.",
        ],
    })
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path, default=OUTPUT)
    mode.add_argument("--verify", type=Path)
    args = parser.parse_args()
    result = compute()
    if args.verify:
        if json.loads(args.verify.read_text()) != result:
            raise ValueError("bpRNA header-length inventory differs")
        print("bpRNA header-length inventory replay passed")
    else:
        with args.output.open("x") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
        print(args.output)
        print("Length bands:", result["length_band_counts"])
        print("400–4999 nt header candidates:", result["eligible_400_4999_metadata_count"])
        print("Invalid headers:", result["invalid_header_count"])


if __name__ == "__main__":
    main()
