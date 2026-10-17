#!/usr/bin/env python3
"""One synthetic long-RNA optimizer step; no biological evaluation or checkpoint."""

import argparse
import json
from pathlib import Path
import resource
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rnastable.helix_pairs import make_helix_model  # noqa: E402
from rnastable.sampled_pair_supervision import sampled_pair_supervision  # noqa: E402
from rnastable.structure_model import tokens  # noqa: E402

CONTROL = ROOT / "results/family_pair_set_training_runs/20261016T012741.486402Z/helix_seed1729/summary.json"


def run(length):
    if type(length) is not int or not 1025 <= length <= 4999:
        raise ValueError("Smoke length must be in 1,025..4,999 nt")
    import torch

    config = json.loads(CONTROL.read_text())["config"]
    torch.set_num_threads(config["cpu_threads"])
    torch.manual_seed(config["seed"])
    sequence = "G" * (length // 2) + "C" * (length - length // 2)
    pairs = [[i, length - 1 - i] for i in range(min(100, length // 2))]
    indices, labels, excluded = sampled_pair_supervision(
        {"sequence": sequence, "pairs": pairs}, seed=config["seed"])
    if excluded or int(labels.sum()) != len(pairs) or len(indices) > len(pairs) + 8192:
        raise ValueError("Synthetic supervision inventory differs")
    model = make_helix_model(config)
    optimizer = torch.optim.Adam(model.parameters(), lr=config["learning_rate"])
    loss_fn = torch.nn.BCEWithLogitsLoss(
        pos_weight=torch.tensor((len(labels) - int(labels.sum())) / int(labels.sum())))
    started = monotonic()
    optimizer.zero_grad(set_to_none=True)
    logits = model(tokens(sequence), indices)
    loss = loss_fn(logits, labels)
    if not bool(torch.isfinite(loss)):
        raise ValueError("Nonfinite synthetic loss")
    loss.backward()
    optimizer.step()
    return {"status": "completed", "kind": "synthetic_resource_smoke_only",
            "length_nt": length, "positive_pairs": int(labels.sum()),
            "sampled_negative_pairs": len(labels) - int(labels.sum()),
            "loss_before_step": float(loss.detach()),
            "step_seconds": monotonic() - started,
            "peak_process_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "biological_accuracy_claim": False, "checkpoint_saved": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--length", type=int, default=4999)
    args = parser.parse_args()
    print(json.dumps(run(args.length), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
