#!/usr/bin/env python3
"""Audit CRW origin accessions in pinned Rfam 15.1 seed and region indexes."""

import argparse
from collections import defaultdict
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.reference import digest  # noqa: E402

ORIGINS = ROOT / "results/bprna_long_origin_binding_v2_runs/20261017T185531.913009Z/summary.json"
SEED = ROOT / "results/rfam_release_15_1_clan_source/Rfam.seed.gz"
REGIONS = ROOT / "results/rfam_release_15_1_clan_source/Rfam.full_region.gz"
PROTOCOL = ROOT / "results/crw_rfam_release_index_protocol.json"


def targets():
    rows = [r for r in json.loads(ORIGINS.read_text())["records"]
            if r["source_group"] == "CRW"]
    if len(rows) != 7:
        raise ValueError("CRW origin inventory changed")
    return {r["id"]: r["same_name_and_sequence_origin"]["original_accession_id"]
            for r in rows}


def policy():
    return {"rfam_release": "15.1", "match": "exact_unversioned_origin_accession",
            "seed_match_does_not_assign_whole_rna_family": True,
            "missing_region_does_not_prove_absence_of_homology": True,
            "independent_test_claim": False, "model_inference_performed": False}


def audit(path):
    manifest = json.loads(Path(path).read_text())
    folder = Path(manifest["run_dir"])
    if (manifest != json.loads((folder / "manifest.json").read_text())
            or manifest["policy"] != policy()
            or manifest["driver_sha256"] != digest(Path(__file__).read_bytes())):
        raise ValueError("Release-index protocol differs")
    for name, sha in manifest["inputs_sha256"].items():
        if digest(Path(name).read_bytes()) != sha:
            raise ValueError(f"Release-index source changed: {name}")
    targets()
    return manifest


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    targets()
    folder = ROOT / "results/crw_rfam_release_index_protocol_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {"run_dir": str(folder), "policy": policy(),
                "inputs_sha256": {str(p): digest(p.read_bytes())
                                  for p in (ORIGINS, SEED, REGIONS)},
                "driver_sha256": digest(Path(__file__).read_bytes())}
    atomic_json(folder / "manifest.json", manifest)
    audit(folder / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen release-index audit:", folder / "manifest.json")


def compute():
    by_id = targets()
    accessions = {a for a in by_id.values() if a != "NA"}
    seed_hits = defaultdict(list)
    family = None
    seed_family_count = 0
    with gzip.open(SEED, "rb") as stream:
        for line in stream:
            if line.startswith(b"#=GF AC "):
                family = line.split()[2].decode()
                seed_family_count += 1
            elif line.startswith(b"//"):
                family = None
            elif family and line and not line.startswith((b"#", b"/")):
                parts = line.split()
                if parts:
                    accession_region = parts[0].decode("ascii", errors="replace")
                    accession = accession_region.split("/")[0].split(".")[0]
                    if accession in accessions:
                        seed_hits[accession].append({"family_id": family,
                                                     "region": accession_region})
    regions = defaultdict(list)
    parsed = 0
    with gzip.open(REGIONS, "rb") as stream:
        for line in stream:
            parsed += 1
            parts = line.rstrip(b"\n").split(b"\t")
            if len(parts) < 10:
                raise ValueError("Malformed Rfam full-region row")
            accession = parts[1].decode("ascii").split(".")[0]
            if accession in accessions:
                regions[accession].append({"family_id": parts[0].decode("ascii"),
                                           "accession": parts[1].decode("ascii"),
                                           "start": int(parts[2]), "end": int(parts[3])})
    rows = [{"id": record_id, "origin_accession": accession,
             "seed_regions": sorted(seed_hits[accession], key=lambda r: (r["family_id"], r["region"])),
             "full_regions": sorted(regions[accession], key=lambda r: (r["family_id"], r["start"])),
             "whole_rna_family_assignment": None}
            for record_id, accession in sorted(by_id.items())]
    return {"policy": policy(), "seed_family_count": seed_family_count,
            "full_region_row_count": parsed, "records": rows,
            "accessions_with_seed_region": sum(bool(r["seed_regions"]) for r in rows),
            "accessions_with_full_region": sum(bool(r["full_regions"]) for r in rows)}


def run():
    manifest = audit(PROTOCOL)
    folder = ROOT / "results/crw_rfam_release_index_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    atomic_json(folder / "protocol.json", manifest)
    result = {"complete": True, "run_dir": str(folder), **compute()}
    atomic_json(folder / "summary.json", result)
    print("Release-index audit:", folder / "summary.json")
    print("Seed regions:", result["accessions_with_seed_region"],
          "full regions:", result["accessions_with_full_region"])


def verify(path):
    folder = Path(path).resolve().parent
    audit(folder / "protocol.json")
    expected = {"complete": True, "run_dir": str(folder), **compute()}
    if json.loads(Path(path).read_text()) != expected:
        raise ValueError("Release-index replay differs")
    print("Release-index replay passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--verify-run", type=Path)
    args = parser.parse_args()
    if args.freeze:
        freeze()
    elif args.run:
        run()
    else:
        verify(args.verify_run)


if __name__ == "__main__":
    main()
