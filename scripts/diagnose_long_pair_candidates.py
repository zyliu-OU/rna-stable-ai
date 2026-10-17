#!/usr/bin/env python3
"""Measure gold-pair coverage before sparse decoding on long development RNAs."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.exposures import record_exposure  # noqa: E402
from rnastable.global_sparse_pairs import sparse_candidates  # noqa: E402
from rnastable.helix_pairs import make_helix_model  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.pair_model import CANONICAL  # noqa: E402
from rnastable.reference import digest  # noqa: E402
from rnastable.structure_model import tokens  # noqa: E402

COMPARISON = ROOT / "results/long_length_checkpoint_evaluation_v2_runs/20261017T034127.811318Z"
PROTOCOL = ROOT / "results/long_pair_candidate_diagnostic_protocol.json"
CODE = [Path(__file__), *(ROOT / "src/rnastable" / name for name in (
    "global_sparse_pairs.py", "helix_pairs.py", "context_pairs.py",
    "structure_model.py", "pair_model.py"))]


def inputs():
    from evaluate_long_length_checkpoints_v2 import audit_protocol

    comparison = json.loads((COMPARISON / "summary.json").read_text())
    if (comparison["complete"] is not True
            or comparison["decoder"] != "greedy_sparse_top16"
            or comparison["independent_test_claim"] is not False):
        raise ValueError("Source long comparison differs")
    prior = json.loads((COMPARISON / "protocol.json").read_text())
    frozen, records, config, checkpoints = audit_protocol(
        Path(prior["run_dir"]) / "manifest.json")
    if frozen != prior:
        raise ValueError("Source long comparison protocol differs")
    return records, config, checkpoints, comparison


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    records, config, checkpoints, _ = inputs()
    run = ROOT / "results/long_pair_candidate_diagnostic_protocol_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "records.json", records)
    atomic_json(run / "config.json", config)
    atomic_json(run / "checkpoints.json", checkpoints)
    atomic_json(run / "policy.json", {
        "schema_version": 1, "stage": "long_development_candidate_coverage",
        "models": ["control", "extended"], "top_k": 16,
        "positive_score_filter": True, "no_model_selection": True,
        "cohort_label_informed": True, "independent_test_claim": False})
    manifest = {"run_dir": str(run),
                "comparison_summary_sha256": digest((COMPARISON / "summary.json").read_bytes()),
                "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
                "code_sha256": {str(p): digest(p.read_bytes()) for p in CODE}}
    atomic_json(run / "manifest.json", manifest)
    audit_protocol(run / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen long pair candidate diagnostic:", run / "manifest.json")


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    if manifest != json.loads((run / "manifest.json").read_text()):
        raise ValueError("Long candidate manifest changed")
    if set(manifest["snapshot_sha256"]) != {"records.json", "config.json", "checkpoints.json", "policy.json"}:
        raise ValueError("Long candidate snapshot inventory changed")
    for name, sha in manifest["snapshot_sha256"].items():
        if digest((run / name).read_bytes()) != sha:
            raise ValueError("Long candidate snapshot changed")
    for name, sha in manifest["code_sha256"].items():
        if digest(Path(name).read_bytes()) != sha:
            raise ValueError("Long candidate code changed")
    records, config, checkpoints, _ = inputs()
    if (digest((COMPARISON / "summary.json").read_bytes()) != manifest["comparison_summary_sha256"]
            or records != json.loads((run / "records.json").read_text())
            or config != json.loads((run / "config.json").read_text())
            or checkpoints != json.loads((run / "checkpoints.json").read_text())):
        raise ValueError("Long candidate source changed")
    policy = json.loads((run / "policy.json").read_text())
    if (policy["models"] != ["control", "extended"] or policy["top_k"] != 16
            or policy["no_model_selection"] is not True
            or policy["independent_test_claim"] is not False):
        raise ValueError("Long candidate policy changed")
    return manifest, records, config, checkpoints


def execute():
    import torch

    protocol, records, config, checkpoints = audit_protocol(PROTOCOL)
    run = ROOT / "results/long_pair_candidate_diagnostic_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "protocol.json", protocol)
    event = record_exposure(run, "validation_started", records)
    torch.set_num_threads(config["cpu_threads"])
    rows = []
    for label in ("control", "extended"):
        model = make_helix_model(config)
        model.load_state_dict(torch.load(checkpoints[label]["path"],
                                         map_location="cpu", weights_only=True))
        model.eval()
        for record in records:
            sequence = record["sequence"]
            gold = {tuple(pair) for pair in record["pairs"]}
            legal = {pair for pair in gold if pair[1] - pair[0] >= 4
                     and sequence[pair[0]] + sequence[pair[1]] in CANONICAL}
            with torch.inference_mode():
                candidates = sparse_candidates(model, sequence, config["top_k"],
                                               config["block_size"])
                indices = torch.tensor(sorted(legal), dtype=torch.long).reshape(-1, 2)
                gold_logits = model(tokens(sequence), indices)
            retained = set(map(tuple, candidates["pairs"].tolist()))
            hit = len(retained & legal)
            row = {"model": label, "id": record["id"], "family_id": record["family_id"],
                   "length_nt": len(sequence), "full_gold_pairs": len(gold),
                   "legal_gold_pairs": len(legal), "candidate_count": len(retained),
                   "gold_pairs_in_candidates": hit,
                   "gold_pairs_with_positive_logit": int((gold_logits > 0).sum()),
                   "candidate_recall_full_gold": hit / len(gold) if gold else None,
                   "candidate_recall_legal_gold": hit / len(legal) if legal else None}
            rows.append(row)
        print(label, "candidate scan complete", flush=True)
    atomic_json(run / "rows.json", rows)
    aggregates = {}
    for label in ("control", "extended"):
        group = [row for row in rows if row["model"] == label]
        aggregates[label] = {"records": len(group),
                             "total_gold_pairs": sum(row["full_gold_pairs"] for row in group),
                             "total_legal_gold_pairs": sum(row["legal_gold_pairs"] for row in group),
                             "total_gold_pairs_in_candidates": sum(row["gold_pairs_in_candidates"] for row in group),
                             "total_gold_pairs_with_positive_logit": sum(row["gold_pairs_with_positive_logit"] for row in group),
                             "total_candidate_count": sum(row["candidate_count"] for row in group)}
        aggregates[label]["weighted_full_gold_candidate_recall"] = (
            aggregates[label]["total_gold_pairs_in_candidates"] /
            aggregates[label]["total_gold_pairs"])
        aggregates[label]["weighted_legal_gold_candidate_recall"] = (
            aggregates[label]["total_gold_pairs_in_candidates"] /
            aggregates[label]["total_legal_gold_pairs"])
    summary = {"complete": True, "run_dir": str(run), "aggregates": aggregates,
               "row_count": len(rows), "cohort_label_informed": True,
               "development_diagnostic_only": True, "no_model_selection": True,
               "independent_test_claim": False, "exposure_event": event}
    atomic_json(run / "summary.json", summary)
    print("Long pair candidate diagnostic:", run / "summary.json")
    print(json.dumps(aggregates, indent=2))


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
        print("Long pair candidate diagnostic protocol replay passed")


if __name__ == "__main__":
    main()
