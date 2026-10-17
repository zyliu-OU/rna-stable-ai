#!/usr/bin/env python3
"""Replay saved long sparse predictions from both frozen checkpoints."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.exposures import exposure_records, read_exposure  # noqa: E402
from rnastable.helix_pairs import make_helix_model  # noqa: E402
from rnastable.pair_set_training import score_predictions  # noqa: E402
from rnastable.reference import digest  # noqa: E402
from evaluate_long_length_checkpoints_v2 import (  # noqa: E402
    COHORT, aggregate, audit_protocol, long_predictions,
)
from verify_long_validation_coverage import audit as audit_cohort  # noqa: E402


def audit(path):
    import torch

    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    if summary != json.loads((run / "summary.json").read_text()):
        raise ValueError("Long comparison summary identity differs")
    audit_cohort(COHORT / "summary.json")
    protocol = json.loads((run / "protocol.json").read_text())
    frozen, records, config, checkpoints = audit_protocol(
        Path(protocol["run_dir"]) / "manifest.json")
    if protocol != frozen:
        raise ValueError("Long comparison protocol binding differs")
    event = summary["exposure_event"]
    event_path = Path(event["path"])
    if (event["stage"] != "validation_started"
            or digest(event_path.read_bytes()) != event["sha256"]
            or read_exposure(event_path)["records"] != exposure_records(
                records, str(run) + " validation_started")):
        raise ValueError("Long comparison exposure event differs")
    saved = json.loads((run / "predictions.json").read_text())
    if (digest((run / "predictions.json").read_bytes()) != summary["prediction_sha256"]
            or set(saved) != {"control", "extended"}):
        raise ValueError("Long comparison prediction artifact differs")
    torch.set_num_threads(config["cpu_threads"])
    means = {}
    for label in ("control", "extended"):
        model = make_helix_model(config)
        model.load_state_dict(torch.load(checkpoints[label]["path"],
                                         map_location="cpu", weights_only=True))
        model.eval()
        with torch.inference_mode():
            rows = long_predictions(model, records, label, config)
        if rows != saved[label]:
            raise ValueError("Long comparison checkpoint prediction replay differs")
        f1, scored = score_predictions(rows, records)
        metrics = summary["model_summaries"][label]
        expected_scores = [{"id": record["id"], "length_nt": len(record["sequence"]),
                            "family_id": record["family_id"], **score}
                           for record, score in zip(records, scored, strict=True)]
        if (metrics["mean_pair_f1"] != f1 or metrics["record_count"] != len(records)
                or metrics["scores"] != expected_scores
                or {key: metrics[key] for key in ("by_length_band", "by_family")}
                != aggregate(scored, records)):
            raise ValueError("Long comparison score replay differs")
        means[label] = f1
    if (summary["paired_mean_f1_difference_extended_minus_control"]
            != means["extended"] - means["control"]
            or summary["cohort_label_informed"] is not True
            or summary["independent_test_claim"] is not False
            or summary["decoder"] != "greedy_sparse_top16"):
        raise ValueError("Long comparison interpretation differs")
    print("Long sparse checkpoint replay passed:", means,
          "difference", means["extended"] - means["control"])
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", type=Path)
    audit(parser.parse_args().summary)


if __name__ == "__main__":
    main()
