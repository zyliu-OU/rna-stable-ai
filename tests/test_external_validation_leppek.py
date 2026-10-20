"""Tests for the first external validation of the stability calibration.

This is the only result in the project compared against measurements the model
was not fitted on, which makes it the one most likely to be overstated later.
These tests pin the things that keep it honest: that the protocol was declared
before the run, that the training overlap is excluded rather than scored, that
nothing was refitted, that the training-subset figure is labelled an upper bound,
that the post-hoc baseline correction is disclosed with its mechanical
justification, and that the verdict flags follow from the numbers.
"""
import glob
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/external_validation_leppek_v1_2026-10-20.json"
RUNS = sorted(glob.glob(str(ROOT / "results/external_validation_leppek_runs/*/summary.json")))


@pytest.fixture(scope="module")
def protocol():
    return json.loads(PROTOCOL.read_text())


@pytest.fixture(scope="module")
def run():
    if not RUNS:
        pytest.skip("external validation not run")
    return json.loads(Path(RUNS[-1]).read_text())


def test_the_protocol_was_declared_before_the_run(protocol):
    assert "DECLARED BEFORE ANY CORRELATION WAS COMPUTED" in protocol["status"]
    assert "so the result can fail" in protocol["status"]
    criteria = protocol["declared_criteria"]
    assert criteria["primary_metric"].startswith("Spearman")
    assert criteria["expected_direction"] == "positive Spearman correlation"
    assert "at or below 0" in criteria["falsification"]
    assert "0.3" in criteria["weak_transfer_threshold"]


def test_the_run_pins_the_protocol_it_followed(run):
    assert run["protocol"] == "configs/external_validation_leppek_v1_2026-10-20.json"
    assert hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() == run["protocol_sha256"]


def test_the_training_overlap_was_found_and_excluded(protocol, run):
    overlap = protocol["training_overlap"]
    assert "fitted on a subset of this dataset" in overlap["finding"]
    assert "69 of 69" in overlap["evidence"]
    assert "INFERRED join" in overlap["join_risk"]
    assert run["counts"]["sheet_rows"] == 192
    assert run["counts"]["training_overlap"] == 69
    assert run["counts"]["held_out"] == 123
    assert run["counts"]["held_out"] + run["counts"]["training_overlap"] == run["counts"]["sheet_rows"]


def test_nothing_was_refitted(protocol, run):
    assert run["refitting_performed"] is False
    assert "Nothing is refitted" in protocol["prediction_procedure"]["no_refitting"]


def test_the_source_workbook_hash_was_verified(run):
    assert run["workbook_hash_verified"] is True
    assert len(run["source"]["file_sha256"]) == 64


def test_the_source_is_not_redistributed(protocol, run):
    assert "Not republished here" in protocol["source"]["redistribution"]
    # No sequence should appear in the published artifact.
    text = json.dumps(run)
    assert "RNA_sequence" not in text
    for row in run["rows"]:
        assert "sequence" not in row


def test_the_primary_metric_is_over_the_held_out_records(run):
    primary = run["primary"]
    assert primary["label"] == "held_out_all"
    assert primary["n"] == 123
    assert primary["spearman"] is not None


def test_the_verdict_flags_follow_from_the_numbers(run):
    rho = run["primary"]["spearman"]
    verdict = run["verdict"]
    assert verdict["spearman"] == rho
    assert verdict["falsified"] is (rho <= 0)
    assert verdict["transfers"] is (rho > 0.3)


def test_the_result_is_positive_but_only_just_over_the_declared_threshold(run):
    """Pinned so a later reader does not inherit it as a strong result."""
    rho = run["primary"]["spearman"]
    assert rho > 0, "a non-positive rho would mean the calibration does not transfer"
    assert 0.3 < rho < 0.4, "the headline is weak transfer, not a strong correlation"


def test_the_in_domain_subset_does_not_change_the_conclusion(run):
    """Otherwise the headline would rest on extrapolating records."""
    both = (run["primary"]["spearman"], run["held_out_in_domain_only"]["spearman"])
    assert abs(both[0] - both[1]) < 0.05
    assert run["held_out_in_domain_only"]["n"] >= run["primary"]["n"] - 5


def test_the_training_figure_is_labelled_an_upper_bound_not_a_result(run):
    upper = run["training_subset_upper_bound"]
    assert upper["label"] == "training_subset"
    assert upper["n"] == 69
    # The generalisation gap is the point: training must look better.
    assert upper["spearman"] > run["primary"]["spearman"]
    text = " ".join(run["no_claim"])
    assert "upper bound on what the model can do, not a result" in text


def test_the_post_hoc_baseline_correction_is_disclosed(run):
    correction = run["baseline_post_hoc_correction"]
    assert "compare the paper's predictor columns raw" in correction["what_was_declared"]
    assert "sums over nucleotides" in correction["what_was_wrong"]
    assert "AFTER the primary result was computed" in correction["when"]
    assert "disclosed, not applied silently" in correction["when"]
    assert correction["justification"].startswith("mechanical")
    assert correction["effect_on_the_primary_metric"].startswith("none")


def test_the_baselines_are_shown_to_be_length_dominated_when_raw(run):
    """The evidence for the correction, not just the assertion of it."""
    for name, metrics in run["baselines_on_the_same_records"].items():
        assert metrics["spearman_raw_vs_length"] > 0.9, name
        assert abs(metrics["spearman_raw_as_declared"]) < 0.15, name
        assert metrics["spearman_per_nucleotide"] < 0, name
        assert metrics["statistic_used_for_ranking"].startswith("per-nucleotide")


def test_length_itself_is_not_a_confound_in_our_prediction(run):
    check = run["length_confound_check"]
    assert abs(check["spearman_length_vs_measured_half_life"]) < 0.15
    assert "not a confound in this project's prediction" in check["note"]


def test_the_calibration_does_not_beat_the_best_published_baseline(run):
    """The honest comparison: it matches EternaFold rather than improving on it."""
    ours = abs(run["primary"]["spearman"])
    best = max(m["absolute_spearman"] for m in run["baselines_on_the_same_records"].values())
    assert abs(ours - best) < 0.05, (
        "if this ever diverges, the claim about matching published predictors must change")


def test_pearson_on_log_exceeds_spearman(run):
    """Monotone in the large, rank-noisy in the middle: worth keeping visible."""
    assert run["primary"]["pearson_log"] > run["primary"]["spearman"]


def test_the_distribution_shift_is_declared_in_the_protocol(protocol):
    held = protocol["held_out_set"]
    assert held["n"] == 123
    assert "distribution shift not only a split" in \
        " ".join(k.replace("_", " ") for k in held)
    shift = held["this_is_a_distribution_shift_not_only_a_split"]
    assert "cannot be separated with this data alone" in shift
    assert "declared here, before the result is known" in shift


def test_the_quantity_match_is_the_stated_reason_for_this_dataset(protocol):
    why = protocol["why_this_dataset"]
    assert "in-solution half-life of purified RNA in buffer, in hours" in why["quantity_match"]
    rejected = " ".join(why["rejected_alternatives"])
    assert "OpenVaccine" in rejected and "Saluki" in rejected and "MPRA" in rejected


def test_the_limits_are_carried_into_the_artifact(protocol, run):
    assert run["what_this_cannot_establish"] == protocol["what_this_cannot_establish"]
    text = " ".join(run["what_this_cannot_establish"])
    assert "A correlation is not a calibration" in text
    assert "1811 nt" in text
    assert "translation side" in text


def test_every_held_out_row_carries_its_measurement_and_prediction(run):
    rows = run["rows"]
    assert len(rows) == 123
    scored = [r for r in rows if r.get("predicted_hours") is not None]
    assert len(scored) == run["counts"]["held_out_scored"]
    for row in scored:
        assert row["measured_hours"] > 0
        assert "features_outside_training_range" in row
        assert row["length_nt"] > 0
