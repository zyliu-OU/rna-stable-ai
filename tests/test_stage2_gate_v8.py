"""Tests for gate v8, which records external evidence that weakens a claim.

Most gate versions in this project add a permission or close a requirement. v8
is the first that REMOVES a licence to claim something, on evidence from outside
the project. These tests pin that the removal is explicit, that the caveats
cutting the other way travel with it, that the new prohibition names what it
applies to, and that nothing was quietly re-opened or re-ratified.
"""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
V7 = ROOT / "configs/stage2_to_stage3_gate_v7_2026-10-20.json"
V8 = ROOT / "configs/stage2_to_stage3_gate_v8_2026-10-20.json"


@pytest.fixture(scope="module")
def v8():
    return json.loads(V8.read_text())


@pytest.fixture(scope="module")
def v7():
    return json.loads(V7.read_text())


def test_v7_is_retained_unedited_at_its_recorded_hash(v8):
    assert hashlib.sha256(V7.read_bytes()).hexdigest() == v8["supersedes"]["sha256"]


def test_nothing_was_reopened_or_rereatified(v7, v8):
    assert v8["requirements_before_stage3"] == v7["requirements_before_stage3"]
    assert v8["requirements_satisfied"] == v7["requirements_satisfied"] == 6
    assert v8["requirements_satisfied_basis_unchanged_from_v5"] == \
        v7["requirements_satisfied_basis_unchanged_from_v5"]
    assert v8["switches_unchanged_from_v6"] == v7["switches_unchanged_from_v6"]
    assert "No requirement is re-opened" in v8["amendment_record"]["what_changed"]
    assert "no switch moves" in v8["amendment_record"]["what_changed"]


def test_it_says_why_a_gate_and_not_only_a_report(v8):
    why = v8["amendment_record"]["why_a_gate_version_rather_than_only_a_report"]
    assert "what must not be claimed" in why
    assert "removes a licence to claim" in why


def test_the_new_prohibition_is_explicit_and_scoped(v8):
    added = v8["new_prohibition_added_here"]
    assert "MUST NOT be presented as the expected measured ordering" in added["prohibition"]
    assert any("design_workflow_runs" in target for target in added["applies_to"])
    assert "sequence-independence assumption" in added["why"]
    assert "still permitted" in " ".join(added) or added["what_is_still_permitted"]
    assert "as predictions on the unmodified sequence" in added["what_is_still_permitted"]


def test_the_modification_finding_carries_its_counter_caveats(v8):
    block = v8["external_evidence_added"]["modification_constancy_not_supported"]
    caveats = " ".join(block["caveats_that_must_travel_with_it"])
    assert "NOT N1-methylpseudouridine" in caveats
    assert "behaves better than psi" in caveats
    assert "TECHNICAL replicate noise" in caveats
    assert "13-fold span and the sign change" in caveats
    assert "no significance claim" in caveats
    assert "cannot be resolved with this dataset" in caveats


def test_the_modification_verdicts_match_the_run(v8):
    block = v8["external_evidence_added"]["modification_constancy_not_supported"]
    run = json.loads((ROOT / block["run"]).read_text())
    assert run["verdicts"]["half_life"] == block["in_solution_half_life"]["verdict"]
    assert run["verdicts"]["protein_6h"] == block["protein_output_6h"]["verdict"]
    assert run["verdicts"]["protein_24h"] == block["protein_output_24h"]["verdict"]
    for key, arm in (("protein_output_6h", "6h"), ("protein_output_24h", "24h")):
        measured = run["protein_output"]["timepoints"][arm]
        assert block[key]["same_direction"] is measured["all_same_direction"]
        assert round(measured["dispersion"]["dispersion_ratio"], 2) == \
            block[key]["dispersion_ratio"]


def test_the_validation_figures_match_the_run(v8):
    block = v8["external_evidence_added"]["stability_calibration_transfers_weakly"]
    run = json.loads((ROOT / block["run"]).read_text())
    assert run["counts"]["held_out"] == block["held_out_records"]
    assert round(run["primary"]["spearman"], 4) == block["spearman"]
    assert round(run["primary"]["pearson_log"], 4) == block["pearson_on_log"]
    assert round(run["training_subset_upper_bound"]["spearman"], 4) == \
        block["training_subset_upper_bound_spearman"]


def test_the_validation_states_what_it_does_not_establish(v8):
    block = v8["external_evidence_added"]["stability_calibration_transfers_weakly"]
    text = block["what_it_does_not_establish"]
    assert "improvement over published predictors" in text
    assert "order SIMILAR" in text
    assert "coarse discrimination, not fine ordering" in text
    assert "must exclude them" in block["training_provenance_now_known"]


def test_requirement_six_now_lists_three_documents(v8):
    documents = v8["requirement_6_documents"]
    assert len(documents) == 3
    for relative in documents:
        assert (ROOT / relative).exists(), relative


def test_the_second_addendum_records_the_adverse_finding(v8):
    text = (ROOT / v8["requirement_6_documents"][2]).read_text()
    assert "not supported on the expression readout" in text
    assert "13-fold" in text
    assert "changes sign" in text
    assert "This is Ψ, not m1Ψ" in text
    assert "doubling the panel" in text


def test_the_prohibitions_grew_rather_than_shrank(v7, v8):
    before = set(v7["what_must_not_be_claimed"])
    after = set(v8["what_must_not_be_claimed"])
    assert before <= after, "an earlier prohibition must never be dropped"
    assert len(after) > len(before)
    added = " ".join(after - before)
    assert "predicted ordering of modified constructs" in added
    assert "matches one that is free" in added
