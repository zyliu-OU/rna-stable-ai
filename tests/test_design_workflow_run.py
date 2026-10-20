"""Tests for the end-to-end design workflow run.

This is the first artifact in the project that attaches predicted values to
sequences nobody supplied, and selects among them. With no experimental data in
existence, the risk is not that a number is wrong but that it is later read as
though it meant something it does not. So these tests pin the labelling as
hard as the arithmetic: that the panel is an illustration, that the panel size
is a placeholder, that no composite is emitted, that extrapolation is reported,
that the protein is preserved on every member, and that the Pareto front really
is non-dominated.
"""
import glob
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNS = sorted(glob.glob(str(ROOT / "results/design_workflow_runs/*/summary.json")))


def _complete_runs():
    complete = []
    for path in RUNS:
        payload = json.loads(Path(path).read_text())
        if "selection" in payload:
            complete.append(path)
    return complete


COMPLETE = _complete_runs()
pytestmark = pytest.mark.skipif(not COMPLETE, reason="no complete design workflow run")


@pytest.fixture(scope="module")
def run():
    return json.loads(Path(COMPLETE[-1]).read_text())


@pytest.fixture(scope="module")
def members():
    return json.loads((Path(COMPLETE[-1]).parent / "scored_members.json").read_text())


def test_the_run_is_authorized_by_the_gate_that_opened_the_switches(run):
    assert run["gate"] == "configs/stage2_to_stage3_gate_v6_2026-10-20.json"
    import hashlib
    assert hashlib.sha256((ROOT / run["gate"]).read_bytes()).hexdigest() == run["gate_sha256"]
    gate = json.loads((ROOT / run["gate"]).read_text())
    for name in ("new_sequence_scoring_enabled", "expression_candidate_design_enabled"):
        assert gate["switches_opened_here"][name]["now"] is True


def test_every_member_is_a_verified_synonymous_variant(run, members):
    assert run["assembly"]["synonymy_verified_on_every_member"] is True
    proteins = {member["protein_sha256"] for member in members}
    lengths = {member["transcript_length_nt"] for member in members}
    references = {member["reference_cds_sha256_dna_uppercase"] for member in members}
    assert len(proteins) == 1
    assert len(lengths) == 1
    assert len(references) == 1, "every member must derive from the same reference"


def test_member_zero_is_the_reference_construct(members):
    first = next(member for member in members if member["member"] == 0)
    assert first["is_reference"] is True
    assert first["substitution_count"] == 0


def test_the_variants_are_unique(members):
    hashes = [member["orf_sha256"] for member in members]
    assert len(set(hashes)) == len(hashes)


def test_no_composite_score_is_emitted_anywhere(run, members):
    assert run["selection"]["composite_score_emitted"] is False
    assert run["selection"]["objectives"] == [
        "predicted_in_solution_half_life_hours", "predicted_TE_A549"]
    assert run["selection"]["directions"] == ["maximize", "maximize"]
    for member in members:
        for banned in ("composite", "combined", "total_score", "overall"):
            assert not any(banned in key for key in member), banned


def test_both_objectives_are_present_on_every_selected_member(run, members):
    by_id = {member["member"]: member for member in members}
    for identifier in run["selection"]["pareto_front_members"] + \
            run["selection"]["panel_members"]:
        member = by_id[identifier]
        assert member["stability"]["predicted_in_solution_half_life_hours"] is not None
        assert member["translation"]["value"] is not None


def test_the_pareto_front_is_non_dominated(run, members):
    """Checked here rather than trusting the run's own list."""
    from rnastable.pareto import dominates

    by_id = {member["member"]: member for member in members}
    points = {}
    for member in members:
        if member.get("stability") and member.get("translation"):
            points[member["member"]] = (
                member["stability"]["predicted_in_solution_half_life_hours"],
                member["translation"]["value"])
    front = run["selection"]["pareto_front_members"]
    assert front
    for identifier in front:
        point = points[identifier]
        assert not any(dominates(other, point)
                       for key, other in points.items() if key != identifier)
        assert by_id[identifier]["member"] == identifier
    # And nothing outside the front is non-dominated.
    for identifier, point in points.items():
        if identifier in front:
            continue
        assert any(dominates(other, point)
                   for key, other in points.items() if key != identifier)


def test_the_panel_is_drawn_from_scored_members_and_is_the_requested_size(run):
    selection = run["selection"]
    assert selection["panel_members"]
    assert len(selection["panel_members"]) == min(
        selection["panel_size_requested"], selection["pareto_front_size"])
    assert len(set(selection["panel_members"])) == len(selection["panel_members"])


def test_the_panel_size_is_labelled_a_placeholder(run):
    assert run["selection"]["panel_size_is_a_placeholder"] is True
    text = " ".join(run["no_claim"])
    assert "panel size is a declared placeholder" in text
    assert "assay's capacity is unknown" in text


def test_the_panel_is_labelled_an_illustration_not_a_recommendation(run):
    text = " ".join(run["no_claim"])
    assert "ILLUSTRATES THE PIPELINE" in text
    assert "not a recommendation to synthesise or assay anything" in text
    assert "not known to beat the reference" in text


def test_the_reference_point_scope_is_limited_to_this_run(run):
    scope = run["selection"]["reference_point_scope"]
    assert "WITHIN this run only" in scope
    assert "No reference point exists on the real scales" in scope


def test_extrapolation_is_counted_and_reported_per_member(run, members):
    assert "extrapolating" in run["stability"]
    counted = sum(1 for member in members
                  if member.get("stability") and member["stability"]["extrapolating"])
    assert run["stability"]["extrapolating"] == counted
    for member in members:
        if member.get("stability"):
            assert "features_outside_training_range" in member["stability"]


def test_the_folding_settings_are_flagged_as_a_provisional_span_convention(run):
    assert "span policy provisional" in run["folding"]["settings_source"]
    text = " ".join(run["no_claim"])
    assert "base-pair span policy is unresolved" in text
    assert "provisional convention, not a resolution" in text


def test_the_modification_and_quantity_mismatches_are_carried(run):
    text = " ".join(run["no_claim"])
    assert "N1-methylpseudouridine" in text
    assert "in-solution half-life in buffer" in text
    assert "in-cell decay by RT-qPCR" in text
    assert "different quantities" in text


def test_the_absence_of_measurement_is_stated_first(run):
    assert "PREDICTION from an unvalidated model" in run["no_claim"][0]
    assert "No construct in this project has been measured" in run["no_claim"][0]


def test_the_gate_prohibitions_are_carried_into_the_artifact(run):
    gate = json.loads((ROOT / run["gate"]).read_text())
    assert run["what_must_not_be_claimed"] == gate["what_must_not_be_claimed"]


def test_the_bo_replay_is_labelled_as_a_counterfactual(run):
    meaning = run["bo_replay_meaning"]
    assert "scored exhaustively" in meaning
    assert "Bayesian optimisation is not needed to find it" in meaning
    if run["bo_replay"]:
        replay = run["bo_replay"]
        assert replay["budget"] <= run["selection"]["complete_members"]
        assert replay["true_front_size"] == run["selection"]["pareto_front_size"]
        assert len(set(replay["selected_members"])) == len(replay["selected_members"])
        assert len(replay["random_members"]) == replay["budget"]


def test_the_design_representation_is_the_edit_pattern(run):
    representation = run["design_feature_representation"]
    assert representation["coordinates"] == len(representation["positions"])
    assert "1.0 if that window codon is substituted" in representation["encoding"]
    assert "would hide which positions changed" in representation["why"]


def test_poly_a_was_not_included(run):
    """The tail is thermodynamically inert and moves strand_alo by dilution."""
    assert run["assembly"]["poly_a_included"] is False


def test_the_run_links_its_design_space_and_formulation(run):
    for key in ("design_space", "formulation", "gate"):
        assert (ROOT / run[key]).exists(), key
