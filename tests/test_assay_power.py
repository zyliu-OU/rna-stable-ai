"""Tests for the assay power arithmetic.

The first group pins every numerical power claim recorded in the frozen
assay_definition_v3 config, so that config stops being an unreplayable
assertion. The second group records that the exact log-normal convention gives
strictly less favourable figures than the ones frozen there.
"""
import json
import math
from pathlib import Path

import pytest

from rnastable.assay_power import (
    DESIGNS,
    DISPERSION_CONVENTIONS,
    assess,
    log_scale_sd,
    minimum_detectable_fold_change,
    power,
    required_replicates,
)

CONFIG = Path(__file__).resolve().parents[1] / "configs" / "assay_definition_v3_2026-10-19.json"
# The convention under which the frozen figures were produced; see the module
# docstring. Tests that replay those figures must use it, not the exact one.
FROZEN = "log1p_cv"


def recorded():
    return json.loads(CONFIG.read_text())["assay"]["measurement_error"]["power_consequence"]


def test_frozen_config_power_at_n3_replays_for_every_recorded_cv():
    """The three per-CV power figures in the frozen config are reproducible."""
    for key, expected in recorded()["power_at_n3"].items():
        cv = int(key.removeprefix("cv_")) / 100.0
        assert power(cv, 3, 1.5, FROZEN) == pytest.approx(expected, abs=5e-4)


def test_frozen_config_required_replicates_replays():
    assert required_replicates(0.20, 1.5, FROZEN) == recorded()["required_n_at_cv_20_for_80pct"]


def test_frozen_config_minimum_detectable_effect_replays():
    """The config's 1.75-fold MDE at n=3 and CV 20 percent is reproducible."""
    assert minimum_detectable_fold_change(0.20, 3, FROZEN) == pytest.approx(1.75, abs=5e-3)


def test_frozen_config_paired_alternative_replays():
    """Six paired units at CV 20 percent reach the recorded 98.9 percent."""
    assert power(0.20, 6, 1.5, FROZEN, design="paired_one_sample") == pytest.approx(0.989, abs=5e-4)


def test_recorded_design_is_underpowered_for_its_own_target():
    """The central finding already in the config: n=3 at CV 20 percent fails twice over."""
    result = assess(0.20, 3, 1.5, FROZEN)
    assert result.power_at_target < 0.80
    assert result.minimum_detectable_fold_change > 1.5
    assert result.target_reachable_at_this_size is False


def test_exact_convention_is_strictly_less_favourable_than_the_frozen_one():
    """The frozen figures are optimistic; the exact log-normal sd lowers them all."""
    for cv in (0.10, 0.15, 0.20):
        assert log_scale_sd(cv, "lognormal_exact") > log_scale_sd(cv, FROZEN)
        assert power(cv, 3, 1.5, "lognormal_exact") < power(cv, 3, 1.5, FROZEN)
    assert minimum_detectable_fold_change(0.20, 3, "lognormal_exact") > minimum_detectable_fold_change(0.20, 3, FROZEN)


def test_required_replicates_at_cv20_is_robust_to_the_convention():
    """n=5 survives the convention change, so that specific claim needs no revision."""
    assert required_replicates(0.20, 1.5, "lognormal_exact") == required_replicates(0.20, 1.5, FROZEN) == 5


def test_conventions_converge_as_cv_shrinks():
    """Both conventions approximate CV to first order, so they agree in the limit."""
    gaps = [abs(log_scale_sd(cv, "lognormal_exact") - log_scale_sd(cv, FROZEN))
            for cv in (0.20, 0.05, 0.01)]
    assert gaps == sorted(gaps, reverse=True)
    assert gaps[-1] < 1e-3


def test_power_rises_with_replicates_and_with_effect_size():
    assert (power(0.20, 3, 1.5, FROZEN) < power(0.20, 4, 1.5, FROZEN)
            < power(0.20, 8, 1.5, FROZEN))
    assert power(0.20, 3, 1.2, FROZEN) < power(0.20, 3, 1.5, FROZEN) < power(0.20, 3, 3.0, FROZEN)


def test_power_falls_as_dispersion_grows():
    assert power(0.05, 3, 1.5, FROZEN) > power(0.20, 3, 1.5, FROZEN) > power(0.60, 3, 1.5, FROZEN)


def test_pairing_beats_unpaired_at_equal_n():
    """Pairing is the cheapest of the remedies the config lists, at equal n."""
    assert (power(0.20, 6, 1.5, FROZEN, design="paired_one_sample")
            > power(0.20, 6, 1.5, FROZEN, design="unpaired_two_sample"))


def test_reduction_and_enhancement_of_the_same_ratio_are_equally_powered():
    """The test is two-sided, so a 1/1.5-fold drop is as detectable as a 1.5-fold rise."""
    assert power(0.20, 3, 1.5, FROZEN) == pytest.approx(power(0.20, 3, 1 / 1.5, FROZEN))


def test_minimum_detectable_effect_is_the_fold_change_at_exactly_target_power():
    """MDE and power are mutual inverses, which is what makes the MDE reportable."""
    mde = minimum_detectable_fold_change(0.20, 4, FROZEN)
    assert power(0.20, 4, mde, FROZEN) == pytest.approx(0.80, abs=1e-6)


def test_normal_approximation_would_have_overstated_power():
    """Records why noncentral t is used: the normal shortcut is badly optimistic here."""
    sd = log_scale_sd(0.20, FROZEN)
    from scipy import stats
    naive = 1.0 - stats.norm.cdf(stats.norm.ppf(0.975) - math.log(1.5) / (sd * math.sqrt(2.0 / 3)))
    assert naive - power(0.20, 3, 1.5, FROZEN) > 0.15


def test_required_replicates_returns_none_when_target_is_unreachable():
    assert required_replicates(0.20, 1.5, FROZEN, max_n=3) is None


def test_unreachable_search_is_not_an_error_but_an_absence():
    """None must not be confused with n=0 or with a raised failure."""
    assert required_replicates(0.20, 1.001, FROZEN, max_n=5) is None


@pytest.mark.parametrize("cv", [0, -0.1, 20, "0.2", True, None])
def test_invalid_cv_rejected(cv):
    with pytest.raises(ValueError):
        log_scale_sd(cv, FROZEN)


def test_percentage_shaped_cv_rejected():
    """20 meaning 20 percent must fail loudly rather than silently model CV=2000 percent."""
    with pytest.raises(ValueError):
        log_scale_sd(20, FROZEN)


def test_unknown_convention_rejected():
    with pytest.raises(ValueError):
        log_scale_sd(0.20, "lognormal")


def test_unknown_design_rejected():
    with pytest.raises(ValueError):
        power(0.20, 3, 1.5, FROZEN, design="paired")


@pytest.mark.parametrize("n", [1, 0, -3, 3.0, True])
def test_insufficient_or_nonintegral_replicates_rejected(n):
    with pytest.raises(ValueError):
        power(0.20, n, 1.5, FROZEN)


@pytest.mark.parametrize("fold", [0, -1.5, "1.5", None])
def test_invalid_fold_change_rejected(fold):
    with pytest.raises(ValueError):
        power(0.20, 3, fold, FROZEN)


def test_null_fold_change_rejected_rather_than_reported_as_alpha():
    with pytest.raises(ValueError):
        power(0.20, 3, 1.0, FROZEN)


@pytest.mark.parametrize("alpha", [0, 1, -0.05, 1.5])
def test_invalid_alpha_rejected(alpha):
    with pytest.raises(ValueError):
        power(0.20, 3, 1.5, FROZEN, alpha=alpha)


@pytest.mark.parametrize("target", [0, 1, -0.1, 1.2])
def test_invalid_target_power_rejected(target):
    with pytest.raises(ValueError):
        required_replicates(0.20, 1.5, FROZEN, target_power=target)
    with pytest.raises(ValueError):
        minimum_detectable_fold_change(0.20, 3, FROZEN, target_power=target)


def test_assessment_is_serialisable_and_carries_its_convention_and_no_claim():
    payload = assess(0.20, 3, 1.5, FROZEN).to_dict()
    assert payload["dispersion_convention"] == FROZEN
    assert payload["design"] in DESIGNS
    assert "no stability, translation or expression benefit" in payload["no_claim"]
    assert json.loads(json.dumps(payload))["power_at_target"] == payload["power_at_target"]


def test_assessment_is_frozen_so_a_recorded_figure_cannot_be_mutated():
    result = assess(0.20, 3, 1.5, FROZEN)
    with pytest.raises(Exception):
        result.power_at_target = 0.99


def test_every_declared_convention_and_design_is_usable():
    for convention in DISPERSION_CONVENTIONS:
        for design in DESIGNS:
            assert 0.0 < power(0.20, 4, 1.5, convention, design=design) < 1.0
