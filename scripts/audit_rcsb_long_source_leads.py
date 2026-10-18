#!/usr/bin/env python3
"""Replay conservative source-lead triage from frozen RCSB metadata."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.artifacts import timestamp
from rnastable.native_journal import atomic_json
from rnastable.reference import digest
from inspect_rcsb_long_shortlist import verify as verify_metadata, SURVEY
from inspect_rcsb_long_coverage_v2 import verify as verify_coverage, METADATA
from audit_bprna_candidate_clans import parse_seed, SOURCE as SEED
from acquire_bgsu_nr_source import audit as verify_bgsu

COVERAGE = ROOT / "results/rcsb_long_coverage_runs/20261018T223032.036748Z"
KNOWN = ROOT / "results/bprna_family_separated_candidates_v3_runs/20261017T190513.066933Z/summary.json"
BGSU = ROOT / "results/bgsu_nr_source_summary.json"


def disposition(*, full_model, exposed_pdb, exposed_family, exposed_clan,
                group_ii, description, title):
    if exposed_pdb:
        return "exposed_pdb"
    if exposed_family:
        return "exposed_family"
    if exposed_clan:
        return "exposed_clan"
    if group_ii:
        return "quarantined_group_II_architecture"
    if not full_model:
        return "no_full_length_model_by_residue_count"
    if re.search(r"rrna|ribosom|\b(?:lsu|ssu|rdn|16s|18s|23s|25s|28s|30s|35s|50s)", description.lower()):
        return "ribosomal_description_requires_family_binding"
    if "ribosom" in title.lower() or "ribosom" in description.lower():
        return "ribosome_context_requires_entity_identity"
    return "source_lead_lineage_sequence_and_contacts_unresolved"


def compute():
    metadata = verify_metadata(METADATA)
    coverage, protocol = verify_coverage(COVERAGE)
    source_protocol = json.loads((SURVEY / "protocol.json").read_text())
    frozen = Path(source_protocol["run_dir"])
    quarantine = json.loads((frozen / "quarantine.json").read_text())
    exposures = json.loads((frozen / "exposures.json").read_text())
    seed = parse_seed()
    known = set(json.loads(KNOWN.read_text())["known_family_ids"])
    known.update(r["family_id"] for r in exposures if r.get("family_id"))
    known.update(quarantine["possible_exposed_family_ids"])
    clans = {seed[f]["clan_id"] for f in known if f in seed and seed[f]["clan_id"]}
    clans.update(quarantine["possible_exposed_clan_ids"])
    exposed_pdbs = {r["pdb_accession"].upper() for r in exposures if r.get("pdb_accession")}
    bgsu = verify_bgsu(BGSU)
    bgsu_path = Path(bgsu["run_dir"]) / "source.json"
    mappings = {}
    for row in json.loads(bgsu_path.read_text()):
        match = re.fullmatch(r"([A-Za-z0-9]{4})\|1\|([^+|]+)", str(row.get("ife_id", "")))
        family = str(row.get("rfam", ""))
        if match and re.fullmatch(r"RF\d{5}", family):
            mappings.setdefault((match[1].upper(), match[2]), set()).add(family)
    by_instance = {r["rcsb_id"]: r for r in coverage}
    records = []
    for row in sorted(metadata, key=lambda r: r["rcsb_id"]):
        ids = row["rcsb_polymer_entity_container_identifiers"]
        length = row["entity_poly"]["rcsb_sample_sequence_length"]
        families, instances = set(), []
        for chain in ids["asym_ids"]:
            instance = by_instance[ids["entry_id"] + "." + chain]
            returned = instance["rcsb_polymer_entity_instance_container_identifiers"]
            if (returned["entry_id"] != ids["entry_id"] or returned["entity_id"] != ids["entity_id"]
                    or returned["asym_id"] != chain or returned["auth_asym_id"] not in ids["auth_asym_ids"]):
                raise ValueError("Entity-to-chain coverage identity differs")
            families.update(mappings.get((ids["entry_id"], returned["auth_asym_id"]), set()))
            modeled = (instance.get("rcsb_polymer_instance_info") or {}).get("modeled_residue_count")
            if modeled is not None and (type(modeled) is not int or not 0 <= modeled <= length):
                raise ValueError("Invalid modeled residue count")
            instances.append({"instance_id": instance["rcsb_id"], "auth_chain_id": returned["auth_asym_id"],
                              "modeled_residue_count": modeled, "full_model_by_count": modeled == length})
        description = row["rcsb_polymer_entity"]["pdbx_description"]
        title = row["entry"]["struct"]["title"]
        has_full = any(r["full_model_by_count"] for r in instances)
        status = disposition(full_model=has_full, exposed_pdb=ids["entry_id"] in exposed_pdbs,
                             exposed_family=bool(families & known),
                             exposed_clan=any(seed[f]["clan_id"] in clans for f in families if f in seed),
                             group_ii=bool(re.search(r"group[ _-]*ii\b", description, re.I)),
                             description=description, title=title)
        records.append({"entity_id": row["rcsb_id"], "sample_length_nt": length,
                        "description": description, "entry_title": title,
                        "resolution_angstrom": row["entry"]["rcsb_entry_info"]["resolution_combined"],
                        "bgsu_single_chain_family_claims": sorted(families), "instances": instances,
                        "status": status, "independent_reference_qualified": False})
    return {"policy": {"metadata_only": True, "candidate_sequences_read": False,
                       "contact_labels_read": False, "model_inference_performed": False,
                       "full_modeled_count_proves_complete_pair_reference": False,
                       "absent_family_annotation_means_independent": False,
                       "quarantine_applied": quarantine},
            "shortlist_entity_count": len(records), "instance_count": len(coverage),
            "entities_with_full_model_by_count": sum(any(i["full_model_by_count"] for i in r["instances"]) for r in records),
            "status_counts": dict(sorted(Counter(r["status"] for r in records).items())),
            "source_leads": [r["entity_id"] for r in records if r["status"].startswith("source_lead_")],
            "qualified_independent_reference_count": 0, "records": records,
            "additional_inputs_sha256": {str(p): digest(p.read_bytes()) for p in (KNOWN, SEED, BGSU, bgsu_path)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--verify-run", type=Path)
    args = parser.parse_args()
    result = compute()
    if args.run:
        folder = ROOT / "results/rcsb_long_source_lead_audit_runs" / timestamp()
        folder.mkdir(parents=True, exist_ok=False)
        atomic_json(folder / "manifest.json", {"driver_sha256": digest(Path(__file__).read_bytes()),
                    "coverage_retrieval_sha256": digest((COVERAGE / "retrieval.json").read_bytes())})
        atomic_json(folder / "summary.json", result)
        print(folder / "summary.json")
        print(result["status_counts"], result["source_leads"])
    else:
        manifest = json.loads((args.verify_run.parent / "manifest.json").read_text())
        if (manifest != {"driver_sha256": digest(Path(__file__).read_bytes()),
                        "coverage_retrieval_sha256": digest((COVERAGE / "retrieval.json").read_bytes())}
                or json.loads(args.verify_run.read_text()) != result):
            raise ValueError("Source-lead audit replay differs")
        print("RCSB long source-lead audit replay passed")


if __name__ == "__main__":
    main()
