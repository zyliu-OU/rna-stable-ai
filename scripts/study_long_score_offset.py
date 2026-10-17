#!/usr/bin/env python3
"""Frozen logit-offset study on retained top-64 long-RNA candidates."""

import argparse
import json
from pathlib import Path
import resource
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.global_sparse_pairs import sparse_candidates  # noqa: E402
from rnastable.helix_pairs import make_helix_model  # noqa: E402
from rnastable.long_exact_sparse_pairs import decode_long_exact_sparse  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.pair_set_training import score_predictions  # noqa: E402
from rnastable.reference import digest  # noqa: E402
from study_long_candidate_budget_matched import (  # noqa: E402
    ARMS, SEEDS, COHORT, CONFIG, CODE as MATCHED_CODE, components, sources,
)

MATCHED = ROOT / "results/long_candidate_budget_matched_runs/20261017T183356.669629Z"
PROTOCOL = ROOT / "results/long_score_offset_protocol.json"
OFFSETS = (-0.5, 0.0, 0.5, 1.0)
CODE = [Path(__file__), *MATCHED_CODE]


def policy():
    return {"arms": list(ARMS), "seeds": list(SEEDS), "candidate_limit": 64,
            "score_offsets": list(OFFSETS), "decoder": "bounded_exact_sparse",
            "checkpoint": "fixed_final_epoch", "cohort_label_informed": True,
            "development_only": True, "independent_test_claim": False,
            "model_defaults_changed": False}


def source_paths():
    return [*sources(), MATCHED / "summary.json",
            *(MATCHED / name / "predictions.json" for name in components())]


def audit(path):
    manifest = json.loads(Path(path).read_text())
    folder = Path(manifest["run_dir"])
    if manifest != json.loads((folder / "manifest.json").read_text()) or manifest["policy"] != policy():
        raise ValueError("Score-offset manifest or policy changed")
    for group in ("source_sha256", "code_sha256"):
        for name, sha in manifest[group].items():
            if digest(Path(name).read_bytes()) != sha:
                raise ValueError(f"Score-offset {group} changed: {name}")
    records = json.loads(COHORT.read_text())["selected"]
    config = json.loads(CONFIG.read_text())
    if len(records) != 11 or config["cpu_threads"] != 2 or config["top_k"] != 16:
        raise ValueError("Score-offset input inventory changed")
    return manifest, records, config


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    folder = ROOT / "results/long_score_offset_protocol_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {"run_dir": str(folder), "policy": policy(),
                "source_sha256": {str(p): digest(p.read_bytes()) for p in source_paths()},
                "code_sha256": {str(p): digest(p.read_bytes()) for p in CODE}}
    atomic_json(folder / "manifest.json", manifest)
    audit(folder / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen long score offsets:", folder / "manifest.json")


def evaluate_component(model, records, config, name):
    predictions = {str(offset): [] for offset in OFFSETS}
    diagnostics = {str(offset): [] for offset in OFFSETS}
    for record in records:
        sequence = record["sequence"]
        started = monotonic()
        candidates = sparse_candidates(model, sequence, 64, config["block_size"])
        scoring_seconds = monotonic() - started
        for offset in OFFSETS:
            key = str(offset)
            started = monotonic()
            decoded = decode_long_exact_sparse(
                sequence, candidates["pairs"], candidates["scores"] + offset)
            predictions[key].append({
                "id": record["id"], "sequence": sequence, "method": name,
                "status": "ok", "structure": decoded["structure"]})
            diagnostics[key].append({
                "id": record["id"], "family_id": record["family_id"],
                "length_nt": len(sequence), "candidate_count": candidates["candidate_count"],
                "scoring_seconds": scoring_seconds, "decode_seconds": monotonic() - started,
                "accepted_pairs": decoded["accepted_pairs"],
                "dp_array_bytes": decoded["dp_array_bytes"]})
    baseline = json.loads((MATCHED / name / "predictions.json").read_text())["64"]
    if [r["structure"] for r in predictions["0.0"]] != [r["structure"] for r in baseline]:
        raise ValueError(f"{name}: zero-offset structure differs from frozen top-64")
    summaries = {}
    for offset in OFFSETS:
        key = str(offset)
        mean, scored = score_predictions(predictions[key], records)
        for row, score in zip(diagnostics[key], scored, strict=True):
            row.update(score)
        summaries[key] = {
            "mean_record_pair_f1": mean,
            "total_predicted_pairs": sum(r["predicted_pairs"] for r in diagnostics[key]),
            "total_shared_pairs": sum(r["shared_pairs"] for r in diagnostics[key]),
            "total_reference_pairs": sum(r["reference_pairs"] for r in diagnostics[key]),
            "total_decode_seconds": sum(r["decode_seconds"] for r in diagnostics[key]),
            "rows": diagnostics[key]}
    return predictions, summaries


def execute():
    import torch

    manifest, records, config = audit(PROTOCOL)
    torch.set_num_threads(config["cpu_threads"])
    folder = ROOT / "results/long_score_offset_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    atomic_json(folder / "protocol.json", manifest)
    summaries = {}
    for name, component in components().items():
        model = make_helix_model(config)
        model.load_state_dict(torch.load(component / "final_model.pt", map_location="cpu", weights_only=True))
        model.eval()
        predictions, offsets = evaluate_component(model, records, config, name)
        part = folder / name
        part.mkdir()
        atomic_json(part / "predictions.json", predictions)
        atomic_json(part / "summary.json", {
            "name": name, "offsets": offsets, "zero_offset_matches_top64": True,
            "predictions_sha256": digest((part / "predictions.json").read_bytes())})
        summaries[name] = {key: {k: v for k, v in value.items() if k != "rows"}
                           for key, value in offsets.items()}
        print(name, {key: round(value["mean_record_pair_f1"], 4)
                     for key, value in offsets.items()}, flush=True)
    result = {"complete": True, "run_dir": str(folder), "component_summaries": summaries,
              "peak_process_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              **policy()}
    atomic_json(folder / "summary.json", result)
    print("Long score-offset study:", folder / "summary.json")


def verify_run(path):
    folder = Path(path).resolve().parent
    summary = json.loads(Path(path).read_text())
    manifest, records, _ = audit(folder / "protocol.json")
    if (summary["run_dir"] != str(folder) or summary["complete"] is not True
            or any(summary[k] != v for k, v in manifest["policy"].items())
            or set(summary["component_summaries"]) != set(components())):
        raise ValueError("Score-offset run inventory changed")
    for name in components():
        part = folder / name
        result = json.loads((part / "summary.json").read_text())
        predictions = json.loads((part / "predictions.json").read_text())
        baseline = json.loads((MATCHED / name / "predictions.json").read_text())["64"]
        if (result["name"] != name or not result["zero_offset_matches_top64"]
                or result["predictions_sha256"] != digest((part / "predictions.json").read_bytes())
                or [r["structure"] for r in predictions["0.0"]] != [r["structure"] for r in baseline]):
            raise ValueError(f"{name}: zero-offset baseline changed")
        for offset in OFFSETS:
            key = str(offset)
            item = result["offsets"][key]
            rows = item["rows"]
            mean, scored = score_predictions(predictions[key], records)
            if len(rows) != 11 or abs(mean - item["mean_record_pair_f1"]) > 1e-12:
                raise ValueError(f"{name}: score changed")
            for row, score, record in zip(rows, scored, records, strict=True):
                if (row["id"] != record["id"]
                        or any(row[k] != v for k, v in score.items())):
                    raise ValueError(f"{name}: record changed")
            for source, field in (("predicted_pairs", "total_predicted_pairs"),
                                  ("shared_pairs", "total_shared_pairs"),
                                  ("reference_pairs", "total_reference_pairs")):
                if item[field] != sum(row[source] for row in rows):
                    raise ValueError(f"{name}: pair aggregate changed")
            if summary["component_summaries"][name][key] != {k: v for k, v in item.items() if k != "rows"}:
                raise ValueError(f"{name}: summary changed")
    print("Long score-offset run replay passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--verify-protocol", type=Path)
    mode.add_argument("--verify-run", type=Path)
    args = parser.parse_args()
    if args.freeze:
        freeze()
    elif args.run:
        execute()
    elif args.verify_run:
        verify_run(args.verify_run)
    else:
        audit(args.verify_protocol)
        print("Long score-offset protocol replay passed")


if __name__ == "__main__":
    main()
