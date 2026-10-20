"""Tests for the window-width scaling fit.

The whole point of this analysis is that a two-point fit was tested against a
third run made afterwards. That only means something if the prediction really
was made from the earlier runs alone, so these tests pin that the held-out fit
excludes the widest width, that the runs are matched on everything else, that
the widest run is labelled a diagnostic rather than a design space, and that a
power law over three points is not described as more than that.
"""
import glob
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNS = sorted(glob.glob(str(ROOT / "results/window_scaling_runs/*/summary.json")))
DIAGNOSTIC = ROOT / "configs/whole_orf_window_diagnostic_v1_2026-10-20.json"

pytestmark = pytest.mark.skipif(not RUNS, reason="scaling fit not run")


@pytest.fixture(scope="module")
def fit():
    return json.loads(Path(RUNS[-1]).read_text())


@pytest.fixture(scope="module")
def diagnostic():
    return json.loads(DIAGNOSTIC.read_text())


def test_three_widths_are_present_in_increasing_order(fit):
    widths = [run["window_codons"] for run in fit["runs"]]
    assert widths == sorted(widths)
    assert widths == [30, 50, 549]


def test_the_runs_are_matched_on_everything_but_the_window(fit):
    for key in ("gc_mode", "pool_size", "seed"):
        assert len({run[key] for run in fit["runs"]}) == 1, key
    assert len({run["window_codons"] for run in fit["runs"]}) == 3


def test_every_run_scored_its_whole_pool(fit):
    for run in fit["runs"]:
        assert run["n"] == run["pool_size"]


def test_the_held_out_prediction_excludes_the_width_it_predicts(fit):
    """Otherwise the test would be fitting and scoring on the same points."""
    held = fit["held_out_prediction"]
    widths = [run["window_nt"] for run in fit["runs"]]
    assert held["fitted_on_widths_nt"] == widths[:-1]
    assert held["predicted_for_width_nt"] == widths[-1]
    assert held["predicted_for_width_nt"] not in held["fitted_on_widths_nt"]
    assert "can refute it" in held["basis"]


def test_the_held_out_prediction_arithmetic_is_reproducible(fit):
    held = fit["held_out_prediction"]
    expected = held["prefactor_used"] * held["predicted_for_width_nt"] ** held["exponent_used"]
    assert held["predicted_fraction_of_training_range"] == pytest.approx(expected)
    assert held["measured_over_predicted"] == pytest.approx(
        held["measured_fraction_of_training_range"]
        / held["predicted_fraction_of_training_range"])


def test_the_measured_value_matches_the_widest_run(fit):
    widest = fit["runs"][-1]
    assert fit["held_out_prediction"]["measured_fraction_of_training_range"] == pytest.approx(
        widest["half_life_range_fraction_of_training_range"])


def test_the_two_point_fit_has_no_r_squared_reported(fit):
    """With two points R-squared is 1 by construction and says nothing."""
    assert "r_squared" not in fit["held_out_prediction"]
    for key in ("half_life_stdev", "half_life_range_fraction"):
        assert fit["fit_all_widths"][key]["points"] == 3
        assert fit["fit_all_widths"][key]["r_squared"] is not None


def test_the_refit_exponents_are_sublinear(fit):
    """Sub-linear is the finding; linear or better would change the conclusion."""
    for key in ("half_life_stdev", "half_life_range_fraction"):
        exponent = fit["fit_all_widths"][key]["exponent"]
        assert 0.0 < exponent < 1.0, key


def test_the_spread_statistic_is_not_range_alone(fit):
    assert "standard deviation" in fit["spread_statistic"]
    assert "not range alone" in fit["spread_statistic"]
    for run in fit["runs"]:
        assert run["half_life_stdev"] > 0
        assert run["half_life_range"] >= run["half_life_stdev"]


def test_the_widest_window_is_recorded_as_the_axis_ceiling(fit):
    ceiling = fit["window_axis_ceiling"]
    assert ceiling["widest_window_codons"] == 549
    assert ceiling["widest_window_fraction_of_transcript"] > 0.9
    assert "widest window the constraints permit" in ceiling["note"]
    assert "not an arbitrary largest case" in ceiling["note"]


def test_the_measured_spread_at_the_ceiling_is_carried(fit):
    ceiling = fit["window_axis_ceiling"]
    assert ceiling["measured_fraction_of_training_range_at_the_ceiling"] == pytest.approx(
        fit["held_out_prediction"]["measured_fraction_of_training_range"])


def test_the_scaling_is_not_called_biology(fit):
    text = " ".join(fit["no_claim"])
    assert "spread of PREDICTIONS from an unvalidated model" in text
    assert "not biology" in text
    assert "description of three points" in text
    assert "judgement" in text


def test_the_widest_run_is_a_diagnostic_not_a_design_space(fit, diagnostic):
    status = diagnostic["status_relative_to_the_campaign_design_space"]
    assert status["is_the_campaign_domain"] is False
    assert "v2" in status["campaign_domain_remains"]
    assert "supersedes_nothing" in status
    assert "destroys regional attribution" in " ".join(fit["no_claim"])
    widest = fit["runs"][-1]
    assert "whole_orf_window_diagnostic" in widest["design_space"]


def test_the_diagnostic_records_the_campaign_domain_hash(diagnostic):
    import hashlib
    status = diagnostic["status_relative_to_the_campaign_design_space"]
    actual = hashlib.sha256((ROOT / status["campaign_domain_remains"]).read_bytes()).hexdigest()
    assert actual == status["campaign_domain_sha256"]


def test_the_diagnostic_states_both_outcomes_before_the_run(diagnostic):
    why = diagnostic["why_the_window_widened"]
    assert why["prediction_being_tested"]["half_life_range_as_fraction_of_training_range"] \
        == pytest.approx(0.078, abs=0.001)
    assert "does not establish an exponent" in why["prediction_being_tested"]["caveat"]
    assert "window width is exhausted as a lever" in why["what_a_confirmation_would_mean"]
    assert "scales faster" in why["what_a_refutation_would_mean"]
    assert "Either outcome is reported" in why["what_a_refutation_would_mean"]


def test_the_ceiling_leaves_the_objective_under_a_tenth_of_the_training_range(fit):
    """The decision-relevant number, pinned so a later edit cannot soften it."""
    measured = fit["held_out_prediction"]["measured_fraction_of_training_range"]
    assert measured < 0.10
    # And the two-point extrapolation was close rather than refuted.
    assert 0.8 < fit["held_out_prediction"]["measured_over_predicted"] < 1.3


def test_the_translation_side_is_reported_at_every_width(fit):
    """The 30 to 50 comparison showed no growth; three points show otherwise."""
    stdevs = [run["translation_stdev"] for run in fit["runs"]]
    assert all(value > 0 for value in stdevs)
    assert stdevs[-1] > stdevs[0], "the widest window must be reported, whatever it shows"
    # Not monotone: the middle width dipped, which is why two points misled.
    assert stdevs[1] < stdevs[0]


def test_the_bo_replay_numbers_are_carried_for_every_width(fit):
    for run in fit["runs"]:
        assert run["bo_front_found"] is not None
        assert run["bo_random_front_found"] is not None
        assert run["pareto_front_size"] >= run["bo_front_found"]


def test_log_fits_use_natural_logs_consistently(fit):
    """A base mix-up would change the exponent silently."""
    held = fit["held_out_prediction"]
    narrow, middle = fit["runs"][0], fit["runs"][1]
    expected = (math.log(middle["half_life_range_fraction_of_training_range"]
                         / narrow["half_life_range_fraction_of_training_range"])
                / math.log(middle["window_nt"] / narrow["window_nt"]))
    assert held["exponent_used"] == pytest.approx(expected)
