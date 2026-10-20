"""Tests for the whole-transcript design domain.

The generator's first version produced 60 members sharing 2 ORFs, and every
other property looked correct: lengths right, protein verified, GC varying,
constraints satisfied. Only a distinct-sequence count caught it. The first test
below is therefore the one that matters most, and the rest pin the constraints
that keep a designed transcript from silently becoming a different construct.
"""
import json
from pathlib import Path

import pytest

from rnastable.synonymous_window import translate, split_codons
from rnastable.transcript_assembly import assemble_designed
from rnastable.transcript_design import (
    KOZAK_SUFFIX,
    TANDEM_STOP_PREFIX,
    build_pool,
    editable_spans,
    out_of_frame_uaug,
    reachable_gc_range,
)

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "configs/full_transcript_design_space_v3_2026-10-20.json"
INPUTS = ROOT / "configs/transcript_inputs_v1_2026-10-19.json"
ORF = ROOT / "data/constructs/fluc_orf.txt"

pytestmark = pytest.mark.skipif(not (INPUTS.exists() and ORF.exists()),
                                reason="reference inputs not available")


@pytest.fixture(scope="module")
def inputs():
    components = json.loads(INPUTS.read_text())["components"]
    return (components["utr5"]["sequence_dna_uppercase"].upper(),
            "".join(ORF.read_text().split()).upper(),
            components["utr3"]["sequence_dna_uppercase"].upper())


@pytest.fixture(scope="module")
def pool(inputs):
    return build_pool(*inputs, size=48, seed=1729)


def test_members_are_distinct_sequences_not_one_orf_repeated(pool):
    """The defect that every other check missed: 60 members, 2 ORFs."""
    orfs = {m["orf"] for m in pool["members"]}
    transcripts = {m["transcript_sha256"] for m in pool["members"]}
    assert len(orfs) == pool["size"], "codon design collapsed onto shared ORFs"
    assert len(transcripts) == pool["size"]


def test_the_protein_is_preserved_on_every_member(pool, inputs):
    protein = translate(split_codons(inputs[1]))
    for member in pool["members"]:
        assert translate(split_codons(member["orf"])) == protein


def test_the_kozak_context_and_tandem_stop_are_preserved(pool):
    for member in pool["members"]:
        assert member["utr5"].endswith(KOZAK_SUFFIX)
        assert member["utr3"].startswith(TANDEM_STOP_PREFIX)


def test_no_member_introduces_an_out_of_frame_uaug(pool):
    """Grounded in this project's own measured uAUG penalty."""
    for member in pool["members"]:
        assert out_of_frame_uaug(member["utr5"]) == []


def test_every_length_is_fixed(pool, inputs):
    utr5, cds, utr3 = inputs
    expected = len(utr5) + len(cds) + len(utr3)
    for member in pool["members"]:
        assert member["transcript_length_nt"] == expected
        assert len(member["utr5"]) == len(utr5)
        assert len(member["orf"]) == len(cds)
        assert len(member["utr3"]) == len(utr3)


def test_the_homopolymer_bound_holds_without_relying_on_rejection(pool):
    for member in pool["members"]:
        assert member["longest_homopolymer"] <= pool["max_homopolymer"]


def test_run_aware_sampling_keeps_the_rejection_rate_low(pool):
    """Generating inside the bound rather than filtering after it."""
    assert pool["attempts"] < pool["size"] * 6


def test_member_zero_is_the_unmodified_reference(pool, inputs):
    first = pool["members"][0]
    assert first["is_reference"] is True
    assert first["substitution_count"] == 0
    assert first["utr5_edits"] == 0 and first["utr3_edits"] == 0
    assert first["utr5"] == inputs[0] and first["orf"] == inputs[1] and first["utr3"] == inputs[2]


def test_the_pool_spans_both_axes(pool):
    """Codons and UTRs must both actually vary, or the widening achieved nothing."""
    assert max(m["substitution_count"] for m in pool["members"]) > 100
    assert max(m["utr5_edits"] for m in pool["members"]) > 5
    assert max(m["utr3_edits"] for m in pool["members"]) > 20


def test_gc_is_steered_across_a_wide_range(pool):
    achieved = [m["transcript_gc_fraction"] for m in pool["members"]]
    assert max(achieved) - min(achieved) > 0.1, "GC steering is the point of this domain"


def test_the_calibration_domain_becomes_reachable(pool):
    """In the synonymous-only domain every member extrapolated on GC."""
    ceiling = 0.6024
    in_domain = sum(1 for m in pool["members"] if m["transcript_gc_fraction"] <= ceiling)
    assert in_domain > pool["size"] // 2
    assert pool["members"][0]["transcript_gc_fraction"] > ceiling, \
        "the reference itself must still be out of domain, which is why this matters"


def test_the_reachable_range_is_wider_than_the_reference(inputs):
    bounds = reachable_gc_range(*inputs)
    assert bounds["minimum"] < 0.40
    assert bounds["maximum"] > 0.65
    assert bounds["free_utr_positions"] == 38 + 111


def test_editable_spans_refuse_a_construct_without_the_protected_motifs(inputs):
    utr5, _, utr3 = inputs
    with pytest.raises(ValueError, match="Kozak"):
        editable_spans(utr5[:-1] + "A", utr3)
    with pytest.raises(ValueError, match="tandem stop"):
        editable_spans(utr5, "GGG" + utr3[3:])


def test_the_pool_is_deterministic(inputs):
    a = build_pool(*inputs, size=12, seed=7)
    b = build_pool(*inputs, size=12, seed=7)
    assert [m["transcript_sha256"] for m in a["members"]] == \
        [m["transcript_sha256"] for m in b["members"]]


def test_a_different_seed_gives_a_different_pool(inputs):
    a = build_pool(*inputs, size=12, seed=7)
    b = build_pool(*inputs, size=12, seed=1729)
    assert [m["transcript_sha256"] for m in a["members"]] != \
        [m["transcript_sha256"] for m in b["members"]]


def test_the_pool_records_that_the_utrs_are_designed(pool):
    assert pool["utrs_are_designed_not_supplied"] is True
    assert pool["scored"] is False


def test_assemble_designed_round_trips_the_reference(inputs):
    """The strongest consistency check available without a measurement."""
    utr5, cds, utr3 = inputs
    _, report = assemble_designed(utr5, cds, utr3, INPUTS, "FLUC-REF-V1", "ref", "ctx")
    assert report.transcript_sha256_rna.startswith("403a45c5cbddc24b")
    assert report.utr5_edits == 0 and report.utr3_edits == 0
    assert report.substituted_codon_indices == ()
    assert report.utrs_designed is True


def test_assemble_designed_refuses_what_would_change_the_construct(inputs, pool):
    utr5, cds, utr3 = inputs
    member = pool["members"][1]
    with pytest.raises(ValueError, match="Kozak"):
        assemble_designed(utr5[:-1] + "A", cds, utr3, INPUTS, "X", "p", "c")
    with pytest.raises(ValueError, match="tandem stop"):
        assemble_designed(utr5, cds, "GGG" + utr3[3:], INPUTS, "X", "p", "c")
    with pytest.raises(ValueError, match="out-of-frame uAUG"):
        assemble_designed("ATG" + utr5[3:], cds, utr3, INPUTS, "X", "p", "c")
    with pytest.raises(ValueError, match="lengths are fixed"):
        assemble_designed(utr5 + "A", cds, utr3, INPUTS, "X", "p", "c")
    with pytest.raises(ValueError, match="does not translate"):
        assemble_designed(utr5, cds[:3] + "TTT" + cds[6:], utr3, INPUTS, "X", "p", "c")
    # A real member must pass.
    _, report = assemble_designed(member["utr5"], member["orf"], member["utr3"],
                                  INPUTS, "OK", "p", "c")
    assert report.synonymous_verified is True


def test_a_designed_transcript_says_it_is_a_new_construct(inputs, pool):
    member = pool["members"][1]
    _, report = assemble_designed(member["utr5"], member["orf"], member["utr3"],
                                  INPUTS, "X", "p", "c")
    assert "UTRs are DESIGNED" in report.no_claim
    assert "new construct, not the supplied construct with tweaks" in report.no_claim


def test_the_spec_records_what_is_gained_and_lost(inputs):
    spec = json.loads(SPEC.read_text())
    lost = " ".join(spec["what_is_gained_and_lost"]["lost"])
    assert "stop being the collaborator's supplied, hash-verified sequences" in lost
    assert "NEW construct" in lost
    assert "less trustworthy, not more" in lost
    assert "preserved exactly and verified" in spec["what_is_gained_and_lost"]["unchanged"]
    assert "does not improve the objective" in spec["why_this_change"]["what_it_does_not_fix"]
    assert spec["constraints"]["no_out_of_frame_uaug_in_the_utr5"][
        "grounded_in_this_project_own_measurement"].startswith("The m1-pseudouridine")
