#!/usr/bin/env python3
"""Acquire modeled-residue counts for all frozen long-shortlist RNA chains."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.artifacts import timestamp
from rnastable.native_journal import atomic_json
from rnastable.reference import digest
from inspect_rcsb_long_shortlist import verify as verify_metadata

METADATA = ROOT / "results/rcsb_long_shortlist_metadata_runs/20261018T222614.858678Z"
SCHEMA = ROOT / "results/rcsb_instance_schema_2026-10-18.json"
QUERY = """query Coverage($ids:[String!]!){polymer_entity_instances(instance_ids:$ids){
rcsb_id rcsb_polymer_instance_container_identifiers{entry_id entity_id asym_id auth_asym_id}
rcsb_polymer_instance_info{modeled_residue_count}
}}"""


def freeze():
    rows = verify_metadata(METADATA)
    instances = []
    for row in rows:
        ids = row["rcsb_polymer_entity_container_identifiers"]
        for chain in ids["asym_ids"]:
            instances.append({"instance_id": ids["entry_id"] + "." + chain,
                              "entity_id": row["rcsb_id"],
                              "sample_length_nt": row["entity_poly"]["rcsb_sample_sequence_length"]})
    folder = ROOT / "results/rcsb_long_coverage_protocol_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {"run_dir": str(folder), "metadata_run": str(METADATA),
                "metadata_retrieval_sha256": digest((METADATA / "retrieval.json").read_bytes()),
                "schema_sha256": digest(SCHEMA.read_bytes()), "query": QUERY,
                "instances": sorted(instances, key=lambda r: r["instance_id"]),
                "driver_sha256": digest(Path(__file__).read_bytes()),
                "candidate_sequences_allowed": False, "contact_labels_allowed": False,
                "model_inference_allowed": False}
    atomic_json(folder / "manifest.json", manifest)
    print(folder / "manifest.json")


def audit(path):
    manifest = json.loads(Path(path).read_text())
    rows = verify_metadata(METADATA)
    expected = sorted([{"instance_id": r["rcsb_polymer_entity_container_identifiers"]["entry_id"] + "." + chain,
                        "entity_id": r["rcsb_id"], "sample_length_nt": r["entity_poly"]["rcsb_sample_sequence_length"]}
                       for r in rows for chain in r["rcsb_polymer_entity_container_identifiers"]["asym_ids"]],
                      key=lambda r: r["instance_id"])
    if (manifest != json.loads((Path(manifest["run_dir"]) / "manifest.json").read_text())
            or manifest["query"] != QUERY or manifest["instances"] != expected
            or manifest["driver_sha256"] != digest(Path(__file__).read_bytes())
            or manifest["metadata_retrieval_sha256"] != digest((METADATA / "retrieval.json").read_bytes())
            or manifest["schema_sha256"] != digest(SCHEMA.read_bytes())):
        raise ValueError("Coverage protocol differs")
    return manifest


def validate(data, ids):
    if data.get("errors"):
        raise ValueError(json.dumps(data["errors"]))
    rows = data["data"]["polymer_entity_instances"]
    if sorted(r["rcsb_id"] for r in rows if r) != sorted(ids):
        raise ValueError("Missing or duplicated coverage response identity")
    return rows


def acquire(path):
    manifest = audit(path)
    folder = ROOT / "results/rcsb_long_coverage_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    atomic_json(folder / "protocol.json", manifest)
    ids = [r["instance_id"] for r in manifest["instances"]]
    for offset in range(0, len(ids), 40):
        selected = ids[offset:offset + 40]
        url = "https://data.rcsb.org/graphql?" + urlencode({"query": QUERY, "variables": json.dumps({"ids": selected})})
        try:
            with urlopen(url, timeout=30) as response:
                raw = response.read(2000001)
            if len(raw) > 2000000:
                raise ValueError("Coverage response oversized")
            (folder / f"response_{offset:03d}.json").write_bytes(raw)
            validate(json.loads(raw), selected)
            print("Coverage batch:", offset, len(selected), flush=True)
        except Exception as error:
            atomic_json(folder / "error.json", {"error": str(error)})
            raise
    atomic_json(folder / "retrieval.json", {"retrieved_utc": datetime.now(timezone.utc).isoformat(),
                "files_sha256": {p.name: digest(p.read_bytes()) for p in folder.iterdir()}})
    print(folder)


def verify(folder):
    manifest = audit(folder / "protocol.json")
    retrieval = json.loads((folder / "retrieval.json").read_text())
    for name, sha in retrieval["files_sha256"].items():
        if digest((folder / name).read_bytes()) != sha:
            raise ValueError("Coverage source bytes differ")
    ids = [r["instance_id"] for r in manifest["instances"]]
    rows = []
    for offset in range(0, len(ids), 40):
        rows.extend(validate(json.loads((folder / f"response_{offset:03d}.json").read_text()), ids[offset:offset + 40]))
    print("RCSB long coverage replay passed:", len(rows))
    return rows, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--acquire", type=Path)
    mode.add_argument("--verify-run", type=Path)
    args = parser.parse_args()
    if args.freeze:
        freeze()
    elif args.acquire:
        acquire(args.acquire)
    else:
        verify(args.verify_run)


if __name__ == "__main__":
    main()
