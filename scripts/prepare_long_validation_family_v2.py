#!/usr/bin/env python3
"""Freeze and screen new Rfam families for longer development validation."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.exposures import collect_known_exposures, record_exposure  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.pair_model import CANONICAL  # noqa: E402
from rnastable.pair_reference import validate_pairs  # noqa: E402
from rnastable.prospective_binding import (  # noqa: E402
    GAPS, bind_pair_reference, parse_stockholm,
)
from rnastable.prospective_data import bounded_download  # noqa: E402
from rnastable.reference import digest  # noqa: E402
from rnastable.sequences import validate_sequence  # noqa: E402
from prepare_bprna_training_subset_v2 import masks, overlap_after_lcs  # noqa: E402

CONFIG = ROOT / "configs/long_validation_family_v2_2026-10-16.json"
PROTOCOL = ROOT / "results/long_validation_family_v2_protocol.json"
SOURCE_LIMIT = 32 * 1024 * 1024


def checked_config(config, exposed):
    families = config["families"]
    if (config.get("schema_version") != 2
            or config["stage"] != "longer_family_development_validation_screen_v2"
            or families != ["RF00177", "RF01849", "RF02542", "RF04321"]
            or any(not re.fullmatch(r"RF\d{5}", family) for family in families)
            or config["minimum_length_nt"] != 400
            or config["maximum_length_nt"] != 4999
            or config["sequence_similarity_threshold"] != 0.8
            or config["candidate_cap_per_family"] != 3
            or config["minimum_complete_per_family"] != 2
            or config["minimum_complete_total"] != 6
            or config["replace_failed_families"] is not False
            or config["development_validation_only"] is not True
            or config["model_inference_authorized_at_screen"] is not False
            or config["independent_test_claim"] is not False):
        raise ValueError("Longer validation screen policy differs")
    if set(families) & {row.get("family_id") for row in exposed}:
        raise ValueError("Candidate family was previously exposed")
    return config


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    config_raw = CONFIG.read_bytes()
    exposures = collect_known_exposures(ROOT)
    checked_config(json.loads(config_raw), exposures)
    run = ROOT / "results/long_validation_family_v2_protocol_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    (run / "config.json").write_bytes(config_raw)
    atomic_json(run / "exposures.json", exposures)
    (run / "driver.py").write_bytes(Path(__file__).read_bytes())
    manifest = {"run_dir": str(run),
                "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
                "driver_sha256": digest(Path(__file__).read_bytes())}
    atomic_json(run / "manifest.json", manifest)
    audit_protocol(run / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen longer-validation family plan:", run / "manifest.json")


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    if manifest != json.loads((run / "manifest.json").read_text()):
        raise ValueError("Protocol manifest changed")
    if set(manifest["snapshot_sha256"]) != {"config.json", "exposures.json", "driver.py"}:
        raise ValueError("Protocol inventory changed")
    for name, sha in manifest["snapshot_sha256"].items():
        if digest((run / name).read_bytes()) != sha:
            raise ValueError("Protocol snapshot changed")
    if digest(Path(__file__).read_bytes()) != manifest["driver_sha256"]:
        raise ValueError("Protocol driver changed")
    config = json.loads((run / "config.json").read_text())
    exposures = json.loads((run / "exposures.json").read_text())
    checked_config(config, exposures)
    return manifest, config, exposures


def select_candidates(alignments, config, exposed):
    known = sorted({row["sequence"] for row in exposed})
    known_masks = [(sequence, masks(sequence)) for sequence in known]
    selected, decisions = [], []
    for family in config["families"]:
        alignment = alignments.get(family)
        if alignment is None:
            continue
        family_count = 0
        for identity, aligned in sorted(alignment["sequences"].items()):
            sequence = "".join(base for base in aligned if base not in GAPS).upper().replace("T", "U")
            row = {"id": family + ":" + identity, "family_id": family,
                   "sequence": sequence, "sequence_sha256": digest(sequence.encode())}
            if family_count >= config["candidate_cap_per_family"]:
                reason = "fixed_family_cap"
            elif not config["minimum_length_nt"] <= len(sequence) <= config["maximum_length_nt"]:
                reason = "outside_length_scope"
            else:
                try:
                    validate_sequence(sequence)
                    if any(overlap_after_lcs(sequence, old, old_masks,
                                             config["sequence_similarity_threshold"])
                           for old, old_masks in known_masks):
                        reason = "prior_exposure_overlap"
                    elif any(overlap_after_lcs(sequence, old["sequence"],
                                               masks(old["sequence"]),
                                               config["sequence_similarity_threshold"])
                             for old in selected):
                        reason = "within_panel_overlap"
                    else:
                        reason = "selected_before_pair_parsing"
                except ValueError:
                    reason = "invalid_sequence"
            decisions.append({"id": row["id"], "family_id": family,
                              "sequence_sha256": row["sequence_sha256"],
                              "length_nt": len(sequence), "reason": reason})
            if reason == "selected_before_pair_parsing":
                selected.append(row)
                family_count += 1
    return selected, decisions


def acquire():
    protocol, config, exposed = audit_protocol(PROTOCOL)
    if collect_known_exposures(ROOT) != exposed:
        raise ValueError("Exposure ledger changed after freeze; replan before acquisition")
    run = ROOT / "results/long_validation_family_v2_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "protocol.json", protocol)
    attempts = []
    alignments = {}
    for family in config["families"]:
        row = {"family_id": family, "status": "started"}
        attempts.append(row)
        atomic_json(run / "attempts.json", attempts)
        try:
            url = f"https://rfam.org/family/{family}/alignment/stockholm"
            content = bounded_download(url, SOURCE_LIMIT, timeout=30)
            alignment = parse_stockholm(content, family)
            (run / f"{family}.sto").write_bytes(content)
            row.update(status="ok", sha256=digest(content),
                       alignment_sequences=len(alignment["sequences"]))
            alignments[family] = alignment
        except Exception as exc:
            row.update(status="failed", error=type(exc).__name__ + ": " + str(exc))
        atomic_json(run / "attempts.json", attempts)
        print(family, row["status"], flush=True)
    selected, decisions = select_candidates(alignments, config, exposed)
    event = record_exposure(run, "validation_started", selected) if selected else None
    atomic_json(run / "selection.json", {"selected": selected, "decisions": decisions})
    bound = []
    for row in selected:
        try:
            result = bind_pair_reference(row, alignments[row["family_id"]])
            validate_pairs(result["pairs"], len(result["sequence"]))
            if not any(j - i >= 4 and result["sequence"][i] + result["sequence"][j]
                       in CANONICAL for i, j in result["pairs"]):
                raise ValueError("No legal canonical reference pairs")
            bound.append({**result, "reference_status": "ok"})
        except (ValueError, KeyError, TypeError) as exc:
            bound.append({**row, "reference_status": "unsupported_reference",
                          "error": type(exc).__name__ + ": " + str(exc)})
    atomic_json(run / "binding.json", bound)
    counts = Counter(row["family_id"] for row in bound if row["reference_status"] == "ok")
    ready = (all(counts[family] >= config["minimum_complete_per_family"]
                 for family in config["families"])
             and sum(counts.values()) >= config["minimum_complete_total"])
    summary = {"complete": True, "run_dir": str(run), "ready_for_development_validation": ready,
               "family_complete_counts": dict(sorted(counts.items())),
               "selected_sequence_count": len(selected),
               "complete_reference_count": sum(counts.values()),
               "decision_counts": dict(sorted(Counter(d["reason"] for d in decisions).items())),
               "attempt_statuses": {row["family_id"]: row["status"] for row in attempts},
               "development_validation_only": True, "model_inference_performed": False,
               "independent_test_claim": False,
               "known_bpRNA_family_lineage_complete": False,
               "exposure_event": event}
    atomic_json(run / "summary.json", summary)
    print("Longer validation screen:", run / "summary.json")
    print("Ready:", ready, "complete references:", sum(counts.values()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--acquire", action="store_true")
    mode.add_argument("--verify-protocol", type=Path)
    args = parser.parse_args()
    if args.freeze:
        freeze()
    elif args.acquire:
        acquire()
    else:
        audit_protocol(args.verify_protocol)
        print("Longer validation family protocol replay passed")


if __name__ == "__main__":
    main()
