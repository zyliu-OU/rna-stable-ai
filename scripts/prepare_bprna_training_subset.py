#!/usr/bin/env python3
"""Freeze and sequence-screen a bounded bpRNA training-only extension."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.exposures import (  # noqa: E402
    collect_known_exposures, exposure_records, read_exposure, record_exposure,
)
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.pair_model import CANONICAL  # noqa: E402
from rnastable.pair_reference import validate_pairs  # noqa: E402
from rnastable.prospective_data import sequence_overlap  # noqa: E402
from rnastable.reference import digest  # noqa: E402
from rnastable.sequences import validate_sequence  # noqa: E402
from inventory_bprna_training_lengths_v2 import OUTPUT as INVENTORY  # noqa: E402

CONFIG = ROOT / "configs/bprna_training_subset_2026-10-16.json"
PROTOCOL = ROOT / "results/bprna_training_subset_protocol.json"
OPEN_TO_CLOSE = {"(": ")", "[": "]", "{": "}", "<": ">"}
OPEN_TO_CLOSE.update({chr(code): chr(code + 32) for code in range(ord("A"), ord("Z") + 1)})
CLOSE_TO_OPEN = {value: key for key, value in OPEN_TO_CLOSE.items()}


def evenly_spaced(rows, count):
    ordered = sorted(rows, key=lambda row: (row["stated_length_nt"], row["id"]))
    if len(ordered) < count or count < 2:
        raise ValueError("Insufficient bpRNA metadata candidates")
    positions = [round(i * (len(ordered) - 1) / (count - 1)) for i in range(count)]
    if len(set(positions)) != count:
        raise ValueError("Repeated bpRNA candidate positions")
    return [ordered[index] for index in positions]


def select(config, inventory):
    if (config["stage"] != "training_only_bprna_length_expansion_screen"
            or config["source_groups"] != ["CRW", "RFAM"]
            or config["length_bins"] != [[400, 599], [600, 799], [800, 1024]]
            or config["per_bin_counts"] != {"CRW": 16, "RFAM": 4}
            or config["maximum_selected"] != 60
            or config["sequence_similarity_threshold"] != 0.8
            or config["replace_excluded_candidates"] is not False
            or config["training_only"] is not True
            or config["independent_test_use_authorized"] is not False
            or config["model_training_authorized_at_screen"] is not False
            or config["model_inference_authorized_at_screen"] is not False
            or inventory["candidate_sequences_read"] is not False
            or inventory["structure_labels_read"] is not False):
        raise ValueError("Invalid training-only bpRNA subset policy/inventory")
    selected = []
    for group in config["source_groups"]:
        for low, high in config["length_bins"]:
            candidates = [row for row in inventory["eligible_400_4999_headers"]
                          if row["source_group"] == group
                          and low <= row["stated_length_nt"] <= high]
            selected.extend(evenly_spaced(candidates, config["per_bin_counts"][group]))
    if len(selected) != 60 or len({row["id"] for row in selected}) != 60:
        raise ValueError("bpRNA subset candidate count/identity differs")
    return selected


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    config_raw = CONFIG.read_bytes()
    inventory_raw = INVENTORY.read_bytes()
    config, inventory = json.loads(config_raw), json.loads(inventory_raw)
    selected = select(config, inventory)
    exposures = collect_known_exposures(ROOT)
    run = ROOT / "results/bprna_training_subset_protocol_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    (run / "config.json").write_bytes(config_raw)
    (run / "inventory.json").write_bytes(inventory_raw)
    atomic_json(run / "candidates.json", selected)
    atomic_json(run / "exposures.json", exposures)
    (run / "driver.py").write_bytes(Path(__file__).read_bytes())
    manifest = {"run_dir": str(run),
                "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
                "source_sha256": inventory["source_sha256"],
                "driver_sha256": digest(Path(__file__).read_bytes())}
    atomic_json(run / "manifest.json", manifest)
    audit_protocol(run / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen bpRNA training-only subset:", run / "manifest.json")
    print("Metadata candidates:", len(selected))


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    if manifest != json.loads((run / "manifest.json").read_text()):
        raise ValueError("bpRNA subset protocol manifest differs")
    if set(manifest["snapshot_sha256"]) != {
            "config.json", "inventory.json", "candidates.json", "exposures.json", "driver.py"}:
        raise ValueError("bpRNA subset snapshot inventory differs")
    for name, sha in manifest["snapshot_sha256"].items():
        if digest((run / name).read_bytes()) != sha:
            raise ValueError("bpRNA subset snapshot changed")
    if digest(Path(__file__).read_bytes()) != manifest["driver_sha256"]:
        raise ValueError("bpRNA subset driver changed")
    config = json.loads((run / "config.json").read_text())
    inventory = json.loads((run / "inventory.json").read_text())
    if (inventory["source_sha256"] != manifest["source_sha256"]
            or select(config, inventory) != json.loads((run / "candidates.json").read_text())):
        raise ValueError("bpRNA subset selection replay differs")
    return manifest


def dot_bracket_pairs(structure):
    stacks = {symbol: [] for symbol in OPEN_TO_CLOSE}
    pairs = []
    for index, symbol in enumerate(structure):
        if symbol == ".":
            continue
        if symbol in OPEN_TO_CLOSE:
            stacks[symbol].append(index)
        elif symbol in CLOSE_TO_OPEN:
            opening = CLOSE_TO_OPEN[symbol]
            if not stacks[opening]:
                raise ValueError("Unmatched bpRNA closing bracket")
            pairs.append([stacks[opening].pop(), index])
        else:
            raise ValueError("Unsupported bpRNA dot-bracket symbol")
    if any(stacks.values()):
        raise ValueError("Unmatched bpRNA opening bracket")
    return sorted(pairs)


def read_candidate(archive, candidate):
    info = archive.getinfo(candidate["zip_path"])
    if info.file_size > 10000:
        raise ValueError("Oversized selected bpRNA DBN file")
    raw = archive.read(info)
    lines = raw.decode("ascii").splitlines()
    if len(lines) != 5 or lines[0].strip() != "#Name: " + candidate["id"]:
        raise ValueError("Selected bpRNA DBN record format differs")
    sequence = lines[3].strip().upper().replace("T", "U")
    structure = lines[4].strip()
    validate_sequence(sequence)
    if len(sequence) != candidate["stated_length_nt"] or len(structure) != len(sequence):
        raise ValueError("bpRNA sequence/structure length differs from header")
    pairs = dot_bracket_pairs(structure)
    validate_pairs(pairs, len(sequence))
    legal = sum(j - i >= 4 and sequence[i] + sequence[j] in CANONICAL
                for i, j in pairs)
    return {"id": candidate["id"], "sequence": sequence,
            "sequence_sha256": digest(sequence.encode()),
            "structure_sha256": digest(structure.encode()),
            "pairs": pairs, "legal_canonical_pairs": legal,
            "source_group": candidate["source_group"],
            "stated_length_nt": candidate["stated_length_nt"]}


def evaluate(protocol):
    plan = Path(protocol["run_dir"])
    inventory = json.loads((plan / "inventory.json").read_text())
    source = Path(inventory["source_run_dir"]) / "source.zip"
    if digest(source.read_bytes()) != inventory["source_sha256"]:
        raise ValueError("bpRNA subset source changed")
    candidates = json.loads((plan / "candidates.json").read_text())
    prior = json.loads((plan / "exposures.json").read_text())
    valid, errors = [], {}
    with zipfile.ZipFile(source) as archive:
        for candidate in candidates:
            try:
                valid.append(read_candidate(archive, candidate))
            except (ValueError, UnicodeDecodeError, KeyError, OSError, zipfile.BadZipFile) as exc:
                errors[candidate["id"]] = type(exc).__name__ + ": " + str(exc)
    return valid, errors, prior, candidates


def screen(valid, errors, prior, candidates, threshold):
    by_id = {row["id"]: row for row in valid}
    selected, decisions = [], []
    old = sorted({row["sequence"] for row in prior})
    for candidate in candidates:
        row = by_id.get(candidate["id"])
        if row is None:
            reason = "unsupported_source_record"
        elif not row["pairs"] or not row["legal_canonical_pairs"]:
            reason = "no_legal_training_pairs"
        elif any(sequence_overlap(row["sequence"], sequence, threshold) for sequence in old):
            reason = "prior_exposure_overlap"
        elif any(sequence_overlap(row["sequence"], previous["sequence"], threshold)
                 for previous in selected):
            reason = "within_subset_redundancy"
        else:
            reason = "training_only_candidate"
            selected.append(row)
        decisions.append({"id": candidate["id"], "reason": reason,
                          "sequence_sha256": row["sequence_sha256"] if row else None,
                          "error": errors.get(candidate["id"])})
    return selected, decisions


def execute():
    protocol = audit_protocol(PROTOCOL)
    plan = Path(protocol["run_dir"])
    if collect_known_exposures(ROOT) != json.loads((plan / "exposures.json").read_text()):
        raise ValueError("Exposure ledger changed before bpRNA subset screen")
    run = ROOT / "results/bprna_training_subset_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "protocol.json", protocol)
    valid, errors, prior, candidates = evaluate(protocol)
    event = record_exposure(run, "training_started", valid) if valid else None
    threshold = json.loads((plan / "config.json").read_text())["sequence_similarity_threshold"]
    selected, decisions = screen(valid, errors, prior, candidates, threshold)
    atomic_json(run / "valid_records.json", valid)
    atomic_json(run / "selection.json", {"selected": selected, "decisions": decisions})
    manifest = {"run_dir": str(run), "protocol_run": protocol["run_dir"],
                "exposure_event": event,
                "snapshot_sha256": {str(p.relative_to(run)): digest(p.read_bytes())
                                    for p in run.rglob("*") if p.is_file()}}
    atomic_json(run / "manifest.json", manifest)
    summary = {"complete": True, "run_dir": str(run),
               "manifest_sha256": digest((run / "manifest.json").read_bytes()),
               "candidate_count": len(candidates), "valid_sequence_count": len(valid),
               "selected_training_only_count": len(selected),
               "reason_counts": dict(sorted(Counter(row["reason"] for row in decisions).items())),
               "training_only": True, "model_training_performed": False,
               "model_inference_performed": False,
               "independent_test_use_authorized": False}
    atomic_json(run / "summary.json", summary)
    audit(run / "summary.json")
    print("bpRNA training-only screen:", run / "summary.json")
    print("Selected:", len(selected), "of", len(candidates), summary["reason_counts"])


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    if summary != json.loads((run / "summary.json").read_text()):
        raise ValueError("bpRNA subset summary differs")
    manifest_raw = (run / "manifest.json").read_bytes()
    if digest(manifest_raw) != summary["manifest_sha256"]:
        raise ValueError("bpRNA subset run manifest changed")
    manifest = json.loads(manifest_raw)
    protocol = audit_protocol(Path(manifest["protocol_run"]) / "manifest.json")
    if json.loads((run / "protocol.json").read_text()) != protocol:
        raise ValueError("bpRNA subset protocol copy differs")
    valid, errors, prior, candidates = evaluate(protocol)
    plan = Path(protocol["run_dir"])
    threshold = json.loads((plan / "config.json").read_text())["sequence_similarity_threshold"]
    selected, decisions = screen(valid, errors, prior, candidates, threshold)
    if valid != json.loads((run / "valid_records.json").read_text()):
        raise ValueError("bpRNA source record binding differs")
    if {"selected": selected, "decisions": decisions} != json.loads(
            (run / "selection.json").read_text()):
        raise ValueError("bpRNA subset selection differs")
    event = manifest["exposure_event"]
    if bool(event) != bool(valid):
        raise ValueError("bpRNA valid sequences lack exposure event")
    expected_files = {"protocol.json", "valid_records.json", "selection.json"}
    if event:
        ep = Path(event["path"])
        expected_files.add(str(ep.relative_to(run)))
        if (digest(ep.read_bytes()) != event["sha256"]
                or read_exposure(ep)["records"] != exposure_records(
                    valid, str(run) + " training_started")):
            raise ValueError("bpRNA subset exposure event differs")
    if set(manifest["snapshot_sha256"]) != expected_files:
        raise ValueError("bpRNA subset file inventory differs")
    for name, sha in manifest["snapshot_sha256"].items():
        if digest((run / name).read_bytes()) != sha:
            raise ValueError("bpRNA subset run snapshot changed")
    expected = {"complete": True, "run_dir": str(run),
                "manifest_sha256": digest(manifest_raw),
                "candidate_count": len(candidates), "valid_sequence_count": len(valid),
                "selected_training_only_count": len(selected),
                "reason_counts": dict(sorted(Counter(row["reason"] for row in decisions).items())),
                "training_only": True, "model_training_performed": False,
                "model_inference_performed": False,
                "independent_test_use_authorized": False}
    if summary != expected:
        raise ValueError("bpRNA subset summary values differ")
    print("bpRNA training-only subset replay passed")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--screen", action="store_true")
    mode.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.freeze:
        freeze()
    elif args.screen:
        execute()
    else:
        audit(args.verify)


if __name__ == "__main__":
    main()
