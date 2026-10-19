"""Unit tests for the named RNAfold calibration fit and its frozen criterion."""
import csv
import json
from pathlib import Path

import pytest

from fit_strand_rnafold_calibration import (
    COHORT_FILES, COLUMNS, build_feature_rows, cross_language_check, metric,
    primary_arm, write_feature_csvs,
)
from rnastable.strand_reference import FEATURE_ORDER

ROOT = Path(__file__).resolve().parents[1]
CRITERION = ROOT/"configs/strand_rnafold_calibration_criterion_v2_2026-10-19.json"


def test_criterion_is_gated_and_names_the_model():
    criterion = json.loads(CRITERION.read_text())
    assert criterion["model_name"] == "strand_rnafold_calibration_v1"
    assert criterion["arms"]["both_prespecified"] is True
    assert criterion["feature_source"]["energy_feature"] == "ensemble_energy_per_nt"
    assert criterion["feature_source"]["alo_transform"] == "identity"
    assert criterion["new_sequence_scoring_enabled"] is False
    assert criterion["expression_candidate_design_enabled"] is False
    assert criterion["stage3_ready"] is False
    assert criterion["fitting_procedure"]["fit_repetitions"] >= 2


def test_criterion_declares_the_exposure_and_leakage_limits():
    criterion = json.loads(CRITERION.read_text())
    assert "project-exposed" in criterion["evaluation"]["exposure_disclosure"]
    assert criterion["arms"]["leakage_disclosure"]
    assert any("not validation" in claim for claim in criterion["no_claim_permitted"])


def test_criterion_reference_points_match_published_record():
    points = json.loads(CRITERION.read_text())["acceptance_criterion"]["reference_points_not_bars"]
    assert points["published_with_alo_egfp_rmse_hours"] == 0.1893218848801146
    assert points["published_without_alo_egfp_rmse_hours"] == 0.2174279666658343


def test_primary_arm_picks_lower_training_loo():
    assert primary_arm({"with_alo": 0.30, "without_alo": 0.29}) == "without_alo"
    assert primary_arm({"with_alo": 0.28, "without_alo": 0.29}) == "with_alo"


def test_primary_arm_breaks_near_ties_toward_published_default():
    assert primary_arm({"with_alo": 0.3, "without_alo": 0.3 + 1e-15}) == "with_alo"


def test_primary_arm_requires_both_arms():
    with pytest.raises(ValueError):
        primary_arm({"with_alo": 0.3})


CRITERION_STUB = {"feature_source": {"energy_feature": "ensemble_energy_per_nt",
                                     "alo_transform": "identity"}}


def fake_fold(paired, ensemble_per_nt, gc_fraction):
    return {"paired_probability_per_position": paired,
            "feature_candidates": {"mfe_energy_per_nt": ensemble_per_nt+0.01,
                                   "ensemble_energy_per_nt": ensemble_per_nt,
                                   "gc_fraction": gc_fraction,
                                   "aup": 1-sum(paired)/len(paired), "alo": 0.0}}


def test_build_feature_rows_splits_by_cohort_and_carries_labels():
    records = [{"name": "a", "cohort": "train", "observed_half_life": 1.0},
               {"name": "b", "cohort": "egfp", "observed_half_life": 2.0},
               {"name": "c", "cohort": "mev_exploratory", "observed_half_life": 3.0}]
    folds = {r["name"]: fake_fold([0.3, 0.4], -0.4, 0.52) for r in records}
    rows = build_feature_rows(CRITERION_STUB, records, folds)
    assert [len(rows[c]) for c in ("train", "egfp", "mev_exploratory")] == [1, 1, 1]
    assert rows["train"][0]["in_solution_half_life"] == 1.0
    assert rows["egfp"][0]["GC"] == pytest.approx(52.0)
    assert rows["train"][0]["energy_per_length"] == pytest.approx(-0.4)
    assert set(rows["train"][0]) == {"name", *FEATURE_ORDER, "in_solution_half_life"}


def test_feature_csvs_are_written_round_trip_exact(tmp_path):
    records = [{"name": "a", "cohort": "train", "observed_half_life": 0.7644412712345678}]
    folds = {"a": fake_fold([0.123456789012345, 0.9], -0.4177959705221242, 0.5204741379310345)}
    rows = build_feature_rows(CRITERION_STUB, records, folds)
    for cohort in ("egfp", "mev_exploratory"):
        rows[cohort] = []
    write_feature_csvs(rows, tmp_path)
    for name in COHORT_FILES.values():
        assert (tmp_path/name).exists()
    read = list(csv.DictReader((tmp_path/"train_features.csv").open()))
    assert list(read[0]) == COLUMNS
    for field in (*FEATURE_ORDER, "in_solution_half_life"):
        assert float(read[0][field]) == rows["train"][0][field]


def test_feature_csvs_refuse_to_overwrite(tmp_path):
    rows = {c: [] for c in COHORT_FILES}
    write_feature_csvs(rows, tmp_path)
    with pytest.raises(FileExistsError):
        write_feature_csvs(rows, tmp_path)


def test_metric_lookup_matches_arm_ncomp_and_cohort():
    models = {"metrics": [{"arm": "with_alo", "ncomp": 1, "cohort": "egfp", "rmse": 0.5},
                          {"arm": "with_alo", "ncomp": 2, "cohort": "egfp", "rmse": 0.4}]}
    assert metric(models, "with_alo", 2, "egfp")["rmse"] == 0.4
    with pytest.raises(ValueError):
        metric(models, "without_alo", 1, "egfp")


def write_replay_fixture(tmp_path, prediction):
    component = {"ncomp": 1, "feature_order": ["energy_per_length", "GC", "aup"],
                 "intercept": 0.0,
                 "coefficients": {"energy_per_length": 1.0, "GC": 0.0, "aup": 0.0}}
    (tmp_path/"r_models.json").write_text(json.dumps(
        {"models": {"without_alo": {"components": {"1": component}}}}))
    with (tmp_path/"r_predictions.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["arm", "ncomp", "cohort", "name", "observed", "prediction"])
        writer.writerow(["without_alo", "1", "train", "a", "1.0", repr(prediction)])
        # LOO rows use per-fold refits and are deliberately not replayed.
        writer.writerow(["without_alo", "1", "train_loo", "a", "1.0", "999.0"])
    return {"train": [{"name": "a", "energy_per_length": -0.4, "GC": 50.0, "aup": 0.3,
                       "alo": 1.0, "in_solution_half_life": 1.0}]}


def test_cross_language_check_accepts_matching_predictions(tmp_path):
    rows = write_replay_fixture(tmp_path, -0.4)
    result = cross_language_check(tmp_path, rows, 1e-10)
    assert result["comparisons"] == 1
    assert result["max_abs_difference"] == pytest.approx(0.0, abs=1e-15)


def test_cross_language_check_rejects_drift(tmp_path):
    rows = write_replay_fixture(tmp_path, -0.4+1e-6)
    with pytest.raises(ValueError):
        cross_language_check(tmp_path, rows, 1e-10)
