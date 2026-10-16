#!/usr/bin/env python3
"""Audit metadata-only room for a fresh PDB-derived reference panel."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.exposures import collect_known_exposures  # noqa: E402
from rnastable.reference import digest  # noqa: E402
from prepare_structure_derived_binding import mapping_rows  # noqa: E402

SOURCE = ROOT / "results/structure_derived_source_runs/20261015T021501.529110Z/source"
OUTPUT = ROOT / "results/fresh_structure_inventory_2026-10-15.json"


def cached_clans(allow_paths=None):
    """Use retained Rfam release 15.1 descriptions; reject inconsistent copies."""
    clans, sources = {}, {}
    for path in sorted((ROOT / "results").rglob("RF?????.json")):
        relative = str(path.relative_to(ROOT))
        if allow_paths is not None and relative not in allow_paths:
            continue
        try:
            rfam = json.loads(path.read_text())["rfam"]
            family = rfam["acc"]
            if path.stem != family or rfam["release"]["number"] != "15.1":
                continue
            clan = rfam["clan"]["acc"]
        except (KeyError, TypeError, ValueError):
            continue
        if family in clans and clans[family] != clan:
            raise ValueError(f"Conflicting cached clan for {family}")
        clans[family] = clan
        sources.setdefault(family, []).append(relative)
    return clans, sources


def inventory(mappings, exposures, clans, screened_families):
    exposed_pdbs = {r["pdb_accession"].lower() for r in exposures if r.get("pdb_accession")}
    exposed_families = {r["family_id"] for r in exposures if r.get("family_id")}
    exposed_families |= {f for f, pdb, chain in mappings if pdb in exposed_pdbs}
    all_screened = exposed_families | screened_families
    exposed_clans = {clans[f] for f in all_screened if f in clans and clans[f]}
    rows = defaultdict(list)
    for family, pdb, chain in sorted(mappings):
        rows[family].append((pdb, chain))
    families = []
    for family in sorted(rows):
        possible = sorted((p, c) for p, c in rows[family] if p not in exposed_pdbs)
        if family in exposed_families:
            status = "exposed_family"
        elif family in screened_families:
            status = "development_source_screened"
        elif family not in clans:
            status = "clan_unresolved"
        elif clans[family] in exposed_clans and clans[family] is not None:
            status = "exposed_clan"
        elif not possible:
            status = "no_unexposed_pdb"
        else:
            status = "metadata_candidate_only"
        families.append({
            "family_id": family,
            "clan_id": clans.get(family, "unresolved"),
            "status": status,
            "mapped_chain_count": len(rows[family]),
            "unexposed_chain_count": len(possible),
            "unexposed_pdb_count": len({p for p, _ in possible}),
        })
    counts = {status: sum(f["status"] == status for f in families)
              for status in sorted({f["status"] for f in families})}
    return {
        "schema_version": 1,
        "stage": "metadata_only_inventory",
        "mapped_family_count": len(rows),
        "mapped_chain_count": len(mappings),
        "known_exposed_sequence_count": len(exposures),
        "known_exposed_family_count": len(exposed_families),
        "development_source_screened_families": sorted(screened_families),
        "known_exposed_pdb_count": len(exposed_pdbs),
        "known_exposed_clans": sorted(exposed_clans),
        "status_counts": counts,
        "families": families,
        "annotation_labels_read": False,
        "candidate_sequences_bound": False,
        "supported_references_count": 0,
        "independent_experimental_panel_ready": False,
        "model_inference_authorized": False,
    }


def compute(metadata_paths=None):
    paths = [SOURCE / "pdb_full_region.txt", SOURCE / "pdb_full_region_curated.txt"]
    mappings = mapping_rows(paths[0].read_bytes()) | mapping_rows(paths[1].read_bytes(), curated=True)
    clans, sources = cached_clans(metadata_paths)
    selection_path = ROOT / "results/family_provenance_dataset_metadata_summary.json"
    selection = json.loads(selection_path.read_text())["selection"]["selected_families"]
    screened_families = {row["family_id"] for row in selection} | {"RF00022"}
    exposures = collect_known_exposures(ROOT)
    result = inventory(mappings, exposures, clans, screened_families)
    result["exposure_snapshot_sha256"] = digest(
        json.dumps(exposures, sort_keys=True).encode()
    )
    result["source_sha256"] = {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in paths}
    result["development_selection_sha256"] = digest(selection_path.read_bytes())
    result["metadata_sources"] = sources
    result["metadata_sha256"] = {
        path: digest((ROOT / path).read_bytes())
        for paths in sources.values() for path in paths
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    result = compute()
    if args.verify:
        frozen = json.loads(args.verify.read_text())
        result = compute(set(frozen["metadata_sha256"]))
        if frozen != result:
            raise ValueError("Fresh-structure inventory differs from retained sources or exposures")
        print("Metadata-only inventory replay passed")
    else:
        if OUTPUT.exists():
            raise FileExistsError(OUTPUT)
        OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
        print(OUTPUT)
        print(result["status_counts"])


if __name__ == "__main__":
    main()
