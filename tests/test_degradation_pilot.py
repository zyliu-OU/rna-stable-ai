"""Frozen empirical-proxy accounting and journal replay on constructed inputs."""

import importlib.util
import sys
from pathlib import Path

import pytest

from rnastable.native_journal import NativeJournal, atomic_json, canonical
from rnastable.reference import digest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "degradation_pilot", PROJECT / "scripts/evaluate_degradation_pilot.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def records(count=3):
    return [
        {
            "id": f"r{i}",
            "sequence": "GGAAAACC",
            "sequence_sha256": digest(b"GGAAAACC"),
            "seq_length": 8,
            "seq_scored": 2,
            "SN_filter": 1,
            "prediction_allowed": True,
            "assays": {
                target: {
                    "status": "ok",
                    "mean": float(i + 1),
                    "values": [i + 1, i + 1],
                    "errors": [0.1, 0.1],
                }
                for target in module.PLAN["targets"]
            },
        }
        for i in range(count)
    ]


def predictions(rs):
    structures = ["((....))", "(......)", "........"]
    return [
        {
            "id": r["id"],
            "method": m,
            "sequence_sha256": r["sequence_sha256"],
            "status": "ok",
            "structure": "." * 8 if m == "all_unpaired" else structures[i],
            **({"mfe_kcal_mol": float(i - 3)} if m in module.NATIVE else {}),
        }
        for i, r in enumerate(rs)
        for m in module.METHODS
    ]


def find(
    aggregates, method="helix", proxy="unpaired_fraction_of_scored_prefix", group="all"
):
    return next(
        r
        for r in aggregates
        if r["method"] == method
        and r["proxy_name"] == proxy
        and r["target"] == "reactivity"
        and r["quality_slice"] == group
    )


def test_exact_prefix_proxy_ranks_and_all_empty_constant_slices():
    rs = records()
    rows, aggregates = module.score(rs, predictions(rs))
    assert len(rows) == 135 and len(aggregates) == 180
    assert find(aggregates)["spearman_rho"] == 1.0
    assert find(aggregates, "ViennaRNA", "native_mfe_per_nt")["spearman_rho"] == 1.0
    assert find(aggregates, "all_unpaired")["null_reason"] == "constant_proxy"
    empty = find(aggregates, group="SN_filter_0")
    assert empty["planned_records"] == 0 and empty["spearman_rho"] is None
    assert (
        find(aggregates, "sequence_only", "gc_fraction_of_scored_prefix")["null_reason"]
        == "constant_proxy"
    )


def test_missing_prediction_and_assay_keep_counts_and_null_coefficients():
    rs = records()
    ps = predictions(rs)
    ps[2] = {k: v for k, v in ps[2].items() if k != "structure"}
    ps[2].update(status="error", error="constructed prediction failure")
    rs[1]["assays"]["reactivity"].update(status="unsupported", mean=None)
    rows, aggregates = module.score(rs, ps)
    assert len(rows) == 135
    a = find(aggregates)
    assert a["planned_records"] == 3 and a["complete_records"] == 1
    assert a["missing_prediction_records"] == a["unsupported_assay_records"] == 1
    assert a["missing_paired_records"] == 2 and a["spearman_rho"] is None


@pytest.mark.parametrize(
    "tamper",
    [
        "missing",
        "duplicate",
        "wrong_sequence",
        "logits_as_energy",
        "stale_failure",
        "skip_eligible",
    ],
)
def test_prediction_inventory_and_semantics_reject_invalid_outcomes(tamper):
    rs, ps = records(), predictions(records())
    if tamper == "missing":
        ps.pop()
    elif tamper == "duplicate":
        ps[-1] = ps[0]
    elif tamper == "wrong_sequence":
        ps[0]["sequence_sha256"] = "changed"
    elif tamper == "logits_as_energy":
        ps[0]["mfe_kcal_mol"] = 2.0
    elif tamper == "stale_failure":
        ps[0].update(status="error", error="failure")
    else:
        ps[0].pop("structure")
        ps[0].update(status="prior_overlap", error="incorrect skip")
    with pytest.raises(ValueError):
        module.score(rs, ps)


def test_constant_measurements_and_unknown_quality_retained():
    rs = records()
    for r in rs:
        r["SN_filter"] = None
        r["assays"]["reactivity"]["mean"] = 1.0
    _, aggregates = module.score(rs, predictions(rs))
    assert find(aggregates, group="SN_filter_unknown")["complete_records"] == 3
    assert find(aggregates)["null_reason"] == "constant_measurement"


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "ROOT", tmp_path)
    run = tmp_path / "pilot"
    run.mkdir()
    rs = records(2)
    manifest = {
        "run_dir": str(run),
        "analysis_plan": module.PLAN,
        "folding": module.FOLDING,
    }
    atomic_json(run / "manifest.json", manifest)
    binding = {"records": rs}
    monkeypatch.setattr(module, "context", lambda directory: (manifest, binding, {}))
    monkeypatch.setattr(
        module,
        "load_models",
        lambda protocol: {m: (None, {}) for m in ("baseline", "stack", "helix")},
    )
    monkeypatch.setattr(
        module, "decode_loaded", lambda *args: {"structure": "((....))"}
    )
    calls = []

    def fold(root, sequence, config, method, raw):
        assert (run / "test_event.json").exists()
        calls.append(method)
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_text("constructed raw fold")
        return {
            "status": "ok",
            "structure": "((....))",
            "mfe_kcal_mol": -1.0,
            "wall_seconds": 0.1,
        }

    monkeypatch.setattr(module, "fold_sequence", fold)
    return run, rs, manifest, calls


def test_event_before_native_work_and_replay_performs_no_folds_or_new_events(
    pipeline, monkeypatch
):
    run, rs, manifest, calls = pipeline
    result = module.evaluate(run)
    assert result["planned_predictions"] == result["successful_predictions"] == 12
    assert result["planned_assay_proxy_outcomes"] == 90
    assert result["native_accounting"]["completed_requests"] == len(calls) == 4
    events = list((run / "exposures").glob("*.json"))
    monkeypatch.setattr(
        module, "fold_sequence", lambda *a: pytest.fail("Audit performed native fold")
    )
    assert module.audit(run / "summary.json") == result
    assert module.evaluate(run) == result
    assert list((run / "exposures").glob("*.json")) == events
    (run / "predictions.json").write_text("[]\n")
    with pytest.raises(ValueError, match="artifact changed"):
        module.audit(run / "summary.json")


def test_interrupted_native_request_is_never_retried(pipeline):
    run, rs, manifest, calls = pipeline
    module.exposure(run, rs, True)
    journal = NativeJournal(run / "native_journal", digest(canonical(manifest)))
    journal.check_directory_binding(create=True)
    key, params = module.parameters(run, 0, "ViennaRNA")
    journal.write(
        key,
        {
            "state": "started",
            "key": key,
            "binding_sha256": journal.binding,
            "sequence_sha256": rs[0]["sequence_sha256"],
            "parameters": params,
        },
    )
    result = module.evaluate(run)
    assert result["native_accounting"]["unknown_requests"] == 1
    assert result["native_accounting"]["completed_requests"] == len(calls) == 3
    assert result["successful_predictions"] == 11
    assert module.audit(run / "summary.json") == result
    assert len(calls) == 3


def test_orphan_prediction_rejected_before_test_event(pipeline):
    run, rs, manifest, calls = pipeline
    atomic_json(run / "predictions.json", [])
    with pytest.raises(ValueError, match="before test exposure"):
        module.evaluate(run)
    assert not calls and not (run / "test_event.json").exists()


def test_native_raw_tampering_rejected_without_callbacks(pipeline):
    run, rs, manifest, calls = pipeline
    module.evaluate(run)
    next((run / "raw").glob("*.txt")).write_text("changed native bytes")
    with pytest.raises(ValueError, match="raw output changed"):
        module.audit(run / "summary.json")
    assert len(calls) == 4


@pytest.fixture
def guarded_context(tmp_path, monkeypatch):
    run = tmp_path / "guarded"
    run.mkdir()
    bound = tmp_path / "bound"
    bound.mkdir()
    source = tmp_path / "source"
    source.mkdir()
    protocol = {"run_dir": str(tmp_path / "source_protocol"), "models": {}}
    binding = {"run_dir": str(bound), "records": records()}
    atomic_json(bound / "source.json", {"run_dir": str(source)})
    atomic_json(source / "protocol.json", protocol)
    atomic_json(run / "protocol.json", protocol)
    atomic_json(run / "binding.json", binding)
    code = tmp_path / "dependency.py"
    code.write_text("frozen dependency")
    manifest = {
        "run_dir": str(run),
        "analysis_plan": module.PLAN,
        "folding": module.FOLDING,
        "environment": {"version": 1},
        "limitations": module.LIMITATIONS,
        "native_runtime": {"version": 1},
        "code_sha256": {str(code): digest(code.read_bytes())},
        "snapshot_sha256": {
            name: digest((run / name).read_bytes())
            for name in ("binding.json", "protocol.json")
        },
    }
    atomic_json(run / "manifest.json", manifest)
    monkeypatch.setattr(module, "environment", lambda: {"version": 1})
    monkeypatch.setattr(module, "native_runtime", lambda *a: {"version": 1})
    monkeypatch.setattr(module, "audit_binding", lambda *a: binding)
    monkeypatch.setattr(module, "audit_protocol", lambda *a: protocol)
    return run, code, source, manifest


@pytest.mark.parametrize(
    "change",
    ["code", "snapshot", "environment", "native_runtime", "association", "plan"],
)
def test_source_code_runtime_and_model_association_gates(
    guarded_context, monkeypatch, change
):
    run, code, source, manifest = guarded_context
    assert module.context(run)[0] == manifest
    if change == "code":
        code.write_text("changed")
    elif change == "snapshot":
        (run / "binding.json").write_text("{}\n")
    elif change == "environment":
        monkeypatch.setattr(module, "environment", lambda: {"version": 2})
    elif change == "native_runtime":
        monkeypatch.setattr(module, "native_runtime", lambda *a: {"version": 2})
    elif change == "association":
        atomic_json(source / "protocol.json", {"run_dir": "another model protocol"})
    else:
        manifest["analysis_plan"] = {**module.PLAN, "minimum_complete_records": 2}
        atomic_json(run / "manifest.json", manifest)
    with pytest.raises(ValueError):
        module.context(run)
    assert not (run / "test_event.json").exists()


def test_partial_run_resumes_without_repeating_interrupted_request(
    pipeline, monkeypatch
):
    run, rs, manifest, calls = pipeline
    original = module.fold_sequence
    interrupted_calls = []

    def interrupted(*args):
        interrupted_calls.append(True)
        raise KeyboardInterrupt("constructed native interruption")

    monkeypatch.setattr(module, "fold_sequence", interrupted)
    with pytest.raises(KeyboardInterrupt):
        module.evaluate(run)
    assert len(interrupted_calls) == 1
    event_bytes = (run / "test_event.json").read_bytes()
    monkeypatch.setattr(module, "fold_sequence", original)
    result = module.evaluate(run)
    assert result["native_accounting"]["unknown_requests"] == 1
    assert len(calls) == result["native_accounting"]["completed_requests"] == 3
    assert (run / "test_event.json").read_bytes() == event_bytes
    assert module.audit(run / "summary.json") == result
