#!/usr/bin/env python3
"""Freeze a second, broader metadata-only PDB candidate protocol."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from audit_fresh_structure_inventory import SOURCE, compute as compute_inventory  # noqa: E402
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.exposures import collect_known_exposures  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.reference import digest  # noqa: E402
from prepare_structure_derived_binding import mapping_rows  # noqa: E402

CONFIG = ROOT / "configs/fresh_structure_panel_2026-10-16.json"
POINTER = ROOT / "results/sequence_diverse_structure_panel_protocol.json"
BASE = "https://rna.bgsu.edu/rna3dhub/rest/getSequenceBasePairs"


def evenly_spaced(values, limit):
    """Return deterministic coverage across a sorted value range."""
    values = sorted(values)
    if len(values) <= limit:
        return values
    if limit < 2:
        raise ValueError("Stratified selection needs at least two candidates")
    indices = [round(i * (len(values) - 1) / (limit - 1)) for i in range(limit)]
    if len(set(indices)) != limit:
        raise ValueError("Stratified indices unexpectedly overlap")
    return [values[i] for i in indices]


def validate_policy(config):
    plan = config["future_binding"]
    expected = {
        "minimum_length": 20,
        "maximum_length": 512,
        "sequence_similarity_threshold": 0.8,
        "maximum_supported_records_per_family": 4,
        "contact_target": "all_returned_cWW_contacts_without_projection",
        "multiple_partners": "unsupported_do_not_delete_contacts",
        "replace_unsupported_records": False,
        "minimum_supported_total": 12,
        "minimum_supported_families": 3,
        "minimum_supported_per_family": 3,
        "reference_kind": "computational_PDB_derived",
        "require_per_sequence_annotation_audit": True,
        "require_tool_training_provenance_audit": True,
    }
    if plan != expected:
        raise ValueError("Future binding or provenance policy differs")


def select(config, inventory, mappings, exposures):
    if (config["stage"] != "metadata_only_sequence_diverse_structure_panel"
            or config["structure_labels_allowed_at_freeze"] is not False
            or config["candidate_sequences_allowed_at_freeze"] is not False
            or config["model_inference_authorized"] is not False):
        raise ValueError("Protocol freeze must remain metadata-only")
    validate_policy(config)
    if (inventory["stage"] != "metadata_only_inventory"
            or inventory["annotation_labels_read"] is not False
            or inventory["candidate_sequences_bound"] is not False
            or inventory["model_inference_authorized"] is not False):
        raise ValueError("Inventory is not metadata-only")
    if config["candidate_order"] != (
            "family_then_evenly_spaced_sorted_distinct_pdb_then_first_chain"):
        raise ValueError("Candidate order differs")
    minimum = config["minimum_pdb_chains_per_family"]
    maximum = config["maximum_pdb_chains_per_family"]
    if not 5 <= minimum <= maximum <= 16:
        raise ValueError("Invalid family candidate limits")
    families = config["families"]
    if len(families) != 8 or families != sorted(set(families)):
        raise ValueError("Expected eight sorted distinct families")
    by_family = {row["family_id"]: row for row in inventory["families"]}
    if any(by_family[f]["status"] != "metadata_candidate_only"
           or by_family[f]["unexposed_pdb_count"] < minimum for f in families):
        raise ValueError("Family failed frozen metadata/exposure screen")
    known_clans = [by_family[f]["clan_id"] for f in families
                   if by_family[f]["clan_id"]]
    if len(known_clans) < 4 or len(known_clans) != len(set(known_clans)):
        raise ValueError("Known clans must be distinct and sufficiently broad")

    exposed_pdbs = {row["pdb_accession"].lower() for row in exposures
                    if row.get("pdb_accession")}
    mapped = defaultdict(lambda: defaultdict(list))
    for family, pdb, chain in mappings:
        if family in families:
            mapped[family][pdb].append(chain)
    selected = []
    used_pdbs = set(exposed_pdbs)
    eligible_counts = {}
    for family in families:
        eligible = {pdb: sorted(chains)[0] for pdb, chains in mapped[family].items()
                    if pdb not in used_pdbs}
        eligible_counts[family] = len(eligible)
        chosen = evenly_spaced(eligible, min(maximum, len(eligible)))
        if len(chosen) < minimum:
            raise ValueError(f"Insufficient unique PDB accessions for {family}")
        for pdb in chosen:
            chain = eligible[pdb]
            used_pdbs.add(pdb)
            selected.append({
                "family_id": family,
                "pdb_accession": pdb,
                "chain_id": chain,
                "url": BASE + "?" + urlencode({
                    "pdb_id": pdb.upper(), "chain": chain, "only_nested": "False"
                }),
            })
    counts = {family: sum(row["family_id"] == family for row in selected)
              for family in families}
    return {
        "candidates": selected,
        "candidate_counts": counts,
        "eligible_distinct_pdb_counts": eligible_counts,
        "known_clans": {family: by_family[family]["clan_id"] for family in families},
        "selection_used_structure_labels": False,
        "selection_used_candidate_sequences": False,
        "annotation_labels_read": False,
        "model_inference_authorized": False,
    }


def source_paths():
    return [SOURCE / "pdb_full_region.txt", SOURCE / "pdb_full_region_curated.txt"]


def freeze():
    config_bytes = CONFIG.read_bytes()
    config = json.loads(config_bytes)
    inventory = compute_inventory()
    exposures = collect_known_exposures(ROOT)
    if digest(json.dumps(exposures, sort_keys=True).encode()) != inventory["exposure_snapshot_sha256"]:
        raise ValueError("Exposure changed during inventory construction")
    paths = source_paths()
    mappings = mapping_rows(paths[0].read_bytes()) | mapping_rows(
        paths[1].read_bytes(), curated=True)
    result = select(config, inventory, mappings, exposures)
    run = ROOT / "results/sequence_diverse_structure_panel_protocol_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    (run / "config.json").write_bytes(config_bytes)
    atomic_json(run / "inventory.json", inventory)
    atomic_json(run / "exposures.json", exposures)
    atomic_json(run / "selection.json", result)
    manifest = {
        "run_dir": str(run),
        "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
        "mapping_sha256": {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in paths},
        "metadata_sha256": inventory["metadata_sha256"],
        "driver_sha256": digest(Path(__file__).read_bytes()),
    }
    atomic_json(run / "manifest.json", manifest)
    audit(run / "manifest.json")
    atomic_json(POINTER, manifest)
    print("Frozen sequence-diverse candidate panel:", run / "manifest.json")
    print(result["candidate_counts"])


def audit(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    if manifest != json.loads((run / "manifest.json").read_text()):
        raise ValueError("Protocol manifest differs")
    for name, expected in manifest["snapshot_sha256"].items():
        if digest((run / name).read_bytes()) != expected:
            raise ValueError("Protocol snapshot changed")
    for name, expected in {**manifest["mapping_sha256"],
                           **manifest["metadata_sha256"]}.items():
        if digest((ROOT / name).read_bytes()) != expected:
            raise ValueError("Retained metadata source changed")
    if digest(Path(__file__).read_bytes()) != manifest["driver_sha256"]:
        raise ValueError("Protocol driver changed")
    config = json.loads((run / "config.json").read_text())
    inventory = json.loads((run / "inventory.json").read_text())
    exposures = json.loads((run / "exposures.json").read_text())
    if digest(json.dumps(exposures, sort_keys=True).encode()) != inventory["exposure_snapshot_sha256"]:
        raise ValueError("Frozen exposures differ from inventory")
    paths = source_paths()
    mappings = mapping_rows(paths[0].read_bytes()) | mapping_rows(
        paths[1].read_bytes(), curated=True)
    if select(config, inventory, mappings, exposures) != json.loads(
            (run / "selection.json").read_text()):
        raise ValueError("Protocol selection replay differs")
    print("Sequence-diverse metadata-only panel replay passed")
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
