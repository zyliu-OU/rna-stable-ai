import importlib.util
import json
from pathlib import Path

import pytest

from rnastable.prospective_binding import (
    bind_record,
    clan_from_description,
    parse_stockholm,
    pdb_accessions,
    wuss_pairs,
    build_binding,
)
from rnastable.reference import digest


def record(sequence="GGAAAACC"):
    return {
        "id": "RF00059:member",
        "family_id": "RF00059",
        "sequence": sequence,
        "sequence_sha256": digest(sequence.encode()),
    }


def alignment(sequence="GGAAAACC", consensus="<<____>>"):
    return {
        "sequences": {"member": sequence},
        "consensus": consensus,
        "annotations": {"SS": ["fixture"]},
    }


def test_nested_wuss_maps_every_contact_without_deletion():
    result = bind_record(record(), alignment())
    assert result["reference_status"] == "ok" and result["structure"] == "((....))"
    assert result["consensus_pairs"] == 2 and result["missing_paired_columns"] == 0
    assert result["reference_kind"] == "computational"


def test_gaps_in_unpaired_columns_keep_exact_sequence_coordinates():
    result = bind_record(record("GGAAACC"), alignment("GG.AAACC"))
    assert result["structure"] == "((...))" and result["reference_status"] == "ok"


def test_missing_paired_column_is_unsupported_not_dropped():
    result = bind_record(record("GAAAACC"), alignment("G.AAAACC"))
    assert result["reference_status"] == "unsupported_reference"
    assert result["missing_paired_columns"] == 1 and "structure" not in result


def test_pseudoknot_contacts_counted_but_never_projected():
    result = bind_record(record(), alignment(consensus="<A___>a_"))
    assert result["consensus_pairs"] == 2 and result["pseudoknot_present"]
    assert result["error"] == "pseudoknot_not_supported" and "structure" not in result


@pytest.mark.parametrize(
    "ss", ["((____).", "<[_>_]__", "A_______", "a_______", "?_______"]
)
def test_invalid_consensus_rejects(ss):
    with pytest.raises(ValueError):
        wuss_pairs(ss)


def test_sequence_mismatch_rejects_annotation_binding():
    with pytest.raises(ValueError, match="sequence differs"):
        bind_record(record(), alignment("CGAAAACC"))


def test_multiblock_stockholm_preserves_width_and_family():
    raw = b"# STOCKHOLM 1.0\n#=GF AC RF00059\nmember GGAA\n#=GC SS_cons <<__\n\nmember AACC\n#=GC SS_cons __>>\n//\n"
    parsed = parse_stockholm(raw, "RF00059")
    assert bind_record(record(), parsed)["structure"] == "((....))"
    with pytest.raises(ValueError, match="family differs"):
        parse_stockholm(raw, "RF00162")
    with pytest.raises(ValueError, match="width differs"):
        parse_stockholm(raw.replace(b"AACC", b"ACC"), "RF00059")


def test_pdb_family_binding_and_case_normalization():
    assert pdb_accessions(
        b'{"mapping":[{"rfam_acc":"RF00059","pdb_id":"1ABC"}]}', "RF00059"
    ) == ["1abc"]
    with pytest.raises(ValueError, match="family differs"):
        pdb_accessions(
            b'{"mapping":[{"rfam_acc":"RF00162","pdb_id":"1ABC"}]}', "RF00059"
        )
    with pytest.raises(ValueError, match="schema"):
        pdb_accessions(b"{}", "RF00059")


def test_null_clan_is_explicit_source_metadata_not_unknown():
    raw = b'{"rfam":{"acc":"RF00059","release":{"number":"15.1"},"clan":{"acc":null}}}'
    assert clan_from_description(raw, "RF00059", "15.1") is None
    with pytest.raises(ValueError, match="release differs"):
        clan_from_description(raw, "RF00059", "future")


def evaluation_module(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "prospective_eval", root / "scripts/evaluate_prospective_panel.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_unsupported_records_remain_in_every_method_denominator(monkeypatch):
    module = evaluation_module(monkeypatch)
    good = {**record(), "structure": "((....))", "reference_status": "ok"}
    bad = {
        **record(),
        "id": "RF00059:unsupported",
        "reference_status": "unsupported_reference",
    }
    predictions = [
        {
            "id": r["id"],
            "method": m,
            "sequence_sha256": r["sequence_sha256"],
            "status": r["reference_status"],
            **({"structure": "((....))"} if r is good else {}),
        }
        for r in (good, bad)
        for m in module.METHODS
    ]
    rows, totals, families = module.score([good, bad], predictions)
    assert len(rows) == 12 and all(
        a["planned_inputs"] == 2
        and a["measured_inputs"] == 1
        and a["mean_pair_f1"] == 1
        for a in totals
    )
    assert all(r["pair_f1"] is None for r in rows if r["reference_id"] == bad["id"])
    predictions[-1]["structure"] = "((....))"
    with pytest.raises(ValueError, match="Unsupported reference was scored"):
        module.score([good, bad], predictions)


def test_prediction_missing_or_wrong_sequence_rejected(monkeypatch):
    module = evaluation_module(monkeypatch)
    good = {**record(), "structure": "((....))", "reference_status": "ok"}
    predictions = [
        {
            "id": good["id"],
            "method": m,
            "sequence_sha256": good["sequence_sha256"],
            "status": "ok",
            "structure": good["structure"],
        }
        for m in module.METHODS
    ]
    with pytest.raises(ValueError, match="denominator"):
        module.score([good], predictions[:-1])
    predictions[0]["sequence_sha256"] = "changed"
    with pytest.raises(ValueError, match="sequence differs"):
        module.score([good], predictions)


def test_exposed_family_rejected_before_new_annotation_access(tmp_path):
    (tmp_path / "plan.json").write_text(json.dumps({"rfam_release": "15.1"}))
    acquisition = {"run_dir": str(tmp_path), "families_downloaded": ["RF00059"]}
    with pytest.raises(ValueError, match="families already exposed"):
        build_binding(
            tmp_path,
            acquisition,
            [{"family_id": "RF00059", "sequence": "AAAA", "source": "test_started"}],
        )


def test_native_accounting_preserves_unknown_and_rejects_unplanned_work(
    tmp_path, monkeypatch
):
    from rnastable.native_journal import NativeJournal, canonical

    module = evaluation_module(monkeypatch)
    manifest = {"run_dir": str(tmp_path)}
    journal = NativeJournal(tmp_path / "native_journal", digest(canonical(manifest)))
    good = {**record(), "reference_status": "ok"}
    journal.run(
        "record_00_ViennaRNA",
        good["sequence"],
        {},
        lambda: {
            "status": "ok",
            "structure": "((....))",
            "mfe_kcal_mol": -1.0,
            "wall_seconds": 0.25,
        },
    )
    with pytest.raises(KeyboardInterrupt):
        journal.run(
            "record_00_LinearFold",
            good["sequence"],
            {},
            lambda: (_ for _ in ()).throw(KeyboardInterrupt()),
        )
    result = module.native_accounting(tmp_path, manifest, [good])
    assert result == {
        "planned_requests": 2,
        "completed_requests": 1,
        "unknown_requests": 1,
        "known_wall_seconds": 0.25,
    }
    journal.run("unplanned", good["sequence"], {}, lambda: {"status": "error"})
    with pytest.raises(ValueError, match="request inventory"):
        module.native_accounting(tmp_path, manifest, [good])


def test_missing_journal_audit_does_not_create_files(tmp_path, monkeypatch):
    module = evaluation_module(monkeypatch)
    with pytest.raises(ValueError, match="journal missing"):
        module.native_accounting(tmp_path, {}, [])
    assert not list(tmp_path.iterdir())


def test_completed_prospective_evaluation_replays_frozen_models(monkeypatch):
    module = evaluation_module(monkeypatch)
    path = module.ROOT / "results/prospective_evaluation_summary.json"
    if not path.exists():
        pytest.skip("No completed prospective comparison")
    result = module.audit_evaluation(path)
    assert result["planned_predictions"] == 90 and result["unsupported_references"] == 6
    assert all(
        a["planned_inputs"] == 15 and a["measured_inputs"] == 9
        for a in result["aggregates"]
    )
