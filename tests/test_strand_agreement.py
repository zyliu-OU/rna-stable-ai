"""Unit tests for the frozen STRAND/RNAfold engine-agreement logic."""
import json
import math
from pathlib import Path

import pytest

from rnastable.strand_agreement import (
    alo_transform, decide, feature_deltas, feature_tolerances, output_differences,
    quantile, released_decimals, rounding_half_widths, select_cell,
    substituted_features, summarize,
)
from rnastable.strand_reference import FEATURE_ORDER

ROOT = Path(__file__).resolve().parents[1]
CRITERION = ROOT/"configs/strand_rnafold_agreement_criterion_v1_2026-10-19.json"


def test_criterion_is_closed_and_gated():
    criterion = json.loads(CRITERION.read_text())
    assert criterion["hypothesis_grid"]["closed"] is True
    assert criterion["new_sequence_scoring_enabled"] is False
    assert criterion["expression_candidate_design_enabled"] is False
    assert criterion["stage3_ready"] is False
    assert len(criterion["cohort_split"]["selection_set"]) == 6


def test_identity_transform_preserves_values():
    values = [0.0, 1e-12, 0.5, 1.0]
    assert alo_transform("identity")(values) == values


def test_floor_zeroes_only_below_threshold():
    out = alo_transform("floor_0.001")([0.0, 0.0005, 0.001, 0.9999, 1.0])
    assert out == [0.0, 0.0, 0.001, 0.9999, 1.0]


def test_two_sided_saturates_both_ends():
    out = alo_transform("two_sided_0.001")([0.0005, 0.5, 0.9995, 1.0])
    assert out == [0.0, 0.5, 1.0, 1.0]


@pytest.mark.parametrize("name", ["floor_0", "two_sided_0.9", "beam_0.01", "floor_x"])
def test_unknown_transforms_rejected(name):
    with pytest.raises(ValueError):
        alo_transform(name)


def test_released_decimals_counts_fractional_digits():
    assert released_decimals("52.04741379") == 8
    assert released_decimals("57.04") == 2
    assert released_decimals("60") == 0


def test_rounding_half_width_scales_energy_by_length():
    widths = rounding_half_widths({"energy": "-387.6", "GC": "57.04", "aup": "0.34"}, 1000)
    assert widths["energy_per_length"] == pytest.approx(0.05/1000)
    assert widths["GC"] == pytest.approx(0.005)
    assert widths["aup"] == pytest.approx(0.005)
    assert widths["alo"] == 0.0


def test_rounding_half_width_requires_positive_length():
    with pytest.raises(ValueError):
        rounding_half_widths({"energy": "-1.0", "GC": "50.0", "aup": "0.3"}, 0)


def test_quantile_interpolates_linearly():
    assert quantile([0.0, 1.0, 2.0, 3.0], 0.5) == pytest.approx(1.5)
    assert quantile([0.0, 1.0, 2.0, 3.0], 0.25) == pytest.approx(0.75)
    assert quantile([5.0], 0.95) == 5.0


def test_feature_tolerances_are_interquartile_fractions():
    records = [{"features": {name: float(i) for name in FEATURE_ORDER}} for i in range(5)]
    tolerances = feature_tolerances(records, 0.05)
    assert all(t == pytest.approx(0.05*2.0) for t in tolerances.values())


def test_degenerate_spread_is_rejected():
    records = [{"features": {name: 1.0 for name in FEATURE_ORDER}} for _ in range(4)]
    with pytest.raises(ValueError):
        feature_tolerances(records, 0.05)


def fake_folding(paired, mfe_per_nt=-0.4, ensemble_per_nt=-0.41, gc_fraction=0.52):
    return {"paired_probability_per_position": paired,
            "feature_candidates": {"mfe_energy_per_nt": mfe_per_nt,
                                   "ensemble_energy_per_nt": ensemble_per_nt,
                                   "gc_fraction": gc_fraction,
                                   "aup": 1-sum(paired)/len(paired),
                                   "alo": 0.0}}


def test_substituted_features_convert_gc_to_percent_and_honour_energy_choice():
    folding = fake_folding([0.3, 0.4, 0.5])
    mfe = substituted_features(folding, "mfe_energy_per_nt", "identity")
    ensemble = substituted_features(folding, "ensemble_energy_per_nt", "identity")
    assert mfe["GC"] == pytest.approx(52.0)
    assert mfe["energy_per_length"] == pytest.approx(-0.4)
    assert ensemble["energy_per_length"] == pytest.approx(-0.41)
    assert set(mfe) == set(FEATURE_ORDER)


def test_transform_changes_alo_but_not_aup():
    folding = fake_folding([1e-8, 0.5, 0.9])
    plain = substituted_features(folding, "ensemble_energy_per_nt", "identity")
    floored = substituted_features(folding, "ensemble_energy_per_nt", "floor_0.001")
    assert floored["aup"] == pytest.approx(plain["aup"])
    assert floored["alo"] < plain["alo"]


def test_unknown_energy_hypothesis_rejected():
    with pytest.raises(ValueError):
        substituted_features(fake_folding([0.5]), "ensemble_energy", "identity")


def test_feature_deltas_subtract_rounding_half_width():
    reference = {name: 0.0 for name in FEATURE_ORDER}
    substituted = {name: 0.004 for name in FEATURE_ORDER}
    widths = {"energy_per_length": 0.0, "GC": 0.005, "aup": 0.005, "alo": 0.0}
    deltas = feature_deltas(reference, substituted, widths)
    assert deltas["GC"]["excess_over_rounding"] == 0.0
    assert deltas["alo"]["excess_over_rounding"] == pytest.approx(0.004)
    assert deltas["alo"]["delta"] == pytest.approx(0.004)


def test_feature_deltas_require_full_feature_set():
    with pytest.raises(ValueError):
        feature_deltas({"GC": 1.0}, {name: 1.0 for name in FEATURE_ORDER},
                       {name: 0.0 for name in FEATURE_ORDER})


def test_selection_minimizes_worst_selection_set_difference():
    rows = [{"energy": {"mfe_energy_per_nt": 0.02, "ensemble_energy_per_nt": 1e-6},
             "alo": {"identity": 0.3, "floor_0.001": 0.01, "two_sided_0.001": 0.02}},
            {"energy": {"mfe_energy_per_nt": 0.01, "ensemble_energy_per_nt": 2e-6},
             "alo": {"identity": 0.2, "floor_0.001": 0.05, "two_sided_0.001": 0.01}}]
    chosen = select_cell(rows, ["mfe_energy_per_nt", "ensemble_energy_per_nt"],
                         ["identity", "floor_0.001", "two_sided_0.001"])
    # Worst-case over rows: identity 0.3, floor_0.001 0.05, two_sided_0.001 0.02.
    assert chosen == {"energy_hypothesis": "ensemble_energy_per_nt", "alo_transform": "two_sided_0.001"}


def test_selection_prefers_identity_on_ties():
    rows = [{"energy": {"ensemble_energy_per_nt": 1.0},
             "alo": {"identity": 0.1, "floor_0.001": 0.1}}]
    chosen = select_cell(rows, ["ensemble_energy_per_nt"], ["identity", "floor_0.001"])
    assert chosen["alo_transform"] == "identity"


def test_selection_requires_rows():
    with pytest.raises(ValueError):
        select_cell([], ["ensemble_energy_per_nt"], ["identity"])


def test_summarize_passes_only_within_tolerance():
    deltas = [{name: {"excess_over_rounding": 0.01} for name in FEATURE_ORDER},
              {name: {"excess_over_rounding": 0.03} for name in FEATURE_ORDER}]
    tolerances = {name: 0.02 for name in FEATURE_ORDER}
    summary = summarize(deltas, tolerances)
    assert summary["alo"]["max_excess"] == pytest.approx(0.03)
    assert summary["alo"]["passes"] is False
    assert summary["alo"]["n"] == 2
    summary_ok = summarize(deltas, {name: 0.05 for name in FEATURE_ORDER})
    assert all(summary_ok[name]["passes"] for name in FEATURE_ORDER)


COMPONENT = {"feature_order": FEATURE_ORDER, "intercept": 0.0,
             "coefficients": {"energy_per_length": 1.0, "GC": 0.0, "aup": 0.0, "alo": 0.5}}


def test_output_differences_report_substitution_shift():
    reference = {"energy_per_length": -0.4, "GC": 50.0, "aup": 0.3, "alo": 1.0}
    substituted = dict(reference, alo=1.2)
    diff = output_differences(COMPONENT, reference, substituted, None)
    assert diff["difference_hours"] == pytest.approx(0.1)
    assert diff["frozen_replay_consistent"] is True


def test_output_differences_flag_frozen_replay_drift():
    reference = {"energy_per_length": -0.4, "GC": 50.0, "aup": 0.3, "alo": 1.0}
    diff = output_differences(COMPONENT, reference, reference, 99.0)
    assert diff["frozen_replay_consistent"] is False
    assert diff["difference_hours"] == 0.0


def test_decide_requires_every_feature_for_unchanged_model():
    passing = {name: {"passes": True} for name in FEATURE_ORDER}
    failing = dict(passing, alo={"passes": False})
    both = decide(passing, 0.001, 0.01)
    assert both["outcome"] == "feature_level_compatible"
    assert both["unchanged_published_strand_applicable"] is True
    output_only = decide(failing, 0.001, 0.01)
    assert output_only["outcome"] == "output_level_equivalent_separately_named_calibration_required"
    assert output_only["unchanged_published_strand_applicable"] is False
    rejected = decide(failing, 1.0, 0.01)
    assert rejected["outcome"] == "rejected"
    for result in (both, output_only, rejected):
        assert result["new_sequence_scoring_enabled"] is False
        assert result["stage3_ready"] is False


def test_log_odds_saturation_drives_alo_gap():
    """A single zeroed position moves ALO by log-odds(1e-10)/n, the suspected mechanism."""
    from rnastable.component_integration import strand_alo
    base = [0.5]*100
    zeroed = [0.0]+[0.5]*99
    shift = strand_alo(zeroed)-strand_alo(base)
    assert shift == pytest.approx(math.log(1e-10/(1-1e-10))/100, rel=1e-9)
