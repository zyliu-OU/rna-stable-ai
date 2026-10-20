"""Tests for assembly of the reference transcript from recorded components.

The real CDS bases have not been supplied, so these tests build a synthetic CDS
of the recorded length and write their own config fixture around it. The
production hash check therefore runs unmodified and has no test-only bypass.

The last group runs against the real committed config, to catch the recorded
UTRs or the recorded boundary decision drifting apart from each other.
"""
import hashlib
import json
from pathlib import Path

import pytest

from rnastable.component_integration import classify_construct_edit
from rnastable.transcript_assembly import STOP_CODONS, assemble, load_inputs, to_rna

REAL_CONFIG = Path(__file__).resolve().parents[1] / "configs" / "transcript_inputs_v1_2026-10-19.json"
UTR5 = "AAATAAGAGAGAAAAGAAGAGTAAGAAGAAATATAAGAGCCACC"
UTR3 = ("TAAGCTGGAGCCTCGGTGGCCATGCTTCTTGCCCCTTGGGCCTCCCCCCAGCCCCTCCTCCCC"
        "TTCCTGCACCCGTACCCCCGTGGTCTTTGAATAAAGTCTGAGTGGGCGGCA")


def synthetic_cds(codons=551):
    """ATG + sense codons + TAA, matching the recorded 551-codon geometry."""
    return "ATG" + "GCT" * (codons - 2) + "TAA"


def write_config(tmp_path, cds=None, utr5=UTR5, utr3=UTR3, cds_sha=None, lengths=None):
    cds = synthetic_cds() if cds is None else cds
    sha = cds_sha or hashlib.sha256(cds.encode()).hexdigest()
    lengths = lengths or {"utr5": len(utr5), "cds": len(cds), "utr3": len(utr3)}
    payload = {
        "components": {
            "utr5": {"sequence_dna_uppercase": utr5},
            "utr3": {"sequence_dna_uppercase": utr3},
            "cds": {"sha256_dna_uppercase": sha, "length_nt": len(cds)},
        },
        "region_boundary_decision": {
            "consequence": {
                "utr5_length_nt": lengths["utr5"],
                "cds_length_nt": lengths["cds"],
                "utr3_length_nt": lengths["utr3"],
                "transcript_length_nt": lengths["utr5"] + lengths["cds"] + lengths["utr3"],
            }
        },
    }
    path = tmp_path / "inputs.json"
    path.write_text(json.dumps(payload))
    return path, cds


def build(tmp_path, **kw):
    path, cds = write_config(tmp_path, **kw)
    return assemble(cds, path, "FLUC-REF", "synthetic test CDS", "assay_definition_v3")


# --- assembly ------------------------------------------------------------

def test_assembles_under_the_recorded_layout(tmp_path):
    transcript, report = build(tmp_path)
    assert report.utr5_length_nt == 44
    assert report.cds_length_nt == 1653
    assert report.utr3_length_nt == 114
    assert report.transcript_length_nt == 1811
    assert (report.cds_start, report.cds_end) == (44, 1697)


def test_regions_land_exactly_where_the_boundary_decision_says(tmp_path):
    transcript, _ = build(tmp_path)
    assert transcript.sequence[:44] == to_rna(UTR5)
    assert transcript.sequence[1697:] == to_rna(UTR3)
    assert transcript.cds == to_rna(synthetic_cds())


def test_protein_length_is_the_recorded_550_residues(tmp_path):
    _, report = build(tmp_path)
    assert report.protein_length_aa == 550


def test_assembled_transcript_is_rna_not_dna(tmp_path):
    transcript, report = build(tmp_path)
    assert "T" not in transcript.sequence
    assert set(transcript.sequence) <= set("ACGU")
    assert "T converted to U" in report.alphabet_conversion


def test_tandem_stop_is_detected_and_named(tmp_path):
    """The recorded decision assigns a second stop to the 3' UTR; report it."""
    _, report = build(tmp_path)
    assert report.tandem_stop_present is True
    assert report.tandem_stop_codon == "UAA"
    assert report.tandem_stop_codon in STOP_CODONS


def test_tandem_stop_reported_absent_when_the_utr3_does_not_start_with_one(tmp_path):
    """Presence is measured, not assumed from the recorded decision."""
    _, report = build(tmp_path, utr3="GCT" + UTR3[3:])
    assert report.tandem_stop_present is False
    assert report.tandem_stop_codon is None


def test_no_ribonn_exclusion_for_this_construct(tmp_path):
    _, report = build(tmp_path)
    assert report.ribonn_exclusion is None


def test_report_is_serialisable_and_carries_its_no_claim(tmp_path):
    _, report = build(tmp_path)
    payload = report.to_dict()
    assert json.loads(json.dumps(payload))["transcript_length_nt"] == 1811
    assert "no stability, translation or expression claim" in payload["no_claim"]


def test_report_is_frozen(tmp_path):
    _, report = build(tmp_path)
    with pytest.raises(Exception):
        report.transcript_length_nt = 1


def test_assembly_is_deterministic(tmp_path):
    a = build(tmp_path)[1]
    b = build(tmp_path)[1]
    assert a.transcript_sha256_rna == b.transcript_sha256_rna
    assert a.identity_sha256 == b.identity_sha256


# --- selecting which recorded construct to assemble ----------------------

def two_construct_config(tmp_path):
    """A config recording two constructs of different length, as the real one does."""
    path, fluc = write_config(tmp_path)
    pest = synthetic_cds(592)
    payload = json.loads(path.read_text())
    payload["components"]["cds_fluc_pest"] = {
        "sha256_dna_uppercase": hashlib.sha256(pest.encode()).hexdigest(),
        "length_nt": len(pest),
    }
    path.write_text(json.dumps(payload))
    return path, fluc, pest


def test_second_construct_assembles_against_its_own_hash(tmp_path):
    path, _, pest = two_construct_config(tmp_path)
    _, report = assemble(pest, path, "PEST", "p", "a", cds_component="cds_fluc_pest")
    assert report.cds_component == "cds_fluc_pest"
    assert report.cds_length_nt == len(pest) == 1776
    assert report.transcript_length_nt == 44 + 1776 + 114


def test_each_construct_is_bound_to_its_own_hash(tmp_path):
    """The central guarantee: one construct cannot pass as the other."""
    path, fluc, pest = two_construct_config(tmp_path)
    with pytest.raises(ValueError, match="does not match the recorded CDS 'cds_fluc_pest'"):
        assemble(fluc, path, "T", "p", "a", cds_component="cds_fluc_pest")
    with pytest.raises(ValueError, match="does not match the recorded CDS 'cds'"):
        assemble(pest, path, "T", "p", "a")


def test_the_two_constructs_differ_in_identity(tmp_path):
    path, fluc, pest = two_construct_config(tmp_path)
    _, a = assemble(fluc, path, "FLUC", "p", "a")
    _, b = assemble(pest, path, "PEST", "p", "a", cds_component="cds_fluc_pest")
    assert a.transcript_sha256_rna != b.transcript_sha256_rna
    assert a.cds_sha256_dna_uppercase != b.cds_sha256_dna_uppercase


def test_shared_utr_layout_still_applies_to_the_second_construct(tmp_path):
    """UTRs and the tandem stop are shared; only the CDS length differs."""
    path, _, pest = two_construct_config(tmp_path)
    _, report = assemble(pest, path, "PEST", "p", "a", cds_component="cds_fluc_pest")
    assert report.utr5_length_nt == 44
    assert report.utr3_length_nt == 114
    assert report.tandem_stop_present is True
    assert report.cds_start == 44


def test_unknown_cds_component_is_refused(tmp_path):
    path, cds = write_config(tmp_path)
    with pytest.raises(ValueError, match="records no CDS component"):
        assemble(cds, path, "T", "p", "a", cds_component="cds_nonexistent")


def test_real_config_records_both_constructs_with_distinct_lengths():
    components = load_inputs(REAL_CONFIG)["components"]
    assert components["cds"]["length_nt"] == 1653
    assert components["cds_fluc_pest"]["length_nt"] == 1776


# --- poly(A) ------------------------------------------------------------

def poly_a_config(tmp_path, length=103):
    path, cds = write_config(tmp_path)
    payload = json.loads(path.read_text())
    payload["construct_context_from_ping"] = {"poly_a": {"length_nt": length}}
    path.write_text(json.dumps(payload))
    return path, cds


def test_poly_a_is_excluded_by_default(tmp_path):
    """Recording a tail in the config must not silently put it in the model input."""
    path, cds = poly_a_config(tmp_path)
    _, report = assemble(cds, path, "T", "p", "a")
    assert report.poly_a_included is False
    assert report.poly_a_length_nt == 0
    assert report.transcript_length_nt == 1811


def test_poly_a_is_appended_only_when_asked(tmp_path):
    path, cds = poly_a_config(tmp_path)
    transcript, report = assemble(cds, path, "T", "p", "a", include_poly_a=True)
    assert report.poly_a_included is True
    assert report.poly_a_length_nt == 103
    assert report.transcript_length_nt == 1914
    assert transcript.sequence.endswith("A" * 103)


def test_poly_a_does_not_move_the_cds_boundaries(tmp_path):
    """The tail is 3' of everything, so region accounting must be unchanged."""
    path, cds = poly_a_config(tmp_path)
    _, core = assemble(cds, path, "T", "p", "a")
    _, tailed = assemble(cds, path, "T", "p", "a", include_poly_a=True)
    assert (core.cds_start, core.cds_end) == (tailed.cds_start, tailed.cds_end) == (44, 1697)
    assert core.utr3_length_nt == tailed.utr3_length_nt == 114


def test_poly_a_changes_the_transcript_hash(tmp_path):
    """Two different molecules must not share an identity hash."""
    path, cds = poly_a_config(tmp_path)
    _, core = assemble(cds, path, "T", "p", "a")
    _, tailed = assemble(cds, path, "T", "p", "a", include_poly_a=True)
    assert core.transcript_sha256_rna != tailed.transcript_sha256_rna
    assert core.identity_sha256 != tailed.identity_sha256


def test_requesting_poly_a_when_none_is_recorded_is_refused(tmp_path):
    path, cds = write_config(tmp_path)
    with pytest.raises(ValueError, match="No poly\\(A\\) is recorded"):
        assemble(cds, path, "T", "p", "a", include_poly_a=True)


# --- the hash gate -------------------------------------------------------

def test_cds_failing_the_recorded_hash_is_refused(tmp_path):
    """The central guarantee: a different sequence cannot pass as the same one."""
    wrong = "ATG" + "GCA" * 549 + "TAA"
    path, _ = write_config(tmp_path, cds=synthetic_cds())
    with pytest.raises(ValueError, match="does not match the recorded CDS"):
        assemble(wrong, path, "FLUC-REF", "wrong", "assay_definition_v3")


def test_refusal_names_both_hashes_and_both_lengths(tmp_path):
    path, _ = write_config(tmp_path)
    with pytest.raises(ValueError) as e:
        assemble("ATG" + "GCA" * 549 + "TAA", path, "T", "p", "a")
    message = str(e.value)
    assert "Expected sha256" in message and "observed" in message
    assert "1653 nt" in message


def test_hash_check_is_alphabet_insensitive(tmp_path):
    """The same sequence given as RNA still matches a DNA-form hash."""
    path, cds = write_config(tmp_path)
    transcript, report = assemble(cds.replace("T", "U"), path, "T", "p", "a")
    assert report.cds_sha256_dna_uppercase == hashlib.sha256(cds.encode()).hexdigest()


def test_lowercase_cds_is_accepted_and_folded(tmp_path):
    path, cds = write_config(tmp_path)
    _, report = assemble(cds.lower(), path, "T", "p", "a")
    assert report.cds_length_nt == len(cds)


def test_a_truncated_cds_is_refused_by_the_hash_not_by_luck(tmp_path):
    path, cds = write_config(tmp_path)
    with pytest.raises(ValueError, match="does not match"):
        assemble(cds[:-3], path, "T", "p", "a")


# --- contradiction between components and the recorded decision ----------

def test_utr_length_contradicting_the_boundary_decision_is_refused(tmp_path):
    path, cds = write_config(tmp_path, lengths={"utr5": 44, "cds": 1653, "utr3": 111})
    with pytest.raises(ValueError, match="contradicts the recorded region boundary"):
        assemble(cds, path, "T", "p", "a")


def test_the_refusal_points_at_the_decision_rather_than_offering_a_workaround(tmp_path):
    path, cds = write_config(tmp_path, lengths={"utr5": 44, "cds": 1653, "utr3": 111})
    with pytest.raises(ValueError) as e:
        assemble(cds, path, "T", "p", "a")
    assert "must be revisited" in str(e.value)


def test_cds_length_contradicting_its_own_component_record_is_refused(tmp_path):
    """Guards a config whose recorded CDS length disagrees with its own hashed sequence."""
    path, cds = write_config(tmp_path)
    payload = json.loads(path.read_text())
    payload["components"]["cds"]["length_nt"] = 1650
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="contradicts the recorded region boundary"):
        assemble(cds, path, "T", "p", "a")


# --- CDS validity, enforced by Transcript --------------------------------

def test_cds_without_a_terminal_stop_is_refused(tmp_path):
    bad = "ATG" + "GCT" * 550
    path, _ = write_config(tmp_path, cds=bad)
    with pytest.raises(Exception):
        assemble(bad, path, "T", "p", "a")


def test_cds_with_an_internal_stop_is_refused(tmp_path):
    bad = "ATG" + "GCT" * 200 + "TAA" + "GCT" * 348 + "TAA"
    path, _ = write_config(tmp_path, cds=bad)
    with pytest.raises(Exception):
        assemble(bad, path, "T", "p", "a")


def test_cds_not_a_multiple_of_three_is_refused(tmp_path):
    bad = "ATG" + "GCT" * 549 + "TA"
    path, _ = write_config(tmp_path, cds=bad)
    with pytest.raises(Exception):
        assemble(bad, path, "T", "p", "a")


def test_cds_without_a_start_codon_is_refused(tmp_path):
    bad = "GCT" * 550 + "TAA"
    path, _ = write_config(tmp_path, cds=bad)
    with pytest.raises(Exception):
        assemble(bad, path, "T", "p", "a")


# --- input validation ----------------------------------------------------

@pytest.mark.parametrize("bad", ["", None, 123, "   "])
def test_empty_or_nonstring_cds_refused(tmp_path, bad):
    path, _ = write_config(tmp_path)
    with pytest.raises(ValueError):
        assemble(bad, path, "T", "p", "a")


def test_non_nucleotide_characters_refused(tmp_path):
    path, _ = write_config(tmp_path)
    with pytest.raises(ValueError, match="canonical"):
        assemble("ATGXYZ", path, "T", "p", "a")


def test_mixed_t_and_u_refused_as_ambiguous():
    with pytest.raises(ValueError, match="ambiguous"):
        to_rna("ATGU")


def test_to_rna_rejects_non_nucleotide():
    with pytest.raises(ValueError):
        to_rna("ATGN")


def test_to_rna_is_idempotent():
    assert to_rna(to_rna("ATGC")) == to_rna("ATGC") == "AUGC"


def test_config_without_the_required_sections_is_refused(tmp_path):
    path = tmp_path / "x.json"
    path.write_text(json.dumps({"components": {}}))
    with pytest.raises(ValueError, match="not a transcript inputs record"):
        load_inputs(path)


# --- the real committed config -------------------------------------------

def test_real_config_components_match_its_own_boundary_decision():
    """Guards the committed config against internal drift."""
    data = load_inputs(REAL_CONFIG)
    c, recorded = data["components"], data["region_boundary_decision"]["consequence"]
    assert len(c["utr5"]["sequence_dna_uppercase"]) == recorded["utr5_length_nt"] == 44
    assert len(c["utr3"]["sequence_dna_uppercase"]) == recorded["utr3_length_nt"] == 114
    assert c["cds"]["length_nt"] == recorded["cds_length_nt"] == 1653
    total = recorded["utr5_length_nt"] + recorded["cds_length_nt"] + recorded["utr3_length_nt"]
    assert total == recorded["transcript_length_nt"] == 1811


def test_real_config_records_the_user_tandem_stop_decision():
    data = load_inputs(REAL_CONFIG)
    assert data["components"]["utr3"]["sequence_dna_uppercase"][:3] == "TAA"
    assert data["region_boundary_decision"]["decided_by"].startswith("user")


def test_real_cds_is_supplied_and_hashes_to_the_recorded_reference():
    """The CDS landed 2026-10-19 and recovered the hash recorded in assay_definition_v3."""
    cds = load_inputs(REAL_CONFIG)["components"]["cds"]
    assert cds["supplied"] is True
    bases = Path(REAL_CONFIG).parent.parent / cds["sequence_file"]
    observed = hashlib.sha256(bases.read_text().strip().upper().encode()).hexdigest()
    assert observed == cds["sha256_dna_uppercase"] == assay_cds()["sha256_dna_uppercase"]


def test_real_fluc_pest_is_a_distinct_construct():
    """Fluc and Fluc-PEST must never be interchangeable."""
    components = load_inputs(REAL_CONFIG)["components"]
    assert (components["cds_fluc_pest"]["sha256_dna_uppercase"]
            != components["cds"]["sha256_dna_uppercase"])
    assert components["cds_fluc_pest"]["length_nt"] > components["cds"]["length_nt"]


def test_real_transcript_assembles_from_the_committed_sequence_file():
    """End-to-end on the real committed inputs, not a fixture."""
    cds = load_inputs(REAL_CONFIG)["components"]["cds"]
    bases = (Path(REAL_CONFIG).parent.parent / cds["sequence_file"]).read_text()
    transcript, report = assemble(bases, REAL_CONFIG, "FLUC-REF-V1", "committed inputs", "assay_v3")
    assert report.transcript_length_nt == 1811
    assert report.protein_length_aa == 550
    assert report.tandem_stop_present is True
    assert report.ribonn_exclusion is None


def test_real_config_utr_hashes_are_self_consistent():
    c = load_inputs(REAL_CONFIG)["components"]
    for key in ("utr5", "utr3"):
        seq = c[key]["sequence_dna_uppercase"]
        assert hashlib.sha256(seq.encode()).hexdigest() == c[key]["sha256_dna_uppercase"]


# --- agreement with the frozen assay definition ---------------------------

ASSAY_V3 = Path(__file__).resolve().parents[1] / "configs" / "assay_definition_v3_2026-10-19.json"


def assay_cds():
    return json.loads(ASSAY_V3.read_text())["reference_construct"]["cds"]


def test_cds_hash_agrees_across_both_configs():
    """The two configs describe one CDS; a divergence would silently split provenance."""
    assert (load_inputs(REAL_CONFIG)["components"]["cds"]["sha256_dna_uppercase"]
            == assay_cds()["sha256_dna_uppercase"])


def test_cds_geometry_agrees_across_both_configs():
    recorded, assay = load_inputs(REAL_CONFIG)["components"]["cds"], assay_cds()
    assert recorded["length_nt"] == assay["length_nt"] == 1653
    assert recorded["codons"] == assay["codons"] == 551
    assert recorded["protein_length_aa"] == assay["protein_length_aa"] == 550


def test_codon_count_is_consistent_with_length_and_protein():
    """551 codons over 1653 nt encoding 550 residues implies an included stop."""
    cds = assay_cds()
    assert cds["length_nt"] == cds["codons"] * 3
    assert cds["protein_length_aa"] == cds["codons"] - 1


def test_assembled_utr5_stays_within_the_ribonn_upstream_limit():
    """The 1381 nt upstream-domain limit is an exclusion rule in the frozen assay."""
    assert load_inputs(REAL_CONFIG)["region_boundary_decision"]["consequence"]["utr5_length_nt"] <= 1381


# --- integration with the existing edit classifier ------------------------

def test_assembled_transcript_is_usable_by_classify_construct_edit(tmp_path):
    """Assembly produces an input the existing region accounting accepts."""
    transcript, _ = build(tmp_path)
    result = classify_construct_edit(transcript, transcript)
    assert result["valid_under_assay_v3"] is True


def test_a_utr5_substitution_on_an_assembled_transcript_stays_valid(tmp_path):
    """The tandem stop sits in utr3, so UTR edits remain UTR edits."""
    transcript, _ = build(tmp_path)
    edited = type(transcript)(
        tx_id=transcript.tx_id,
        sequence="G" + transcript.sequence[1:],
        cds_start=transcript.cds_start,
        cds_end=transcript.cds_end,
        provenance=transcript.provenance,
        assay_context=transcript.assay_context,
    )
    assert classify_construct_edit(transcript, edited)["valid_under_assay_v3"] is True
