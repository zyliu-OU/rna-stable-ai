"""Tests for the 2,000-2,999 nt native-control band expansion.

The band held exactly one record because a per-family cap stopped selection.
That cap bounded what a learned model could be trained and evaluated on, and
the learned model was retired on 2026-10-20, so evaluating the thermodynamic
folders on more references is folding rather than fitting.

Expanding a cohort is the easiest place for a frozen selection to be quietly
replaced, and for an availability count to be repeated without being checked.
The tests below pin both: that the frozen selection is untouched, and that the
census's overstated eligibility is recorded rather than inherited.
"""
import glob
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNS = sorted(glob.glob(str(ROOT / "results/band_native_control_runs/*/summary.json")))

pytestmark = pytest.mark.skipif(not RUNS, reason="band expansion not run")


@pytest.fixture(scope="module")
def payload():
    return json.loads(Path(RUNS[-1]).read_text())


def test_the_frozen_selection_was_not_modified(payload):
    assert payload["frozen_selection_modified"] is False
    assert "unchanged" in payload["relation_to_the_frozen_cohort"]


def test_nothing_was_fitted(payload):
    assert payload["model_fitted"] is False
    assert payload["learned_model_involved"] is False
    assert "no training set" in payload["why_the_cap_does_not_apply"]


def test_the_band_bounds_are_the_gate_band(payload):
    assert payload["band"] == {"minimum_inclusive": 2000, "maximum_exclusive": 3000}


def test_the_expansion_is_real_and_carries_dispersion(payload):
    """One record carries no dispersion; reporting it is the point of this run."""
    for method in ("LinearFold", "ViennaRNA"):
        stats = payload["per_method"][method]
        assert stats["n"] >= 5
        assert stats["stdev_pair_f1"] is not None
        assert stats["max_pair_f1"] > stats["min_pair_f1"]


def test_the_census_eligibility_overstatement_is_recorded(payload):
    """50 of the 55 'eligible' records cannot bind a reference at all."""
    correction = payload["census_eligibility_correction"]
    assert "overstates" in correction
    assert "BEFORE" in correction
    assert "Only 5 bind" in correction
    assert payload["skipped"]["binding_failed"] == 50


def test_the_absence_of_family_contrast_within_this_cohort_is_stated(payload):
    """All five bound records are RF02540, so this cohort alone contrasts nothing."""
    for method in ("LinearFold", "ViennaRNA"):
        assert payload["per_method"][method]["families"] == 1
        assert set(payload["per_method"][method]["family_means"]) == {"RF02540"}
    text = " ".join(payload["no_claim"])
    assert "no family contrast within itself" in text


def test_every_fold_succeeded(payload):
    assert payload["fold_failures"] == {}


def test_it_does_not_claim_biological_validation_or_a_satisfied_gate(payload):
    text = " ".join(payload["no_claim"])
    assert "not biological validation" in text
    assert "gate-review judgement" in text
