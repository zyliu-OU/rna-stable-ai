#!/usr/bin/env python3
"""Three-seed structured-versus-BCE helix development on frozen snapshots."""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from analyze_development_slices import replay
from train_structured_comparative_development import make_loss
from rnastable.artifacts import publish, timestamp
from rnastable.context_inference import load_checkpoint
from rnastable.context_training import train_context
from rnastable.development_slices import SEEDS, source_group, length_group
from rnastable.exposures import record_exposure, read_exposure, exposure_records
from rnastable.folding import run_bounded
from rnastable.full_pair_supervision import full_supervision
from rnastable.helix_pairs import make_helix_model
from rnastable.native_journal import atomic_json, exclusive_driver
from rnastable.pair_head_study import predictions, METHODS
from rnastable.reference import digest
from rnastable.reference_audit import require
from rnastable.scoring import structure_agreement
from rnastable.structure_model import tokens

NAME = "helix_objective_development"
OBJECTIVE = {
    "top_k": 16,
    "margin": 1.0,
    "bce_coefficient": 0.1,
    "validation_loss": "full_weighted_bce",
    "normalizer": "supported_gold_count",
}
LIMITATIONS = [
    "Development-only comparison on the same89 training/47 validation records; no independent accuracy claim.",
    "Three seeds share biological labels. Original BCE checkpoints are reused; structured models are newly trained from matched initializations.",
    "Both objectives independently select epoch by development F1, then lower full weighted validation BCE, then earliest epoch.",
    "Pruned loss-augmented training retains supported gold; inference uses unaugmented positive top16 pools. No full-graph structured optimality claim.",
    "Training losses have different units/scales and are not directly comparable; logits are not folding energies or stability measurements.",
    "No prospective inputs, native folds or inference default changes. Resource measurements are bounded CPU observations.",
]


def objective_config(source):
    cfg = source["config"]
    require(
        source["head"] == "helix"
        and cfg["pair_features"] == "local_helix_context_v1"
        and cfg["top_k"] == 16
        and cfg["inference_decoder"] == "exact_sparse"
        and cfg["epochs"] == 10
        and "structured_loss" not in cfg,
        "Expected unchanged BCE helix source",
    )
    return {**cfg, "structured_loss": dict(OBJECTIVE)}


def loss_inventory(decisions, history, records, config, samples):
    """Verify every labelled training decision in deterministic epoch order."""
    expected, orders = [], []
    rng = random.Random(config["seed"])
    for _ in range(config["epochs"]):
        order = list(range(len(records)))
        rng.shuffle(order)
        order = [i for i in order if len(samples[i][1])]
        orders.append(order)
        expected.extend(order)
    require(len(decisions) == len(expected), "Training step denominator differs")
    for step, (row, index) in enumerate(zip(decisions, expected), 1):
        record = records[index]
        _, labels, _ = samples[index]
        require(
            row["step"] == step
            and row["id"] == record["id"]
            and row["sequence_sha256"] == digest(record["sequence"].encode())
            and row["target_sha256"] == digest(labels.numpy().tobytes()),
            "Training decision binding differs",
        )
        gold = int(labels.sum())
        require(
            row["gold_pairs"] == gold
            and row["normalizer"] == max(1, gold)
            and row["candidate_count"] >= gold,
            "Supported gold retention differs",
        )
        for k in (
            "hinge_loss",
            "weighted_bce",
            "mixed_loss",
            "augmented_objective",
            "raw_margin_violation",
        ):
            require(
                type(row[k]) in (int, float) and math.isfinite(row[k]),
                "Invalid training loss observation",
            )
        require(
            row["hinge_loss"] == max(0, row["raw_margin_violation"]) / row["normalizer"]
            and row["mixed_loss"]
            == row["hinge_loss"] + OBJECTIVE["bce_coefficient"] * row["weighted_bce"],
            "Mixed loss arithmetic differs",
        )
    offset = 0
    require(len(history) == config["epochs"], "Epoch count differs")
    for row, order in zip(history, orders):
        require(
            row["mean_train_loss"]
            == sum(r["mixed_loss"] for r in decisions[offset : offset + len(order)])
            / len(order),
            "Epoch training denominator differs",
        )
        offset += len(order)
    return expected


def train_component(run):
    run = Path(run).resolve()
    manifest = json.loads((run / "manifest.json").read_text())
    plan = json.loads((run.parents[1] / "manifest.json").read_text())
    require(
        digest((run.parents[1] / "manifest.json").read_bytes())
        == manifest["study_manifest_sha256"],
        "Study plan changed",
    )
    for p, sha in plan["code_sha256"].items():
        require(digest(Path(p).read_bytes()) == sha, "Execution code changed")
    source = json.loads((run / "source_summary.json").read_text())
    config = objective_config(source)
    require(config == manifest["config"], "Objective configuration changed")
    splits = {
        name: json.loads((run / (name + ".json")).read_text())["records"]
        for name in ("train", "validation")
    }
    for name in ("train", "validation", "source_summary"):
        require(
            digest((run / (name + ".json")).read_bytes())
            == manifest["snapshot_sha256"][name + ".json"],
            "Component input changed",
        )
    events = [
        record_exposure(
            run,
            "training_started" if name == "train" else "validation_started",
            splits[name],
        )
        for name in ("train", "validation")
    ]
    samples = [
        full_supervision(r, config["training_max_length"]) for r in splits["train"]
    ]
    positive = sum(int(y.sum()) for _, y, _ in samples)
    negative = sum(len(y) - int(y.sum()) for _, y, _ in samples)
    weight = (negative / positive) ** config["positive_weight_exponent"]
    decisions = []

    def record_decision(row):
        row = {"step": len(decisions) + 1, **row}
        decisions.append(row)
        with (run / "loss_decisions.jsonl").open("a") as f:
            f.write(json.dumps(row, allow_nan=False) + "\n")

    initial, model, training = train_context(
        splits["train"],
        splits["validation"],
        config,
        run,
        model_factory=make_helix_model,
        labeler=lambda r: full_supervision(r, config["training_max_length"]),
        predictor=lambda m, rs, method: predictions(m, rs, method, config),
        training_loss_fn=make_loss(config, weight, record_decision),
    )
    methods = METHODS["helix"]
    rows = predictions(initial, splits["validation"], methods[0], config) + predictions(
        model, splits["validation"], methods[1], config
    )
    atomic_json(
        run / "predictions.json",
        {"schema_version": 1, "methods": list(methods), "records": rows},
    )
    summary = {
        "complete": True,
        "run_dir": str(run),
        "mode": config["mode"],
        "head": "helix",
        "seed": config["seed"],
        "config": config,
        "test_evaluated": False,
        "development_only": True,
        "counts": {name: len(rs) for name, rs in splits.items()},
        **training,
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "predictions_sha256": digest((run / "predictions.json").read_bytes()),
        "loss_decisions_sha256": digest((run / "loss_decisions.jsonl").read_bytes()),
        "training_decisions": len(decisions),
        "exposure_events": events,
    }
    atomic_json(run / "summary.json", summary)
    return summary


def audit_component(run):
    import torch

    run = Path(run)
    summary = json.loads((run / "summary.json").read_text())
    manifest = json.loads((run / "manifest.json").read_text())
    source = json.loads((run / "source_summary.json").read_text())
    config = objective_config(source)
    require(
        summary["complete"] is True
        and summary["test_evaluated"] is False
        and summary["development_only"] is True
        and config == manifest["config"] == summary["config"]
        and summary["seed"] == config["seed"]
        and summary["head"] == "helix"
        and summary["mode"] == config["mode"]
        and summary["run_dir"] == str(run)
        and digest((run / "manifest.json").read_bytes()) == summary["manifest_sha256"],
        "Component identity differs",
    )
    splits = {}
    for name in ("train", "validation", "source_summary"):
        p = run / (name + ".json")
        require(
            digest(p.read_bytes()) == manifest["snapshot_sha256"][p.name],
            "Component snapshot changed",
        )
        if name != "source_summary":
            require(
                p.read_bytes() == (Path(source["run_dir"]) / p.name).read_bytes(),
                "Original BCE cohort differs",
            )
            splits[name] = json.loads(p.read_text())["records"]
    require(
        summary["counts"] == {n: len(rs) for n, rs in splits.items()},
        "Cohort counts differ",
    )
    samples = [
        full_supervision(r, config["training_max_length"]) for r in splits["train"]
    ]
    positive = sum(int(y.sum()) for _, y, _ in samples)
    negative = sum(len(y) - int(y.sum()) for _, y, _ in samples)
    require(
        summary["train_positive_pairs"] == positive
        and summary["train_negative_pairs"] == negative
        and summary["train_only_positive_weight"]
        == (negative / positive) ** config["positive_weight_exponent"]
        and summary["excluded_train_contacts"] == sum(s[2] for s in samples)
        and summary["excluded_validation_contacts"]
        == sum(
            full_supervision(r, config["training_max_length"])[2]
            for r in splits["validation"]
        ),
        "Supervision denominator differs",
    )
    events = summary["exposure_events"]
    require(
        len(events) == 2
        and {Path(e["path"]) for e in events}
        == set((run / "exposures").glob("*.json")),
        "Exposure inventory differs",
    )
    for event, name, stage in zip(
        events, ("train", "validation"), ("training_started", "validation_started")
    ):
        p = Path(event["path"])
        observed = read_exposure(p)
        require(
            p.resolve().parent == (run / "exposures").resolve()
            and digest(p.read_bytes()) == event["sha256"]
            and observed["stage"] == event["stage"] == stage
            and observed["records"]
            == exposure_records(splits[name], str(run) + " " + stage),
            "Exposure differs",
        )
    history = summary["history"]
    require(
        history
        == [
            json.loads(line) for line in (run / "epochs.jsonl").read_text().splitlines()
        ]
        and [r["epoch"] for r in history] == list(range(1, config["epochs"] + 1)),
        "Epoch ledger differs",
    )
    require(
        digest((run / "loss_decisions.jsonl").read_bytes())
        == summary["loss_decisions_sha256"],
        "Loss ledger changed",
    )
    decisions = [
        json.loads(line)
        for line in (run / "loss_decisions.jsonl").read_text().splitlines()
    ]
    require(len(decisions) == summary["training_decisions"], "Decision count changed")
    expected = loss_inventory(decisions, history, splits["train"], config, samples)
    chosen = max(
        history,
        key=lambda r: (r["validation_mean_pair_f1"], -r["mean_validation_loss"]),
    )
    require(
        chosen["epoch"] == summary["selected_epoch"]
        and chosen["validation_mean_pair_f1"] == summary["selected_validation_pair_f1"],
        "Epoch selection differs",
    )
    torch.set_num_threads(config["cpu_threads"])
    replayed = []
    for filename, method in zip(
        ("initial_context_model.pt", "best_context_model.pt"), METHODS["helix"]
    ):
        p = run / filename
        require(
            digest(p.read_bytes()) == summary["checkpoint_sha256"][filename],
            "Checkpoint changed",
        )
        torch.manual_seed(config["seed"])
        model = make_helix_model(config)
        state = torch.load(p, map_location="cpu", weights_only=True)
        if filename.startswith("initial"):
            original = torch.load(
                Path(source["run_dir"]) / filename,
                map_location="cpu",
                weights_only=True,
            )
            require(
                set(state) == set(original)
                and all(
                    torch.equal(v, state[k]) and torch.equal(v, original[k])
                    for k, v in model.state_dict().items()
                ),
                "Matched helix initialization differs",
            )
            first = splits["train"][expected[0]]
            edges, labels, _ = samples[expected[0]]
            anchor = []
            with torch.inference_mode():
                make_loss(config, summary["train_only_positive_weight"], anchor.append)(
                    model(tokens(first["sequence"]), edges), edges, labels, first
                )
            require(
                anchor[0] == {k: v for k, v in decisions[0].items() if k != "step"},
                "First loss/graph anchor differs",
            )
        model.load_state_dict(state)
        require(
            sum(p.numel() for p in model.parameters())
            == summary["parameters"]
            == source["parameters"],
            "Model size differs",
        )
        rows = predictions(model, splits["validation"], method, config)
        replayed.extend(rows)
        if filename.startswith("best"):
            require(
                sum(
                    structure_agreement(p["structure"], r["structure"])["pair_f1"]
                    for p, r in zip(rows, splits["validation"])
                )
                / len(rows)
                == summary["selected_validation_pair_f1"],
                "Selected prediction F1 differs",
            )
            model.eval()
            losses = []
            loss_fn = torch.nn.BCEWithLogitsLoss(
                pos_weight=torch.tensor(summary["train_only_positive_weight"])
            )
            with torch.inference_mode():
                for r in splits["validation"]:
                    edges, labels, _ = full_supervision(
                        r, config["training_max_length"]
                    )
                    if len(labels):
                        losses.append(
                            loss_fn(model(tokens(r["sequence"]), edges), labels).item()
                        )
            require(
                sum(losses) / len(losses) == chosen["mean_validation_loss"],
                "Full validation BCE differs",
            )
    require(
        digest((run / "predictions.json").read_bytes()) == summary["predictions_sha256"]
        and json.loads((run / "predictions.json").read_text())["records"] == replayed,
        "Predictions differ",
    )
    original_rows = json.loads(
        (Path(source["run_dir"]) / "predictions.json").read_text()
    )["records"]
    require(
        replayed[: len(splits["validation"])]
        == [r for r in original_rows if r["method"].startswith("untrained_")],
        "Initial predictions differ from BCE",
    )
    print(
        f"Helix objective audit:seed{config['seed']}, {len(decisions)} bound loss decisions, matched initialization and exact checkpoint replay",
        flush=True,
    )
    return summary


def summarize(run, plan, attempts, components):
    rows, slices, fits = [], [], []
    for item, attempt in zip(plan["components"], attempts):
        source = json.loads(Path(item["source_summary"]).read_text())
        directory = Path(attempt["run_dir"])
        comp = components.get(item["seed"])
        fits.append(
            {
                "seed": item["seed"],
                "status": "ok"
                if comp
                else attempt.get("result", {}).get("status", attempt["state"]),
                "bce_selected_epoch": source["selected_epoch"],
                "bce_validation_pair_f1": source["selected_validation_pair_f1"],
                "structured_selected_epoch": comp["selected_epoch"] if comp else None,
                "structured_validation_pair_f1": comp["selected_validation_pair_f1"]
                if comp
                else None,
                "f1_delta": comp["selected_validation_pair_f1"]
                - source["selected_validation_pair_f1"]
                if comp
                else None,
                "known_wall_seconds": attempt.get("result", {}).get("wall_seconds"),
            }
        )
        records = json.loads((directory / "validation.json").read_text())["records"]
        old = {
            r["id"]: r
            for r in json.loads(
                (Path(source["run_dir"]) / "predictions.json").read_text()
            )["records"]
            if r["method"].startswith("trained_")
        }
        new = (
            {
                r["id"]: r
                for r in json.loads((directory / "predictions.json").read_text())[
                    "records"
                ]
                if r["method"].startswith("trained_")
            }
            if comp
            else {}
        )
        require(
            len(records) == 47
            and set(old) == {r["id"] for r in records}
            and (not comp or set(new) == set(old)),
            "Paired record inventory differs",
        )
        for record in records:
            before = structure_agreement(
                old[record["id"]]["structure"], record["structure"]
            )
            after = (
                structure_agreement(new[record["id"]]["structure"], record["structure"])
                if comp
                else None
            )
            rows.append(
                {
                    "seed": item["seed"],
                    "id": record["id"],
                    "source_group": source_group(record),
                    "length_group": length_group(len(record["sequence"])),
                    "reference_kind": record["reference_kind"],
                    "status": "ok"
                    if comp
                    else attempt.get("result", {}).get("status", attempt["state"]),
                    "bce_f1": before["pair_f1"],
                    "structured_f1": after["pair_f1"] if after else None,
                    "f1_delta": after["pair_f1"] - before["pair_f1"] if after else None,
                    "bce_false_positives": before["predicted_pairs"]
                    - before["shared_pairs"],
                    "structured_false_positives": after["predicted_pairs"]
                    - after["shared_pairs"]
                    if after
                    else None,
                }
            )
    for seed in SEEDS:
        for dimension, groups in (
            ("all", ("all",)),
            ("source_group", ("PDB-derived", "Rfam-comparative", "CRW-comparative")),
            ("length_group", ("1..64", "65..128", "129..256", "257..1024")),
            ("reference_kind", ("experimental", "computational")),
        ):
            for group in groups:
                selected = [
                    r
                    for r in rows
                    if r["seed"] == seed
                    and (dimension == "all" or r[dimension] == group)
                ]
                measured = [r for r in selected if r["status"] == "ok"]
                slices.append(
                    {
                        "seed": seed,
                        "dimension": dimension,
                        "group": group,
                        "planned_records": len(selected),
                        "measured_records": len(measured),
                        "mean_f1_delta": sum(r["f1_delta"] for r in measured)
                        / len(measured)
                        if measured
                        else None,
                        "improved_records": sum(r["f1_delta"] > 0 for r in measured),
                        "regressed_records": sum(r["f1_delta"] < 0 for r in measured),
                        "bce_false_positives": sum(
                            r["bce_false_positives"] for r in measured
                        ),
                        "structured_false_positives": sum(
                            r["structured_false_positives"] for r in measured
                        )
                        if measured
                        else None,
                    }
                )
    require(len(rows) == 141, "Planned paired denominator differs")
    return {
        "complete": True,
        "run_dir": str(run),
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "development_only": True,
        "test_evaluated": False,
        "defaults_changed": False,
        "planned_fits": 3,
        "completed_fits": len(components),
        "planned_paired_records": 141,
        "measured_paired_records": sum(r["status"] == "ok" for r in rows),
        "fits": fits,
        "rows": rows,
        "slices": slices,
        "attempt_sha256": {
            str(Path(a["run_dir"]) / "attempt.json"): digest(
                (Path(a["run_dir"]) / "attempt.json").read_bytes()
            )
            for a in attempts
        },
        "component_summary_sha256": {
            str(Path(c["run_dir"]) / "summary.json"): digest(
                (Path(c["run_dir"]) / "summary.json").read_bytes()
            )
            for c in components.values()
        },
        "limitations": LIMITATIONS,
    }


def source_bindings():
    source_path = ROOT / "results/pair_head_development_study_summary.json"
    _, _, bindings = replay(source_path)
    source = json.loads(source_path.read_text())
    components = []
    for item in source["components"]:
        s = json.loads(Path(item["summary"]).read_text())
        if s["head"] == "helix":
            objective_config(s)
            _, _, checkpoint, _ = load_checkpoint(Path(item["summary"]))
            for p in (
                checkpoint,
                Path(s["run_dir"]) / "initial_context_model.pt",
                Path(s["run_dir"]) / "train.json",
            ):
                bindings[str(p)] = digest(p.read_bytes())
            components.append({"seed": s["seed"], "source_summary": item["summary"]})
    require(
        sorted(c["seed"] for c in components) == list(SEEDS),
        "Expected all three BCE helix seeds",
    )
    return components, bindings


def audit(run):
    run = Path(run)
    summary = json.loads((run / "summary.json").read_text())
    plan = json.loads((run / "manifest.json").read_text())
    components, bindings = source_bindings()
    require(
        plan["components"] == components
        and plan["source_sha256"] == bindings
        and plan["objective"] == OBJECTIVE
        and plan["component_timeout_seconds"] == 600
        and plan["memory_limit_gib"] == 8
        and plan["limitations"] == LIMITATIONS,
        "Study bindings differ",
    )
    for p, sha in plan["code_sha256"].items():
        require(digest(Path(p).read_bytes()) == sha, "Study code changed")
    attempts, fitted = [], {}
    for item in components:
        directory = run / "components" / str(item["seed"])
        m = json.loads((directory / "manifest.json").read_text())
        require(
            m["study_manifest_sha256"] == digest((run / "manifest.json").read_bytes())
            and m["config"]
            == objective_config(json.loads(Path(item["source_summary"]).read_text()))
            and (directory / "source_summary.json").read_bytes()
            == Path(item["source_summary"]).read_bytes(),
            "Component source differs",
        )
        attempt = json.loads((directory / "attempt.json").read_text())
        require(
            attempt["run_dir"] == str(directory)
            and attempt["seed"] == item["seed"]
            and attempt["state"]
            in ("complete", "interrupted", "recovered_complete_unknown_cost"),
            "Attempt state differs",
        )
        attempts.append(attempt)
        if (directory / "summary.json").exists():
            fitted[item["seed"]] = audit_component(directory)
    require(
        summarize(run, plan, attempts, fitted) == summary,
        "Study summary/denominators differ",
    )
    print(
        f"Helix objective study replay passed:{len(fitted)}/3 fits,141 planned paired outcomes; no test or native folds."
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component-run", type=Path)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--resume", type=Path)
    args = parser.parse_args()
    if args.component_run:
        return train_component(args.component_run)
    if args.verify:
        summary = json.loads((ROOT / "results" / (NAME + "_summary.json")).read_text())
        require(
            summary
            == json.loads((Path(summary["run_dir"]) / "summary.json").read_text()),
            "Published summary differs",
        )
        return audit(summary["run_dir"])
    if args.resume:
        run = args.resume.resolve()
        plan = json.loads((run / "manifest.json").read_text())
        comps, bindings = source_bindings()
        require(
            plan["components"] == comps and plan["source_sha256"] == bindings,
            "Resume sources changed",
        )
        for p, sha in plan["code_sha256"].items():
            require(digest(Path(p).read_bytes()) == sha, "Resume code changed")
    else:
        comps, bindings = source_bindings()
        run = ROOT / "results" / (NAME + "_runs") / timestamp()
        run.mkdir(parents=True, exist_ok=False)
        paths = [
            Path(__file__),
            ROOT / "scripts/analyze_development_slices.py",
            ROOT / "scripts/train_structured_comparative_development.py",
            *sorted((ROOT / "src/rnastable").glob("*.py")),
        ]
        plan = {
            "run_dir": str(run),
            "components": comps,
            "source_sha256": bindings,
            "code_sha256": {str(p): digest(p.read_bytes()) for p in paths},
            "objective": OBJECTIVE,
            "component_timeout_seconds": 600,
            "memory_limit_gib": 8,
            "limitations": LIMITATIONS,
        }
        atomic_json(run / "manifest.json", plan)
    with exclusive_driver(run / ".driver.lock"):
        if (run / "summary.json").exists():
            return audit(run)
        attempts, fitted = [], {}
        for item in plan["components"]:
            directory = run / "components" / str(item["seed"])
            p = directory / "attempt.json"
            if p.exists():
                attempt = json.loads(p.read_text())
                if attempt["state"] == "started":
                    attempt["state"] = (
                        "recovered_complete_unknown_cost"
                        if (directory / "summary.json").exists()
                        else "interrupted"
                    )
                    atomic_json(p, attempt)
            else:
                directory.mkdir(parents=True, exist_ok=False)
                source = json.loads(Path(item["source_summary"]).read_text())
                for name in ("train", "validation"):
                    (directory / (name + ".json")).write_bytes(
                        (Path(source["run_dir"]) / (name + ".json")).read_bytes()
                    )
                (directory / "source_summary.json").write_bytes(
                    Path(item["source_summary"]).read_bytes()
                )
                atomic_json(
                    directory / "manifest.json",
                    {
                        "study_manifest_sha256": digest(
                            (run / "manifest.json").read_bytes()
                        ),
                        "config": objective_config(source),
                        "snapshot_sha256": {
                            name: digest((directory / name).read_bytes())
                            for name in (
                                "train.json",
                                "validation.json",
                                "source_summary.json",
                            )
                        },
                    },
                )
                attempt = {
                    "run_dir": str(directory),
                    "seed": item["seed"],
                    "state": "started",
                }
                atomic_json(p, attempt)
                print(f"Structured helix fit:seed{item['seed']}", flush=True)
                result = run_bounded(
                    [
                        sys.executable,
                        str(Path(__file__).resolve()),
                        "--component-run",
                        str(directory),
                    ],
                    "",
                    600,
                    8,
                    ROOT,
                )
                output = result.pop("stdout", "")
                (directory / "process.log").write_text(
                    output + "\nSTDERR:\n" + result.get("error", "")
                )
                attempt.update(state="complete", result=result)
                atomic_json(p, attempt)
            attempts.append(attempt)
            if (directory / "summary.json").exists():
                fitted[item["seed"]] = audit_component(directory)
        summary = summarize(run, plan, attempts, fitted)
        atomic_json(run / "summary.json", summary)
        report = [
            "# Matched-seed helix training-objective development",
            "",
            *LIMITATIONS,
            "",
            "| Seed | Status | BCE epoch | BCE F1 | Structured epoch | Structured F1 | Delta |",
            "|---:|---|---:|---:|---:|---:|---:|",
        ]
        fields = (
            "seed",
            "status",
            "bce_selected_epoch",
            "bce_validation_pair_f1",
            "structured_selected_epoch",
            "structured_validation_pair_f1",
            "f1_delta",
        )
        report.extend(
            "| " + " | ".join(str(r[k]) for k in fields) + " |" for r in summary["fits"]
        )
        publish(
            ROOT,
            NAME,
            summary,
            summary["rows"],
            list(summary["rows"][0]),
            "\n".join(report) + "\n",
        )
        return summary


if __name__ == "__main__":
    main()
