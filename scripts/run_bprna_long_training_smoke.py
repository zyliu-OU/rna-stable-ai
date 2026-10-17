#!/usr/bin/env python3
"""Frozen one-step resource check on a real 3,995-nt training-only RNA."""

import argparse
import json
from pathlib import Path
import resource
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.exposures import record_exposure  # noqa: E402
from rnastable.helix_pairs import make_helix_model  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.reference import digest  # noqa: E402
from rnastable.sampled_pair_supervision import sampled_pair_supervision  # noqa: E402
from rnastable.structure_model import tokens  # noqa: E402

SOURCE = ROOT / "results/bprna_long_training_smoke_runs/20261017T033749.792816Z"
CONTROL = ROOT / "results/family_pair_set_training_runs/20261016T012741.486402Z/helix_seed1729/summary.json"
PROTOCOL = ROOT / "results/bprna_long_training_step_protocol.json"
TARGET = "bpRNA_RFAM_43122"
CODE = [Path(__file__), *(ROOT / "src/rnastable" / name for name in (
    "sampled_pair_supervision.py", "helix_pairs.py", "global_sparse_pairs.py",
    "context_pairs.py", "structure_model.py", "pair_reference.py"))]


def inputs():
    source = json.loads((SOURCE / "summary.json").read_text())
    if (source["complete"] is not True or source["training_only"] is not True
            or source["selected_training_only_count"] != 17):
        raise ValueError("Long training-only screen differs")
    selected = json.loads((SOURCE / "selection.json").read_text())["selected"]
    target = next((row for row in selected if row["id"] == TARGET), None)
    if target is None or len(target["sequence"]) != 3995:
        raise ValueError("Fixed real training record differs")
    config = json.loads(CONTROL.read_text())["config"]
    if config["seed"] != 1729 or config["pair_features"] != "local_helix_context_v1":
        raise ValueError("Helix model configuration differs")
    return target, config


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    record, config = inputs()
    run = ROOT / "results/bprna_long_training_step_protocol_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "record.json", record)
    atomic_json(run / "config.json", config)
    atomic_json(run / "policy.json", {
        "schema_version": 1, "stage": "single_real_long_training_resource_step",
        "record_id": TARGET, "steps": 1, "epochs": 0,
        "max_negatives": 8192, "negatives_per_positive": 4,
        "checkpoint_selection": False, "checkpoint_saved": False,
        "model_inference_performed": False, "accuracy_claim": False})
    manifest = {"run_dir": str(run),
                "source_summary_sha256": digest((SOURCE / "summary.json").read_bytes()),
                "source_selection_sha256": digest((SOURCE / "selection.json").read_bytes()),
                "control_summary_sha256": digest(CONTROL.read_bytes()),
                "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
                "code_sha256": {str(path): digest(path.read_bytes()) for path in CODE}}
    atomic_json(run / "manifest.json", manifest)
    audit_protocol(run / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen real long training step:", run / "manifest.json")


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    if manifest != json.loads((run / "manifest.json").read_text()):
        raise ValueError("Long training-step manifest differs")
    if set(manifest["snapshot_sha256"]) != {"record.json", "config.json", "policy.json"}:
        raise ValueError("Long training-step snapshot inventory differs")
    for name, sha in manifest["snapshot_sha256"].items():
        if digest((run / name).read_bytes()) != sha:
            raise ValueError("Long training-step snapshot changed")
    for path, sha in manifest["code_sha256"].items():
        if digest(Path(path).read_bytes()) != sha:
            raise ValueError("Long training-step execution code changed")
    if (digest((SOURCE / "summary.json").read_bytes()) != manifest["source_summary_sha256"]
            or digest((SOURCE / "selection.json").read_bytes()) != manifest["source_selection_sha256"]
            or digest(CONTROL.read_bytes()) != manifest["control_summary_sha256"]):
        raise ValueError("Long training-step source/control changed")
    record, config = inputs()
    if (record != json.loads((run / "record.json").read_text())
            or config != json.loads((run / "config.json").read_text())):
        raise ValueError("Long training-step frozen input differs")
    policy = json.loads((run / "policy.json").read_text())
    if (policy["record_id"] != TARGET or policy["steps"] != 1
            or policy["max_negatives"] != 8192 or policy["negatives_per_positive"] != 4
            or policy["checkpoint_saved"] is not False
            or policy["accuracy_claim"] is not False):
        raise ValueError("Long training-step policy differs")
    return manifest, record, config, policy


def execute():
    import torch

    protocol, record, config, policy = audit_protocol(PROTOCOL)
    run = ROOT / "results/bprna_long_training_step_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "protocol.json", protocol)
    event = record_exposure(run, "training_started", [record])
    torch.set_num_threads(config["cpu_threads"])
    torch.manual_seed(config["seed"])
    torch.use_deterministic_algorithms(True)
    indices, labels, excluded = sampled_pair_supervision(
        record, seed=config["seed"], max_negatives=policy["max_negatives"],
        negatives_per_positive=policy["negatives_per_positive"])
    positive = int(labels.sum())
    negative = len(labels) - positive
    if positive == 0 or negative == 0:
        raise ValueError("Real long record lacks both training classes")
    model = make_helix_model(config)
    optimizer = torch.optim.Adam(model.parameters(), lr=config["learning_rate"])
    loss_fn = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(negative / positive))
    before = [parameter.detach().clone() for parameter in model.parameters()]
    started = monotonic()
    optimizer.zero_grad(set_to_none=True)
    logits = model(tokens(record["sequence"]), indices)
    loss = loss_fn(logits, labels)
    if not bool(torch.isfinite(loss)):
        raise ValueError("Nonfinite real long training loss")
    loss.backward()
    if any(parameter.grad is None or not bool(torch.isfinite(parameter.grad).all())
           for parameter in model.parameters()):
        raise ValueError("Missing or nonfinite real long gradients")
    optimizer.step()
    updated = any(not torch.equal(old, parameter.detach())
                  for old, parameter in zip(before, model.parameters(), strict=True))
    if not updated:
        raise ValueError("Optimizer did not update the model")
    result = {"status": "completed", "run_dir": str(run),
              "record_id": TARGET, "length_nt": len(record["sequence"]),
              "legal_positive_pairs": positive, "sampled_negative_pairs": negative,
              "unsupported_gold_pairs": excluded,
              "sampled_pair_count": len(labels),
              "loss_before_step": float(loss.detach()),
              "step_seconds": monotonic() - started,
              "peak_process_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              "model_parameters_updated": updated, "checkpoint_saved": False,
              "accuracy_claim": False, "exposure_event": event}
    atomic_json(run / "summary.json", result)
    print("Real long training resource step:", run / "summary.json")
    print(json.dumps(result, indent=2, allow_nan=False))


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
        print("Real long training-step protocol replay passed")


if __name__ == "__main__":
    main()
