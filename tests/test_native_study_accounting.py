import json
from pathlib import Path
import pytest
from rnastable.native_journal import NativeJournal, atomic_json, canonical
from rnastable.native_study_accounting import study_accounting
from rnastable.pooled_native import PooledNativeRunner
from rnastable.reference import digest


def fixture(tmp_path):
    run = tmp_path / "study"
    run.mkdir()
    config = {
        "steps": 8,
        "pool_size": 16,
        "seed": 7,
        "temperature_c": 37,
        "beam_size": 100,
        "timeout_seconds": 30,
        "finalist_timeout_seconds": 300,
    }
    plan = [{"input_index": 0, "seed": 7}, {"input_index": 1, "seed": 8}]
    atomic_json(run / "manifest.json", {"plan": plan, "config": config})
    child = run / "snapshot/results/checkpoint_prior_pilot_runs/component"
    child.mkdir(parents=True)
    binding = {
        "run_dir": str(child),
        "replication_component": str(run / "component_0.json"),
        "input_index": 0,
        "config": config,
    }
    atomic_json(child / "manifest.json", binding)
    adapter = PooledNativeRunner.__new__(PooledNativeRunner)
    adapter.root = run / "snapshot"
    adapter.run = child
    adapter.config = config
    return run, child, binding, adapter


def test_partial_study_keeps_started_unknown_and_unstarted_denominators(tmp_path):
    run, child, binding, adapter = fixture(tmp_path)
    journal = NativeJournal(child / "native_journal", digest(canonical(binding)))
    parameters = adapter.parameters("random_pool", "baseline", 0)
    journal.run(
        "random_pool_baseline_0000",
        "GGAAAACC",
        parameters,
        lambda: {
            "status": "ok",
            "structure": "((....))",
            "mfe_kcal_mol": -1.0,
            "wall_seconds": 0.25,
        },
    )
    with pytest.raises(KeyboardInterrupt):
        journal.run(
            "random_pool_proposal_0001",
            "GGAAAACC",
            adapter.parameters("random_pool", "proposal", 1),
            lambda: (_ for _ in ()).throw(KeyboardInterrupt()),
        )
    atomic_json(
        child / "attempts/first.json",
        {
            "state": "started",
            "completed_proxy_calls": 3,
            "known_proxy_wall_seconds": 0.5,
        },
    )
    result = study_accounting(run)
    totals = result["totals"]
    assert (
        totals["planned_native_requests"] == 66
        and totals["started_native_requests"] == 2
        and totals["completed_native_requests"] == 1
        and totals["unknown_native_requests"] == 1
        and totals["not_started_native_requests"] == 64
    )
    assert (
        totals["known_native_wall_seconds"] == 0.25
        and totals["completed_proxy_calls"] == 3
        and totals["incomplete_proxy_attempts"] == 1
    )
    assert (
        result["all_planned_native_outcomes_and_costs_known"] is False
        and result["native_requests_retried"] is False
    )
    assert result["rows"][1]["component_run_dir"] is None


def test_accounting_rejects_unplanned_request_and_invalid_proxy_cost(tmp_path):
    run, child, binding, adapter = fixture(tmp_path)
    journal = NativeJournal(child / "native_journal", digest(canonical(binding)))
    journal.run("outside_plan", "GGAAAACC", {}, lambda: {"status": "error"})
    with pytest.raises(ValueError, match="Unplanned"):
        study_accounting(run)
    journal.path("outside_plan").unlink()
    atomic_json(
        child / "attempts/first.json",
        {
            "state": "started",
            "completed_proxy_calls": 1,
            "known_proxy_wall_seconds": -1,
        },
    )
    with pytest.raises(ValueError, match="proxy cost"):
        study_accounting(run)


def test_orphan_raw_output_preserves_unknown_work_without_creating_or_retrying_journal(
    tmp_path,
):
    run, child, binding, adapter = fixture(tmp_path)
    raw = Path(adapter.parameters("random_pool", "baseline", 0)["raw_output"])
    raw.parent.mkdir()
    raw.write_text(
        "Orphan output: outcome/cost cannot be trusted without the request marker"
    )
    result = study_accounting(run)
    assert result["totals"]["planned_native_requests"] == 66
    assert (
        result["totals"]["started_native_requests"]
        == result["totals"]["unknown_native_requests"]
        == result["totals"]["orphan_raw_native_requests"]
        == 1
    )
    assert (
        result["totals"]["journal_recorded_native_requests"] == 0
        and result["totals"]["not_started_native_requests"] == 65
    )
    assert (
        str(raw) in result["source_sha256"] and not (child / "native_journal").exists()
    )
