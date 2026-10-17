#!/usr/bin/env python3
"""Replay all six fixed-epoch sampled fits and longer development predictions."""

import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.exposures import exposure_records, read_exposure  # noqa: E402
from rnastable.reference import digest  # noqa: E402
from train_sampled_long_development import (  # noqa: E402
    ARMS, SEEDS, audit_protocol, fit_one,
)
from verify_long_validation_coverage import audit as audit_cohort  # noqa: E402


def audit(path):
    import torch

    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    if summary != json.loads((run / "summary.json").read_text()) or summary["complete"] is not True:
        raise ValueError("Sampled-long summary identity/status differs")
    audit_cohort(ROOT / "results/long_validation_coverage_runs/20261017T033935.363253Z/summary.json")
    protocol = json.loads((run / "protocol.json").read_text())
    frozen, old, extra, validation, config = audit_protocol(
        Path(protocol["run_dir"]) / "manifest.json")
    if frozen != protocol:
        raise ValueError("Sampled-long protocol binding differs")
    expected_names = [f"{arm}_seed{seed}" for seed in SEEDS for arm in ARMS]
    if set(summary["component_paths"]) != set(expected_names):
        raise ValueError("Sampled-long component inventory differs")
    differences = {}
    for seed in SEEDS:
        initials = {}
        scores = {}
        for arm in ARMS:
            name = f"{arm}_seed{seed}"
            component = Path(summary["component_paths"][name])
            if component != run / name:
                raise ValueError("Sampled-long component path differs")
            saved = json.loads((component / "summary.json").read_text())
            train = old if arm == "control_88" else old + extra
            if (saved["arm"] != arm or saved["seed"] != seed
                    or saved["train_records"] != len(train)
                    or saved["checkpoint_selection"] != "fixed_final_epoch"
                    or saved["independent_test_claim"] is not False):
                raise ValueError("Sampled-long component policy differs")
            for event, stage, records in zip(saved["exposure_events"],
                                             ("training_started", "validation_started"),
                                             (train, validation), strict=True):
                ep = Path(event["path"])
                if (event["stage"] != stage or digest(ep.read_bytes()) != event["sha256"]
                        or read_exposure(ep)["records"] != exposure_records(
                            records, str(component) + " " + stage)):
                    raise ValueError("Sampled-long exposure event differs")
            for filename, sha in saved["checkpoint_sha256"].items():
                if digest((component / filename).read_bytes()) != sha:
                    raise ValueError("Sampled-long checkpoint hash differs")
            if digest((component / "predictions.json").read_bytes()) != saved["predictions_sha256"]:
                raise ValueError("Sampled-long prediction hash differs")
            with tempfile.TemporaryDirectory() as temp:
                replay_dir = Path(temp) / name
                replay_dir.mkdir()
                replay = fit_one(train, validation, config, seed, replay_dir)
                for key in ("seed", "train_records", "train_max_length_nt",
                            "sampled_positive_pairs", "sampled_negative_pairs",
                            "unsupported_train_gold_pairs", "positive_weight", "history",
                            "validation_mean_pair_f1", "validation_scores",
                            "by_length_band", "by_family", "checkpoint_selection",
                            "independent_test_claim"):
                    if replay[key] != saved[key]:
                        raise ValueError(f"Sampled-long deterministic replay differs: {name} {key}")
                if json.loads((replay_dir / "predictions.json").read_text()) != json.loads(
                        (component / "predictions.json").read_text()):
                    raise ValueError("Sampled-long prediction replay differs")
                for filename in ("initial_model.pt", "final_model.pt"):
                    a = torch.load(component / filename, map_location="cpu", weights_only=True)
                    b = torch.load(replay_dir / filename, map_location="cpu", weights_only=True)
                    if not all(torch.equal(value, b[key]) for key, value in a.items()):
                        raise ValueError("Sampled-long state replay differs")
            initials[arm] = torch.load(component / "initial_model.pt",
                                       map_location="cpu", weights_only=True)
            scores[arm] = saved["validation_mean_pair_f1"]
            print("Replayed", name, scores[arm], flush=True)
        if not all(torch.equal(value, initials["extended_105"][key])
                   for key, value in initials["control_88"].items()):
            raise ValueError("Sampled-long paired initialization differs")
        differences[str(seed)] = scores["extended_105"] - scores["control_88"]
    if (summary["paired_f1_differences"] != differences
            or summary["mean_paired_f1_difference"] != sum(differences.values()) / len(differences)
            or summary["matched_initial_weights"] is not True
            or summary["cohort_label_informed"] is not True
            or summary["independent_test_claim"] is not False
            or summary["model_defaults_changed"] is not False):
        raise ValueError("Sampled-long paired summary differs")
    print("Sampled-long six-fit replay passed:", differences)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", type=Path)
    audit(parser.parse_args().summary)


if __name__ == "__main__":
    main()
