#!/usr/bin/env python3
"""Compare frozen helix checkpoints with the existing long sparse decoder."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import resource
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.exposures import record_exposure  # noqa: E402
from rnastable.global_sparse_pairs import decode_sparse, sparse_candidates  # noqa: E402
from rnastable.helix_pairs import make_helix_model  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.pair_set_training import score_predictions  # noqa: E402
from rnastable.reference import digest  # noqa: E402

COHORT = ROOT / "results/long_validation_coverage_runs/20261017T033935.363253Z"
CONTROL = ROOT / "results/family_pair_set_training_runs/20261016T012741.486402Z/helix_seed1729"
EXTENDED = ROOT / "results/bprna_length_pilot_runs/20261016T174449.083968Z"
PROTOCOL = ROOT / "results/long_length_checkpoint_evaluation_v2_protocol.json"
CODE = [Path(__file__), *(ROOT / "src/rnastable" / name for name in (
    "helix_pairs.py", "global_sparse_pairs.py", "context_pairs.py",
    "exact_sparse_pairs.py", "pair_head_study.py", "pair_set_training.py",
    "pair_reference.py", "scoring.py", "structure_model.py"))]


def inputs():
    cohort = json.loads((COHORT / "summary.json").read_text())
    if (cohort["ready_for_development_validation"] is not True
            or cohort["selected_complete_reference_count"] != 11
            or cohort["label_informed_selection"] is not True
            or cohort["model_inference_performed"] is not False):
        raise ValueError("Long development cohort readiness differs")
    records = json.loads((COHORT / "selection.json").read_text())["selected"]
    if len(records) != 11 or not all(1399 <= len(r["sequence"]) <= 3100 for r in records):
        raise ValueError("Long development reference inventory differs")
    control = json.loads((CONTROL / "summary.json").read_text())
    extended = json.loads((EXTENDED / "summary.json").read_text())
    config = control["config"]
    if (control["head"] != "helix" or control["seed"] != 1729
            or extended["matched_initial_weights"] is not True
            or extended["new_longer_train_records"] != 27
            or config["top_k"] != 16 or config["inference_decoder"] != "exact_sparse"):
        raise ValueError("Frozen helix comparison differs")
    paths = {"control": CONTROL / "best_model.pt", "extended": EXTENDED / "best_model.pt"}
    return records, config, paths


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    records, config, paths = inputs()
    run = ROOT / "results/long_length_checkpoint_evaluation_v2_protocol_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "records.json", records)
    atomic_json(run / "config.json", config)
    atomic_json(run / "checkpoints.json", {
        label: {"path": str(path), "sha256": digest(path.read_bytes())}
        for label, path in paths.items()})
    atomic_json(run / "policy.json", {
        "schema_version": 1, "stage": "frozen_long_length_development_comparison",
        "models": ["control", "extended"], "length_scope_nt": [1, 4999],
        "decoder": "greedy_sparse_top16", "checkpoint_selection_from_new_cohort": False,
        "cohort_label_informed": True, "bpRNA_training_family_lineage_complete": False,
        "model_defaults_changed": False, "independent_test_claim": False})
    manifest = {"run_dir": str(run),
                "cohort_summary_sha256": digest((COHORT / "summary.json").read_bytes()),
                "cohort_selection_sha256": digest((COHORT / "selection.json").read_bytes()),
                "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
                "code_sha256": {str(p): digest(p.read_bytes()) for p in CODE}}
    atomic_json(run / "manifest.json", manifest)
    audit_protocol(run / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen longer development checkpoint comparison:", run / "manifest.json")


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    if manifest != json.loads((run / "manifest.json").read_text()):
        raise ValueError("Long comparison manifest changed")
    if set(manifest["snapshot_sha256"]) != {"records.json", "config.json", "checkpoints.json", "policy.json"}:
        raise ValueError("Long comparison snapshot inventory changed")
    for name, sha in manifest["snapshot_sha256"].items():
        if digest((run / name).read_bytes()) != sha:
            raise ValueError("Long comparison snapshot changed")
    for name, sha in manifest["code_sha256"].items():
        if digest(Path(name).read_bytes()) != sha:
            raise ValueError("Long comparison code changed")
    if (digest((COHORT / "summary.json").read_bytes()) != manifest["cohort_summary_sha256"]
            or digest((COHORT / "selection.json").read_bytes()) != manifest["cohort_selection_sha256"]):
        raise ValueError("Long comparison cohort source changed")
    records, config, paths = inputs()
    if (records != json.loads((run / "records.json").read_text())
            or config != json.loads((run / "config.json").read_text())):
        raise ValueError("Long comparison input changed")
    checkpoints = json.loads((run / "checkpoints.json").read_text())
    if checkpoints != {label: {"path": str(path), "sha256": digest(path.read_bytes())}
                       for label, path in paths.items()}:
        raise ValueError("Long comparison checkpoint changed")
    policy = json.loads((run / "policy.json").read_text())
    if (policy["models"] != ["control", "extended"]
            or policy["decoder"] != "greedy_sparse_top16"
            or policy["checkpoint_selection_from_new_cohort"] is not False
            or policy["cohort_label_informed"] is not True
            or policy["independent_test_claim"] is not False):
        raise ValueError("Long comparison interpretation changed")
    return manifest, records, config, checkpoints


def band(length):
    if 1000 <= length < 2000:
        return "1000_1999"
    if 2000 <= length < 3000:
        return "2000_2999"
    if 3000 <= length < 4000:
        return "3000_3999"
    return "other_under_5000"


def aggregate(scored, records):
    by_band, by_family = defaultdict(list), defaultdict(list)
    for score, record in zip(scored, records, strict=True):
        by_band[band(len(record["sequence"]))].append(score["pair_f1"])
        by_family[record["family_id"]].append(score["pair_f1"])
    return {"by_length_band": {k: {"n": len(v), "mean_pair_f1": sum(v) / len(v)}
                               for k, v in sorted(by_band.items())},
            "by_family": {k: {"n": len(v), "mean_pair_f1": sum(v) / len(v)}
                          for k, v in sorted(by_family.items())}}


def long_predictions(model, records, label, config):
    rows = []
    for record in records:
        candidates = sparse_candidates(model, record["sequence"],
                                       config["top_k"], config["block_size"])
        decoded = decode_sparse(record["sequence"], candidates["pairs"],
                                candidates["scores"])
        rows.append({"id": record["id"], "sequence": record["sequence"],
                     "method": label, "status": "ok", "structure": decoded["structure"]})
    return rows


def execute():
    import torch

    protocol, records, config, checkpoints = audit_protocol(PROTOCOL)
    run = ROOT / "results/long_length_checkpoint_evaluation_v2_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "protocol.json", protocol)
    event = record_exposure(run, "validation_started", records)
    torch.set_num_threads(config["cpu_threads"])
    all_rows, model_summaries = {}, {}
    for label in ("control", "extended"):
        model = make_helix_model(config)
        model.load_state_dict(torch.load(checkpoints[label]["path"],
                                         map_location="cpu", weights_only=True))
        model.eval()
        started = monotonic()
        with torch.inference_mode():
            rows = long_predictions(model, records, label, config)
        f1, scored = score_predictions(rows, records)
        all_rows[label] = rows
        model_summaries[label] = {"mean_pair_f1": f1, "record_count": len(records),
                                  "seconds": monotonic() - started,
                                  "scores": [{"id": record["id"], "length_nt": len(record["sequence"]),
                                              "family_id": record["family_id"], **score}
                                             for record, score in zip(records, scored, strict=True)],
                                  **aggregate(scored, records)}
        print(label, "mean pair F1", f1, flush=True)
    atomic_json(run / "predictions.json", all_rows)
    summary = {"complete": True, "run_dir": str(run),
               "model_summaries": model_summaries,
               "paired_mean_f1_difference_extended_minus_control":
                   model_summaries["extended"]["mean_pair_f1"]
                   - model_summaries["control"]["mean_pair_f1"],
               "prediction_sha256": digest((run / "predictions.json").read_bytes()),
               "peak_process_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               "cohort_label_informed": True, "development_validation_only": True,
               "decoder": "greedy_sparse_top16",
               "bpRNA_training_family_lineage_complete": False,
               "independent_test_claim": False, "model_defaults_changed": False,
               "exposure_event": event}
    atomic_json(run / "summary.json", summary)
    print("Longer development comparison:", run / "summary.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--verify-protocol", type=Path)
    args = parser.parse_args()
    if args.freeze:
        freeze()
    elif args.run:
        execute()
    else:
        audit_protocol(args.verify_protocol)
        print("Longer development comparison protocol replay passed")


if __name__ == "__main__":
    main()
