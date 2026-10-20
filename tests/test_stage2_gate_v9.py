"""Tests for gate v9, which both strengthens and narrows v8's prohibition.

A revision that narrows a prohibition is the easiest place for one to be
quietly relaxed. These tests pin that the prohibition still holds, that the
narrowing licenses nothing, that the superseded wording is recorded beside the
new one, that no earlier prohibition was dropped, and that the gate's quoted
figures match the run they come from.
"""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
V8 = ROOT / "configs/stage2_to_stage3_gate_v8_2026-10-20.json"
V9 = ROOT / "configs/stage2_to_stage3_gate_v9_2026-10-20.json"
FEATURES = ("out_of_frame_uaug", "gc_fraction", "vienna_mfe")


@pytest.fixture(scope="module")
def v9():
    return json.loads(V9.read_text())


@pytest.fixture(scope="module")
def v8():
    return json.loads(V8.read_text())


@pytest.fixture(scope="module")
def evidence(v9):
    return v9["external_evidence_added"]["m1pseudouridine_rescales_the_gc_relationship"]


def test_v8_is_retained_unedited_at_its_recorded_hash(v9):
    assert hashlib.sha256(V8.read_bytes()).hexdigest() == v9["supersedes"]["sha256"]


def test_nothing_was_reopened_or_rereatified(v8, v9):
    assert v9["requirements_before_stage3"] == v8["requirements_before_stage3"]
    assert v9["requirements_satisfied"] == v8["requirements_satisfied"] == 6
    assert v9["requirements_satisfied_basis_unchanged_from_v5"] == \
        v8["requirements_satisfied_basis_unchanged_from_v5"]
    assert v9["switches_unchanged_from_v6"] == v8["switches_unchanged_from_v6"]
    assert "No requirement is re-opened" in v9["amendment_record"]["what_changed"]
    assert "no switch moves" in v9["amendment_record"]["what_changed"]


def test_the_amendment_explains_why_it_moves_in_both_directions(v9):
    why = v9["amendment_record"]["why_both_directions"]
    assert "pseudouridine across six constructs" in why
    assert "N1-methylpseudouridine across 40,000 sequences per arm" in why
    assert "localises to GC composition" in why
    assert "stable within replicate noise" in why


def test_the_prohibition_still_holds_and_names_the_mechanism(v9):
    revised = v9["prohibition_revised_here"]
    assert "MUST NOT be presented as the expected measured ordering" in revised["revised"]
    assert "any ordering that depends on GC content is unsupported" in revised["revised"]
    assert "3.7" in revised["revised"]
    assert revised["supersedes"] == \
        json.loads(V8.read_text())["new_prohibition_added_here"]["prohibition"]
    assert "still holds" in revised["what_is_now_more_precise"]


def test_the_narrowing_licenses_nothing(v9):
    """The dangerous half of a narrowing: ambiguous is not supported."""
    text = v9["prohibition_revised_here"]["what_is_NOT_licensed_by_the_narrowing"]
    assert "AMBIGUOUS" in text
    assert "not supported" in text
    assert "must not be claimed" in text.lower()


def test_no_earlier_prohibition_was_dropped(v8, v9):
    before, after = set(v8["what_must_not_be_claimed"]), set(v9["what_must_not_be_claimed"])
    assert before <= after
    assert len(after) == len(before) + 3
    added = " ".join(after - before)
    assert "depending on GC content" in added
    assert "ambiguous, which is not the same as supported" in added
    assert "effect on stability is known" in added


def test_the_recorded_figures_match_the_run(v9, evidence):
    run = json.loads((ROOT / evidence["run"]).read_text())
    for feature in FEATURES:
        recorded = evidence["results"][feature]
        measured = run["comparison"][feature]
        assert recorded["verdict"] == measured["verdict"], feature
        assert recorded["ratio_between_over_within"] == pytest.approx(
            measured["ratio"]), feature
        assert recorded["unmodified_mean_slope"] == pytest.approx(
            measured["unmodified_mean"]), feature
        assert recorded["sign_changed"] is measured["sign_changed"], feature


def test_only_gc_is_recorded_as_sequence_dependent(evidence):
    assert evidence["results"]["gc_fraction"]["verdict"] == "sequence_dependent"
    for feature in ("out_of_frame_uaug", "vienna_mfe"):
        assert evidence["results"][feature]["verdict"] in (
            "ambiguous", "consistent_with_constant"), feature


def test_the_compounding_problem_with_gc_is_named(evidence):
    text = evidence["why_this_is_the_worst_feature_for_this_project"]
    assert "three inputs to strand_rnafold_calibration_v1" in text
    assert "EXTRAPOLATES" in text
    assert "64.4 percent" in text
    assert "compound rather than cancel" in text


def test_the_limitations_travel_with_the_evidence(evidence):
    text = " ".join(evidence["limitations_that_must_travel_with_it"])
    assert "NO replicate arm" in text
    assert "borrowed from the unmodified" in text
    assert "14 times noisier" in text
    assert "corrected mid-run" in text
    assert "says nothing about the stability side" in text
    assert "not causation" in text


def test_the_earlier_pseudouridine_finding_is_not_overwritten(v9, evidence):
    assert "modification_constancy_not_supported" in v9["external_evidence_added"]
    assert "stands as what it was" in \
        evidence["relationship_to_the_pseudouridine_check_in_v8"]


def test_requirement_six_now_lists_four_documents(v9):
    documents = v9["requirement_6_documents"]
    assert len(documents) == 4
    for relative in documents:
        assert (ROOT / relative).exists(), relative
    assert documents[3].endswith("_V3.md")


def test_the_third_addendum_records_the_narrowing_and_its_cost(v9):
    text = (ROOT / v9["requirement_6_documents"][3]).read_text()
    assert "strengthens and narrows" in text
    assert "3.7" in text
    assert "no replicate" in text.lower()
    assert "worst feature for this project" in text
    # Markdown emphasis sits inside the sentence, so match its stable halves.
    assert "*ambiguous*" in text
    assert "which is not the same as supported" in text
