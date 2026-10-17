#!/usr/bin/env python3
"""Freeze and screen a small 1,025–3,999-nt bpRNA training-only pool."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.exposures import collect_known_exposures, record_exposure  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.reference import digest  # noqa: E402
from prepare_bprna_training_subset import evenly_spaced, read_candidate  # noqa: E402
from prepare_bprna_training_subset_v2 import masks, overlap_after_lcs  # noqa: E402
from inventory_bprna_training_lengths_v2 import OUTPUT as INVENTORY  # noqa: E402

CONFIG = ROOT / "configs/bprna_long_training_smoke_2026-10-16.json"
PROTOCOL = ROOT / "results/bprna_long_training_smoke_protocol.json"


def candidates(config, inventory):
    if (config.get("schema_version") != 1
            or config.get("stage") != "training_only_bprna_long_resource_screen"
            or config.get("source_groups") != ["CRW", "RFAM"]
            or config.get("length_bins") != [[1025, 1499], [1500, 2499], [2500, 3999]]
            or config.get("candidates_per_group_bin") != 4
            or config.get("sequence_similarity_threshold") != 0.8
            or config.get("replace_failed_candidates") is not False
            or config.get("training_only") is not True
            or config.get("model_training_authorized_at_screen") is not False
            or config.get("model_inference_authorized_at_screen") is not False
            or config.get("independent_test_claim") is not False
            or inventory.get("candidate_sequences_read") is not False
            or inventory.get("structure_labels_read") is not False):
        raise ValueError("Long bpRNA training-screen policy differs")
    selected = []
    for group in config["source_groups"]:
        for low, high in config["length_bins"]:
            rows = [row for row in inventory["eligible_400_4999_headers"]
                    if row["source_group"] == group
                    and low <= row["stated_length_nt"] <= high]
            selected.extend(evenly_spaced(rows, config["candidates_per_group_bin"]))
    if len(selected) != 24 or len({row["id"] for row in selected}) != 24:
        raise ValueError("Long bpRNA metadata candidate inventory differs")
    return selected


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    config_raw, inventory_raw = CONFIG.read_bytes(), INVENTORY.read_bytes()
    config, inventory = json.loads(config_raw), json.loads(inventory_raw)
    chosen = candidates(config, inventory)
    exposed = collect_known_exposures(ROOT)
    run = ROOT / "results/bprna_long_training_smoke_protocol_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    (run / "config.json").write_bytes(config_raw)
    (run / "inventory.json").write_bytes(inventory_raw)
    atomic_json(run / "candidates.json", chosen)
    atomic_json(run / "exposures.json", exposed)
    (run / "driver.py").write_bytes(Path(__file__).read_bytes())
    manifest = {"run_dir": str(run), "source_sha256": inventory["source_sha256"],
                "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
                "driver_sha256": digest(Path(__file__).read_bytes())}
    atomic_json(run / "manifest.json", manifest)
    audit_protocol(run / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen long bpRNA training screen:", run / "manifest.json")


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    if manifest != json.loads((run / "manifest.json").read_text()):
        raise ValueError("Long bpRNA screen manifest differs")
    if set(manifest["snapshot_sha256"]) != {
            "config.json", "inventory.json", "candidates.json", "exposures.json", "driver.py"}:
        raise ValueError("Long bpRNA screen snapshot inventory differs")
    for name, sha in manifest["snapshot_sha256"].items():
        if digest((run / name).read_bytes()) != sha:
            raise ValueError("Long bpRNA screen snapshot changed")
    if digest(Path(__file__).read_bytes()) != manifest["driver_sha256"]:
        raise ValueError("Long bpRNA screen driver changed")
    config = json.loads((run / "config.json").read_text())
    inventory = json.loads((run / "inventory.json").read_text())
    if (inventory["source_sha256"] != manifest["source_sha256"]
            or candidates(config, inventory) != json.loads((run / "candidates.json").read_text())):
        raise ValueError("Long bpRNA screen candidate selection changed")
    return manifest, config, inventory


def screen():
    protocol, config, inventory = audit_protocol(PROTOCOL)
    plan = Path(protocol["run_dir"])
    exposed = json.loads((plan / "exposures.json").read_text())
    if collect_known_exposures(ROOT) != exposed:
        raise ValueError("Exposure ledger changed since freeze; replan before source read")
    source = Path(inventory["source_run_dir"]) / "source.zip"
    if digest(source.read_bytes()) != inventory["source_sha256"]:
        raise ValueError("bpRNA source identity changed")
    run = ROOT / "results/bprna_long_training_smoke_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "protocol.json", protocol)
    headers = json.loads((plan / "candidates.json").read_text())
    valid, errors = [], {}
    with zipfile.ZipFile(source) as archive:
        for header in headers:
            try:
                valid.append(read_candidate(archive, header))
            except (ValueError, KeyError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
                errors[header["id"]] = type(exc).__name__ + ": " + str(exc)
    event = record_exposure(run, "training_started", valid) if valid else None
    atomic_json(run / "valid_records.json", valid)
    known = sorted({row["sequence"] for row in exposed})
    known_masks = [(sequence, masks(sequence)) for sequence in known]
    by_id = {row["id"]: row for row in valid}
    selected, decisions = [], []
    for header in headers:
        row = by_id.get(header["id"])
        if row is None:
            reason = "unsupported_source_record"
        elif not row["pairs"] or not row["legal_canonical_pairs"]:
            reason = "no_legal_training_pairs"
        elif any(overlap_after_lcs(row["sequence"], old, old_masks, 0.8)
                 for old, old_masks in known_masks):
            reason = "prior_exposure_overlap"
        elif any(overlap_after_lcs(row["sequence"], old["sequence"],
                                   masks(old["sequence"]), 0.8) for old in selected):
            reason = "within_screen_overlap"
        else:
            reason = "training_only_candidate"
            selected.append(row)
        decisions.append({"id": header["id"], "reason": reason,
                          "error": errors.get(header["id"]),
                          "sequence_sha256": row["sequence_sha256"] if row else None})
    atomic_json(run / "selection.json", {"selected": selected, "decisions": decisions})
    summary = {"complete": True, "run_dir": str(run),
               "candidate_count": len(headers), "valid_sequence_count": len(valid),
               "selected_training_only_count": len(selected),
               "selected_length_min_nt": min((len(r["sequence"]) for r in selected), default=None),
               "selected_length_max_nt": max((len(r["sequence"]) for r in selected), default=None),
               "reason_counts": dict(sorted(Counter(r["reason"] for r in decisions).items())),
               "exposure_event": event, "training_only": True,
               "model_training_performed": False, "model_inference_performed": False,
               "independent_test_claim": False}
    atomic_json(run / "summary.json", summary)
    print("Long bpRNA training-only screen:", run / "summary.json")
    print("Selected:", len(selected), "of", len(headers), summary["reason_counts"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--screen", action="store_true")
    mode.add_argument("--verify-protocol", type=Path)
    args = parser.parse_args()
    if args.freeze:
        freeze()
    elif args.screen:
        screen()
    else:
        audit_protocol(args.verify_protocol)
        print("Long bpRNA training-screen protocol replay passed")


if __name__ == "__main__":
    main()
