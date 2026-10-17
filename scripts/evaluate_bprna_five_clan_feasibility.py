#!/usr/bin/env python3
"""Fixed six-checkpoint and native comparison on a five-clan feasibility panel."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.folding import fold_sequence  # noqa: E402
from rnastable.helix_pairs import make_helix_model  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.pair_reference import pair_agreement, validate_pairs  # noqa: E402
from rnastable.pair_set_training import score_predictions  # noqa: E402
from rnastable.reference import digest  # noqa: E402
from rnastable.scoring import base_pairs  # noqa: E402
from evaluate_long_length_checkpoints_v3 import long_predictions  # noqa: E402

REFERENCES = ROOT / "results/bprna_five_clan_reference_screen_runs/20261017T191404.643416Z/references.json"
REFERENCE_SUMMARY = ROOT / "results/bprna_five_clan_reference_screen_runs/20261017T191404.643416Z/summary.json"
CONFIG = ROOT / "results/sampled_long_development_protocol_runs/20261017T034843.520152Z/config.json"
SOURCE = ROOT / "results/sampled_long_development_runs/20261017T034847.147062Z"
PROTOCOL = ROOT / "results/bprna_five_clan_feasibility_evaluation_protocol.json"
SEEDS = (7, 1729, 20261015)
ARMS = ("control_88", "extended_105")
NATIVES = ("LinearFold", "ViennaRNA")
NATIVE_CONFIG = {"temperature_c": 37, "beam_size": 100,
                 "timeout_seconds": 30, "memory_limit_gib": 4}
CODE = [Path(__file__), ROOT / "scripts/evaluate_long_length_checkpoints_v3.py",
        *(ROOT / "src/rnastable" / name for name in (
            "folding.py", "vienna_worker.py", "helix_pairs.py", "global_sparse_pairs.py",
            "context_pairs.py", "long_exact_sparse_pairs.py", "pair_reference.py",
            "pair_set_training.py", "scoring.py", "structure_model.py"))]


def components():
    return {f"{arm}_seed{seed}": SOURCE / f"{arm}_seed{seed}" / "final_model.pt"
            for seed in SEEDS for arm in ARMS}


def policy():
    return {"stage": "conditional_five_clan_comparative_feasibility",
            "length_scope_nt": [1, 4999], "arms": list(ARMS), "seeds": list(SEEDS),
            "checkpoint": "fixed_final_epoch", "decoder": "bounded_exact_sparse_top16",
            "native_methods": list(NATIVES), "native_config": NATIVE_CONFIG,
            "failed_native_folds_remain_unknown": True,
            "no_checkpoint_or_decoder_selection_from_cohort": True,
            "crw_lineage_gate_satisfied": False,
            "independent_test_claim": False, "model_defaults_changed": False}


def inputs():
    summary = json.loads(REFERENCE_SUMMARY.read_text())
    records = json.loads(REFERENCES.read_text())
    config = json.loads(CONFIG.read_text())
    if (summary["supported_reference_count"] != 13 or len(records) != 13
            or len({r["clan_id"] for r in records}) != 5
            or not all(1 <= len(r["sequence"]) <= 4999 for r in records)
            or config["top_k"] != 16 or config["cpu_threads"] != 2):
        raise ValueError("Five-clan references or fixed model config changed")
    return records, config


def audit(path):
    manifest = json.loads(Path(path).read_text())
    folder = Path(manifest["run_dir"])
    if (manifest != json.loads((folder / "manifest.json").read_text())
            or manifest["policy"] != policy()
            or manifest["driver_sha256"] != digest(Path(__file__).read_bytes())):
        raise ValueError("Five-clan evaluation protocol differs")
    for group in ("inputs_sha256", "checkpoint_sha256", "code_sha256"):
        for name, sha in manifest[group].items():
            if digest(Path(name).read_bytes()) != sha:
                raise ValueError(f"Five-clan evaluation {group} changed: {name}")
    inputs()
    return manifest


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    inputs()
    folder = ROOT / "results/bprna_five_clan_feasibility_evaluation_protocol_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {"run_dir": str(folder), "policy": policy(),
                "inputs_sha256": {str(p): digest(p.read_bytes())
                                  for p in (REFERENCES, REFERENCE_SUMMARY, CONFIG)},
                "checkpoint_sha256": {str(p): digest(p.read_bytes())
                                      for p in components().values()},
                "code_sha256": {str(p): digest(p.read_bytes()) for p in CODE},
                "driver_sha256": digest(Path(__file__).read_bytes())}
    atomic_json(folder / "manifest.json", manifest)
    audit(folder / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen five-clan evaluation:", folder / "manifest.json")


def score_rows(predictions, records):
    mean, metrics = score_predictions(predictions, records)
    enriched = [{"id": record["id"], "family_id": record["family_id"],
                 "clan_id": record["clan_id"], "length_nt": len(record["sequence"]),
                 **score} for record, score in zip(records, metrics, strict=True)]
    by_clan = defaultdict(list)
    for row in enriched:
        by_clan[row["clan_id"]].append(row["pair_f1"])
    clan_means = {clan: sum(values) / len(values) for clan, values in sorted(by_clan.items())}
    return {"mean_record_pair_f1": mean,
            "mean_clan_pair_f1": sum(clan_means.values()) / len(clan_means),
            "by_clan": clan_means, "rows": enriched}


def run():
    import torch

    manifest = audit(PROTOCOL)
    records, config = inputs()
    torch.set_num_threads(config["cpu_threads"])
    folder = ROOT / "results/bprna_five_clan_feasibility_evaluation_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    atomic_json(folder / "protocol.json", manifest)
    summaries = {}
    for name, checkpoint in components().items():
        model = make_helix_model(config)
        model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True))
        model.eval()
        with torch.inference_mode():
            predictions = long_predictions(model, records, name, config)
        result = score_rows(predictions, records)
        atomic_json(folder / (name + "_predictions.json"), predictions)
        atomic_json(folder / (name + "_scores.json"), result)
        summaries[name] = {k: v for k, v in result.items() if k != "rows"}
        print(name, round(result["mean_record_pair_f1"], 4), flush=True)
    native_results = {}
    for method in NATIVES:
        predictions, folds = [], []
        for record in records:
            fold = fold_sequence(ROOT, record["sequence"], NATIVE_CONFIG, method,
                                 folder / "raw" / (record["id"] + "_" + method + ".txt"))
            folds.append({"id": record["id"], "fold": fold})
            predictions.append({"id": record["id"], "sequence": record["sequence"],
                                "method": method, "status": fold["status"],
                                "structure": fold.get("structure")})
        atomic_json(folder / (method + "_folds.json"), folds)
        atomic_json(folder / (method + "_predictions.json"), predictions)
        ok = [i for i, row in enumerate(predictions) if row["status"] == "ok"]
        if ok:
            result = score_rows([predictions[i] for i in ok], [records[i] for i in ok])
            native_results[method] = {"successful_count": len(ok),
                                      "failed_count": len(records) - len(ok),
                                      **{k: v for k, v in result.items() if k != "rows"}}
        else:
            native_results[method] = {"successful_count": 0,
                                      "failed_count": len(records),
                                      "mean_record_pair_f1": None, "mean_clan_pair_f1": None}
        print(method, native_results[method]["successful_count"],
              native_results[method]["mean_record_pair_f1"], flush=True)
    paired = {str(seed): {metric: summaries[f"extended_105_seed{seed}"][metric]
                          - summaries[f"control_88_seed{seed}"][metric]
                          for metric in ("mean_record_pair_f1", "mean_clan_pair_f1")}
              for seed in SEEDS}
    result = {"complete": True, "run_dir": str(folder), "policy": policy(),
              "record_count": len(records), "model_summaries": summaries,
              "native_summaries": native_results, "paired_extended_minus_control": paired,
              "independent_test_claim": False}
    atomic_json(folder / "summary.json", result)
    print("Five-clan feasibility:", folder / "summary.json")


def verify(path):
    folder = Path(path).resolve().parent
    audit(folder / "protocol.json")
    records, _ = inputs()
    summary = json.loads(Path(path).read_text())
    if summary["run_dir"] != str(folder) or summary["policy"] != policy():
        raise ValueError("Five-clan evaluation summary differs")
    for name in components():
        predictions = json.loads((folder / (name + "_predictions.json")).read_text())
        scored = json.loads((folder / (name + "_scores.json")).read_text())
        if score_rows(predictions, records) != scored:
            raise ValueError(f"Five-clan checkpoint score differs: {name}")
    for method in NATIVES:
        predictions = json.loads((folder / (method + "_predictions.json")).read_text())
        folds = json.loads((folder / (method + "_folds.json")).read_text())
        if len(predictions) != len(records) or len(folds) != len(records):
            raise ValueError("Native prediction inventory differs")
        for prediction, fold, record in zip(predictions, folds, records, strict=True):
            if (prediction["id"] != record["id"] or fold["id"] != record["id"]
                    or prediction["status"] != fold["fold"]["status"]
                    or prediction["structure"] != fold["fold"].get("structure")):
                raise ValueError("Native fold record differs")
    print("Five-clan feasibility replay passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--verify-run", type=Path)
    args = parser.parse_args()
    if args.freeze:
        freeze()
    elif args.run:
        run()
    else:
        verify(args.verify_run)


if __name__ == "__main__":
    main()
