"""Region-aware edit classification for the assay_definition_v3 design space."""

import pytest

from rnastable.component_integration import (
    Transcript, check_synonymous_edit, classify_construct_edit,
)


def transcript(rid="parent", cds="AUGGCUUAA", utr5="GGG", utr3="CCC"):
    return Transcript(rid, utr5+cds+utr3, len(utr5), len(utr5)+len(cds),
                      "unit-test synthetic", "no biological measurements")


def test_utr_substitution_is_valid_here_and_rejected_by_the_frozen_check():
    parent = transcript()
    candidate = transcript("utr5_sub", utr5="AAA")
    verdict = classify_construct_edit(parent, candidate)
    assert verdict["valid_under_assay_v3"]
    assert verdict["regions_changed"] == ["utr5"]
    assert verdict["protein_invariant"] and verdict["orf_unchanged"]
    assert not verdict["orf_synonymous"]
    # The gap this function exists to close: the frozen contract cannot say yes.
    assert not check_synonymous_edit(parent, candidate, max_edits=3)


def test_utr_length_change_is_permitted_and_reported():
    parent = transcript()
    candidate = transcript("utr3_longer", utr3="CCCUUU")
    verdict = classify_construct_edit(parent, candidate)
    assert verdict["valid_under_assay_v3"]
    assert verdict["transcript_length_delta_nt"] == 3
    assert verdict["regions"]["utr3"]["length_delta_nt"] == 3
    # Substitution counts are undefined across unequal lengths.
    assert verdict["regions"]["utr3"]["substitutions"] is None
    assert verdict["regions"]["utr5"]["substitutions"] == 0


def test_synonymous_orf_edit_is_valid_and_labelled_synonymous():
    verdict = classify_construct_edit(transcript(), transcript("syn", "AUGGCCUAA"))
    assert verdict["valid_under_assay_v3"]
    assert verdict["orf_synonymous"] and verdict["protein_invariant"]
    assert verdict["regions_changed"] == ["orf"]
    assert verdict["regions"]["orf"]["substitutions"] == 1
    assert verdict["parent_protein_sha256"] == verdict["candidate_protein_sha256"]


def test_missense_orf_edit_is_invalid_with_an_explicit_reason():
    verdict = classify_construct_edit(transcript(), transcript("missense", "AUGGACUAA"))
    assert not verdict["valid_under_assay_v3"]
    assert verdict["invalid_reasons"] == ["orf_edit_changes_encoded_protein"]
    assert not verdict["protein_invariant"]
    assert verdict["parent_protein_sha256"] != verdict["candidate_protein_sha256"]


def test_in_frame_orf_deletion_changing_protein_length_is_invalid():
    # Dropping one codon keeps the frame and the stop, so only protein identity
    # catches it; "in frame" must not be mistaken for "synonymous".
    verdict = classify_construct_edit(transcript(), transcript("shorter", "AUGUAA"))
    assert not verdict["valid_under_assay_v3"]
    assert set(verdict["invalid_reasons"]) == {
        "orf_edit_changes_encoded_protein", "orf_length_changed",
    }


def test_multi_region_edit_reports_every_changed_region():
    parent = transcript()
    candidate = transcript("all_three", "AUGGCCUAA", utr5="AAA", utr3="GGG")
    verdict = classify_construct_edit(parent, candidate)
    assert verdict["valid_under_assay_v3"]
    assert verdict["regions_changed"] == ["orf", "utr3", "utr5"]
    assert verdict["model_input_coupling"]["strand_features_move"]
    assert not verdict["model_input_coupling"]["ribonn_region_sizes_move"]


def test_identical_candidate_moves_no_model_input():
    verdict = classify_construct_edit(transcript(), transcript("same"))
    assert verdict["valid_under_assay_v3"]
    assert verdict["regions_changed"] == []
    assert verdict["orf_unchanged"] and not verdict["orf_synonymous"]
    assert not verdict["model_input_coupling"]["strand_features_move"]
    assert not verdict["model_input_coupling"]["ribonn_region_sizes_move"]


def test_oversized_utr5_candidate_is_invalid_on_the_upstream_domain_limit():
    parent = transcript()
    candidate = transcript("huge_utr5", utr5="A"*1382)
    verdict = classify_construct_edit(parent, candidate)
    assert not verdict["valid_under_assay_v3"]
    assert verdict["invalid_reasons"] == ["candidate_utr5_exceeds_1381_nt"]
    assert verdict["model_input_coupling"]["candidate_ribonn_exclusion"] == "utr5_exceeds_1381_nt"
    assert verdict["model_input_coupling"]["ribonn_region_sizes_move"]


def test_identity_hashes_are_carried_for_provenance_binding():
    parent, candidate = transcript(), transcript("syn", "AUGGCCUAA")
    verdict = classify_construct_edit(parent, candidate)
    assert verdict["parent_identity_sha256"] == parent.identity_sha256
    assert verdict["candidate_identity_sha256"] == candidate.identity_sha256
    assert verdict["parent_tx_id"] == "parent" and verdict["candidate_tx_id"] == "syn"


def test_non_transcript_and_cross_table_inputs_are_refused():
    parent = transcript()
    with pytest.raises(ValueError):
        classify_construct_edit(parent, "AUGGCCUAA")
    with pytest.raises(ValueError):
        classify_construct_edit("AUGGCCUAA", parent)


def test_no_benefit_claim_is_attached_to_a_valid_verdict():
    verdict = classify_construct_edit(transcript(), transcript("syn", "AUGGCCUAA"))
    assert "establishes no stability, translation or expression benefit" in verdict["no_claim"]
