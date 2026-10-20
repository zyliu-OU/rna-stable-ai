"""Tests for the variant assembly path.

`assemble` hash-gates the CDS against the config, which refuses a designed
variant by design. `assemble_variant` is the deliberate separate path, and the
thing worth pinning is that it is STRICTER rather than looser: the reference is
still read from the config and still hash-verified, and the variant must then
prove it is a synonymous variant of that exact sequence.

The failure that matters most is a non-synonymous sequence being assembled as
though it were synonymous, so that is tested from several directions.
"""
import json
from pathlib import Path

import pytest

from rnastable.synonymous_window import build_pool, codon_table, split_codons, synonyms
from rnastable.transcript_assembly import assemble, assemble_variant

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/transcript_inputs_v1_2026-10-19.json"
ORF = ROOT / "data/constructs/fluc_orf.txt"

pytestmark = pytest.mark.skipif(not (CONFIG.exists() and ORF.exists()),
                                reason="reference inputs not available")


@pytest.fixture(scope="module")
def reference_cds():
    return "".join(ORF.read_text().split())


@pytest.fixture(scope="module")
def variants(reference_cds):
    pool = build_pool(reference_cds, window_codons=30, size=6, seed=1729, gc_mode="neutral")
    return ["".join(member["codons"]) for member in pool["members"]]


def build(cds, tx_id="FLUC-VAR-TEST"):
    return assemble_variant(cds, CONFIG, tx_id, "design pool member",
                            "provisional; no measurement exists")


def test_the_reference_passed_as_a_variant_reproduces_the_reference_assembly(reference_cds):
    """The strongest consistency check available without a measurement."""
    plain, plain_report = assemble(reference_cds, CONFIG, "FLUC-REF-V1",
                                   "reference", "assay_definition_v3_2026-10-19")
    variant, variant_report = build(reference_cds, "FLUC-REF-V1")
    assert variant.sequence == plain.sequence
    assert variant_report.transcript_sha256_rna == plain_report.transcript_sha256_rna
    assert variant_report.substituted_codon_indices == ()


def test_a_real_variant_assembles_with_both_hashes_recorded(variants):
    transcript, report = build(variants[1])
    assert report.synonymous_verified is True
    assert report.variant_of == "cds"
    assert report.cds_sha256_dna_uppercase != report.reference_cds_sha256_dna_uppercase
    assert len(report.cds_sha256_dna_uppercase) == 64
    assert len(report.reference_cds_sha256_dna_uppercase) == 64
    assert report.substituted_codon_indices
    assert report.transcript_length_nt == len(transcript.sequence)


def test_the_variant_fields_distinguish_it_from_a_reference_assembly(reference_cds):
    """A variant must never be mistakable for the reference in an artifact."""
    _, plain = assemble(reference_cds, CONFIG, "FLUC-REF-V1", "reference", "ctx")
    assert plain.variant_of is None
    assert plain.synonymous_verified is None
    assert plain.substituted_codon_indices is None
    assert plain.protein_sha256 is None


def test_every_pool_member_preserves_the_transcript_length_and_protein(variants):
    lengths, proteins = set(), set()
    for cds in variants:
        _, report = build(cds)
        lengths.add(report.transcript_length_nt)
        proteins.add(report.protein_sha256)
        assert report.synonymous_verified is True
    assert len(lengths) == 1
    assert len(proteins) == 1


def test_a_non_synonymous_variant_is_refused(reference_cds):
    codons = split_codons(reference_cds)
    changed = list(codons)
    changed[5] = "TTT" if codons[5] != "TTT" else "GGG"
    with pytest.raises(ValueError, match="not a synonymous variant"):
        build("".join(changed))


def test_a_variant_that_changes_only_the_start_codon_is_refused(reference_cds):
    codons = split_codons(reference_cds)
    with pytest.raises(ValueError):
        build("".join(["GTG"] + codons[1:]))


def test_a_variant_with_an_internal_stop_is_refused(reference_cds):
    codons = split_codons(reference_cds)
    changed = list(codons)
    changed[10] = "TAA"
    with pytest.raises(ValueError):
        build("".join(changed))


def test_a_variant_of_the_wrong_length_is_refused(reference_cds):
    with pytest.raises(ValueError, match="same length"):
        build(reference_cds[:-3])
    with pytest.raises(ValueError, match="same length"):
        build(reference_cds[:3] + reference_cds)


def test_an_empty_or_non_canonical_variant_is_refused():
    with pytest.raises(ValueError):
        build("")
    with pytest.raises(ValueError):
        build("ATGNNNTGA")
    with pytest.raises(ValueError):
        build(None)


def test_a_component_without_a_sequence_file_is_refused(reference_cds):
    """utr5 has no sequence_file, so a variant cannot be checked against it."""
    config = json.loads(CONFIG.read_text())
    assert "sequence_file" not in config["components"]["utr5"]
    with pytest.raises(ValueError, match="records no sequence_file"):
        assemble_variant(reference_cds, CONFIG, "X", "p", "c", reference_component="utr5")


def test_an_unknown_component_is_refused(reference_cds):
    with pytest.raises(ValueError, match="records no CDS component"):
        assemble_variant(reference_cds, CONFIG, "X", "p", "c",
                         reference_component="not_a_component")


def test_rna_spelling_is_accepted_and_normalised(variants):
    _, dna = build(variants[1])
    _, rna = build(variants[1].replace("T", "U"))
    assert rna.cds_sha256_dna_uppercase == dna.cds_sha256_dna_uppercase
    assert rna.transcript_sha256_rna == dna.transcript_sha256_rna


def test_the_tandem_stop_is_still_reported(variants):
    _, report = build(variants[1])
    assert report.tandem_stop_present is True
    assert report.tandem_stop_codon in ("UAA", "UAG", "UGA")


def test_the_no_claim_text_names_the_absence_of_measurement(variants):
    _, report = build(variants[1])
    assert "protein is preserved and verified" in report.no_claim
    assert "no measurement of any kind" in report.no_claim


def test_a_synonymous_variant_outside_the_window_is_still_accepted(reference_cds):
    """The window is the design space's rule, not the assembler's.

    The assembler's job is synonymy, not enforcing which positions a generator
    was allowed to touch. Conflating the two would let a future generator bug
    pass silently as long as it stayed synonymous.
    """
    codons = split_codons(reference_cds)
    table, groups = codon_table(), synonyms()
    index = next(i for i in range(400, 500)
                 if len(groups[table[codons[i]]]) > 1)
    changed = list(codons)
    changed[index] = next(c for c in groups[table[codons[index]]] if c != codons[index])
    _, report = build("".join(changed))
    assert report.synonymous_verified is True
    assert report.substituted_codon_indices == (index,)
