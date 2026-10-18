#!/usr/bin/env python3
"""Acquire descriptions and annotations, without sequences, for a frozen RNA shortlist."""

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
from survey_rcsb_long_rna_metadata import verify as verify_survey

SURVEY = ROOT / "results/rcsb_long_rna_survey_runs/20261018T222454.417426Z"
QUERY = """query Metadata($ids:[String!]!){polymer_entities(entity_ids:$ids){
rcsb_id entity_poly{type rcsb_sample_sequence_length}
rcsb_polymer_entity{pdbx_description}
rcsb_polymer_entity_container_identifiers{entry_id entity_id asym_ids auth_asym_ids}
rcsb_polymer_entity_annotation{annotation_id name type provenance_source}
rcsb_polymer_entity_feature_summary{type count coverage}
entry{struct{title} exptl{method} rcsb_entry_info{resolution_combined}}
}}"""


def freeze():
    verify_survey(SURVEY)
    ids = sorted(r["identifier"] for r in json.loads((SURVEY / "description_shortlist.json").read_text())["result_set"])
    folder = ROOT / "results/rcsb_long_shortlist_protocol_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {"run_dir": str(folder), "survey_run": str(SURVEY), "entity_ids": ids,
                "survey_shortlist_sha256": digest((SURVEY / "description_shortlist.json").read_bytes()),
                "query": QUERY, "batch_size": 40, "maximum_response_bytes": 4000000,
                "driver_sha256": digest(Path(__file__).read_bytes()),
                "candidate_sequences_allowed": False, "contacts_allowed": False,
                "model_inference_allowed": False}
    atomic_json(folder / "manifest.json", manifest)
    print(folder / "manifest.json")


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    verify_survey(SURVEY)
    ids = sorted(r["identifier"] for r in json.loads((SURVEY / "description_shortlist.json").read_text())["result_set"])
    if (manifest != json.loads((Path(manifest["run_dir"]) / "manifest.json").read_text())
            or manifest["query"] != QUERY or manifest["entity_ids"] != ids
            or manifest["driver_sha256"] != digest(Path(__file__).read_bytes())
            or manifest["survey_shortlist_sha256"] != digest((SURVEY / "description_shortlist.json").read_bytes())):
        raise ValueError("Metadata inspection protocol differs")
    return manifest


def validate_batch(data, ids):
    if data.get("errors"):
        raise ValueError("GraphQL errors: " + json.dumps(data["errors"]))
    rows = data["data"]["polymer_entities"]
    returned = [row["rcsb_id"] for row in rows if row]
    if sorted(returned) != sorted(ids):
        raise ValueError("Missing or duplicate metadata identities")
    for row in rows:
        if row["entity_poly"]["type"] != "polyribonucleotide":
            raise ValueError("Returned entity is not RNA")
        if not 1000 <= row["entity_poly"]["rcsb_sample_sequence_length"] <= 4999:
            raise ValueError("Returned metadata length outside frozen range")
    return rows


def acquire(path):
    manifest = audit_protocol(path)
    folder = ROOT / "results/rcsb_long_shortlist_metadata_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    atomic_json(folder / "protocol.json", manifest)
    ids = manifest["entity_ids"]
    for offset in range(0, len(ids), 40):
        selected = ids[offset:offset + 40]
        payload = {"query": QUERY, "variables": {"ids": selected}}
        atomic_json(folder / f"request_{offset:03d}.json", payload)
        url = "https://data.rcsb.org/graphql?" + urlencode({"query": QUERY, "variables": json.dumps(payload["variables"])})
        try:
            with urlopen(url, timeout=30) as response:
                raw = response.read(4000001)
            if len(raw) > 4000000:
                raise ValueError("Metadata response oversized")
            (folder / f"response_{offset:03d}.json").write_bytes(raw)
            validate_batch(json.loads(raw), selected)
            print("Metadata batch:", offset, len(selected), flush=True)
        except Exception as error:
            atomic_json(folder / "error.json", {"error": str(error)})
            raise
    atomic_json(folder / "retrieval.json", {"retrieved_utc": datetime.now(timezone.utc).isoformat(),
                "files_sha256": {p.name: digest(p.read_bytes()) for p in folder.iterdir()}})
    print(folder)


def verify(folder):
    manifest = audit_protocol(folder / "protocol.json")
    retrieval = json.loads((folder / "retrieval.json").read_text())
    for name, sha in retrieval["files_sha256"].items():
        if digest((folder / name).read_bytes()) != sha:
            raise ValueError("Metadata response bytes changed")
    rows = []
    for offset in range(0, len(manifest["entity_ids"]), 40):
        ids = manifest["entity_ids"][offset:offset + 40]
        request = json.loads((folder / f"request_{offset:03d}.json").read_text())
        if request != {"query": QUERY, "variables": {"ids": ids}}:
            raise ValueError("Saved metadata request differs")
        rows.extend(validate_batch(json.loads((folder / f"response_{offset:03d}.json").read_text()), ids))
    print("RCSB shortlist metadata replay passed:", len(rows))
    return rows


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
