#!/usr/bin/env python3
"""Recover comma-wrapped bpRNA length headers without rereading labels."""

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
from inventory_bprna_training_lengths import (  # noqa: E402
    NAME, OUTPUT as PRIOR, SOURCE_SUMMARY, length_band,
)

OUTPUT = ROOT / "results/bprna_training_length_inventory_2026-10-16_v2.json"
COMMA_LENGTH = re.compile(r"#Length:\s*,(\d+),\s*\Z")


def recover(archive, path):
    match = NAME.fullmatch(path)
    if match is None:
        return None
    with archive.open(path) as stream:
        name = stream.readline(256).decode("ascii").strip()
        length = stream.readline(256).decode("ascii").strip()
        page = stream.readline(256).decode("ascii").strip()
    found = COMMA_LENGTH.fullmatch(length)
    if name != "#Name: " + match.group(1) or found is None or not page.startswith("#PageNumber:"):
        return None
    number = int(found.group(1))
    if not 1 <= number <= 100000:
        return None
    return {"id": match.group(1), "source_group": match.group(2),
            "stated_length_nt": number, "zip_path": path,
            "header_format": "comma_wrapped_length"}


def compute():
    prior_raw = PRIOR.read_bytes()
    prior = json.loads(prior_raw)
    summary = audit_source(SOURCE_SUMMARY)
    if (prior["source_run_dir"] != summary["run_dir"]
            or prior["source_summary_sha256"] != digest(SOURCE_SUMMARY.read_bytes())
            or prior["candidate_sequences_read"] is not False
            or prior["structure_labels_read"] is not False):
        raise ValueError("Prior bpRNA inventory/source identity differs")
    source = Path(summary["run_dir"]) / "source.zip"
    if digest(source.read_bytes()) != prior["source_sha256"]:
        raise ValueError("bpRNA source bytes differ")
    recovered, unresolved = [], []
    with zipfile.ZipFile(source) as archive:
        for old in prior["invalid_headers"]:
            path = old["zip_path"]
            try:
                row = recover(archive, path)
            except (UnicodeDecodeError, OSError, ValueError, KeyError, zipfile.BadZipFile):
                row = None
            if row is None:
                unresolved.append(old)
            else:
                recovered.append(row)
    bands = Counter(prior["length_band_counts"])
    groups = defaultdict(Counter)
    for group, counts in prior["source_group_length_band_counts"].items():
        groups[group].update(counts)
    eligible = list(prior["eligible_400_4999_headers"])
    for row in recovered:
        band = length_band(row["stated_length_nt"])
        bands[band] += 1
        groups[row["source_group"]][band] += 1
        if band in ("400_1024", "1025_4999"):
            eligible.append(row)
    if len({row["id"] for row in eligible}) != len(eligible):
        raise ValueError("Recovered bpRNA metadata ID duplicates prior inventory")
    return {
        "schema_version": 2,
        "stage": "training_source_header_length_inventory",
        "prior_inventory_sha256": digest(prior_raw),
        "source_run_dir": summary["run_dir"],
        "source_sha256": prior["source_sha256"],
        "all_file_count": prior["all_file_count"],
        "parsed_record_count": prior["parsed_record_count"] + len(recovered),
        "recovered_comma_length_header_count": len(recovered),
        "unresolved_header_count": len(unresolved),
        "length_band_counts": dict(sorted(bands.items())),
        "source_group_length_band_counts": {
            group: dict(sorted(counts.items())) for group, counts in sorted(groups.items())},
        "eligible_400_4999_metadata_count": len(eligible),
        "eligible_400_4999_headers": sorted(eligible, key=lambda row: row["id"]),
        "unresolved_headers": unresolved,
        "training_only": True,
        "candidate_sequences_read": False,
        "structure_labels_read": False,
        "independent_test_use_authorized": False,
        "model_training_authorized": False,
        "model_inference_authorized": False,
        "limitations": prior["limitations"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path, default=OUTPUT)
    mode.add_argument("--verify", type=Path)
    args = parser.parse_args()
    result = compute()
    if args.verify:
        if json.loads(args.verify.read_text()) != result:
            raise ValueError("bpRNA recovered-header inventory differs")
        print("bpRNA recovered-header inventory replay passed")
    else:
        with args.output.open("x") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
        print(args.output)
        print("Length bands:", result["length_band_counts"])
        print("Recovered comma headers:", result["recovered_comma_length_header_count"])
        print("Unresolved headers:", result["unresolved_header_count"])


if __name__ == "__main__":
    main()
