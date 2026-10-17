#!/usr/bin/env python3
"""Bind the frozen five-clan panel to bpRNA dot-bracket references."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.exposures import record_exposure  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.reference import digest  # noqa: E402
from prepare_bprna_training_subset import read_candidate  # noqa: E402

PANEL = ROOT / "results/bprna_five_clan_feasibility_protocol_runs/20261017T191211.629652Z/selection.json"
PANEL_PROTOCOL = ROOT / "results/bprna_five_clan_feasibility_protocol_runs/20261017T191211.629652Z/manifest.json"
INVENTORY = ROOT / "results/bprna_training_length_inventory_2026-10-16_v2.json"
PROTOCOL = ROOT / "results/bprna_five_clan_reference_screen_protocol.json"


def source():
    return Path(json.loads(INVENTORY.read_text())["source_run_dir"]) / "source.zip"


def policy():
    return {"stage": "conditional_five_clan_reference_feasibility",
            "all_frozen_records_audited": True, "failed_references_replaced": False,
            "duplicate_sequence_structure_discordance": "unsupported",
            "minimum_legal_canonical_pairs": 1,
            "independent_test_claim": False,
            "model_inference_performed": False}


def audit(path):
    manifest = json.loads(Path(path).read_text())
    folder = Path(manifest["run_dir"])
    if (manifest != json.loads((folder / "manifest.json").read_text())
            or manifest["policy"] != policy()
            or manifest["driver_sha256"] != digest(Path(__file__).read_bytes())):
        raise ValueError("Reference screen protocol differs")
    for name, sha in manifest["inputs_sha256"].items():
        if digest(Path(name).read_bytes()) != sha:
            raise ValueError(f"Reference screen source changed: {name}")
    panel = json.loads(PANEL.read_text())
    if (panel["selected_count"] != 13 or panel["structure_labels_read"] is not False
            or json.loads(PANEL_PROTOCOL.read_text())["selection_sha256"] != digest(PANEL.read_bytes())):
        raise ValueError("Label-blind panel changed")
    return manifest, panel


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    folder = ROOT / "results/bprna_five_clan_reference_screen_protocol_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {"run_dir": str(folder), "policy": policy(),
                "inputs_sha256": {str(p): digest(p.read_bytes())
                                  for p in (PANEL, PANEL_PROTOCOL, INVENTORY, source())},
                "driver_sha256": digest(Path(__file__).read_bytes())}
    atomic_json(folder / "manifest.json", manifest)
    audit(folder / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen reference screen:", folder / "manifest.json")


def compute(panel):
    results, valid = [], []
    with zipfile.ZipFile(source()) as archive:
        for item in panel["selected"]:
            variants = []
            errors = []
            for match in item["source_matches"]:
                path = match["zip_path"]
                candidate = {"zip_path": path,
                             "id": Path(path).stem,
                             "stated_length_nt": item["length_nt"],
                             "source_group": "RFAM"}
                try:
                    row = read_candidate(archive, candidate)
                    if row["sequence_sha256"] != item["sequence_sha256"]:
                        raise ValueError("Sequence binding differs")
                    variants.append({"source_path": path, "record": row})
                except (ValueError, KeyError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
                    errors.append({"source_path": path, "error": type(exc).__name__ + ": " + str(exc)})
            if errors or not variants:
                status = "unsupported_source_reference"
            elif len({v["record"]["structure_sha256"] for v in variants}) != 1:
                status = "discordant_duplicate_structures"
            elif variants[0]["record"]["legal_canonical_pairs"] < 1:
                status = "no_legal_canonical_pairs"
            else:
                status = "ok"
                reference = variants[0]["record"]
                valid.append({"id": item["sql_name"], "family_id": item["family_id"],
                              "clan_id": item["clan_id"], "sequence": reference["sequence"],
                              "sequence_sha256": reference["sequence_sha256"],
                              "pairs": reference["pairs"],
                              "reference_kind": "computational",
                              "source": "bpRNA 1m DBN sequence-bound source"})
            results.append({"id": item["sql_name"], "family_id": item["family_id"],
                            "clan_id": item["clan_id"], "length_nt": item["length_nt"],
                            "status": status, "source_match_count": len(item["source_matches"]),
                            "variant_structure_sha256": sorted({v["record"]["structure_sha256"]
                                                                 for v in variants}),
                            "reference_pair_count": len(variants[0]["record"]["pairs"])
                            if variants else None,
                            "legal_canonical_pairs": variants[0]["record"]["legal_canonical_pairs"]
                            if variants else None,
                            "errors": errors})
    return results, valid


def run():
    manifest, panel = audit(PROTOCOL)
    folder = ROOT / "results/bprna_five_clan_reference_screen_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    atomic_json(folder / "protocol.json", manifest)
    rows, valid = compute(panel)
    event = record_exposure(folder, "validation_started", valid) if valid else None
    atomic_json(folder / "references.json", valid)
    result = {"complete": True, "run_dir": str(folder), "policy": policy(),
              "selected_count": len(rows), "supported_reference_count": len(valid),
              "status_counts": dict(sorted(Counter(r["status"] for r in rows).items())),
              "rows": rows, "reference_sha256": digest((folder / "references.json").read_bytes()),
              "exposure_event": event, "independent_test_claim": False}
    atomic_json(folder / "summary.json", result)
    print("Reference screen:", folder / "summary.json")
    print("Supported:", len(valid), "of", len(rows), result["status_counts"])


def verify(path):
    folder = Path(path).resolve().parent
    _, panel = audit(folder / "protocol.json")
    saved = json.loads(Path(path).read_text())
    rows, valid = compute(panel)
    if (saved["run_dir"] != str(folder) or saved["policy"] != policy()
            or saved["rows"] != rows or saved["selected_count"] != len(rows)
            or saved["supported_reference_count"] != len(valid)
            or json.loads((folder / "references.json").read_text()) != valid
            or saved["reference_sha256"] != digest((folder / "references.json").read_bytes())):
        raise ValueError("Reference screen replay differs")
    print("Reference screen replay passed")


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
