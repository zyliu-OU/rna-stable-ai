"""Read every native request in a stopped study, including unfinished components."""

import json
import math
from pathlib import Path
from .native_journal import NativeJournal, canonical
from .pooled_native import PooledNativeRunner
from .reference import digest
from .reference_audit import require


def study_accounting(run):
    """Caller holds the parent driver's lock; this function never recovers/retries requests."""
    run = Path(run).resolve()
    parent = json.loads((run / "manifest.json").read_text())
    child_root = run / "snapshot/results/checkpoint_prior_pilot_runs"
    plan = parent["plan"]
    config = parent["config"]
    planned_per_component = 3 * (config["steps"] + 3)
    bindings = {}
    for path in sorted(child_root.glob("*/manifest.json")):
        binding = json.loads(path.read_text())
        pointer = Path(binding["replication_component"]).resolve()
        require(pointer.parent == run, "Component pointer outside study")
        index = next(
            (i for i in range(len(plan)) if pointer.name == f"component_{i}.json"), None
        )
        require(
            index is not None and index not in bindings,
            "Unknown or duplicate component",
        )
        expected = plan[index]
        require(
            binding["input_index"] == expected["input_index"]
            and binding["config"] == {**config, "seed": expected["seed"]},
            "Component fixed plan differs",
        )
        require(
            Path(binding["run_dir"]).resolve() == path.parent.resolve(),
            "Child directory identity differs",
        )
        bindings[index] = (path.parent, binding)
    rows = []
    sources = {str(run / "manifest.json"): digest((run / "manifest.json").read_bytes())}
    for index, expected in enumerate(plan):
        row = {
            "component_index": index,
            **expected,
            "planned_native_requests": planned_per_component,
            "started_native_requests": 0,
            "journal_recorded_native_requests": 0,
            "orphan_raw_native_requests": 0,
            "completed_native_requests": 0,
            "unknown_native_requests": 0,
            "known_native_wall_seconds": 0.0,
            "completed_proxy_calls": 0,
            "known_proxy_wall_seconds": 0.0,
            "incomplete_proxy_attempts": 0,
            "summary_present": False,
            "component_run_dir": None,
        }
        if index in bindings:
            child, binding = bindings[index]
            row["component_run_dir"] = str(child)
            sources[str(child / "manifest.json")] = digest(
                (child / "manifest.json").read_bytes()
            )
            directory = child / "native_journal"
            allowed = {
                f"{policy}_{phase}_{step:04d}": (policy, phase, step)
                for policy in (
                    "random_pool",
                    "compatibility_only",
                    "checkpoint_prior",
                )
                for phase, steps in (
                    ("baseline", [0]),
                    ("proposal", range(1, config["steps"] + 1)),
                    ("validation_input", [0]),
                    ("validation_finalist", [0]),
                )
                for step in steps
            }
            adapter = PooledNativeRunner.__new__(PooledNativeRunner)
            adapter.root = run / "snapshot"
            adapter.run = child
            adapter.config = binding["config"]
            recorded_keys = set()
            if directory.is_dir():
                journal = NativeJournal(directory, digest(canonical(binding)))
                for path in sorted(directory.glob("*.json")):
                    require(path.stem in allowed, "Unplanned native request key")
                    payload = journal.read(path.stem)
                    require(
                        payload["parameters"]
                        == adapter.parameters(*allowed[path.stem]),
                        "Native request parameters differ from fixed study",
                    )
                    recorded_keys.add(path.stem)
                    row["started_native_requests"] += 1
                    row["journal_recorded_native_requests"] += 1
                    row["completed_native_requests"] += int(
                        payload["state"] == "complete"
                    )
                    row["unknown_native_requests"] += int(
                        payload["state"] != "complete"
                    )
                    row["known_native_wall_seconds"] += payload.get("result", {}).get(
                        "wall_seconds", 0
                    )
                    sources[str(path)] = digest(path.read_bytes())
                marker = directory / ".binding"
                if marker.exists():
                    sources[str(marker)] = digest(marker.read_bytes())
            for key, identity in allowed.items():
                raw = Path(adapter.parameters(*identity)["raw_output"])
                if key not in recorded_keys and raw.is_file():
                    row["started_native_requests"] += 1
                    row["unknown_native_requests"] += 1
                    row["orphan_raw_native_requests"] += 1
                    sources[str(raw)] = digest(raw.read_bytes())
            for path in sorted((child / "attempts").glob("*.json")):
                attempt = json.loads(path.read_text())
                require(
                    attempt["state"] in ("started", "complete"),
                    "Unknown proxy attempt state",
                )
                require(
                    type(attempt["completed_proxy_calls"]) is int
                    and 0
                    <= attempt["completed_proxy_calls"]
                    <= config["steps"] * config["pool_size"],
                    "Invalid proxy count",
                )
                require(
                    type(attempt["known_proxy_wall_seconds"]) in (int, float)
                    and math.isfinite(attempt["known_proxy_wall_seconds"])
                    and attempt["known_proxy_wall_seconds"] >= 0,
                    "Invalid proxy cost",
                )
                row["completed_proxy_calls"] += attempt["completed_proxy_calls"]
                row["known_proxy_wall_seconds"] += attempt["known_proxy_wall_seconds"]
                row["incomplete_proxy_attempts"] += int(attempt["state"] != "complete")
                sources[str(path)] = digest(path.read_bytes())
            summary = child / "summary.json"
            if summary.exists():
                row["summary_present"] = True
                sources[str(summary)] = digest(summary.read_bytes())
                component = json.loads(summary.read_text())
                native = component["cost_accounting"]["native"]
                for key, counterpart in (
                    ("unique_requests", "started_native_requests"),
                    ("completed_requests", "completed_native_requests"),
                    ("unknown_requests", "unknown_native_requests"),
                ):
                    require(
                        native[key] == row[counterpart],
                        "Completed native summary denominator differs",
                    )
                require(
                    native["known_native_wall_seconds"]
                    == row["known_native_wall_seconds"],
                    "Completed native cost differs",
                )
        require(
            row["started_native_requests"] <= planned_per_component,
            "Unplanned native requests",
        )
        row["not_started_native_requests"] = (
            planned_per_component - row["started_native_requests"]
        )
        row["native_outcomes_and_costs_known"] = (
            row["not_started_native_requests"] == 0
            and row["unknown_native_requests"] == 0
        )
        rows.append(row)
    totals = {
        key: sum(row[key] for row in rows)
        for key in (
            "planned_native_requests",
            "started_native_requests",
            "journal_recorded_native_requests",
            "orphan_raw_native_requests",
            "completed_native_requests",
            "unknown_native_requests",
            "not_started_native_requests",
            "known_native_wall_seconds",
            "completed_proxy_calls",
            "known_proxy_wall_seconds",
            "incomplete_proxy_attempts",
        )
    }
    return {
        "run_dir": str(run),
        "source_sha256": sources,
        "rows": rows,
        "totals": totals,
        "all_planned_native_outcomes_and_costs_known": all(
            row["native_outcomes_and_costs_known"] for row in rows
        ),
        "native_requests_retried": False,
        "policy": "Every fixed planned component, including unstarted and incomplete components; started/interrupted native entries and orphan raw requests retain unknown outcome/cost. Proxy known costs count completed calls across attempts; incomplete attempts can have additional unknown work. Read-only inspection under stopped parent driver lock.",
    }
