from pathlib import Path
import pytest
from rnastable.exposures import record_exposure, collect_known_exposures


def test_nested_component_and_frozen_runner_exposures_remain_known(tmp_path):
    root = tmp_path / "workspace"
    record_exposure(
        root / "results/study_runs/run/components/seed_head",
        "training_started",
        [{"sequence": "GGAAAACC", "family_id": "family_A"}],
    )
    record_exposure(
        root / "results/native_runs/run/snapshot/results/pilot_runs/child",
        "test_started",
        [{"sequence": "GGGAAACCC"}],
    )
    record_exposure(
        root / "results/simple_runs/run",
        "validation_started",
        [{"sequence": "GAAAAC", "pdb_accession": "fixture"}],
    )
    record_exposure(
        root / "results/duplicate_runs/run",
        "training_started",
        [{"sequence": "GGAAAACC", "family_id": "family_A"}],
    )
    known = collect_known_exposures(root)
    assert {
        (row["sequence"], row.get("family_id"), row.get("pdb_accession"))
        for row in known
    } == {
        ("GGAAAACC", "family_A", None),
        ("GGGAAACCC", None, None),
        ("GAAAAC", None, "fixture"),
    }


def test_exposure_collection_does_not_follow_external_directory_symlinks(tmp_path):
    root = tmp_path / "workspace"
    external = tmp_path / "external"
    record_exposure(external / "study", "test_started", [{"sequence": "GGAAAACC"}])
    (root / "results/study_runs/run/snapshot").mkdir(parents=True)
    (root / "results/study_runs/run/snapshot/external").symlink_to(
        external, target_is_directory=True
    )
    assert collect_known_exposures(root) == []


def test_corrupt_nested_event_is_not_silently_skipped(tmp_path):
    root = tmp_path / "workspace"
    event = record_exposure(
        root / "results/study_runs/run/components/head",
        "validation_started",
        [{"sequence": "GGAAAACC"}],
    )
    Path(event["path"]).write_text("{}")
    with pytest.raises(ValueError, match="schema"):
        collect_known_exposures(root)
