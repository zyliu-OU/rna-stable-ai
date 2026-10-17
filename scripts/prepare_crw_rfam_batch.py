#!/usr/bin/env python3
"""Freeze six unresolved CRW sequences for Rfam single-sequence searches."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.reference import digest  # noqa: E402

SELECTED = ROOT / "results/bprna_long_training_smoke_runs/20261017T033749.792816Z/selection.json"
FIRST = ROOT / "results/crw_rfam_13049_completed_response.json"


def main():
    records = [r for r in json.loads(SELECTED.read_text())["selected"]
               if r["source_group"] == "CRW"]
    first = json.loads(FIRST.read_text())
    first_record = next(r for r in records if r["id"] == "bpRNA_CRW_13049")
    if (len(records) != 7 or first["searchSequence"] != first_record["sequence"]
            or first["jobId"] != "infernal_cmscan-R20261017-195709-0511-4231837-p1m"
            or not first["hits"] or not first["closed"]):
        raise ValueError("First CRW search is not sequence-bound and completed")
    folder = ROOT / "results/crw_rfam_batch_protocol_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    requests = []
    for record in sorted(records, key=lambda r: r["id"]):
        if record["id"] == first_record["id"]:
            continue
        sequence = record["sequence"]
        if not 1 <= len(sequence) < 5000 or set(sequence) - set("ACGU"):
            raise ValueError("CRW record is outside active scope")
        filename = record["id"] + ".seq"
        data = (sequence + "\n").encode()
        (folder / filename).write_bytes(data)
        requests.append({"id": record["id"], "filename": filename,
                         "length_nt": len(sequence),
                         "sequence_sha256": hashlib.sha256(sequence.encode()).hexdigest(),
                         "file_sha256": digest(data),
                         "url": "https://batch.rfam.org/submit-job"})
    manifest = {"stage": "crw_rfam_single_sequence_batch_queries",
                "run_dir": str(folder), "selected_sha256": digest(SELECTED.read_bytes()),
                "first_response_sha256": digest(FIRST.read_bytes()),
                "driver_sha256": digest(Path(__file__).read_bytes()),
                "requests": requests, "family_assignment_claim": False}
    atomic_json(folder / "manifest.json", manifest)
    print(folder / "manifest.json")


if __name__ == "__main__":
    main()
