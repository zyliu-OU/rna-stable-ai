#!/usr/bin/env python3
"""Finish the frozen bpRNA screen with an exact safe LCS prefilter."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.exposures import exposure_records, read_exposure, record_exposure  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.prospective_data import sequence_overlap  # noqa: E402
from rnastable.reference import digest  # noqa: E402
from prepare_bprna_training_subset import (  # noqa: E402
    PROTOCOL as PARENT, audit_protocol as audit_parent, evaluate,
)

PROTOCOL = ROOT / "results/bprna_training_subset_v2_protocol.json"
INTERRUPTED = ROOT / "results/bprna_training_subset_runs/20261016T173814.060855Z"


def masks(sequence):
    result = {base: 0 for base in "ACGU"}
    for index, base in enumerate(sequence):
        result[base] |= 1 << index
    return result


def lcs_length(first, second_masks):
    """Exact bit-parallel LCS length; upper-bounds SequenceMatcher matches."""
    state = 0
    for base in first:
        match = second_masks[base] | state
        shifted = (state << 1) | 1
        state = match & (match ^ (match - shifted))
    return state.bit_count()


def overlap_after_lcs(first, second, second_masks, threshold):
    if 2 * min(len(first), len(second)) < threshold * (len(first) + len(second)):
        return False
    if 2 * lcs_length(first, second_masks) < threshold * (len(first) + len(second)):
        return False
    return sequence_overlap(first, second, threshold)


def screen_fast(valid, errors, prior, candidates, threshold):
    by_id = {row["id"]: row for row in valid}
    known = sorted({row["sequence"] for row in prior})
    known_masks = [(sequence, masks(sequence)) for sequence in known]
    selected, decisions = [], []
    for candidate in candidates:
        row = by_id.get(candidate["id"])
        if row is None:
            reason = "unsupported_source_record"
        elif not row["pairs"] or not row["legal_canonical_pairs"]:
            reason = "no_legal_training_pairs"
        elif any(overlap_after_lcs(row["sequence"], old, old_masks, threshold)
                 for old, old_masks in known_masks):
            reason = "prior_exposure_overlap"
        elif any(overlap_after_lcs(row["sequence"], old["sequence"],
                                   masks(old["sequence"]), threshold)
                 for old in selected):
            reason = "within_subset_redundancy"
        else:
            reason = "training_only_candidate"
            selected.append(row)
        decisions.append({"id": candidate["id"], "reason": reason,
                          "sequence_sha256": row["sequence_sha256"] if row else None,
                          "error": errors.get(candidate["id"])})
    return selected, decisions


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    parent = audit_parent(PARENT)
    old_event_files = sorted((INTERRUPTED / "exposures").glob("*.json"))
    if len(old_event_files) != 1:
        raise ValueError("Interrupted source-read exposure event missing")
    event_path = old_event_files[0]
    read_exposure(event_path)
    run = ROOT / "results/bprna_training_subset_v2_protocol_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "parent_protocol.json", parent)
    policy = {"schema_version": 2, "stage": "same_subset_safe_lcs_prefilter",
              "parent_protocol_run": parent["run_dir"],
              "interrupted_run": str(INTERRUPTED),
              "interrupted_exposure_path": str(event_path),
              "interrupted_exposure_sha256": digest(event_path.read_bytes()),
              "selection_semantics_changed": False,
              "training_only": True, "model_training_authorized": False,
              "independent_test_use_authorized": False}
    atomic_json(run / "policy.json", policy)
    (run / "driver.py").write_bytes(Path(__file__).read_bytes())
    manifest = {"run_dir": str(run),
                "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
                "driver_sha256": digest(Path(__file__).read_bytes())}
    atomic_json(run / "manifest.json", manifest)
    audit_protocol(run / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen bpRNA safe-prefilter continuation:", run / "manifest.json")


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    if manifest != json.loads((run / "manifest.json").read_text()):
        raise ValueError("bpRNA v2 protocol manifest differs")
    if set(manifest["snapshot_sha256"]) != {"parent_protocol.json", "policy.json", "driver.py"}:
        raise ValueError("bpRNA v2 protocol inventory differs")
    for name, sha in manifest["snapshot_sha256"].items():
        if digest((run / name).read_bytes()) != sha:
            raise ValueError("bpRNA v2 protocol snapshot changed")
    if digest(Path(__file__).read_bytes()) != manifest["driver_sha256"]:
        raise ValueError("bpRNA v2 driver changed")
    policy = json.loads((run / "policy.json").read_text())
    if (policy["stage"] != "same_subset_safe_lcs_prefilter"
            or policy["selection_semantics_changed"] is not False
            or policy["model_training_authorized"] is not False
            or policy["independent_test_use_authorized"] is not False):
        raise ValueError("bpRNA v2 policy differs")
    ep = Path(policy["interrupted_exposure_path"])
    if digest(ep.read_bytes()) != policy["interrupted_exposure_sha256"]:
        raise ValueError("Interrupted source-read exposure changed")
    read_exposure(ep)
    parent = audit_parent(Path(policy["parent_protocol_run"]) / "manifest.json")
    if parent != json.loads((run / "parent_protocol.json").read_text()):
        raise ValueError("bpRNA v2 parent protocol differs")
    return manifest, parent


def calculate(parent):
    valid, errors, prior, candidates = evaluate(parent)
    config = json.loads((Path(parent["run_dir"]) / "config.json").read_text())
    selected, decisions = screen_fast(valid, errors, prior, candidates,
                                      config["sequence_similarity_threshold"])
    return valid, selected, decisions, candidates


def execute():
    protocol, parent = audit_protocol(PROTOCOL)
    run = ROOT / "results/bprna_training_subset_v2_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "protocol.json", protocol)
    valid, selected, decisions, candidates = calculate(parent)
    event = record_exposure(run, "training_started", valid) if valid else None
    atomic_json(run / "valid_records.json", valid)
    atomic_json(run / "selection.json", {"selected": selected, "decisions": decisions})
    manifest = {"run_dir": str(run), "protocol_run": protocol["run_dir"],
                "exposure_event": event,
                "snapshot_sha256": {str(p.relative_to(run)): digest(p.read_bytes())
                                    for p in run.rglob("*") if p.is_file()}}
    atomic_json(run / "manifest.json", manifest)
    summary = expected_summary(run, (run / "manifest.json").read_bytes(),
                               valid, selected, decisions, candidates)
    atomic_json(run / "summary.json", summary)
    audit(run / "summary.json")
    print("bpRNA training-only v2 screen:", run / "summary.json")
    print("Selected:", len(selected), "of", len(candidates), summary["reason_counts"])


def expected_summary(run, manifest_raw, valid, selected, decisions, candidates):
    return {"complete": True, "run_dir": str(run),
            "manifest_sha256": digest(manifest_raw),
            "candidate_count": len(candidates), "valid_sequence_count": len(valid),
            "selected_training_only_count": len(selected),
            "reason_counts": dict(sorted(Counter(row["reason"] for row in decisions).items())),
            "interrupted_predecessor_run": str(INTERRUPTED),
            "training_only": True, "model_training_performed": False,
            "model_inference_performed": False,
            "independent_test_use_authorized": False}


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    if summary != json.loads((run / "summary.json").read_text()):
        raise ValueError("bpRNA v2 summary differs")
    manifest_raw = (run / "manifest.json").read_bytes()
    if digest(manifest_raw) != summary["manifest_sha256"]:
        raise ValueError("bpRNA v2 run manifest changed")
    manifest = json.loads(manifest_raw)
    protocol, parent = audit_protocol(Path(manifest["protocol_run"]) / "manifest.json")
    if protocol != json.loads((run / "protocol.json").read_text()):
        raise ValueError("bpRNA v2 protocol copy differs")
    valid, selected, decisions, candidates = calculate(parent)
    if valid != json.loads((run / "valid_records.json").read_text()):
        raise ValueError("bpRNA v2 valid records differ")
    if {"selected": selected, "decisions": decisions} != json.loads(
            (run / "selection.json").read_text()):
        raise ValueError("bpRNA v2 selection differs")
    event = manifest["exposure_event"]
    if bool(event) != bool(valid):
        raise ValueError("bpRNA v2 exposure event missing")
    expected_files = {"protocol.json", "valid_records.json", "selection.json"}
    if event:
        ep = Path(event["path"])
        expected_files.add(str(ep.relative_to(run)))
        if (digest(ep.read_bytes()) != event["sha256"]
                or read_exposure(ep)["records"] != exposure_records(
                    valid, str(run) + " training_started")):
            raise ValueError("bpRNA v2 exposure event differs")
    if set(manifest["snapshot_sha256"]) != expected_files:
        raise ValueError("bpRNA v2 run inventory differs")
    for name, sha in manifest["snapshot_sha256"].items():
        if digest((run / name).read_bytes()) != sha:
            raise ValueError("bpRNA v2 run snapshot changed")
    if summary != expected_summary(run, manifest_raw, valid, selected, decisions, candidates):
        raise ValueError("bpRNA v2 summary values differ")
    print("bpRNA training-only v2 screen replay passed")
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
