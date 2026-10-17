#!/usr/bin/env python3
"""Disclosed label-informed coverage screen over already acquired Rfam seeds."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.exposures import collect_known_exposures, record_exposure  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.pair_model import CANONICAL  # noqa: E402
from rnastable.pair_reference import validate_pairs  # noqa: E402
from rnastable.prospective_binding import GAPS, bind_pair_reference, parse_stockholm  # noqa: E402
from rnastable.reference import digest  # noqa: E402
from rnastable.sequences import validate_sequence  # noqa: E402
from prepare_bprna_training_subset_v2 import masks, overlap_after_lcs  # noqa: E402

CONFIG = ROOT / "configs/long_validation_coverage_2026-10-16.json"
PROTOCOL = ROOT / "results/long_validation_coverage_protocol.json"
SOURCES = {
    "RF01849": ROOT / "results/long_validation_family_v2_runs/20261017T033627.321212Z/RF01849.sto",
    "RF00177": ROOT / "results/long_validation_family_v2_runs/20261017T033627.321212Z/RF00177.sto",
    "RF02542": ROOT / "results/long_validation_family_v2_runs/20261017T033627.321212Z/RF02542.sto",
    "RF04321": ROOT / "results/long_validation_family_v2_runs/20261017T033627.321212Z/RF04321.sto",
    "RF02462": ROOT / "results/long_validation_family_runs/20261017T033513.077462Z/RF02462.sto",
    "RF02540": ROOT / "results/long_validation_family_runs/20261017T033513.077462Z/RF02540.sto",
    "RF02541": ROOT / "results/long_validation_family_runs/20261017T033513.077462Z/RF02541.sto",
}


def checked_config(config):
    if (config.get("schema_version") != 1
            or config.get("stage") != "label_informed_longer_development_coverage"
            or config.get("families") != ["RF00177", "RF01849", "RF02462", "RF02540",
                                           "RF02541", "RF02542", "RF04321"]
            or config.get("minimum_length_nt") != 400
            or config.get("maximum_length_nt") != 4999
            or config.get("sequence_similarity_threshold") != 0.8
            or config.get("maximum_selected_per_family") != 3
            or config.get("minimum_families_with_two_complete") != 3
            or config.get("minimum_complete_total") != 6
            or config.get("selection_uses_reference_completeness") is not True
            or config.get("development_validation_only") is not True
            or config.get("independent_test_claim") is not False
            or config.get("model_inference_authorized_at_screen") is not False):
        raise ValueError("Long coverage development policy differs")
    return config


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    config_raw = CONFIG.read_bytes()
    config = checked_config(json.loads(config_raw))
    exposed = collect_known_exposures(ROOT)
    if set(config["families"]) != set(SOURCES):
        raise ValueError("Coverage source inventory differs")
    run = ROOT / "results/long_validation_coverage_protocol_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    (run / "config.json").write_bytes(config_raw)
    atomic_json(run / "exposures.json", exposed)
    atomic_json(run / "sources.json", {family: {"path": str(path),
              "sha256": digest(path.read_bytes())} for family, path in SOURCES.items()})
    (run / "driver.py").write_bytes(Path(__file__).read_bytes())
    manifest = {"run_dir": str(run),
                "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
                "driver_sha256": digest(Path(__file__).read_bytes())}
    atomic_json(run / "manifest.json", manifest)
    audit_protocol(run / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen label-informed long development coverage:", run / "manifest.json")


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    if manifest != json.loads((run / "manifest.json").read_text()):
        raise ValueError("Coverage protocol manifest differs")
    if set(manifest["snapshot_sha256"]) != {"config.json", "exposures.json", "sources.json", "driver.py"}:
        raise ValueError("Coverage protocol snapshot inventory differs")
    for name, sha in manifest["snapshot_sha256"].items():
        if digest((run / name).read_bytes()) != sha:
            raise ValueError("Coverage protocol snapshot changed")
    if digest(Path(__file__).read_bytes()) != manifest["driver_sha256"]:
        raise ValueError("Coverage protocol driver changed")
    config = checked_config(json.loads((run / "config.json").read_text()))
    sources = json.loads((run / "sources.json").read_text())
    if set(sources) != set(config["families"]):
        raise ValueError("Coverage source families differ")
    for family, entry in sources.items():
        if digest(Path(entry["path"]).read_bytes()) != entry["sha256"]:
            raise ValueError("Coverage source bytes changed")
    return manifest, config, sources


def sequence_candidates(alignments, config):
    output = []
    for family in config["families"]:
        for identity, aligned in sorted(alignments[family]["sequences"].items()):
            sequence = "".join(c for c in aligned if c not in GAPS).upper().replace("T", "U")
            if not config["minimum_length_nt"] <= len(sequence) <= config["maximum_length_nt"]:
                continue
            try:
                validate_sequence(sequence)
            except ValueError:
                continue
            output.append({"id": family + ":" + identity, "family_id": family,
                           "sequence": sequence, "sequence_sha256": digest(sequence.encode())})
    return output


def screen():
    protocol, config, sources = audit_protocol(PROTOCOL)
    plan = Path(protocol["run_dir"])
    exposed = json.loads((plan / "exposures.json").read_text())
    if collect_known_exposures(ROOT) != exposed:
        raise ValueError("Exposure ledger changed after coverage freeze")
    alignments = {family: parse_stockholm(Path(entry["path"]).read_bytes(), family)
                  for family, entry in sources.items()}
    candidates = sequence_candidates(alignments, config)
    run = ROOT / "results/long_validation_coverage_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "protocol.json", protocol)
    event = record_exposure(run, "validation_started", candidates)
    atomic_json(run / "candidates.json", candidates)
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
            except (ValueError, KeyError, TypeError) as exc:
                reason = "unsupported_reference"
        decisions.append({"id": row["id"], "family_id": family, "reason": reason})
    atomic_json(run / "selection.json", {"selected": selected, "decisions": decisions})
    ready = (sum(value >= 2 for value in counts.values())
             >= config["minimum_families_with_two_complete"]
             and sum(counts.values()) >= config["minimum_complete_total"])
    summary = {"complete": True, "run_dir": str(run),
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
    atomic_json(run / "summary.json", summary)
    print("Label-informed longer development coverage:", run / "summary.json")
    print("Ready:", ready, "selected:", len(selected), "families:", dict(counts))


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
        print("Long coverage protocol replay passed")


if __name__ == "__main__":
    main()
