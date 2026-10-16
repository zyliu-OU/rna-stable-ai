#!/usr/bin/env python3
"""Freeze a metadata-selected biological structure candidate panel."""

import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.exposures import collect_known_exposures  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.reference import digest  # noqa: E402
from prepare_structure_derived_binding import mapping_rows  # noqa: E402

CONFIG = ROOT / "configs/fresh_structure_panel_2026-10-15.json"
SOURCE = ROOT / "results/structure_derived_source_runs/20261015T021501.529110Z/source"
POINTER = ROOT / "results/fresh_structure_panel_protocol.json"
BASE = "https://rna.bgsu.edu/rna3dhub/rest/getSequenceBasePairs"


def select(config, inventory, mappings, exposures):
    if (config["stage"] != "metadata_only_fresh_structure_panel"
            or config["structure_labels_allowed_at_freeze"] is not False
            or config["model_inference_authorized"] is not False):
        raise ValueError("Panel freeze must remain metadata-only")
    plan = config["future_binding"]
    if (inventory["stage"] != "metadata_only_inventory"
            or inventory["annotation_labels_read"] is not False
            or inventory["model_inference_authorized"] is not False):
        raise ValueError("Inventory is not metadata-only")
    if (plan["minimum_supported_total"] != 12
            or plan["minimum_supported_families"] != 3
            or plan["minimum_supported_per_family"] != 3
            or plan["replace_unsupported_records"] is not False
            or plan["contact_target"] != "all_returned_cWW_contacts_without_projection"
            or plan["multiple_partners"] != "unsupported_do_not_delete_contacts"
            or plan["minimum_length"] != 20
            or plan["maximum_length"] != 512
            or plan["sequence_similarity_threshold"] != 0.8
            or plan["maximum_supported_records_per_family"] != 4
            or plan["reference_kind"] != "computational_PDB_derived"):
        raise ValueError("Future reference policy differs")
    if (config["candidate_order"] != "family_then_pdb_then_chain_distinct_pdb_globally"
            or not 4 <= config["minimum_pdb_chains_per_family"] <= config["maximum_pdb_chains_per_family"] <= 8):
        raise ValueError("Invalid metadata selection policy")
    families = config["families"]
    if len(families) != 8 or len(set(families)) != 8 or families != sorted(families):
        raise ValueError("Expected eight sorted distinct families")
    by_family = {r["family_id"]: r for r in inventory["families"]}
    if any(by_family[f]["status"] != "metadata_candidate_only"
           or by_family[f]["unexposed_pdb_count"] < config["minimum_pdb_chains_per_family"]
           for f in families):
        raise ValueError("Family failed frozen metadata/exposure screen")
    exposed_pdbs = {r["pdb_accession"].lower() for r in exposures if r.get("pdb_accession")}
    used_pdbs = set(exposed_pdbs)
    selected, decisions = [], []
    for family in families:
        count = 0
        for f, pdb, chain in sorted(mappings):
            if f != family:
                continue
            if pdb in exposed_pdbs:
                reason = "prior_pdb_exposure"
            elif pdb in used_pdbs:
                reason = "duplicate_pdb"
            elif count >= config["maximum_pdb_chains_per_family"]:
                reason = "fixed_family_cap"
            else:
                reason = "metadata_candidate_only"
                count += 1
                used_pdbs.add(pdb)
                selected.append({"family_id": family, "pdb_accession": pdb,
                                 "chain_id": chain, "url": BASE + "?" + urlencode({
                                     "pdb_id": pdb.upper(), "chain": chain,
                                     "only_nested": "False"})})
            decisions.append({"family_id": family, "pdb_accession": pdb,
                              "chain_id": chain, "reason": reason})
        if count < config["minimum_pdb_chains_per_family"]:
            raise ValueError(f"Insufficient unique PDB accessions for {family}")
    return {"candidates": selected, "decisions": decisions,
            "candidate_counts": {f: sum(r["family_id"] == f for r in selected) for f in families},
            "annotation_labels_read": False, "model_inference_authorized": False}


def freeze():
    config_bytes = CONFIG.read_bytes()
    config = json.loads(config_bytes)
    inventory_path = ROOT / config["inventory"]
    inventory_bytes = inventory_path.read_bytes()
    inventory = json.loads(inventory_bytes)
    sources = [SOURCE / "pdb_full_region.txt", SOURCE / "pdb_full_region_curated.txt"]
    for path in sources:
        if inventory["source_sha256"][str(path.relative_to(ROOT))] != digest(path.read_bytes()):
            raise ValueError("Mapping source changed")
    mappings = mapping_rows(sources[0].read_bytes()) | mapping_rows(sources[1].read_bytes(), curated=True)
    exposures = collect_known_exposures(ROOT)
    if digest(json.dumps(exposures, sort_keys=True).encode()) != inventory["exposure_snapshot_sha256"]:
        raise ValueError("Exposure changed since metadata inventory")
    result = select(config, inventory, mappings, exposures)
    run = ROOT / "results/fresh_structure_panel_protocol_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    (run / "config.json").write_bytes(config_bytes)
    (run / "inventory.json").write_bytes(inventory_bytes)
    atomic_json(run / "exposures.json", exposures)
    atomic_json(run / "selection.json", result)
    manifest = {"run_dir": str(run), "snapshot_sha256": {
        p.name: digest(p.read_bytes()) for p in run.iterdir()},
        "mapping_sha256": {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in sources},
        "driver_sha256": digest(Path(__file__).read_bytes())}
    atomic_json(run / "manifest.json", manifest)
    audit(run / "manifest.json")
    atomic_json(POINTER, manifest)
    print("Frozen candidate panel:", run / "manifest.json")
    print(result["candidate_counts"])


def audit(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    if manifest != json.loads((run / "manifest.json").read_text()):
        raise ValueError("Panel manifest differs")
    for name, sha in manifest["snapshot_sha256"].items():
        if digest((run / name).read_bytes()) != sha:
            raise ValueError("Panel snapshot changed")
    for name, sha in manifest["mapping_sha256"].items():
        if digest((ROOT / name).read_bytes()) != sha:
            raise ValueError("PDB mapping changed")
    if digest(Path(__file__).read_bytes()) != manifest["driver_sha256"]:
        raise ValueError("Panel freeze driver changed")
    config = json.loads((run / "config.json").read_text())
    inventory = json.loads((run / "inventory.json").read_text())
    sources = [SOURCE / "pdb_full_region.txt", SOURCE / "pdb_full_region_curated.txt"]
    mappings = mapping_rows(sources[0].read_bytes()) | mapping_rows(sources[1].read_bytes(), curated=True)
    exposures = json.loads((run / "exposures.json").read_text())
    if digest(json.dumps(exposures, sort_keys=True).encode()) != inventory["exposure_snapshot_sha256"]:
        raise ValueError("Frozen exposure differs from inventory")
    if select(config, inventory, mappings, exposures) != json.loads((run / "selection.json").read_text()):
        raise ValueError("Panel selection replay differs")
    print("Metadata-only panel freeze replay passed")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        audit(args.verify)
    else:
        freeze()


if __name__ == "__main__":
    main()
