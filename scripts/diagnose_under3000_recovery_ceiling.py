#!/usr/bin/env python3
"""Freeze/replay gold-informed recovery ceilings on exposed development cohorts."""

import argparse
from collections import Counter
import json
from pathlib import Path
import resource
import sys
from time import monotonic

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.artifacts import timestamp
from rnastable.exposures import exposure_records, read_exposure, record_exposure
from rnastable.global_sparse_pairs import sparse_candidates
from rnastable.helix_pairs import make_helix_model
from rnastable.long_exact_sparse_pairs import decode_long_exact_sparse
from rnastable.native_journal import atomic_json
from rnastable.recovery_ceiling import gold_oracle, recovery_decomposition
from rnastable.reference import digest
from run_under3000_development import audit as audit_baseline, verify as verify_baseline

BASE = ROOT / "results/under3000_development_runs/20261018T223810.974436Z"
BASE_PROTOCOL = ROOT / "results/under3000_development_protocol_runs/20261018T223802.654756Z/manifest.json"
SEEDS = (7, 1729, 20261015)


def policy():
    return {"length_nt": [1, 2999], "seeds": list(SEEDS), "checkpoint": "frozen_103_record_BCE_fixed_final",
            "candidate_top_k": 32, "block_size": 64, "candidate_score_threshold": "strictly_positive",
            "full_oracle": "maximum_cardinality_legal_noncrossing_gold_subset",
            "candidate_oracle": "maximum_cardinality_legal_noncrossing_gold_subset_in_retained_pool",
            "score_denominator": "all_original_reference_pairs_including_unsupported_and_crossing",
            "oracle_is_model_prediction": False, "gold_labels_used": True,
            "actual_baseline_structures_must_reproduce": True,
            "training_performed": False, "development_only": True,
            "independent_test_claim": False, "model_defaults_changed": False, "stage3_ready": False}


def freeze():
    import torch

    verify_baseline(BASE / "summary.json")
    baseline, _, validation, config = audit_baseline(BASE_PROTOCOL)
    folder = ROOT / "results/under3000_recovery_ceiling_protocol_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    atomic_json(folder / "validation.json", validation)
    atomic_json(folder / "config.json", config)
    sources = [BASE_PROTOCOL, BASE / "summary.json", *map(Path, baseline["source_sha256"])]
    for seed in SEEDS:
        sources += [BASE / f"extended_103_seed{seed}" / name for name in ("final_model.pt", "predictions.json", "summary.json")]
    code = [*map(Path, baseline["code_sha256"]), ROOT / "scripts/run_under3000_development.py",
            ROOT / "src/rnastable/recovery_ceiling.py", Path(__file__).resolve()]
    manifest = {"run_dir": str(folder), "policy": policy(), "torch_version": torch.__version__,
                "numpy_version": np.__version__, "source_sha256": {str(p): digest(p.read_bytes()) for p in sources},
                "code_sha256": {str(p): digest(p.read_bytes()) for p in code},
                "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in folder.iterdir()}}
    atomic_json(folder / "manifest.json", manifest)
    print(folder / "manifest.json")


def audit(path):
    import torch

    manifest = json.loads(Path(path).read_text())
    folder = Path(manifest["run_dir"])
    if (manifest != json.loads((folder / "manifest.json").read_text()) or manifest["policy"] != policy()
            or manifest["torch_version"] != torch.__version__ or manifest["numpy_version"] != np.__version__):
        raise ValueError("Recovery-ceiling protocol or runtime differs")
    for group in ("source_sha256", "code_sha256"):
        for name, sha in manifest[group].items():
            if digest(Path(name).read_bytes()) != sha:
                raise ValueError("Recovery-ceiling source changed: " + name)
    for name, sha in manifest["snapshot_sha256"].items():
        if digest((folder / name).read_bytes()) != sha:
            raise ValueError("Recovery-ceiling snapshot changed")
    _, _, validation, config = audit_baseline(BASE_PROTOCOL)
    if (json.loads((folder / "validation.json").read_text()) != validation
            or json.loads((folder / "config.json").read_text()) != config):
        raise ValueError("Recovery-ceiling cohort or model config differs")
    return manifest, validation, config


def records_for(validation):
    return [(name, r) for name, records in validation.items() for r in records]


def full_oracles(validation):
    return [{"cohort": name, "id": r["id"], "family_id": r["family_id"],
             "length_nt": len(r["sequence"]), "oracle": gold_oracle(r["sequence"], r["pairs"])}
            for name, r in records_for(validation)]


def load_model(seed, config):
    import torch

    model = make_helix_model({**config, "seed": seed})
    model.load_state_dict(torch.load(BASE / f"extended_103_seed{seed}" / "final_model.pt", map_location="cpu", weights_only=True))
    model.eval()
    return model


def baseline_predictions(seed, validation):
    rows = json.loads((BASE / f"extended_103_seed{seed}" / "predictions.json").read_text())
    records = [r for _, r in records_for(validation)]
    if (len(rows) != len(records) or any(p["id"] != r["id"] or p["sequence"] != r["sequence"] or p["status"] != "ok"
                                         for p, r in zip(rows, records, strict=True))):
        raise ValueError("Frozen baseline prediction identity differs")
    return rows


def diagnose(model, record, full, expected, cohort, index):
    started = monotonic()
    candidates = sparse_candidates(model, record["sequence"], top_k=32, block_size=64)
    scoring_seconds = monotonic() - started
    started = monotonic()
    actual = decode_long_exact_sparse(record["sequence"], candidates["pairs"], candidates["scores"])
    actual_seconds = monotonic() - started
    if actual["structure"] != expected["structure"]:
        raise ValueError("Actual model decoding no longer reproduces its frozen baseline")
    started = monotonic()
    recovery = recovery_decomposition(record["sequence"], record["pairs"], candidates["pairs"], actual["structure"], full)
    row = {"cohort": cohort, "id": record["id"], "family_id": record["family_id"],
           "length_nt": len(record["sequence"]), "candidate_file": f"{index:03d}.npz",
           "candidate_count": candidates["candidate_count"], "actual_structure": actual["structure"],
           "full_gold_oracle_correct_pairs": full["oracle_correct_pair_count"],
           "full_gold_oracle_f1": full["oracle_metrics_against_full_reference"]["pair_f1"],
           **recovery, "observed_seconds": {"model_scoring": scoring_seconds, "actual_decode": actual_seconds,
                                             "candidate_gold_oracle": monotonic() - started}}
    return row, candidates


def aggregate(rows):
    if not rows:
        raise ValueError("Cannot aggregate an empty recovery cohort")
    loss = Counter()
    for row in rows:
        loss.update(row["missing_gold_decomposition"])
    missing = sum(loss.values())
    legal = sum(r["retained_gold_oracle"]["legal_gold_pair_count"] for r in rows)
    candidate_correct = sum(r["retained_gold_oracle"]["oracle_correct_pair_count"] for r in rows)
    return {"record_seed_rows": len(rows), "unique_reference_count": len({r["id"] for r in rows}),
            "mean_actual_f1": sum(r["actual_metrics"]["pair_f1"] for r in rows) / len(rows),
            "mean_full_gold_oracle_f1": sum(r["full_gold_oracle_f1"] for r in rows) / len(rows),
            "mean_candidate_gold_oracle_f1": sum(r["retained_gold_oracle"]["oracle_metrics_against_full_reference"]["pair_f1"] for r in rows) / len(rows),
            "candidate_legal_gold_recall_micro": sum(r["retained_gold_oracle"]["allowed_gold_pair_count"] for r in rows) / legal if legal else None,
            "actual_to_candidate_oracle_TP_micro": sum(r["actual_metrics"]["shared_pairs"] for r in rows) / candidate_correct if candidate_correct else None,
            "missing_gold_pair_counts": dict(loss),
            "missing_gold_pair_fractions": {k: v / missing if missing else None for k, v in loss.items()},
            "actual_false_positive_pairs": sum(r["actual_false_positive_pairs"] for r in rows)}


def summarize(by_seed):
    return {"complete": True, "policy": policy(),
            "by_cohort": {cohort: aggregate([r for rows in by_seed.values() for r in rows if r["cohort"] == cohort]) for cohort in ("long", "short")},
            "per_seed": {seed: {cohort: aggregate([r for r in rows if r["cohort"] == cohort]) for cohort in ("long", "short")} for seed, rows in by_seed.items()},
            "peak_process_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def run(path):
    import torch

    manifest, validation, config = audit(path)
    torch.set_num_threads(config["cpu_threads"])
    torch.use_deterministic_algorithms(True)
    folder = ROOT / "results/under3000_recovery_ceiling_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    atomic_json(folder / "protocol.json", manifest)
    records = [r for _, r in records_for(validation)]
    event = record_exposure(folder, "validation_started", records)
    full = full_oracles(validation)
    atomic_json(folder / "full_gold_oracles.json", full)
    by_seed = {}
    for seed in SEEDS:
        component = folder / f"seed{seed}"
        component.mkdir()
        model = load_model(seed, config)
        predictions = baseline_predictions(seed, validation)
        rows = []
        for i, ((cohort, record), oracle, prediction) in enumerate(zip(records_for(validation), full, predictions, strict=True)):
            row, candidates = diagnose(model, record, oracle["oracle"], prediction, cohort, i)
            np.savez_compressed(component / row["candidate_file"], pairs=candidates["pairs"], scores=candidates["scores"])
            rows.append(row)
        atomic_json(component / "rows.json", rows)
        by_seed[str(seed)] = rows
        print("Completed seed", seed, {c: aggregate([r for r in rows if r["cohort"] == c])["mean_candidate_gold_oracle_f1"] for c in ("long", "short")}, flush=True)
    summary = summarize(by_seed)
    atomic_json(folder / "summary.json", summary)
    files = [folder / "full_gold_oracles.json", folder / "summary.json", folder / "protocol.json"]
    files += [p for seed in SEEDS for p in (folder / f"seed{seed}").iterdir()]
    atomic_json(folder / "manifest.json", {"exposure_event": event,
                "files_sha256": {str(p.relative_to(folder)): digest(p.read_bytes()) for p in files}})
    print(folder / "summary.json")
    print(json.dumps(summary["by_cohort"], indent=2))


def verify(path):
    import torch

    folder = Path(path).resolve().parent
    _, validation, config = audit(folder / "protocol.json")
    torch.set_num_threads(config["cpu_threads"])
    torch.use_deterministic_algorithms(True)
    manifest = json.loads((folder / "manifest.json").read_text())
    for name, sha in manifest["files_sha256"].items():
        if digest((folder / name).read_bytes()) != sha:
            raise ValueError("Recovery-ceiling artifact bytes differ")
    event = manifest["exposure_event"]
    if digest(Path(event["path"]).read_bytes()) != event["sha256"]:
        raise ValueError("Recovery-ceiling exposure bytes differ")
    saved_event = read_exposure(event["path"])
    if (saved_event["stage"] != "validation_started"
            or saved_event["records"] != exposure_records([r for _, r in records_for(validation)], str(folder) + " validation_started")):
        raise ValueError("Recovery-ceiling exposure inventory differs")
    full = full_oracles(validation)
    if full != json.loads((folder / "full_gold_oracles.json").read_text()):
        raise ValueError("Full legal-gold oracle replay differs")
    by_seed = {}
    for seed in SEEDS:
        component = folder / f"seed{seed}"
        model = load_model(seed, config)
        predictions = baseline_predictions(seed, validation)
        saved = json.loads((component / "rows.json").read_text())
        if len(saved) != len(predictions):
            raise ValueError("Recovery-ceiling saved record count differs")
        for i, ((cohort, record), oracle, prediction, previous) in enumerate(zip(records_for(validation), full, predictions, saved, strict=True)):
            row, candidates = diagnose(model, record, oracle["oracle"], prediction, cohort, i)
            with np.load(component / previous["candidate_file"], allow_pickle=False) as archive:
                if not np.array_equal(archive["pairs"], candidates["pairs"]) or not np.array_equal(archive["scores"], candidates["scores"]):
                    raise ValueError("Retained candidate scoring replay differs")
            row["observed_seconds"] = previous["observed_seconds"]
            if row != previous:
                raise ValueError("Recovery-ceiling decomposition replay differs")
        by_seed[str(seed)] = saved
    expected = summarize(by_seed)
    saved = json.loads(Path(path).read_text())
    expected["peak_process_rss_kib"] = saved["peak_process_rss_kib"]
    if expected != saved:
        raise ValueError("Recovery-ceiling aggregate replay differs")
    print("Full/candidate oracle, baseline inference, candidate-score and decomposition replay passed (no training)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--run", type=Path)
    mode.add_argument("--verify-run", type=Path)
    args = parser.parse_args()
    if args.freeze:
        freeze()
    elif args.run:
        run(args.run)
    else:
        verify(args.verify_run)


if __name__ == "__main__":
    main()
