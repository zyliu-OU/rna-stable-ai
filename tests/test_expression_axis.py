"""Tests for the expression axis on the 24 unexposed CDS designs.

Two things need pinning here, for different reasons.

The source defect: the 'Sequence' column is exactly permuted against
'sequence_with_UTRs' for 5 of 24 rows, and because every design is synonymous
the permuted rows still translate to the right protein. A protein check passes
on all five. This project has already published one wrong number that came from
trusting a column's obvious reading, so the detection is pinned, not just the
workaround.

The result: the primary test falsified the stability route to expression, and
the frozen calibration posted its best correlation anywhere in this project on a
set it never saw. Both are easy to overstate later - the first by quietly
dropping it, the second by promoting an exploratory n=24 number to a claim. The
tests pin the falsification, the declared thresholds, and the caveats that
travel with the calibration result, including that its expression correlation
reverses sign between the two time points.
"""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/expression_axis_v1_2026-10-21.json"
RUNS = ROOT / "results/expression_axis_runs"
GATE_V16 = ROOT / "configs/stage2_to_stage3_gate_v16_2026-10-21.json"


@pytest.fixture(scope="module")
def declared():
    return json.loads(PROTOCOL.read_text())


@pytest.fixture(scope="module")
def run():
    runs = sorted(p for p in RUNS.glob("*/summary.json")) if RUNS.is_dir() else []
    if not runs:
        pytest.skip("no expression_axis run artifact in this checkout")
    return json.loads(runs[-1].read_text())


def test_the_protocol_declares_direction_and_threshold_before_the_result(declared):
    primary = declared["primary_confirmatory_test"]
    assert primary["declared_direction"].startswith("POSITIVE")
    assert "+0.30" in primary["falsification_of_the_stability_route"]
    # Both outcomes were written down in advance, not just the one that happened.
    assert primary["what_will_be_recorded_on_failure"]
    assert primary["what_will_be_recorded_on_success"]


def test_the_run_used_the_protocol_at_its_recorded_hash(run):
    assert run["protocol"]["sha256"] == hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    assert run["protocol"]["name"] == "expression_axis_v1"


def test_nothing_was_fitted_and_no_split_was_made(run, declared):
    assert run["nothing_was_fitted"] is True
    assert run["no_train_test_split_was_made"] is True
    assert "NOTHING is fitted" in declared["design_limits_declared_up_front"]["no_fit"]


def test_the_sequence_column_permutation_is_detected_not_bypassed(run):
    checks = run["integrity"]
    assert checks["authoritative_field"] == "sequence_with_UTRs"
    assert checks["sequence_column_used_for_features"] is False
    assert checks["sequence_column_mismatch_count"] == 5
    assert checks["permutation_resolves_every_mismatch"] is True
    mapping = checks["permutation_map_mismatched_row_to_holder_of_its_cds"]
    # A 2-cycle and a 3-cycle, as the protocol records.
    assert mapping["1220187B1"] == "1220188B1"
    assert mapping["1220188B1"] == "1220187B1"
    assert mapping["1220184B1"] == "1220186B1"
    assert mapping["1220186B1"] == "1220185B1"
    assert mapping["1220185B1"] == "1220184B1"


def test_a_protein_check_cannot_catch_the_permutation(run):
    """Why the defect is dangerous: every bad row still encodes the right protein."""
    checks = run["integrity"]
    assert checks["protein_identical_across_all_rows"] is True
    assert checks["distinct_proteins"] == 1
    assert checks["protein_length_aa"] == 207
    assert "synonymous" in checks["note_on_why_a_protein_check_misses_this"]


def test_the_set_is_length_constant_and_utr_constant(run):
    checks = run["integrity"]
    assert checks["all_full_length_equal"] is True
    assert checks["constant_utr5_len"] == 53
    assert checks["constant_utr3_len"] == 209
    # Which is exactly why the screen's best feature cannot be tested here.
    assert checks["utr_features_have_zero_variance"] is True


def test_utr_features_are_declared_untestable_on_this_set(declared):
    limit = declared["design_limits_declared_up_front"]["utr_features_untestable"]
    assert "utr5_frac_C" in limit and "zero variance" in limit


def test_the_stability_route_to_expression_is_falsified(run):
    primary = run["primary_confirmatory_test"]
    assert primary["declared_direction"] == "POSITIVE"
    assert primary["declared_threshold"] == 0.30
    assert primary["stability_route_falsified"] is True
    assert primary["spearman_vs_expression_24h"] < 0.30
    assert primary["falsification_reasons"], "a falsification must record its reasons"


def test_the_family_sign_reversal_is_recorded(run):
    """The same failure mode measured ribosome load showed, now on expression."""
    families = run["family_stratified_primary_E5"]
    signs = [v["vs_expression_24h"] for v in families.values()
             if v["vs_expression_24h"] is not None]
    assert len(signs) >= 2
    assert any(s > 0 for s in signs) and any(s < 0 for s in signs)
    assert any("sign reverses across design families" in reason
               for reason in run["primary_confirmatory_test"]["falsification_reasons"])


def test_the_calibration_result_is_exploratory_and_keeps_its_caveat(run, declared):
    e1 = run["exploratory"]["E1_frozen_calibration_on_an_unexposed_set"]
    assert e1["declared_direction"] == "POSITIVE"
    assert e1["constructs"] == 24
    assert e1["vs_half_life"] > 0.30
    # The caveat that stops this becoming an expression claim: the sign of the
    # expression correlation is not stable across the two time points.
    assert e1["vs_expression_6h"] < 0 < e1["vs_expression_24h"]
    # And the protocol declared in advance that only the primary is confirmatory.
    assert "exploratory" in declared["design_limits_declared_up_front"]["multiplicity"]
    assert any(entry["id"] == "E1_frozen_calibration_on_an_unexposed_set"
               for entry in declared["exploratory_measurements_declared"])


def test_the_set_really_was_unexposed_and_in_domain(run, declared):
    assert "Zero of the 24" in declared["why_this_construct_set_is_unusually_clean"]["unexposed"]
    # If most constructs were extrapolations the calibration number would mean less.
    assert run["extrapolation"]["constructs_outside_the_calibration_training_range"] <= 2


def test_the_cds_structure_signal_holds_its_declared_direction(run):
    for key in ("E3_cds_aup", "E3_cds_energy_per_nt"):
        entry = run["exploratory"][key]
        assert entry["declared_direction"] == "NEGATIVE"
        assert entry["vs_half_life"] < 0
        assert entry["vs_expression_24h"] < 0


def test_the_measured_cv_replaces_the_planning_bound(run):
    for label in ("6h", "24h"):
        error = run["measurement_error"][label]
        assert error["constructs"] == 24
        assert error["replicates_per_construct"] == [4]
        assert error["planning_bound_in_assay_definition_v3_and_v4"] == 0.20
        assert error["measured_cv_is_below_the_planning_bound"] is True
        assert error["measured_cv"]["median"] < 0.20
        # The 1.5x target was NOT detectable at the assumed bound; it is here.
        assert error["target_is_detectable_at_this_cv_and_n"] is True
        assert error["minimum_detectable_fold_change_at_measured_cv"] < 1.5
        assert error["pairs"] == 276
        assert error["resolvable_pairs"] + error["unresolvable_pairs"] == 276


def test_no_floor_is_frozen_by_this_protocol(declared):
    analysis = declared["measurement_error_analysis_declared"]
    assert "no floor is frozen" in analysis["limit"]
    assert "not the user's lab" in analysis["limit"]


def test_the_protocol_forbids_revision_after_seeing_a_number(declared):
    assert any("Do not revise this protocol after seeing a number" in rule
               for rule in declared["prohibitions_for_this_run"])


def test_this_run_confirms_rather_than_contradicts_gate_v16(run):
    """Gate v16 prohibited the stability-as-expression-proxy claim on 6 constructs.

    The primary test here falsifies the route on 24, so the prohibition is
    strengthened, not withdrawn. If a later change made this run support the
    route instead, this test should fail and force the gate to be revisited.
    """
    gate = json.loads(GATE_V16.read_text())
    proxy = next(entry for entry in gate["prohibitions_added_here"]
                 if entry["id"] == "v16_5_stability_is_not_a_validated_expression_proxy")
    assert "must not be presented as a validated proxy" in proxy["prohibition"].lower()
    assert run["primary_confirmatory_test"]["stability_route_falsified"] is True


def test_gate_v17_corrects_the_label_count_without_editing_v16():
    """v16 said 6 constructs carry measured protein output. It is 24."""
    v17 = json.loads((ROOT / "configs/stage2_to_stage3_gate_v17_2026-10-21.json").read_text())
    correction = v17["correction_to_v16"]
    assert hashlib.sha256(GATE_V16.read_bytes()).hexdigest() == v17["supersedes"]["sha256"]
    assert v17["supersedes"]["status"] == "frozen and unedited"
    assert "24 constructs carry measured protein output" in correction["corrected_value"]
    assert "frozen and unedited" in correction["status_of_v16"]
    # The 13-fold evidence about the 6 PAIRED constructs is a different thing and stands.
    assert "stands unaltered" in correction["scope"]


def test_gate_v17_strengthens_rather_than_withdraws(run):
    v17 = json.loads((ROOT / "configs/stage2_to_stage3_gate_v17_2026-10-21.json").read_text())
    assert v17["prohibition_withdrawn_here"] is None
    assert v17["requirements_satisfied"] == 6
    assert v17["switches_unchanged_from_v6"]["expression_benefit_established"] is False
    assert v17["switches_unchanged_from_v16"]["cell_free_scoring_enabled"] is False
    assert len(v17["prohibitions_strengthened_here"]) == 2
    assert v17["prohibition_added_here"]["id"] == "v17_1_no_single_axis_may_stand_in_for_expression"
    # The gate must carry the run's actual primary number, not a rounded retelling.
    measured = v17["expression_axis_measured_here"]["primary_confirmatory_result"]
    assert measured["measured_spearman_vs_24h_expression"] == pytest.approx(
        run["primary_confirmatory_test"]["spearman_vs_expression_24h"])
    assert measured["verdict"] == "FALSIFIED"


def test_assay_v5_corrects_the_count_and_records_the_measured_cv(run):
    v5 = json.loads((ROOT / "configs/assay_definition_v5_2026-10-21.json").read_text())
    v4 = ROOT / "configs/assay_definition_v4_2026-10-21.json"
    assert hashlib.sha256(v4.read_bytes()).hexdigest() == v5["supersedes"]["v4"]["sha256"]
    assert "24 constructs with measured protein output" in v5[
        "decisions_recorded_2026_10_21"][
        "goal_is_expression_stability_is_the_modeled_axis"]["why_stability_is_the_modeled_axis"]
    error = v5["measured_assay_error"]
    assert error["replicates"] == 4
    assert error["target_detectable"] is True
    assert error["floors_still_not_frozen"] is True
    assert v5["floors_frozen"] is False
    assert error["median_cv"]["24h"] == pytest.approx(
        run["measurement_error"]["24h"]["measured_cv"]["median"], abs=1e-4)
