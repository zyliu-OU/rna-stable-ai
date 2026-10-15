"""Frozen-model comparisons must preserve exposure order and unknown native outcomes."""

import importlib.util
import json
from pathlib import Path

import pytest

from rnastable.exposures import record_exposure
from rnastable.native_journal import atomic_json
from rnastable.reference import digest


@pytest.fixture
def module(monkeypatch):
    project = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(project / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "raw_structure_feasibility_test",
        project / "scripts/evaluate_raw_structure_feasibility.py",
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.fixture
def frozen(module, tmp_path, monkeypatch):
    monkeypatch.setattr(module, "ROOT", tmp_path)
    for name in (
        "evaluate_prospective_panel.py",
        "evaluate_degradation_pilot.py",
        "prepare_raw_structure_references.py",
        "verify_raw_structure_identity.py",
    ):
        p = tmp_path / "scripts" / name
        p.parent.mkdir(exist_ok=True)
        p.write_text("# fixture dependency\n")
    record = {
        "id": "fixture",
        "family_id": "RF09999",
        "pdb_accession": "9abc",
        "chain_id": "A",
        "sequence": "GCGCAU",
        "sequence_sha256": digest(b"GCGCAU"),
        "pairs": [[0, 5], [1, 4]],
        "reference_status": "ok",
        "reference_kind": "computational",
    }
    source_run = tmp_path / "source"
    source_run.mkdir()
    atomic_json(source_run / "exposure_before.json", [])
    event = record_exposure(source_run, "validation_started", [record])
    atomic_json(source_run / "manifest.json", {"exposure_event": event})
    source = {
        "run_dir": str(source_run),
        "binding": {"records": [record], "supported_references": 1},
        "readiness": {
            "scope": "six_family_structure_derived_feasibility_only",
            "feasibility_coverage_met": True,
        },
        "planned_source_requests": 1,
        "limitations": ["fixture"],
    }
    atomic_json(source_run / "summary.json", source)
    identity_run = tmp_path / "identity"
    identity_run.mkdir()
    atomic_json(identity_run / "source.json", source)
    identity = {
        "run_dir": str(identity_run),
        "selected_supported_identity_verified": True,
        "selected_supported_references": 1,
    }
    atomic_json(identity_run / "summary.json", identity)
    planning = tmp_path / "planning"
    planning.mkdir()
    models = {}
    for name in module.METHODS[:3]:
        weights = name.encode()
        (planning / (name + "_checkpoint.pt")).write_bytes(weights)
        (planning / (name + "_summary.json")).write_text("{}")
        models[name] = {
            "config": {
                "seed": 20261006,
                "top_k": 16,
                "inference_decoder": "exact_sparse",
            },
            "checkpoint_sha256": digest(weights),
        }
    atomic_json(planning / "model_protocol.json", {"models": models})
    monkeypatch.setattr(
        module, "audit_references", lambda p: json.loads(Path(p).read_text())
    )
    monkeypatch.setattr(
        module, "audit_identity", lambda p: json.loads(Path(p).read_text())
    )
    monkeypatch.setattr(
        module,
        "source_graph",
        lambda s, i: (
            {
                str(source_run / "summary.json"): digest(
                    (source_run / "summary.json").read_bytes()
                )
            },
            planning,
        ),
    )
    monkeypatch.setattr(module, "collect_known_exposures", lambda root: [record])
    monkeypatch.setattr(module, "environment", lambda: {"fixture": 1})
    monkeypatch.setattr(module, "native_runtime", lambda *a: {"fixture": 1})
    run = module.freeze(source_run / "summary.json", identity_run / "summary.json")
    calls = []

    def loaded(protocol):
        assert (run / "test_event.json").is_file()
        return {name: (name, {}) for name in module.METHODS[:3]}

    def fold(root, sequence, config, method, raw):
        assert (run / "test_event.json").is_file()
        ledger = json.loads(
            (run / "native_journal" / ("record_00_" + method + ".json")).read_text()
        )
        assert ledger["payload"]["state"] == "started"
        calls.append(method)
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_text("fixture native output\n")
        return {
            "status": "ok",
            "structure": "(....)",
            "mfe_kcal_mol": -1.0,
            "wall_seconds": 0.01,
            "raw_output": str(raw),
            "raw_sha256": digest(raw.read_bytes()),
        }

    monkeypatch.setattr(module, "models", loaded)
    monkeypatch.setattr(module, "decode_loaded", lambda *a: {"structure": "(....)"})
    monkeypatch.setattr(module, "fold_sequence", fold)
    return module, run, calls, record


def test_fixed_comparison_preserves_six_methods_and_replay_has_no_native_calls(frozen):
    module, run, calls, _ = frozen
    result = module.evaluate(run)
    assert result["planned_predictions"] == 6 and len(result["rows"]) == 6
    assert calls == ["ViennaRNA", "LinearFold"]
    assert result["native_accounting"]["completed_requests"] == 2
    assert result["native_accounting"]["unknown_requests"] == 0
    assert not result["model_fitted"] and not result["checkpoint_selected_from_test"]
    assert not result["broad_validation_gate_satisfied"]
    assert module.audit(run / "summary.json") == result
    assert calls == ["ViennaRNA", "LinearFold"]
    assert len(list((run / "exposures").glob("*.json"))) == 1


def test_interrupted_native_request_is_unknown_and_never_retried(frozen, monkeypatch):
    module, run, calls, _ = frozen
    original = module.fold_sequence

    def interrupted(*args):
        if args[3] == "ViennaRNA":
            calls.append("interrupted_ViennaRNA")
            raise KeyboardInterrupt
        return original(*args)

    monkeypatch.setattr(module, "fold_sequence", interrupted)
    with pytest.raises(KeyboardInterrupt):
        module.evaluate(run)
    result = module.evaluate(run)
    assert calls == ["interrupted_ViennaRNA", "LinearFold"]
    assert result["native_accounting"]["unknown_requests"] == 1
    row = next(r for r in result["rows"] if r["method"] == "ViennaRNA")
    assert row["status"] == "error" and row["pair_f1"] is None
    module.audit(run / "summary.json")
    module.evaluate(run)
    assert calls == ["interrupted_ViennaRNA", "LinearFold"]


def test_failed_model_prediction_remains_null_in_fixed_denominator(frozen, monkeypatch):
    module, run, _, _ = frozen

    def predict(model, *args):
        if model == "baseline":
            raise RuntimeError("fixture model unavailable")
        return {"structure": "(....)"}

    monkeypatch.setattr(module, "decode_loaded", predict)
    result = module.evaluate(run)
    row = next(r for r in result["rows"] if r["method"] == "baseline")
    assert row["status"] == "error" and row["pair_f1"] is None
    assert len(result["rows"]) == 6


def test_external_exposure_after_freeze_blocks_test_before_model_or_native(
    frozen, monkeypatch
):
    module, run, calls, record = frozen
    monkeypatch.setattr(
        module,
        "collect_known_exposures",
        lambda root: [record, {"sequence": "AAAA", "family_id": "RF09998"}],
    )
    monkeypatch.setattr(
        module,
        "models",
        lambda *a: pytest.fail("No model loading after exposure mismatch"),
    )
    with pytest.raises(ValueError, match="External exposure"):
        module.evaluate(run)
    assert not (run / "test_event.json").exists() and calls == []


@pytest.mark.parametrize("change", ["environment", "runtime", "weights", "code"])
def test_changed_runtime_weights_or_code_block_before_test_start(
    frozen, monkeypatch, change
):
    module, run, calls, _ = frozen
    if change == "environment":
        monkeypatch.setattr(module, "environment", lambda: {"fixture": 2})
    elif change == "runtime":
        monkeypatch.setattr(module, "native_runtime", lambda *a: {"fixture": 2})
    elif change == "weights":
        (run / "models/baseline_checkpoint.pt").write_bytes(b"changed")
    else:
        (module.ROOT / "scripts/evaluate_prospective_panel.py").write_text(
            "# changed fixture"
        )
    with pytest.raises(ValueError):
        module.evaluate(run)
    assert calls == [] and not (run / "test_event.json").exists()


def test_orphan_native_raw_output_is_not_overwritten(frozen):
    module, run, calls, _ = frozen
    raw = run / "raw/record_00_ViennaRNA.txt"
    raw.parent.mkdir()
    raw.write_text("orphan output must be retained")
    with pytest.raises(ValueError, match="without a journal"):
        module.evaluate(run)
    assert raw.read_text() == "orphan output must be retained" and calls == []


@pytest.mark.parametrize("change", ["raw", "journal", "event", "prediction"])
def test_replay_detects_retained_artifact_tampering_without_native_retry(
    frozen, change
):
    module, run, calls, _ = frozen
    module.evaluate(run)
    paths = {
        "raw": run / "raw/record_00_ViennaRNA.txt",
        "journal": run / "native_journal/record_00_ViennaRNA.json",
        "event": run / "test_event.json",
        "prediction": run / "predictions.json",
    }
    p = paths[change]
    p.write_bytes(p.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="artifact"):
        module.audit(run / "summary.json")
    assert calls == ["ViennaRNA", "LinearFold"]


def test_already_frozen_source_reuses_run_and_does_not_start_another_test(frozen):
    module, run, calls, _ = frozen
    source = module.ROOT / "source/summary.json"
    identity = module.ROOT / "identity/summary.json"
    assert module.freeze(source, identity) == run
    assert calls == [] and not (run / "test_event.json").exists()
