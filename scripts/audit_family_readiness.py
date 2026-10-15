#!/usr/bin/env python3
"""Snapshot/replay local family readiness without opening new structure labels."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import publish, timestamp
from rnastable.exposures import collect_known_exposures
from rnastable.family_readiness import METADATA_FILES, metadata_records, screen_families
from rnastable.native_journal import atomic_json
from rnastable.reference import digest
from rnastable.reference_audit import require


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(
        summary == json.loads((run / "summary.json").read_text()),
        "Retained readiness differs",
    )
    manifest_bytes = (run / "manifest.json").read_bytes()
    require(
        digest(manifest_bytes) == summary["manifest_sha256"],
        "Readiness manifest changed",
    )
    manifest = json.loads(manifest_bytes)
    require(manifest["run_dir"] == str(run), "Readiness run identity differs")
    expected_files = {split + ".fasta" for split in METADATA_FILES} | {"exposure.json"}
    require(
        set(manifest["snapshot_sha256"]) == expected_files,
        "Readiness snapshot inventory differs",
    )
    for name, sha in manifest["snapshot_sha256"].items():
        require(
            digest((run / name).read_bytes()) == sha,
            "Readiness snapshot changed: " + name,
        )
    expected = screen_families(
        metadata_records(
            {split: (run / (split + ".fasta")).read_bytes() for split in METADATA_FILES}
        ),
        json.loads((run / "exposure.json").read_text()),
        manifest["minimum_length"],
        manifest["maximum_length"],
    )
    require(expected == summary["screening"], "Readiness screening replay differs")
    print(
        "Family readiness replay passed: frozen metadata and exposure ledger; no new structure labels or inference."
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        return audit(ROOT / "results/family_readiness_summary.json")
    paths = {
        split: ROOT / "external/EternaFold/datasets_in_fasta_form" / name
        for split, name in METADATA_FILES.items()
    }
    contents = {split: path.read_bytes() for split, path in paths.items()}
    exposed = collect_known_exposures(ROOT)
    screening = screen_families(metadata_records(contents), exposed)
    run = ROOT / "results/family_readiness_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    for split, content in contents.items():
        (run / (split + ".fasta")).write_bytes(content)
    atomic_json(run / "exposure.json", exposed)
    manifest = {
        "run_dir": str(run),
        "minimum_length": 20,
        "maximum_length": 1024,
        "source_sha256": {
            str(paths[split]): digest(content) for split, content in contents.items()
        },
        "snapshot_sha256": {
            p.name: digest(p.read_bytes()) for p in run.iterdir() if p.is_file()
        },
        "policy": "FASTA metadata/sequence screening against known prior exposures; no BPSEQ/archive access, model fitting or prediction. Replay describes this frozen ledger, not future readiness.",
    }
    atomic_json(run / "manifest.json", manifest)
    summary = {
        "complete": True,
        "run_dir": str(run),
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "screening": screening,
    }
    atomic_json(run / "summary.json", summary)
    report = [
        "# Metadata-only family evaluation readiness",
        "",
        manifest["policy"],
        "",
        screening["interpretation"],
        "",
        f"Checked {screening['exposure_records_checked']} exposures; {screening['exposure_records_without_family_id']} lack family IDs.",
        f"Found {screening['metadata_records']} Rfam metadata records and {screening['metadata_candidates']} metadata candidates.",
        "",
        "| Family | Records | Candidates | Reasons |",
        "|---|---:|---:|---|",
    ]
    for row in screening["families"]:
        report.append(
            f"| {row['family_id']} | {row['metadata_records']} | {row['metadata_candidates']} | {json.dumps(row['reason_counts'], sort_keys=True)} |"
        )
    report += [
        "",
        "No new structure labels were opened and no test exposure or prediction was created.",
        "",
    ]
    publish(
        ROOT,
        "family_readiness",
        summary,
        screening["rows"],
        ["id", "upstream_split", "family_id", "sequence_sha256", "length", "reason"],
        "\n".join(report),
    )
    audit(run / "summary.json")
    print(f"Metadata candidates: {screening['metadata_candidates']}")
    return summary


if __name__ == "__main__":
    main()
