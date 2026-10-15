import argparse
import importlib.util
import json
from pathlib import Path

import pytest

from rnastable.native_journal import atomic_json
from rnastable.reference import digest


@pytest.fixture
def runner():
    path = (
        Path(__file__).resolve().parents[1] / "scripts/run_helix_prior_replication.py"
    )
    spec = importlib.util.spec_from_file_location("helix_replication_runner", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def retained_study(tmp_path, runner, monkeypatch):
    run = tmp_path / "study"
    snapshot = run / "snapshot"
    snapshot.mkdir(parents=True)
    source = snapshot / "frozen.py"
    source.write_text("original frozen source\n")
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "PLAN", [{"input_index": 0, "seed": 7}])
    atomic_json(
        run / "manifest.json",
        {
            "run_dir": str(run),
            "plan": runner.PLAN,
            "deadline_utc": "2020-01-01T00:00:00+00:00",
            "publish_name": "retained",
            "policy": "Frozen study",
            "frozen_sha256": {"frozen.py": digest(source.read_bytes())},
        },
    )
    monkeypatch.setattr(runner, "publish", lambda *args: None)
    return run, source


@pytest.mark.parametrize("value", ["invalid", "2026-10-11T20:00:00"])
def test_deadline_rejects_invalid_or_ambiguous_time(runner, value):
    with pytest.raises(argparse.ArgumentTypeError):
        runner.parse_deadline(value)


def test_deadline_normalizes_timezone(runner):
    assert (
        runner.parse_deadline("2026-10-11T20:00:00-07:00")
        == "2026-10-12T03:00:00+00:00"
    )
    assert runner.remaining("2020-01-01T00:00:00+00:00") < 0


def test_resume_keeps_expired_manifest_deadline_without_extension(
    runner, tmp_path, monkeypatch
):
    run, _ = retained_study(tmp_path, runner, monkeypatch)
    monkeypatch.setattr(runner.sys, "argv", ["runner", "--resume", str(run)])
    monkeypatch.setattr(
        runner,
        "run_bounded",
        lambda *a, **kw: pytest.fail("Expired study launched native work"),
    )
    assert runner.main()["complete"] is False
    receipt = json.loads(next((run / "execution_attempts").glob("*.json")).read_text())
    assert receipt["execution_deadline_utc"] == receipt["original_deadline_utc"]


def test_resume_extension_is_recorded_without_changing_frozen_manifest(
    runner, tmp_path, monkeypatch
):
    run, source = retained_study(tmp_path, runner, monkeypatch)
    before = (run / "manifest.json").read_bytes()
    monkeypatch.setattr(
        runner.sys,
        "argv",
        ["runner", "--resume", str(run), "--deadline-utc", "2099-01-01T00:00:00Z"],
    )
    calls = []

    def stopped_child(command, stdin, **kwargs):
        calls.append((command, kwargs))
        return {
            "status": "error",
            "stdout": "stopped child",
            "error": "test interruption",
        }

    monkeypatch.setattr(runner, "run_bounded", stopped_child)
    summary = runner.main()
    assert not summary["complete"] and len(calls) == 1
    assert calls[0][0][1] == str(run / "snapshot/scripts/run_checkpoint_prior_pilot.py")
    assert calls[0][1]["timeout"] == 3600
    assert (run / "manifest.json").read_bytes() == before
    assert source.read_text() == "original frozen source\n"
    receipt = json.loads(next((run / "execution_attempts").glob("*.json")).read_text())
    assert receipt["manifest_sha256"] == digest(before)
    assert receipt["execution_deadline_utc"] == "2099-01-01T00:00:00+00:00"
    assert receipt["original_deadline_utc"] == "2020-01-01T00:00:00+00:00"
    assert receipt["resume"] is True


def test_resume_rejects_changed_frozen_code_before_launch(
    runner, tmp_path, monkeypatch
):
    run, source = retained_study(tmp_path, runner, monkeypatch)
    source.write_text("tampered\n")
    monkeypatch.setattr(
        runner.sys,
        "argv",
        ["runner", "--resume", str(run), "--deadline-utc", "2099-01-01T00:00:00Z"],
    )
    monkeypatch.setattr(
        runner, "run_bounded", lambda *a, **kw: pytest.fail("Changed source launched")
    )
    with pytest.raises(ValueError, match="Frozen source changed"):
        runner.main()
    assert not (run / "execution_attempts").exists()


def test_verify_rejects_execution_deadline(runner, monkeypatch):
    monkeypatch.setattr(
        runner.sys,
        "argv",
        ["runner", "--verify", "--deadline-utc", "2099-01-01T00:00:00Z"],
    )
    with pytest.raises(SystemExit) as error:
        runner.main()
    assert error.value.code == 2
