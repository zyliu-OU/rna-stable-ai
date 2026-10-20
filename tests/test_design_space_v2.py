"""Tests for design-space v2, which widens the window to 50 codons.

The window widened because a measurement said the 30-codon objective landscape
was nearly flat. A change made in response to a measurement is easy to overstate
later, so these tests pin that v1 is retained unedited, that the reason is
recorded with the number that prompted it, that the thing widening does NOT fix
is stated, that the cost is stated, and that the expectation is falsifiable.
"""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "configs/synonymous_window_design_space_v1_2026-10-20.json"
V2 = ROOT / "configs/synonymous_window_design_space_v2_2026-10-20.json"


@pytest.fixture(scope="module")
def v1():
    return json.loads(V1.read_text())


@pytest.fixture(scope="module")
def v2():
    return json.loads(V2.read_text())


def test_v1_is_retained_unedited_at_its_recorded_hash(v2):
    assert hashlib.sha256(V1.read_bytes()).hexdigest() == v2["supersedes"]["sha256"]
    assert "frozen and unedited" in v2["supersedes"]["status"]


def test_only_the_window_width_changed(v1, v2):
    assert v2["supersedes"]["what_changed"] == (
        "The window widens from 30 to 50 codons. Nothing else changed.")
    assert v1["window"]["codons"] == 30
    assert v2["window"]["codons"] == 50
    # The constraints, the sampling rule and the rejected alternatives are the
    # parts a width change has no business touching.
    assert v2["constraints"] == v1["constraints"]
    assert v2["sampling"] == v1["sampling"]
    assert v2["why_a_window"]["what_was_rejected"] == v1["why_a_window"]["what_was_rejected"]


def test_the_window_bounds_are_consistent_with_the_width(v2):
    assert "1 through 50" in v2["window"]["codon_indices"]
    assert "4 through 153" in v2["window"]["nucleotides"]


def test_the_measurement_that_prompted_the_change_is_recorded(v2):
    why = v2["why_the_window_widened"]["measurement_that_prompted_it"]
    assert "90 nt of an 1811 nt transcript, 5.0 percent" in why
    assert "1.311 to 1.328 hours" in why
    assert "1.3 percent" in why
    assert "0.720 to 2.030 hour training target range" in why


def test_what_widening_does_not_do_is_stated(v2):
    text = v2["why_the_window_widened"]["what_widening_does_NOT_do"]
    assert "does not fix the mismatch" in text
    assert "design space is LOCAL and the objective features are GLOBAL" in text
    assert "region-local features" in text
    assert "NOT taken and remains open" in text


def test_the_cost_of_widening_is_stated(v2):
    cost = v2["why_the_window_widened"]["cost_of_widening"]
    assert "8,000 variants" in cost
    assert "10^7.2" in cost
    assert "no longer available" in cost
    assert "exhaustively enumerable; at this width it is not" in v2["gc_modes"]["neutral"]["cost"]


def test_the_expectation_is_falsifiable_and_both_runs_are_kept(v2):
    expectation = v2["why_the_window_widened"]["falsifiable_expectation"]
    assert "should be wider at 50 codons than at 30" in expectation
    assert "measured rather than assumed" in expectation


def test_the_width_is_still_labelled_a_declared_choice(v2):
    declared = v2["window"]["window_size_is_a_declared_choice"]
    assert "declared, not derived" in declared
    assert "NOT a finding that 50 is the right width" in declared
    assert "was not optimised" in declared
    text = " ".join(v2["no_claim"])
    assert "not a finding that 50 codons is correct or optimal" in text
    assert "only reduces it" in text


def test_the_tractability_figures_are_updated_for_the_new_width(v2):
    tractability = v2["why_a_window"]["tractability"]
    assert "10^23.4 free and 10^7.2 GC-neutral" in tractability
    assert "sampled into a pool rather than enumerated" in tractability


def test_the_free_mode_confound_is_attributed_to_the_width_it_was_measured_at(v2):
    confound = v2["gc_modes"]["free"]["measured_confound"]
    assert "Measured at the 30-codon width" in confound
    assert "re-measured by each run rather than assumed" in confound


def test_the_window_width_matches_what_the_generator_can_deliver(v2):
    """24 GC-neutral positions at 50 codons, against 13 at 30."""
    from rnastable.synonymous_window import (
        codon_table, split_codons, synonyms, window_indices,
    )

    orf = ROOT / v2["reference"]["orf"]
    if not orf.exists():
        pytest.skip("reference ORF not available")
    codons = split_codons("".join(orf.read_text().split()))
    indices = window_indices(codons, v2["window"]["codons"])
    assert len(indices) == v2["window"]["codons"]
    table, groups = codon_table(), synonyms()

    def gc(codon):
        return codon.count("G") + codon.count("C")

    neutral = [i for i in indices
               if any(c != codons[i] and gc(c) == gc(codons[i]) for c in groups[table[codons[i]]])]
    assert len(neutral) == 24
    assert "24 of the 50 window positions" in v2["gc_modes"]["neutral"]["cost"]
