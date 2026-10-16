#!/usr/bin/env python3
"""Audit informative contact coverage and annotation lineage without inference."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.reference import digest  # noqa: E402
from audit_reference_readiness import annotation_lineage  # noqa: E402
from prepare_fresh_structure_references import audit as audit_references  # noqa: E402

INPUT = ROOT / "results/fresh_structure_references_summary.json"
OUTPUT = ROOT / "results/fresh_structure_readiness_summary.json"


def assess(reference, metadata):
    binding = reference["binding"]
    families = []
    for family in binding["families"]:
        name = family["family_id"]
        records = [r for r in binding["records"] if r["family_id"] == name]
        informative = [r for r in records if r["reference_status"] == "ok" and r["pairs"]]
        source_text = metadata[name]["rfam"]["curation"].get("structure_source", "")
        families.append({"family_id": name,
                         "selected_references": len(records),
                         "raw_graphs_accepted": family["supported_references"],
                         "informative_contact_references": len(informative),
                         "zero_contact_graphs": sum(r["reference_status"] == "ok" and not r["pairs"]
                                                    for r in records),
                         "family_structure_source_text": source_text,
                         "family_source_lineage": annotation_lineage({"SS": [source_text]}),
                         "per_sequence_experimental_annotation_verified": False})
    total = sum(f["informative_contact_references"] for f in families)
    qualified = sum(f["informative_contact_references"] >= 3 for f in families)
    return {"stage": "post_binding_reference_readiness_no_inference",
            "raw_graphs_accepted": binding["supported_references"],
            "informative_contact_references": total,
            "families_with_three_informative_references": qualified,
            "coverage_thresholds_met": total >= 12 and qualified >= 3,
            "independent_experimental_panel_ready": False,
            "tool_training_independence_certified": False,
            "model_inference_authorized": False,
            "families": families}


def compute():
    reference = audit_references(INPUT)
    panel_run = ROOT / "results/fresh_structure_panel_protocol_runs/20261016T014824.927247Z"
    inventory_path = panel_run / "inventory.json"
    inventory = json.loads(inventory_path.read_text())
    metadata = {}
    paths = {}
    for family in json.loads((panel_run / "config.json").read_text())["families"]:
        path = ROOT / inventory["metadata_sources"][family][-1]
        metadata[family] = json.loads(path.read_text())
        paths[str(path.relative_to(ROOT))] = digest(path.read_bytes())
    result = assess(reference, metadata)
    result["input_sha256"] = {
        str(INPUT.relative_to(ROOT)): digest(INPUT.read_bytes()),
        str(inventory_path.relative_to(ROOT)): digest(inventory_path.read_bytes()),
        **paths,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    result = compute()
    if args.verify:
        if json.loads(args.verify.read_text()) != result:
            raise ValueError("Fresh structure readiness replay differs")
        print("Fresh structure readiness replay passed")
    else:
        if OUTPUT.exists():
            raise FileExistsError(OUTPUT)
        OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
        print(OUTPUT)
        print(result["informative_contact_references"],
              result["families_with_three_informative_references"])


if __name__ == "__main__":
    main()
