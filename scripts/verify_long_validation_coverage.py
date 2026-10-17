#!/usr/bin/env python3
"""Replay the frozen long development cohort without model inference."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.exposures import exposure_records, read_exposure  # noqa: E402
from rnastable.pair_model import CANONICAL  # noqa: E402
from rnastable.pair_reference import validate_pairs  # noqa: E402
from rnastable.prospective_binding import bind_pair_reference, parse_stockholm  # noqa: E402
from rnastable.reference import digest  # noqa: E402
from prepare_bprna_training_subset_v2 import masks, overlap_after_lcs  # noqa: E402
from extend_long_validation_coverage import (  # noqa: E402
    audit_protocol, sequence_candidates,
)


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    if summary != json.loads((run / "summary.json").read_text()):
        raise ValueError("Coverage summary identity differs")
    protocol = json.loads((run / "protocol.json").read_text())
    frozen, config, sources = audit_protocol(Path(protocol["run_dir"]) / "manifest.json")
    if protocol != frozen:
        raise ValueError("Coverage protocol binding differs")
    alignments = {family: parse_stockholm(Path(entry["path"]).read_bytes(), family)
                  for family, entry in sources.items()}
    candidates = sequence_candidates(alignments, config)
    if candidates != json.loads((run / "candidates.json").read_text()):
        raise ValueError("Coverage sequence inventory differs")
    event = summary["exposure_event"]
    event_path = Path(event["path"])
    if (event["stage"] != "validation_started"
            or digest(event_path.read_bytes()) != event["sha256"]
            or read_exposure(event_path)["records"] != exposure_records(
                candidates, str(run) + " validation_started")):
        raise ValueError("Coverage exposure event differs")
    plan = Path(protocol["run_dir"])
    exposed = json.loads((plan / "exposures.json").read_text())
    known = sorted({row["sequence"] for row in exposed})
    known_masks = [(sequence, masks(sequence)) for sequence in known]
    selected, decisions = [], []
    counts = Counter()
    for row in candidates:
        family = row["family_id"]
        if counts[family] >= config["maximum_selected_per_family"]:
            reason = "fixed_family_cap"
        else:
            try:
                bound = bind_pair_reference(row, alignments[family])
                validate_pairs(bound["pairs"], len(bound["sequence"]))
                if not any(j - i >= 4 and bound["sequence"][i] + bound["sequence"][j]
                           in CANONICAL for i, j in bound["pairs"]):
                    raise ValueError("No legal canonical reference pairs")
                if any(overlap_after_lcs(row["sequence"], old, old_masks, 0.8)
                       for old, old_masks in known_masks):
                    reason = "prior_exposure_overlap"
                elif any(overlap_after_lcs(row["sequence"], old["sequence"],
                                           masks(old["sequence"]), 0.8) for old in selected):
                    reason = "within_cohort_overlap"
                else:
                    reason = "selected_complete_reference"
                    selected.append(bound)
                    counts[family] += 1
            except (ValueError, KeyError, TypeError):
                reason = "unsupported_reference"
        decisions.append({"id": row["id"], "family_id": family, "reason": reason})
    if {"selected": selected, "decisions": decisions} != json.loads(
            (run / "selection.json").read_text()):
        raise ValueError("Coverage pair selection replay differs")
    ready = (sum(value >= 2 for value in counts.values())
             >= config["minimum_families_with_two_complete"]
             and sum(counts.values()) >= config["minimum_complete_total"])
    expected = {"complete": True, "run_dir": str(run),
                "candidate_sequence_count": len(candidates),
                "selected_complete_reference_count": len(selected),
                "selected_by_family": dict(sorted(counts.items())),
                "selected_length_min_nt": min((len(row["sequence"]) for row in selected), default=None),
                "selected_length_max_nt": max((len(row["sequence"]) for row in selected), default=None),
                "decision_counts": dict(sorted(Counter(row["reason"] for row in decisions).items())),
                "ready_for_development_validation": ready,
                "label_informed_selection": True, "development_validation_only": True,
                "bpRNA_training_family_lineage_complete": False,
                "model_inference_performed": False, "independent_test_claim": False,
                "exposure_event": event}
    if summary != expected:
        raise ValueError("Coverage summary values/policy differ")
    print(f"Long development coverage replay passed: {len(selected)} refs; ready={ready}")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", type=Path)
    audit(parser.parse_args().summary)


if __name__ == "__main__":
    main()
