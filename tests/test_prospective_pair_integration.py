import importlib.util
import json
from pathlib import Path

import pytest

from rnastable.native_journal import atomic_json
from rnastable.prospective_binding import build_binding
from rnastable.reference import digest


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    project = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(project / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "prospective_pair_integration",
        project / "scripts/evaluate_prospective_panel.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    protocol_dir = tmp_path / "protocol"
    protocol_dir.mkdir()
    protocol = {"run_dir": str(protocol_dir), "models": {}}
    atomic_json(protocol_dir / "config.json", {"reference_format": module.PAIR_FORMAT})
    monkeypatch.setattr(module, "audit_protocol", lambda path: protocol)
    source = tmp_path / "source"
    source.mkdir()
    atomic_json(source / "protocol.json", protocol)
    atomic_json(
        source / "RF09991_description.json",
        {
            "rfam": {
                "acc": "RF09991",
                "release": {"number": "fixture"},
                "clan": {"acc": None},
            }
        },
    )
    records = [
        {
            "id": "RF09991:complete",
            "family_id": "RF09991",
            "sequence": "GGAAACAC",
            "sequence_sha256": digest(b"GGAAACAC"),
        },
        {
            "id": "RF09991:incomplete",
            "family_id": "RF09991",
            "sequence": "GAAACAC",
            "sequence_sha256": digest(b"GAAACAC"),
        },
    ]
    acquisition = {
        "run_dir": str(source),
        "families_downloaded": ["RF09991"],
        "metadata_panel": {"records": records},
    }
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    atomic_json(evidence / "acquisition.json", acquisition)
    atomic_json(evidence / "plan.json", {"rfam_release": "fixture"})
    atomic_json(evidence / "RF09991_pdb_mapping.json", {"mapping": []})
    (evidence / "RF09991.sto").write_text(
        "# STOCKHOLM 1.0\n#=GF AC RF09991\n#=GF SS constructed fixture\ncomplete GGAAACAC\nincomplete .GAAACAC\n#=GC SS_cons <.A..>.a\n//\n"
    )
    atomic_json(
        evidence / "manifest.json",
        {
            "snapshot_sha256": {
                p.name: digest(p.read_bytes()) for p in evidence.iterdir()
            }
        },
    )
    monkeypatch.setattr(
        module,
        "audit_evidence",
        lambda path: {"sources_complete": True, "run_dir": str(evidence)},
    )
    monkeypatch.setattr(module, "native_runtime", lambda *a: {"fixture": True})
    return module, tmp_path, evidence, source, acquisition, protocol_dir


def test_pair_format_accepts_crossing_contacts_and_retains_incomplete_records(
    workspace,
):
    module, _, evidence, _, acquisition, _ = workspace
    legacy = build_binding(evidence, acquisition, [])
    pair = build_binding(evidence, acquisition, [], module.PAIR_FORMAT)
    assert "reference_format" not in legacy and legacy["supported_references"] == 0
    assert (
        pair["reference_format"] == module.PAIR_FORMAT
        and pair["supported_references"] == 1
    )
    assert pair["records"][0]["pairs"] == [[0, 5], [2, 7]]
    assert "structure" not in pair["records"][0]
    assert pair["records"][1]["reference_status"] == "unsupported_reference"
    assert pair["records"][1]["error"] == "missing_annotated_paired_column"
    assert pair["planned_records"] == 2


def test_reference_format_must_be_declared_before_acquisition(workspace):
    module, root, _, _, _, protocol_dir = workspace
    atomic_json(protocol_dir / "config.json", {})
    with pytest.raises(ValueError, match="not frozen"):
        module.prepare(module.PAIR_FORMAT)
    assert not (root / "results").exists()


def test_declared_pair_protocol_cannot_fall_back_to_legacy(workspace):
    module, root, _, _, _, _ = workspace
    with pytest.raises(ValueError, match="not frozen"):
        module.prepare(module.LEGACY_FORMAT)
    assert not (root / "results").exists()


def test_complete_fixture_pipeline_scores_crossing_contacts_and_consumes_family(
    workspace, monkeypatch
):
    module, root, _, _, _, _ = workspace
    binding = module.prepare(module.PAIR_FORMAT)
    assert module.audit_binding(Path(binding["run_dir"]) / "summary.json") == binding
    calls = []

    def event_run():
        events = list(
            (root / "results/prospective_pair_evaluation_runs").glob(
                "*/test_event.json"
            )
        )
        assert len(events) == 1
        return events[0].parent

    def loaded(protocol):
        event_run()
        return {name: (None, {}) for name in ("baseline", "stack", "helix")}

    def decode(*args):
        event_run()
        return {"structure": "(....).."}

    def native(root, sequence, config, tool, path):
        event_run()
        calls.append(tool)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(sequence + "\n(....).. (-1.0)\n")
        return {
            "status": "ok",
            "structure": "(....)..",
            "mfe_kcal_mol": -1.0,
            "wall_seconds": 0.1,
        }

    monkeypatch.setattr(module, "models", loaded)
    monkeypatch.setattr(module, "decode_loaded", decode)
    monkeypatch.setattr(module, "fold_sequence", native)
    result = module.evaluate(reference_format=module.PAIR_FORMAT)
    assert result["planned_predictions"] == 12 and result["unsupported_references"] == 1
    assert result["crossing_reference_records"] == 1
    assert result["native_accounting"]["completed_requests"] == 2
    assert sorted(calls) == ["LinearFold", "ViennaRNA"]
    assert all(
        a["planned_inputs"] == 2 and a["measured_inputs"] == 1
        for a in result["aggregates"]
    )
    helix = next(a for a in result["aggregates"] if a["method"] == "helix")
    assert helix["mean_pair_f1"] == pytest.approx(2 / 3)
    assert not (root / "results/prospective_evaluation_summary.json").exists()
    path = Path(result["run_dir"]) / "summary.json"
    monkeypatch.setattr(
        module, "fold_sequence", lambda *a: pytest.fail("Audit invoked native folding")
    )
    assert module.audit_evaluation(path) == result
    assert len(calls) == 2
    with pytest.raises(ValueError, match="families already exposed"):
        module.evaluate(reference_format=module.PAIR_FORMAT)
    with pytest.raises(ValueError, match="Resume reference format"):
        module.evaluate(Path(result["run_dir"]), module.LEGACY_FORMAT)
    (Path(result["run_dir"]) / "predictions.json").write_text("[]")
    with pytest.raises(ValueError, match="artifact changed"):
        module.audit_evaluation(path)


def test_pair_scoring_rejects_contacts_on_unsupported_reference(workspace):
    module, _, evidence, _, acquisition, _ = workspace
    records = build_binding(evidence, acquisition, [], module.PAIR_FORMAT)["records"]
    pred = [
        {
            "id": r["id"],
            "sequence_sha256": r["sequence_sha256"],
            "method": m,
            "status": r["reference_status"],
            **({"structure": "(....).."} if r["reference_status"] == "ok" else {}),
        }
        for r in records
        for m in module.METHODS
    ]
    rows, _, _ = module.score(records, pred, module.PAIR_FORMAT)
    assert len(rows) == 12 and sum(r["pair_f1"] is None for r in rows) == 6
    pred[-1]["pairs"] = [[0, 5]]
    with pytest.raises(ValueError, match="Unsupported reference was scored"):
        module.score(records, pred, module.PAIR_FORMAT)


def test_protocol_validator_accepts_only_supported_formats(monkeypatch):
    project = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "prospective_config_format",
        project / "scripts/prepare_prospective_family_panel.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config = json.loads((project / "configs/prospective_family_panel.json").read_text())
    config["reference_format"] = "pair_set_zero_based_v1"
    module.validate_config(config)
    config["reference_format"] = "ignore_crossing_pairs"
    with pytest.raises(ValueError, match="reference format"):
        module.validate_config(config)


def test_failed_predictions_keep_unknown_metrics_and_reject_stale_contacts(workspace):
    module, _, evidence, _, acquisition, _ = workspace
    records = build_binding(evidence, acquisition, [], module.PAIR_FORMAT)["records"]
    pred = [
        {
            "id": r["id"],
            "sequence_sha256": r["sequence_sha256"],
            "method": m,
            "status": "timeout"
            if r["reference_status"] == "ok"
            else r["reference_status"],
            "error": "fixture timeout",
        }
        for r in records
        for m in module.METHODS
    ]
    rows, agg, _ = module.score(records, pred, module.PAIR_FORMAT)
    assert all(r["pair_f1"] is None for r in rows)
    assert all(a["planned_inputs"] == 2 and a["measured_inputs"] == 0 for a in agg)
    pred[0]["pairs"] = [[0, 5]]
    with pytest.raises(ValueError, match="Failed prediction"):
        module.score(records, pred, module.PAIR_FORMAT)
