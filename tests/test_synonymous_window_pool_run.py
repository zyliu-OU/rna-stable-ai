"""Tests for the design-space specification and the enumerated pools.

A design space is where unstated assumptions become permanent, so these pin
that the declared choices are labelled as choices rather than findings, that the
measured GC confound is recorded rather than glossed, that the pools are not
scored and not proposed as candidates, and that the specification does not open
a gate switch.
"""
import glob
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "configs/synonymous_window_design_space_v1_2026-10-20.json"
RUNS = sorted(glob.glob(str(ROOT / "results/synonymous_window_pool_runs/*/summary.json")))


@pytest.fixture(scope="module")
def spec():
    return json.loads(SPEC.read_text())


@pytest.fixture(scope="module")
def run():
    if not RUNS:
        pytest.skip("pool not built")
    return json.loads(Path(RUNS[-1]).read_text())


@pytest.fixture(scope="module")
def pools(run):
    directory = Path(RUNS[-1]).parent
    return {mode: json.loads((directory / f"pool_{mode}.json").read_text())
            for mode in ("free", "neutral")}


def test_the_window_and_region_are_labelled_as_declared_choices(spec):
    assert "NOTHING IN THIS PROJECT ESTABLISHES IT" in spec["why_a_window"]["region_choice"]
    assert "declared, not derived" in spec["window"]["window_size_is_a_declared_choice"]
    text = " ".join(spec["no_claim"])
    assert "declared choices, not findings" in text


def test_the_start_and_stop_exclusions_are_justified(spec):
    assert "its own only synonym" in spec["window"]["start_codon_excluded"]
    assert "tandem-stop" in spec["window"]["terminator_excluded"]


def test_the_homopolymer_bound_is_justified_rather_than_arbitrary(spec):
    assert spec["constraints"]["max_homopolymer_run"] == 6
    why = spec["constraints"]["why_six"]
    assert "longest homopolymer run is exactly 6" in why
    assert "not a literature threshold" in why


def test_failures_are_discarded_rather_than_repaired(spec):
    assert "rejected and counted by cause" in \
        spec["constraints"]["failures_are_discarded_not_repaired"]


def test_the_constraints_deliberately_left_out_are_named(spec):
    text = " ".join(spec["not_constrained_deliberately"])
    assert "Restriction sites" in text
    assert "Out-of-frame AUG" in text
    assert "Local secondary structure" in text


def test_the_spec_explains_why_sampling_is_not_per_position(spec):
    why = spec["sampling"]["why_not_per_position_independent"]
    assert "concentrates every member" in why
    assert "nothing near the reference" in why


def test_both_gc_modes_are_specified_with_their_costs(spec):
    modes = spec["gc_modes"]
    assert "-0.8777" in modes["free"]["measured_confound"]
    assert "GC-maximal" in modes["free"]["why_it_cannot_be_removed_by_sampling"]
    assert "cannot be separated" in modes["free"]["consequence"]
    assert "EXACTLY constant" in modes["neutral"]["effect"]
    assert "10^3.9" in modes["neutral"]["cost"]
    assert modes["which_is_primary"].startswith("NOT DECIDED")


def test_the_spec_does_not_open_a_gate_switch(spec):
    unchanged = spec["does_not_change"]
    assert unchanged["new_sequence_scoring_enabled"] is False
    assert unchanged["expression_candidate_design_enabled"] is False
    gate = json.loads(
        (ROOT / "configs/stage2_to_stage3_gate_v5_2026-10-20.json").read_text())
    assert gate["new_sequence_scoring_enabled"] is False
    assert gate["expression_candidate_design_enabled"] is False


def test_what_scoring_would_require_is_stated(spec):
    text = " ".join(spec["what_scoring_the_pool_would_require"])
    assert "span policy" in text
    assert "hash-gated" in text
    assert "reference point" in text


def test_the_run_verified_every_member(run):
    assert run["all_members_verified"] is True
    assert all(not failures for failures in run["verification_failures"].values())
    assert run["protein_preserved_on_every_member"] is True


def test_the_run_is_unscored_and_proposes_nothing(run):
    assert run["scored"] is False
    assert run["optimizer_features_emitted"] is False
    assert run["candidates_proposed_for_assay"] is False
    text = " ".join(run["no_claim"])
    assert "No member was scored, ranked or proposed for an assay" in text


def test_the_run_records_the_measured_confound(run):
    confound = run["gc_confound"]
    assert confound["free_mode_pearson_substitutions_vs_window_gc"] < -0.5
    assert confound["neutral_mode_window_gc_is_constant"] is True
    assert "not a sampler artifact" in confound["why"]
    assert "cannot be separated" in confound["consequence"]


def test_both_modes_were_built_and_differ_as_specified(run):
    free, neutral = run["per_mode"]["free"], run["per_mode"]["neutral"]
    assert free["window_gc_is_constant"] is False
    assert neutral["window_gc_is_constant"] is True
    assert neutral["substitutable_positions"] < free["substitutable_positions"]
    for mode in (free, neutral):
        assert mode["unique_members"] == mode["size"]
        assert mode["substitution_count_range"][0] == 0


def test_the_window_matches_the_specification(run, spec):
    assert run["window_codons"] == spec["window"]["codons"]
    assert run["window_codon_indices"][0] == 1
    assert len(run["window_codon_indices"]) == spec["window"]["codons"]
    assert run["codon_count"] == spec["reference"]["codon_count"]
    assert run["orf_length_nt"] == spec["reference"]["orf_length_nt"]


def test_the_written_pools_preserve_the_protein(pools):
    from rnastable.synonymous_window import split_codons, translate

    for mode, pool in pools.items():
        members = pool["members"]
        reference = next(m for m in members if m["is_reference"])
        protein = translate(split_codons(reference["orf"]))
        for member in members:
            assert translate(split_codons(member["orf"])) == protein, mode


def test_the_written_pools_carry_no_score_fields(pools):
    for mode, pool in pools.items():
        for member in pool["members"]:
            for banned in ("score", "objective", "predicted", "rank"):
                assert not any(banned in key for key in member), (mode, banned)


def test_the_written_pool_hashes_match_their_sequences(pools):
    import hashlib

    for mode, pool in pools.items():
        for member in pool["members"]:
            assert member["orf_sha256"] == hashlib.sha256(
                member["orf"].encode()).hexdigest(), mode


def test_the_run_links_its_specification_the_formulation_and_the_gate(run):
    for key in ("specification", "formulation", "gate"):
        assert (ROOT / run[key]).exists(), key
    assert "synonymous_window_design_space_v1" in run["specification"]
    assert "pareto_objective_formulation_v1" in run["formulation"]
