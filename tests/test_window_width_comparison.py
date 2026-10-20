"""Tests for the window-width spread comparison.

Design-space v2 widened the window on the strength of a falsifiable
expectation. A comparison made to check one's own change is the easiest place
to accidentally guarantee the answer, so these tests pin that the two runs are
matched on everything except the window, that the verdict is computed from the
numbers rather than asserted, that spread is reported more than one way, and
that a wider spread is not described as evidence the predictions are right.
"""
import glob
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNS = sorted(glob.glob(str(ROOT / "results/window_width_comparison_runs/*/summary.json")))

pytestmark = pytest.mark.skipif(not RUNS, reason="comparison not run")


@pytest.fixture(scope="module")
def comparison():
    return json.loads(Path(RUNS[-1]).read_text())


def test_the_runs_are_matched_on_everything_but_the_window(comparison):
    narrow, wide = comparison["narrow"], comparison["wide"]
    for key in ("gc_mode", "pool_size", "seed", "transcript_length_nt"):
        assert narrow[key] == wide[key], key
    assert narrow["window_codons"] < wide["window_codons"]
    assert "window width" in comparison["deliberate_difference"]
    assert "gc_mode" in comparison["matched_on"]


def test_the_two_windows_are_the_ones_the_specs_declare(comparison):
    assert comparison["narrow"]["window_codons"] == 30
    assert comparison["wide"]["window_codons"] == 50
    assert comparison["narrow"]["window_nt"] == 90
    assert comparison["wide"]["window_nt"] == 150
    assert "v1" in comparison["narrow"]["design_space"]
    assert "v2" in comparison["wide"]["design_space"]


def test_both_design_space_configs_exist(comparison):
    for side in ("narrow", "wide"):
        assert (ROOT / comparison[side]["design_space"]).exists()
        assert (ROOT / comparison[side]["run"] / "summary.json").exists()


def test_spread_is_reported_more_than_one_way(comparison):
    """A range is set by two members; stdev and IQR are not."""
    for side in ("narrow", "wide"):
        for quantity in ("half_life_hours", "translation", "substitution_count"):
            stats = comparison[side][quantity]
            for key in ("min", "max", "range", "stdev", "iqr", "median", "n"):
                assert stats[key] is not None, (side, quantity, key)
            assert stats["max"] >= stats["min"]
            assert stats["range"] == pytest.approx(stats["max"] - stats["min"])


def test_the_half_life_spread_is_normalised_against_the_training_range(comparison):
    for side in ("narrow", "wide"):
        stats = comparison[side]["half_life_hours"]
        low, high = comparison[side]["calibration_training_target_range_hours"]
        assert low < high
        assert stats["range_as_fraction_of_training_target_range"] == pytest.approx(
            stats["range"] / (high - low))


def test_the_verdict_follows_from_the_numbers(comparison):
    """The flag must not be able to disagree with the measurement."""
    expected = (comparison["comparison"]["half_life_stdev_ratio"] or 0) > 1.0
    assert comparison["expectation_held"] is expected


def test_every_ratio_is_wide_over_narrow(comparison):
    ratios = comparison["comparison"]
    pairs = (
        ("half_life_range_ratio", "half_life_hours", "range"),
        ("half_life_stdev_ratio", "half_life_hours", "stdev"),
        ("half_life_iqr_ratio", "half_life_hours", "iqr"),
        ("translation_range_ratio", "translation", "range"),
        ("translation_stdev_ratio", "translation", "stdev"),
    )
    for name, quantity, statistic in pairs:
        assert ratios[name] == pytest.approx(
            comparison["wide"][quantity][statistic]
            / comparison["narrow"][quantity][statistic]), name
    assert ratios["window_nt_ratio"] == pytest.approx(150 / 90)
    assert ratios["substitutable_position_ratio"] == pytest.approx(
        comparison["wide"]["substitutable_positions"]
        / comparison["narrow"]["substitutable_positions"])


def test_per_feature_spreads_are_reported_so_flatness_can_be_attributed(comparison):
    """A flat objective should name the feature that is not moving."""
    for side in ("narrow", "wide"):
        features = comparison[side]["features"]
        assert set(features) == {"energy_per_length", "GC", "aup"}
        for name, stats in features.items():
            assert stats["stdev"] is not None, name
    assert set(comparison["comparison"]["feature_stdev_ratio"]) == {
        "energy_per_length", "GC", "aup"}


def test_gc_is_held_constant_by_the_neutral_mode_in_both_runs(comparison):
    """The GC-neutral pool should show no GC variation to attribute anything to."""
    for side in ("narrow", "wide"):
        assert comparison[side]["gc_mode"] == "neutral"
        assert comparison[side]["features"]["GC"]["range"] == pytest.approx(0.0, abs=1e-9)


def test_both_runs_folded_every_member(comparison):
    for side in ("narrow", "wide"):
        assert comparison[side]["folds_ok"] == comparison[side]["pool_size"]
        assert comparison[side]["complete_members"] == comparison[side]["pool_size"]


def test_extrapolation_is_carried_for_both_runs(comparison):
    for side in ("narrow", "wide"):
        assert comparison[side]["extrapolating"] == comparison[side]["pool_size"]
    text = " ".join(comparison["no_claim"])
    assert "extrapolates on GC in both runs" in text


def test_a_wider_spread_is_not_called_evidence(comparison):
    text = " ".join(comparison["no_claim"])
    assert "NOT evidence that the predictions are right" in text
    assert "A spread is not an effect" in text
    assert "no molecule in this project has been measured" in text.lower()
    assert "judgement, not an output" in text


def test_the_expectation_under_test_is_stated(comparison):
    assert "wider window should widen the objective spread" in \
        comparison["expectation_under_test"]
