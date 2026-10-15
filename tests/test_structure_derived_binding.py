"""Keep per-sequence PDB identities, crossing contacts, and missing data intact."""

import importlib.util
import json
from pathlib import Path

import pytest

from rnastable.native_journal import atomic_json
from rnastable.reference import digest


@pytest.fixture
def module(monkeypatch):
    project = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(project / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "derived_binding_test", project / "scripts/prepare_structure_derived_binding.py"
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def alignment(
    family="RF09999",
    structure="(..{..).}",
    sequence="GCACGUAGC",
    identity="seq",
    pdb="9ABC_A",
):
    return f"# STOCKHOLM 1.0\n#=GF ID constructed\n#=GF AC {family}\n{identity} {sequence}\n#=GR {identity} {pdb}_SS {structure}\n#=GC SS_cons .........\n//\n".encode()


def test_sequence_specific_crossing_brackets_override_no_consensus(module):
    source = module.parse_alignment(alignment(), "RF09999")
    record = source["candidates"][0]
    assert module.map_contacts(record) == [[0, 6], [3, 8]]
    bound = module.bind_selected([record], ["RF09999"])
    assert bound["records"][0]["reference_has_crossing_pairs"]
    assert bound["records"][0]["pairs"] == [[0, 6], [3, 8]]
    assert not bound["records"][0]["raw_interaction_completeness_verified"]
    assert bound["records"][0]["reference_kind"] == "computational"


def test_gap_coordinates_are_mapped_without_losing_contacts(module):
    record = module.parse_alignment(
        alignment(structure="(..{..).}", sequence="GC.CGUAGC"), "RF09999"
    )["candidates"][0]
    assert record["sequence"] == "GCCGUAGC"
    assert module.map_contacts(record) == [[0, 5], [2, 7]]


@pytest.mark.parametrize(
    "structure,sequence",
    [
        ("(..{..).}", ".CACGUAGC"),
        ("(..{..)..", "GCACGUAGC"),
        ("(..?..).}", "GCACGUAGC"),
    ],
)
def test_missing_columns_unbalanced_and_unknown_annotations_stay_unsupported(
    module, structure, sequence
):
    record = module.parse_alignment(
        alignment(structure=structure, sequence=sequence), "RF09999"
    )["candidates"][0]
    binding = module.bind_selected([record], ["RF09999"])
    assert binding["planned_records"] == 1 and binding["supported_references"] == 0
    assert "pairs" not in binding["records"][0]
    assert binding["records"][0]["reference_status"] == "unsupported_reference"


def test_consensus_only_records_do_not_become_pdb_references(module):
    raw = b"# STOCKHOLM 1.0\n#=GF ID example\nx GCAU\n#=GC SS_cons <..>\n//\n"
    result = module.parse_alignment(raw, "RF09999")
    assert result["alignment_sequences"] == 1 and result["candidates"] == []


def test_per_sequence_tag_requires_exact_identity_and_width(module):
    for raw in (
        alignment().replace(b"#=GR seq", b"#=GR other"),
        alignment().replace(b"9ABC_A_SS", b"unbound_SS"),
        alignment().replace(b"(..{..).}", b"(..)"),
    ):
        with pytest.raises(ValueError):
            module.parse_alignment(raw, "RF09999")


@pytest.fixture
def plan():
    return {"minimum_length": 1, "maximum_length": 512, "max_records_per_family": 5}


def test_repeated_pdb_chain_copies_do_not_inflate_independent_sequence_count(
    module, plan
):
    a = module.parse_alignment(alignment(pdb="9ABC_A"), "RF09999")
    b = module.parse_alignment(alignment(pdb="9ABC_B"), "RF09999")["candidates"][0]
    a["candidates"].append(b)
    selected, decisions, _ = module.select_panel(
        [a], {("RF09999", "9abc", "A"), ("RF09999", "9abc", "B")}, [], plan
    )
    assert len(selected) == 1
    assert decisions[1]["reason"] == "panel_sequence_redundancy"


def test_family_inferred_from_prior_pdb_mapping_is_conservatively_excluded(
    module, plan
):
    a = module.parse_alignment(alignment(), "RF09999")
    mappings = {("RF09999", "9abc", "A"), ("RF09999", "1xyz", "B")}
    selected, decisions, inferred = module.select_panel(
        [a], mappings, [{"pdb_accession": "1XYZ", "sequence": "AAAA"}], plan
    )
    assert selected == [] and inferred == ["RF09999"]
    assert decisions[0]["reason"] == "known_family_or_pdb_exposure"


def test_selected_bad_annotation_is_not_replaced_by_later_good_reference(module, plan):
    plan["max_records_per_family"] = 1
    a = module.parse_alignment(alignment(structure="........."), "RF09999")
    a["candidates"][0]["annotation"] = "unbalanced"
    b = module.parse_alignment(
        alignment(sequence="UUUUUUUUU", pdb="9BCD_A"), "RF09999"
    )["candidates"][0]
    a["candidates"].append(b)
    selected, decisions, _ = module.select_panel(
        [a], {("RF09999", "9abc", "A"), ("RF09999", "9bcd", "A")}, [], plan
    )
    result = module.bind_selected(selected, ["RF09999"])
    assert result["planned_records"] == 1 and result["supported_references"] == 0
    assert decisions[1]["reason"] == "fixed_family_cap"


@pytest.fixture
def workspace(module, tmp_path, monkeypatch):
    monkeypatch.setattr(module, "ROOT", tmp_path)
    source = tmp_path / "source_run"
    directory = source / "source/data/output"
    directory.mkdir(parents=True)
    (directory / "RF09999.sto").write_bytes(alignment())
    (source / "source/pdb_full_region.txt").write_text(
        "RF09999 9abc A 1 9 30.0 1e-6 1 9 fixture 1\n"
    )
    (source / "source/pdb_full_region_curated.txt").write_text("")
    protocol = tmp_path / "protocol"
    protocol.mkdir()
    atomic_json(
        protocol / "config.json",
        {
            "families": ["RF09999"],
            "future_binding": {
                "minimum_length": 1,
                "maximum_length": 512,
                "max_records_per_family": 5,
            },
        },
    )
    project = Path(__file__).resolve().parents[1]
    (protocol / "readiness_policy.json").write_bytes(
        (project / "configs/reference_readiness.json").read_bytes()
    )
    atomic_json(source / "manifest.json", {"protocol_run": str(protocol)})
    summary = {
        "run_dir": str(source),
        "sources_complete": True,
        "manifest_sha256": digest((source / "manifest.json").read_bytes()),
    }
    atomic_json(source / "summary.json", summary)
    monkeypatch.setattr(
        module, "audit_source", lambda p: json.loads(Path(p).read_text())
    )
    monkeypatch.setattr(module, "collect_known_exposures", lambda root: [])
    return module, source / "summary.json"


def test_annotation_contacts_are_parsed_after_durable_source_exposure(
    workspace, monkeypatch
):
    module, source = workspace
    original = module.map_contacts

    def guarded(record):
        events = list((module.ROOT / "results").rglob("exposures/*.json"))
        assert len(events) == 1
        data = module.read_exposure(events[0])
        assert any(r["sequence"] == record["sequence"] for r in data["records"])
        return original(record)

    monkeypatch.setattr(module, "map_contacts", guarded)
    result = module.build(source)
    assert result["binding"]["supported_references"] == 1
    assert not result["readiness"]["fresh_comparative_panel_ready"]
    assert not result["test_inference_allowed"]


def test_replay_does_not_create_new_exposure_or_read_live_state(workspace, monkeypatch):
    module, source = workspace
    result = module.build(source)
    monkeypatch.setattr(
        module,
        "collect_known_exposures",
        lambda *a: pytest.fail("No live exposure reads"),
    )
    monkeypatch.setattr(
        module, "record_exposure", lambda *a: pytest.fail("No new exposure")
    )
    assert module.audit(Path(result["run_dir"]) / "summary.json") == result


@pytest.mark.parametrize("file", ["selection.json", "exposure_before.json"])
def test_replay_rejects_changed_selection_and_prior_inventory(workspace, file):
    module, source = workspace
    result = module.build(source)
    p = Path(result["run_dir"]) / file
    p.write_bytes(p.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="snapshot changed"):
        module.audit(Path(result["run_dir"]) / "summary.json")
