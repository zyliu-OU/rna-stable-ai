"""Tests for the Stage 2 gate review recorded in v5.

v5 is the version that closes Stage 2, so it is the version with the most to
lose from being quietly generous. Two of its six requirements are satisfied by
accepting a documented limitation rather than by improving the data, and one
was re-scoped after the artifact it referred to was deleted. The tests below
pin the things that keep that honest: that v4 is retained unedited, that each
accepted limitation states what it costs and what would close it properly,
that the re-scope records what was not restored, that v3's band limitation and
the correction to v3's availability figure both survive, and that opening the
gate did not also open the switches behind it.
"""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
V4 = ROOT / "configs/stage2_to_stage3_gate_v4_2026-10-20.json"
V5 = ROOT / "configs/stage2_to_stage3_gate_v5_2026-10-20.json"


@pytest.fixture(scope="module")
def v5():
    return json.loads(V5.read_text())


@pytest.fixture(scope="module")
def v4():
    return json.loads(V4.read_text())


def test_v4_is_retained_unedited_at_its_recorded_hash(v5):
    assert hashlib.sha256(V4.read_bytes()).hexdigest() == v5["supersedes"]["sha256"]


def test_only_requirement_five_text_changed(v4, v5):
    before = list(v4["requirements_before_stage3"])
    after = list(v5["requirements_before_stage3"])
    assert len(before) == len(after) == 6
    differing = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
    assert differing == [4]
    assert "native_path" in after[4]


def test_all_six_requirements_are_recorded_as_satisfied(v5):
    assert v5["requirements_satisfied"] == 6
    detail = v5["requirements_satisfied_detail"]
    assert len(detail["satisfied"]) == 6
    assert detail["not_satisfied"] == []
    assert set(detail["satisfied"]) == set(v5["requirements_before_stage3"])


def test_the_two_accepted_limitations_are_labelled_as_such(v5):
    """Satisfied-by-narrowing must never read the same as satisfied-on-evidence."""
    basis = v5["requirements_satisfied_detail"]["basis_by_requirement"]
    assert basis["1"].startswith("accepted_as_documented_limitation")
    assert basis["3"].startswith("accepted_as_documented_limitation")
    for key in ("2", "4", "5", "6"):
        assert basis[key].startswith("satisfied_on_evidence")
    assert "does NOT mean the structure evidence is strong" in \
        v5["requirements_satisfied_detail"]["caution"]


def test_requirement_one_acceptance_states_its_cost_and_its_cure(v5):
    resolution = v5["requirement_1_resolution"]
    assert resolution["resolution"] == "accepted_as_documented_limitation"
    assert "not_by_acquiring_references" in resolution["status"]
    limitation = resolution["what_the_limitation_is"]
    assert "6 in-scope records" in limitation["cohort_size"]
    assert "3 families and 2 clans" in limitation["cohort_size"]
    assert "NO experimental-structure reference in scope" in limitation["label_provenance"]
    assert "data acquisition problem" in limitation["character_of_the_gap"]
    assert "Acquiring experimental-structure references" in \
        resolution["what_would_close_it_properly"]


def test_the_separation_by_construction_argument_stays_scope_limited(v5):
    """It must not become a general exemption for a future learned component."""
    satisfied = v5["requirement_1_resolution"]["what_is_genuinely_satisfied"]
    assert "no training set" in satisfied["separation"]
    assert "ONLY to these two tools" in satisfied["scope_limit_of_that_argument"]
    assert "future replacement for the retired model" in \
        satisfied["scope_limit_of_that_argument"]
    binding = " ".join(v5["requirement_1_resolution"]["binding_consequence"])
    assert "MUST NOT be reused for any learned component" in binding
    assert "'independent' MUST NOT be used" in binding


def test_requirement_five_rescope_records_what_was_not_restored(v5):
    rescope = v5["requirement_5_rescope_and_ratification"]
    assert "deleted" in rescope["why_rescoped"]
    assert "learned-model replay leg" in rescope["what_was_not_restored"]
    assert "MUST NOT be read as having been satisfied on its original terms" in \
        rescope["what_was_not_restored"]
    assert all(leg["passed"] is True for leg in rescope["legs"].values())


def test_the_vienna_constraint_finding_is_recorded_with_its_mitigation(v5):
    """A silently dropped constraint would make the decoder leg unfalsifiable."""
    finding = v5["requirement_5_rescope_and_ratification"]["legs"]["refusal_control"]["finding"]
    assert "silently DROPS" in finding
    assert "vienna_constraint_worker.py" in finding
    assert "hc_add_from_db" in finding


def test_v3_band_limitation_and_its_correction_both_survive(v5):
    resolution = v5["requirement_3_resolution"]
    assert resolution["resolution"] == "accepted_as_documented_limitation"
    assert v5["claimed_length_range"]["claimable_without_caveat"]["maximum_exclusive"] == 2000
    assert "MUST NOT be claimed" in resolution["binding_consequence"]
    correction = resolution["correction_to_v3"]
    assert "overstates" in correction["what_is_true"]
    assert "Only 5 of the 55" in correction["what_is_true"]
    assert "NOT edited" in correction["handling"]


def test_the_band_expansion_did_not_touch_the_frozen_selection(v5):
    expansion = v5["requirement_3_resolution"]["expansion_on_2026_10_20"]
    assert expansion["frozen_selection_modified"] is False
    assert expansion["records"] == "1 -> 5"
    assert "no family contrast within itself" in expansion["what_is_still_limited"]


def test_requirement_four_does_not_overstate_what_credible_means(v5):
    text = v5["requirement_4_ratification"]["what_credible_means_here"]
    assert "NOT a strong structural result" in text
    assert "0.42-0.44" in text
    assert "propagates" in v5["requirement_4_ratification"]["downstream_consequence"]


def test_requirement_six_freezes_both_documents(v5):
    ratification = v5["requirement_6_ratification"]
    assert len(ratification["documents"]) == 2
    for relative, expected in ratification["documents_sha256"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    assert "unedited" in ratification["relationship"]


def test_opening_the_gate_did_not_open_the_switches_behind_it(v5):
    assert v5["stage3_ready"] is True
    for key in ("stage3_development_started", "model_defaults_changed",
                "expression_benefit_established", "new_sequence_scoring_enabled",
                "expression_candidate_design_enabled"):
        assert v5[key] is False, key
    switches = v5["stage3_ready_detail"]["separate_switches_not_opened_here"]
    assert "blinded 85-record evaluation set is unspent" in \
        switches["new_sequence_scoring_enabled"]
    assert "BoTorch" in switches["expression_candidate_design_enabled"]


def test_stage3_ready_says_what_it_does_not_mean(v5):
    meaning = v5["stage3_ready_detail"]["meaning"]
    assert "does NOT mean the structure evidence is strong" in meaning
    assert "or that the assay can run" in meaning
    assert "expression or stability benefit is established" in meaning
    assert v5["stage3_ready_detail"]["stage3_entry_preconditions_outside_this_gate"]


def test_the_prohibited_claims_are_carried_forward(v5):
    text = " ".join(v5["what_must_not_be_claimed"])
    assert "six of six satisfied" in text
    assert "biological validation" in text
    assert "original terms" in text
    assert "reproduced from the tree" in text


def test_every_cited_evidence_path_exists(v5):
    sections = ("requirement_1_resolution", "requirement_2_ratification",
                "requirement_4_ratification", "requirement_5_rescope_and_ratification",
                "requirement_6_ratification")
    for name in sections:
        section = v5[name]
        for key in ("evidence", "documents", "tests"):
            for relative in section.get(key, []):
                assert (ROOT / relative).exists(), f"{name}.{key}: {relative}"


def test_every_recorded_evidence_hash_matches(v5):
    for name in ("requirement_2_ratification", "requirement_4_ratification",
                 "requirement_5_rescope_and_ratification"):
        for relative, expected in v5[name].get("evidence_sha256", {}).items():
            actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            assert actual == expected, relative


def test_the_reported_figures_match_their_source_artifacts(v5):
    """A gate that paraphrases its own evidence is where drift starts."""
    validation = json.loads(
        (ROOT / "results/native_control_validation/native_control_validation.json").read_text())
    recorded = v5["requirement_2_ratification"]["results"]["long_rfam_consensus_in_scope"]
    for method in ("LinearFold", "ViennaRNA"):
        cohort = validation["cohorts"][method]["long_rfam_consensus"]
        assert cohort["n"] == recorded["n"]
        assert round(cohort["mean_record_pair_f1"], 4) == recorded[method]["record"]
        assert round(cohort["mean_family_pair_f1"], 4) == recorded[method]["family"]
        assert round(cohort["mean_clan_pair_f1"], 4) == recorded[method]["clan"]
    band_run = v5["requirement_3_resolution"]["expansion_on_2026_10_20"]["run"]
    band = json.loads((ROOT / band_run).read_text())
    for method in ("LinearFold", "ViennaRNA"):
        stats = band["per_method"][method]
        expected = v5["requirement_3_resolution"]["expansion_on_2026_10_20"][method]
        assert stats["n"] == expected["n"]
        assert round(stats["mean_record_pair_f1"], 4) == expected["mean_pair_f1"]
        assert round(stats["stdev_pair_f1"], 4) == expected["stdev"]


def test_the_learned_model_remains_retired(v5):
    status = v5["learned_model_status"]
    assert status["relied_upon"] is False
    assert status["disposition"].startswith("RETIRED")
    assert "only by a later gate version" in status["may_be_restored"]


def test_the_acceptance_is_reversible_by_a_later_version_not_an_edit(v5):
    assert "superseded by v6 rather than edited" in v5["amendment_record"]["reversible"]
