#!/usr/bin/env python3
"""Frozen-code helix prior replication on exposed synthetic inputs, with bounded native jobs."""

import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp, publish
from rnastable.folding import run_bounded
from rnastable.native_journal import atomic_json, exclusive_driver
from rnastable.reference import digest
from rnastable.reference_audit import require

PLAN = [
    {"input_index": index, "seed": seed}
    for index in (0, 1, 2)
    for seed in (20261006, 20261007)
]
DEADLINE = "2026-10-07T04:00:00+00:00"


def remaining():
    return (
        datetime.datetime.fromisoformat(DEADLINE)
        - datetime.datetime.now(datetime.timezone.utc)
    ).total_seconds()


def audit_child(snapshot, path):
    env = {**os.environ, "PYTHONPATH": str(snapshot / "src")}
    result = subprocess.run(
        [
            sys.executable,
            str(snapshot / "scripts/verify_checkpoint_prior_pilot.py"),
            str(path),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    require(
        result.returncode == 0, "Frozen child audit failed: " + result.stderr[-2000:]
    )
    print(result.stdout.strip(), flush=True)
    return json.loads(Path(path).read_text())


def aggregate(run, manifest, components):
    rows = [
        {"input_id": summary["input_id"], "seed": summary["seed"], **row}
        for summary in components
        for row in summary["rows"]
    ]
    return {
        "complete": len(components) == len(PLAN),
        "run_dir": str(run),
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "plan": PLAN,
        "test_accuracy_evaluated": False,
        "model_fitted": False,
        "components": [
            {
                "summary": str(Path(summary["run_dir"]) / "summary.json"),
                "sha256": digest(
                    (Path(summary["run_dir"]) / "summary.json").read_bytes()
                ),
            }
            for summary in components
        ],
        "rows": rows,
        "unique_native_requests": sum(
            s["cost_accounting"]["native"]["unique_requests"] for s in components
        ),
        "unknown_native_requests": sum(
            s["cost_accounting"]["native"]["unknown_requests"] for s in components
        ),
        "known_native_wall_seconds": sum(
            s["cost_accounting"]["native"]["known_native_wall_seconds"]
            for s in components
        ),
        "completed_proxy_calls_across_attempts": sum(
            s["cost_accounting"]["completed_proxy_calls_across_attempts"]
            for s in components
        ),
        "known_proxy_wall_seconds_across_attempts": sum(
            s["cost_accounting"]["known_proxy_wall_seconds_across_attempts"]
            for s in components
        ),
        "equal_native_proposal_budget_measured": all(
            s["equal_native_proposal_budget_measured"] for s in components
        ),
        **(
            {"source_model_seed": manifest["source_model_seed"]}
            if "source_model_seed" in manifest
            else {}
        ),
        "limitations": [
            "Previously exposed synthetic sequences and two search seeds; no fresh accuracy test, biological assay or generalization claim.",
            "Helix checkpoint replaces the prior; the other proposal-ranking and mutation settings remain fixed. Vienna final validation is explicitly extended from30 to300 seconds for every arm.",
            "The earlier stack replication used30-second finalist validation; compare the separately extended10k stack selections with this study, not its original timeouts.",
            "Code is frozen for all components. Native requests run serially within the study, but other development checks may overlap; timings are observations, not isolated speed benchmarks.",
            "Unknown or interrupted native requests are retained in denominators and never automatically retried. Deadline may leave a partial study.",
        ],
    }


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(
        summary == json.loads((run / "summary.json").read_text()),
        "Retained aggregate differs",
    )
    require(
        digest((run / "manifest.json").read_bytes()) == summary["manifest_sha256"],
        "Manifest changed",
    )
    manifest = json.loads((run / "manifest.json").read_text())
    require(
        manifest["plan"] == PLAN and manifest["run_dir"] == str(run),
        "Study plan differs",
    )
    snapshot = run / "snapshot"
    for name, sha in manifest["frozen_sha256"].items():
        require(
            digest((snapshot / name).read_bytes()) == sha,
            "Frozen source changed: " + name,
        )
    require(len(summary["components"]) <= len(PLAN), "Too many components")
    components = []
    bindings = []
    for expected, item in zip(PLAN, summary["components"]):
        path = Path(item["summary"])
        require(
            path.resolve().is_relative_to(
                (snapshot / "results/checkpoint_prior_pilot_runs").resolve()
            ),
            "Child outside retained study",
        )
        require(digest(path.read_bytes()) == item["sha256"], "Child changed")
        component = audit_child(snapshot, path)
        binding = json.loads((Path(component["run_dir"]) / "manifest.json").read_text())
        require(
            binding["input_index"] == expected["input_index"]
            and component["seed"] == expected["seed"],
            "Input/seed differs",
        )
        require(
            binding["config"] == {**manifest["config"], "seed": expected["seed"]}
            and binding["model_config"]["pair_features"] == "local_helix_context_v1",
            "Fixed config/model differs",
        )
        require(
            binding["snapshot_sha256"]["source_summary.json"]
            == manifest["source_summary_sha256"],
            "Checkpoint source differs",
        )
        components.append(component)
        bindings.append(binding)
    for key in ("checkpoint_sha256", "code_sha256", "native_runtime"):
        require(
            all(binding[key] == bindings[0][key] for binding in bindings),
            "Shared source/runtime differs",
        )
    require(
        aggregate(run, manifest, components) == summary, "Aggregate accounting differs"
    )
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--source-summary", type=Path)
    parser.add_argument("--publish-name")
    args = parser.parse_args()
    if args.verify:
        return audit(
            ROOT
            / "results"
            / ((args.publish_name or "helix_prior_replication") + "_summary.json")
        )
    if args.resume:
        run = args.resume.resolve()
    else:
        run = ROOT / "results/helix_prior_replication_runs" / timestamp()
        run.mkdir(parents=True, exist_ok=False)
        snapshot = run / "snapshot"
        for name in ("src", "scripts", "configs"):
            shutil.copytree(
                ROOT / name,
                snapshot / name,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        (snapshot / "external").symlink_to(ROOT / "external", target_is_directory=True)
        (snapshot / "results").mkdir()
        (snapshot / "reports").mkdir()
        for name in (
            "helix_comparative_development_summary.json",
            "stack_scalability_summary.json",
        ):
            source_path = (
                args.source_summary
                if name == "helix_comparative_development_summary.json"
                and args.source_summary is not None
                else ROOT / "results" / name
            )
            shutil.copy2(source_path, snapshot / "results" / name)
        config = {
            **json.loads((ROOT / "configs/checkpoint_prior_pilot.json").read_text()),
            "finalist_timeout_seconds": 300,
        }
        atomic_json(snapshot / "configs/helix_prior_replication.json", config)
        manifest = {
            "run_dir": str(run),
            "plan": PLAN,
            "deadline_utc": DEADLINE,
            "publish_name": args.publish_name or "helix_prior_replication",
            "source_model_seed": json.loads(
                (
                    snapshot / "results/helix_comparative_development_summary.json"
                ).read_text()
            )["config"]["seed"],
            "config": config,
            "source_summary_sha256": digest(
                (
                    snapshot / "results/helix_comparative_development_summary.json"
                ).read_bytes()
            ),
            "frozen_sha256": {
                str(p.relative_to(snapshot)): digest(p.read_bytes())
                for directory in ("src", "scripts", "configs")
                for p in sorted((snapshot / directory).rglob("*"))
                if p.is_file()
            },
            "policy": "Frozen code and model, fixed exposed synthetic input/seed plan, serial bounded native requests. No test accuracy or model fitting.",
        }
        atomic_json(run / "manifest.json", manifest)
    snapshot = run / "snapshot"
    manifest = json.loads((run / "manifest.json").read_text())
    components = []
    if args.publish_name is not None:
        require(
            args.publish_name
            == manifest.get("publish_name", "helix_prior_replication"),
            "Resume publication name differs",
        )
    if args.source_summary is not None:
        require(
            digest(args.source_summary.read_bytes())
            == manifest["source_summary_sha256"],
            "Resume source differs",
        )
    with exclusive_driver(run / ".driver.lock"):
        for index, item in enumerate(PLAN):
            pointer = run / ("component_" + str(index) + ".json")
            name = "helix_prior_replica_" + str(index)
            if pointer.exists():
                state = json.loads(pointer.read_text())
                require(
                    digest(Path(state["summary"]).read_bytes()) == state["sha256"],
                    "Completed pointer changed",
                )
                components.append(audit_child(snapshot, state["summary"]))
                continue
            if remaining() < 600:
                print("Deadline reserve reached; retain partial study.", flush=True)
                break
            existing = [
                p.parent
                for p in (snapshot / "results/checkpoint_prior_pilot_runs").glob(
                    "*/manifest.json"
                )
                if json.loads(p.read_text()).get("replication_component")
                == str(pointer)
            ]
            require(len(existing) <= 1, "Ambiguous resume")
            command = [
                sys.executable,
                str(snapshot / "scripts/run_checkpoint_prior_pilot.py"),
                "--source-summary",
                str(snapshot / "results/helix_comparative_development_summary.json"),
                "--config",
                str(snapshot / "configs/helix_prior_replication.json"),
                "--seed",
                str(item["seed"]),
                "--input-index",
                str(item["input_index"]),
                "--replication-component",
                str(pointer),
                "--publish-name",
                name,
            ]
            if existing:
                config_position = command.index("--config")
                del command[config_position : config_position + 2]
                command += ["--resume", str(existing[0])]
            print(f"Helix replica {index + 1}/{len(PLAN)}: {item}", flush=True)
            prior_path = os.environ.get("PYTHONPATH")
            os.environ["PYTHONPATH"] = str(snapshot / "src")
            try:
                result = run_bounded(
                    command,
                    "",
                    timeout=min(3600, max(1, remaining() - 300)),
                    memory_limit_gib=8,
                    cwd=ROOT,
                )
            finally:
                if prior_path is None:
                    os.environ.pop("PYTHONPATH", None)
                else:
                    os.environ["PYTHONPATH"] = prior_path
            (run / ("component_" + str(index) + ".log")).write_text(
                result.pop("stdout", "") + "\n" + result.get("error", "")
            )
            atomic_json(run / ("component_" + str(index) + "_process.json"), result)
            if result["status"] != "ok":
                print(
                    "Bounded component failed; retain journal and partial denominators.",
                    flush=True,
                )
                break
            path = (
                existing[0] / "summary.json"
                if existing
                else Path(
                    json.loads(
                        (snapshot / "results" / (name + "_summary.json")).read_text()
                    )["run_dir"]
                )
                / "summary.json"
            )
            component = audit_child(snapshot, path)
            components.append(component)
            atomic_json(
                pointer, {"summary": str(path), "sha256": digest(path.read_bytes())}
            )
            atomic_json(run / "progress.json", aggregate(run, manifest, components))
        summary = aggregate(run, manifest, components)
        atomic_json(run / "summary.json", summary)
        report = [
            "# Helix checkpoint-prior synthetic replication",
            "",
            manifest["policy"],
            "",
            *summary["limitations"],
            "",
            "| Input | Seed | Policy | Proposals | Proxy calls | Selected Vienna delta | Reason |",
            "|---|---:|---|---:|---:|---:|---|",
        ]
        for row in summary["rows"]:
            report.append(
                f"| {row['input_id']} | {row['seed']} | {row['policy']} | {row['attempted_proposal_folds']} | {row['proxy_evaluations']} | {row['selected_vienna_delta_kcal_mol']} | {row['selection_reason']} |"
            )
        publish(
            ROOT,
            manifest.get("publish_name", "helix_prior_replication"),
            summary,
            summary["rows"],
            list(summary["rows"][0])
            if summary["rows"]
            else ["input_id", "seed", "policy"],
            "\n".join(report) + "\n",
        )
        print(json.dumps(summary, indent=2))
        return summary


if __name__ == "__main__":
    main()
