#!/usr/bin/env python3
"""Freeze and acquire a metadata-only RCSB long-RNA source survey."""

import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
from rnastable.artifacts import timestamp
from rnastable.exposures import collect_known_exposures
from rnastable.native_journal import atomic_json
from rnastable.reference import digest

QUARANTINE = ROOT / "results/crw_original_provenance_audit_runs/20261018T222023.684010Z/quarantine.json"
SEED = ROOT / "results/rfam_release_15_1_clan_source/Rfam.seed.gz"
KNOWN = ROOT / "results/bprna_family_separated_candidates_v3_runs/20261017T190513.066933Z/summary.json"
ENDPOINT = "https://search.rcsb.org/rcsbsearch/v2/query"


def queries():
    def term(attribute, operator, value, negate=False):
        params = {"attribute": attribute, "operator": operator, "value": value}
        if negate:
            params["negation"] = True
        return {"type": "terminal", "service": "text", "parameters": params}
    base = {"query": {"type": "group", "logical_operator": "and", "nodes": [
        term("entity_poly.rcsb_entity_polymer_type", "exact_match", "RNA"),
        term("entity_poly.rcsb_sample_sequence_length", "range",
             {"from": 1000, "to": 4999, "include_lower": True, "include_upper": True})]},
        "return_type": "polymer_entity", "request_options": {
            "results_content_type": ["experimental"], "paginate": {"start": 0, "rows": 0},
            "facets": [{"name": "descriptions", "aggregation_type": "terms",
                        "attribute": "rcsb_polymer_entity.pdbx_description", "max_num_intervals": 10000}]}}
    shortlist = copy.deepcopy(base)
    shortlist["query"]["nodes"].append(term("rcsb_polymer_entity.pdbx_description", "contains_words",
                                             "ribosomal rRNA 16S 18S 23S 25S 28S", True))
    shortlist["request_options"]["paginate"]["rows"] = 10000
    return {"all_long_experimental_rna": base, "description_shortlist": shortlist}


def freeze():
    folder = ROOT / "results/rcsb_long_rna_survey_protocol_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    quarantine = json.loads(QUARANTINE.read_text())
    if digest(Path(quarantine["evidence_summary"]).read_bytes()) != quarantine["evidence_sha256"]:
        raise ValueError("Quarantine evidence changed")
    atomic_json(folder / "queries.json", queries())
    atomic_json(folder / "exposures.json", collect_known_exposures(ROOT))
    (folder / "quarantine.json").write_bytes(QUARANTINE.read_bytes())
    (folder / "driver.py").write_bytes(Path(__file__).read_bytes())
    manifest = {"endpoint": ENDPOINT, "run_dir": str(folder),
                "files_sha256": {name: digest((folder / name).read_bytes()) for name in
                                  ("queries.json", "exposures.json", "quarantine.json", "driver.py")},
                "source_sha256": {str(p): digest(p.read_bytes()) for p in (SEED, KNOWN)},
                "policy": {"metadata_only": True, "candidate_sequences_allowed": False,
                           "contacts_allowed": False, "model_inference_allowed": False,
                           "shortlist_description_filter_proves_family_independence": False,
                           "quarantine_enforcement": "all_candidates_require_family_clan_and_group_II_screen_before_freeze",
                           "maximum_response_bytes": 8000000, "timeout_seconds": 30}}
    atomic_json(folder / "manifest.json", manifest)
    print(folder / "manifest.json")


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    folder = Path(manifest["run_dir"])
    for name, sha in manifest["files_sha256"].items():
        if digest((folder / name).read_bytes()) != sha:
            raise ValueError("Protocol snapshot changed: " + name)
    for name, sha in manifest["source_sha256"].items():
        if digest(Path(name).read_bytes()) != sha:
            raise ValueError("Source snapshot changed: " + name)
    if (manifest["endpoint"] != ENDPOINT
            or digest(Path(__file__).read_bytes()) != manifest["files_sha256"]["driver.py"]
            or json.loads((folder / "queries.json").read_text()) != queries()):
        raise ValueError("Survey identity changed")
    return manifest


def acquire(protocol):
    manifest = audit_protocol(protocol)
    folder = ROOT / "results/rcsb_long_rna_survey_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    atomic_json(folder / "protocol.json", manifest)
    for name, query in queries().items():
        (folder / (name + "_request.json")).write_text(json.dumps(query, indent=2) + "\n")
        url = ENDPOINT + "?" + urlencode({"json": json.dumps(query)})
        try:
            with urlopen(url, timeout=30) as response:
                raw = response.read(8000001)
            if len(raw) > 8000000:
                raise ValueError("Response exceeds frozen bound")
            data = json.loads(raw)
            if "total_count" not in data:
                raise ValueError("Search response lacks total_count")
            (folder / (name + ".json")).write_bytes(raw)
            print(name, data["total_count"])
        except Exception as error:
            atomic_json(folder / (name + "_error.json"), {"error": str(error)})
            raise
    atomic_json(folder / "retrieval.json", {
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "files_sha256": {p.name: digest(p.read_bytes()) for p in folder.iterdir()}})
    print(folder)


def verify(folder):
    retrieval = json.loads((folder / "retrieval.json").read_text())
    for name, sha in retrieval["files_sha256"].items():
        if digest((folder / name).read_bytes()) != sha:
            raise ValueError("Saved response changed: " + name)
    manifest = audit_protocol(folder / "protocol.json")
    if json.loads((Path(manifest["run_dir"]) / "manifest.json").read_text()) != manifest:
        raise ValueError("Saved protocol differs")
    for name, query in queries().items():
        if json.loads((folder / (name + "_request.json")).read_text()) != query:
            raise ValueError("Saved request differs")
        data = json.loads((folder / (name + ".json")).read_text())
        if name == "description_shortlist":
            ids = [r["identifier"] for r in data.get("result_set", [])]
            if len(ids) != len(set(ids)) or len(ids) != data["total_count"]:
                raise ValueError("Shortlist is duplicated or truncated")
    print("RCSB long RNA survey source replay passed")


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
