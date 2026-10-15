"""Verify the matched objective contract, training ledger and failed denominators."""

import importlib.util
import random
import sys
from pathlib import Path

import pytest
import torch

from rnastable.full_pair_supervision import full_supervision
from rnastable.native_journal import atomic_json

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location(
    "helix_objective", SCRIPTS / "run_helix_objective_development.py"
)
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


def source():
    return {
        "head": "helix",
        "config": {
            "pair_features": "local_helix_context_v1",
            "top_k": 16,
            "inference_decoder": "exact_sparse",
            "epochs": 10,
            "seed": 20261006,
            "learning_rate": 0.001,
        },
    }


def test_objective_only_adds_declared_loss_and_leaves_source_intact():
    original = source()
    config = study.objective_config(original)
    assert {k: v for k, v in config.items() if k != "structured_loss"} == original[
        "config"
    ]
    config["structured_loss"]["margin"] = 2
    assert (
        study.OBJECTIVE["margin"] == 1 and "structured_loss" not in original["config"]
    )


@pytest.mark.parametrize(
    "key,value",
    [
        ("top_k", 32),
        ("epochs", 20),
        ("inference_decoder", "greedy"),
        ("pair_features", "adjacent_stackability"),
        ("structured_loss", {}),
    ],
)
def test_rejects_unmatched_source_config(key, value):
    original = source()
    original["config"][key] = value
    with pytest.raises(ValueError):
        study.objective_config(original)


def training_ledger():
    records = [
        {"id": f"r{i}", "sequence": "GAAAAC", "structure": "(....)"} for i in range(2)
    ]
    config = {"seed": 20261006, "epochs": 2, "structured_loss": study.OBJECTIVE}
    samples = [full_supervision(r) for r in records]
    decisions, history = [], []
    rng = random.Random(config["seed"])
    loss_fn = study.make_loss(config, 1.0, decisions.append)
    for epoch in range(1, 3):
        order = list(range(2))
        rng.shuffle(order)
        losses = []
        for index in order:
            edges, labels, _ = samples[index]
            loss = loss_fn(torch.ones(len(edges)), edges, labels, records[index])
            decisions[-1]["step"] = len(decisions)
            losses.append(loss.item())
        history.append({"epoch": epoch, "mean_train_loss": sum(losses) / len(losses)})
    return decisions, history, records, config, samples


def test_complete_training_order_and_arithmetic_are_bound():
    args = training_ledger()
    assert len(study.loss_inventory(*args)) == 4


@pytest.mark.parametrize(
    "tamper", ["missing_step", "record", "target", "gold", "mixed_loss", "epoch_mean"]
)
def test_training_ledger_rejects_missing_or_tampered_observations(tamper):
    decisions, history, records, config, samples = training_ledger()
    if tamper == "missing_step":
        decisions.pop()
    elif tamper == "epoch_mean":
        history[0]["mean_train_loss"] += 1
    else:
        key = {
            "record": "id",
            "target": "target_sha256",
            "gold": "gold_pairs",
            "mixed_loss": "mixed_loss",
        }[tamper]
        decisions[0][key] = (
            "tampered" if tamper in ("record", "target") else decisions[0][key] + 1
        )
    with pytest.raises(ValueError):
        study.loss_inventory(decisions, history, records, config, samples)


def test_failed_fits_keep_every_paired_record_and_empty_slices(tmp_path):
    plan = {"components": []}
    atomic_json(tmp_path / "manifest.json", plan)
    attempts = []
    records = [
        {
            "id": f"PDB_{i}",
            "sequence": "GAAAAC",
            "structure": "(....)",
            "reference_kind": "experimental",
        }
        for i in range(47)
    ]
    for seed in study.SEEDS:
        directory = tmp_path / str(seed)
        directory.mkdir()
        atomic_json(directory / "validation.json", {"records": records})
        atomic_json(
            directory / "predictions.json",
            {
                "records": [
                    {
                        "id": r["id"],
                        "method": "trained_helix_sparse",
                        "structure": r["structure"],
                    }
                    for r in records
                ]
            },
        )
        atomic_json(
            directory / "source_summary.json",
            {
                "run_dir": str(directory),
                "selected_epoch": 1,
                "selected_validation_pair_f1": 1.0,
            },
        )
        attempt = {
            "run_dir": str(directory),
            "state": "complete",
            "result": {"status": "timeout"},
        }
        atomic_json(directory / "attempt.json", attempt)
        attempts.append(attempt)
        plan["components"].append(
            {"seed": seed, "source_summary": str(directory / "source_summary.json")}
        )
    result = study.summarize(tmp_path, plan, attempts, {})
    assert result["planned_paired_records"] == len(result["rows"]) == 141
    assert result["completed_fits"] == result["measured_paired_records"] == 0
    assert all(
        r["structured_f1"] is None and r["status"] == "timeout" for r in result["rows"]
    )
    empty = next(r for r in result["slices"] if r["group"] == "CRW-comparative")
    assert empty["planned_records"] == 0 and empty["mean_f1_delta"] is None
