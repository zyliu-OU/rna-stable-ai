"""Tests for the Stage 2 gate v4 amendment.

Requirement 4 now concerns the native controls the project relies on rather than
the learned pair model. An amendment like this is the easiest place for a gate to
be quietly weakened, so the tests below pin the things that stop it being one:
that it does not satisfy itself, that `requirements_satisfied` did not move, that
the learned model is demoted rather than deleted, and that v3's band limitation
survives.
"""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
V3 = ROOT / "configs/stage2_to_stage3_gate_v3_2026-10-19.json"
V4 = ROOT / "configs/stage2_to_stage3_gate_v4_2026-10-20.json"

OLD_REQ4 = "Demonstrate_credible_structure_accuracy_with_explicit_review_of_native_baseline_gaps"


@pytest.fixture(scope="module")
def v4():
    return json.loads(V4.read_text())


@pytest.fixture(scope="module")
def v3():
    return json.loads(V3.read_text())


def test_v3_is_retained_unedited_at_its_recorded_hash(v4):
    assert hashlib.sha256(V3.read_bytes()).hexdigest() == v4["supersedes"]["sha256"]


def test_requirement_four_text_changed_and_names_the_native_controls(v4):
    req4 = v4["requirements_before_stage3"][3]
    assert req4 != OLD_REQ4
    assert "native_controls" in req4
    assert "relied_upon" in req4


def test_only_requirement_four_changed(v3, v4):
    before = list(v3["requirements_before_stage3"])
    after = list(v4["requirements_before_stage3"])
    assert len(before) == len(after) == 6
    differing = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
    assert differing == [3]


def test_the_amendment_does_not_satisfy_itself(v4):
    """The central guard: changing what must be shown is not showing it."""
    clause = v4["requirement_4_amendment"]["DOES_NOT_SATISFY_ITSELF"]
    assert clause["requirement_4_status"] == "not_satisfied"
    assert "does not demonstrate it" in clause["why"]
    assert "did not become satisfied" in clause["what_changed_in_practice"]


def test_requirements_satisfied_did_not_move(v3, v4):
    assert v4["requirements_satisfied"] == v3["requirements_satisfied"] == 1


def test_requirement_four_is_still_listed_as_unsatisfied(v4):
    not_satisfied = v4["requirements_satisfied_detail"]["not_satisfied"]
    assert len(not_satisfied) == 5
    assert any("native_controls" in r for r in not_satisfied)
    assert OLD_REQ4 not in not_satisfied


def test_the_native_evidence_is_not_mistaken_for_validation(v4):
    """0.6261 comes from a feasibility cohort, and the gate must say so."""
    why = v4["requirement_4_amendment"]["DOES_NOT_SATISFY_ITSELF"]["why"]
    assert "0.6261" in why
    assert "broad_validation_gate_satisfied false" in why
    assert "feasibility cohort, not independent validation" in why


def test_the_learned_model_is_retired_and_its_evidence_retained(v4):
    """Weights are gone; the evidence that justified removing them is not."""
    status = v4["requirement_4_amendment"]["learned_model_status"]
    assert status["relied_upon"] is False
    assert status["disposition"].startswith("RETIRED")
    assert "deleted" in status["disposition"]
    retained = " ".join(status["what_was_retained"])
    assert "metric" in retained and "intact and auditable" in retained
    assert "source code" in retained
    assert status["historical_runs_remain_development_evidence"] is True
    assert "only by a later gate version" in status["may_be_restored"]


def test_the_test_consequence_of_retirement_is_recorded(v4):
    """38 replay tests became unrunnable; that must be stated, not hidden."""
    text = v4["requirement_4_amendment"]["learned_model_status"]["test_consequence"]
    assert "38 replay tests" in text
    assert "NOT deleted" in text
    assert "RiboNN weights are excluded" in text


def test_the_forward_architecture_is_recorded(v4):
    arch = v4["requirement_4_amendment"]["learned_model_status"]["forward_architecture"]
    assert "LinearFold" in arch and "ViennaRNA" in arch
    assert "STRAND" in arch and "RiboNN" in arch and "BoTorch" in arch


def test_the_measured_gap_is_recorded_with_the_amendment(v4):
    gap = v4["requirement_4_amendment"]["evidence_of_the_gap"]
    assert gap["rfam_consensus_long_refs"]["learned_best"] == 0.2965
    assert gap["structure_derived_refs"]["native_both"] == 0.6261
    assert "not a threshold artifact" in gap["loss_attribution"]
    assert "61 training records" in gap["training_scale"]


def test_v3_band_limitation_survives_into_v4(v4):
    """The 2,000–2,999 nt acceptance must not be lost by a later amendment."""
    assert v4["requirement_3_resolution"]["resolution"] == "accepted_as_documented_limitation"
    assert v4["claimed_length_range"]["claimable_without_caveat"]["maximum_exclusive"] == 2000


def test_the_stage3_target_amendment_survives(v4):
    assert v4["stage3_target"] == "transfected_cell_expression"


def test_amending_a_requirement_does_not_open_the_gate(v4):
    assert v4["stage3_ready"] is False
    assert v4["stage3_development_started"] is False
    assert v4["new_sequence_scoring_enabled"] is False
    assert v4["expression_candidate_design_enabled"] is False
    assert v4["model_defaults_changed"] is False


def test_what_would_satisfy_it_is_stated(v4):
    text = v4["requirement_4_amendment"]["DOES_NOT_SATISFY_ITSELF"]["what_would_now_satisfy_it"]
    assert "family and clan separated" in text
    assert "2000-2999" in text


def test_every_cited_evidence_path_exists(v4):
    for relative in v4["requirement_4_amendment"]["evidence"]:
        assert (ROOT / relative).exists(), relative
