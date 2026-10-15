import importlib.util
from pathlib import Path

import pytest

from rnastable.family_readiness import METADATA_FILES, metadata_records, screen_families
from rnastable.native_journal import atomic_json
from rnastable.reference import digest
from rnastable.rfam_data import select_cohort


def fasta(sequence="AAAA", family="RF00099", identity="RFA_00001"):
    return f">SSTRAND_ID={identity}; EXT_SOURCE=Rfam Database; EXT_ID={family} fixture; ORGANISM=fixture\n{sequence}\n".encode()


def contents(train=b"", holdout=b"", test=b""):
    return {"train": train, "holdout": holdout, "test": test}


def test_exposed_family_blocks_dissimilar_sequence_and_selector():
    records = metadata_records(contents(test=fasta("CCCC", "RF00099")))
    exposed = [{"sequence": "AAAA", "family_id": "RF00099", "source": "earlier test"}]
    result = screen_families(records, exposed, 1, 1024)
    assert result["metadata_candidates"] == 0
    assert result["rows"][0]["reason"] == "prior_family_exposure"
    config = {"families": {"train": [], "validation": [], "test": ["RF00099"]}}
    with pytest.raises(ValueError, match="family was previously exposed"):
        select_cohort([], config, exposed)


def test_unknown_family_provenance_still_checks_sequence_similarity():
    records = metadata_records(contents(test=fasta("AAAAC")))
    result = screen_families(
        records, [{"sequence": "AAAAA", "source": "training"}], 1, 1024
    )
    assert result["rows"][0]["reason"] == "prior_sequence_exposure"
    assert result["exposure_records_without_family_id"] == 1
    assert not result["family_independence_established"]


def test_unseen_family_is_only_metadata_candidate_without_labels():
    result = screen_families(
        metadata_records(contents(test=fasta("CCCC"))),
        [{"sequence": "AAAA", "source": "old"}],
        1,
        1024,
    )
    assert result["metadata_candidates"] == 1
    assert not result["new_structure_labels_read"] and not result["inference_performed"]
    assert (
        not result["test_evaluated"] and not result["family_independence_established"]
    )


def test_invalid_sequence_and_length_keep_denominators():
    records = metadata_records(contents(train=fasta("NNNN"), test=fasta("CCCC")))
    result = screen_families(records, [], 5, 1024)
    assert result["metadata_records"] == 2 and result["metadata_candidates"] == 0
    assert {r["reason"] for r in result["rows"]} == {
        "invalid_sequence",
        "outside_fixed_length_range",
    }


def test_fragment_identity_is_sequence_bound_and_exact_duplicates_rejected():
    rows = metadata_records(contents(train=fasta("AAAA") + fasta("CCCC")))
    assert len(rows) == 2 and rows[0]["id"] != rows[1]["id"]
    with pytest.raises(ValueError, match="Duplicate metadata"):
        metadata_records(contents(train=fasta() + fasta()))


@pytest.mark.parametrize(
    "bad", [contents(test=fasta(family="unverified")), contents(test=b"AAAA\n")]
)
def test_malformed_metadata_fails_closed(bad):
    with pytest.raises(ValueError):
        metadata_records(bad)


def test_snapshot_replay_detects_tampering_without_archive_access(
    tmp_path, monkeypatch
):
    path = Path(__file__).resolve().parents[1] / "scripts/audit_family_readiness.py"
    spec = importlib.util.spec_from_file_location("audit_family_readiness", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    for split, name in METADATA_FILES.items():
        target = tmp_path / "external/EternaFold/datasets_in_fasta_form" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(fasta("CCCC") if split == "test" else b"")
    # No BPSEQ archive exists. Any attempt to open one must fail the test.
    import zipfile

    monkeypatch.setattr(
        zipfile, "ZipFile", lambda *a, **kw: pytest.fail("Read structure archive")
    )
    monkeypatch.setattr(module.sys, "argv", ["audit_family_readiness"])
    summary = module.main()
    run = Path(summary["run_dir"])
    assert not list((tmp_path / "results").rglob("exposures/*.json"))
    assert module.audit(run / "summary.json") == summary
    (run / "test.fasta").write_bytes(fasta("AAAA"))
    with pytest.raises(ValueError, match="snapshot changed"):
        module.audit(run / "summary.json")


def test_replay_rejects_altered_result_even_when_retained_copies_match(
    tmp_path, monkeypatch
):
    path = Path(__file__).resolve().parents[1] / "scripts/audit_family_readiness.py"
    spec = importlib.util.spec_from_file_location("audit_family_readiness_result", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    raw = contents(test=fasta())
    for split, content in raw.items():
        (tmp_path / (split + ".fasta")).write_bytes(content)
    atomic_json(tmp_path / "exposure.json", [])
    manifest = {
        "run_dir": str(tmp_path),
        "minimum_length": 1,
        "maximum_length": 1024,
        "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in tmp_path.iterdir()},
    }
    atomic_json(tmp_path / "manifest.json", manifest)
    result = screen_families(metadata_records(raw), [], 1, 1024)
    result["metadata_candidates"] = 999
    summary = {
        "run_dir": str(tmp_path),
        "manifest_sha256": digest((tmp_path / "manifest.json").read_bytes()),
        "screening": result,
    }
    atomic_json(tmp_path / "summary.json", summary)
    with pytest.raises(ValueError, match="screening replay differs"):
        module.audit(tmp_path / "summary.json")
