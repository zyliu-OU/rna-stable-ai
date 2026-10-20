"""Tests for the three-part stability ablation.

The concordance result is the most consequential measurement in this project:
it says the objective cannot order sequences at the scale the design space
produces. A number that undercuts the pipeline's purpose must be hard to soften
later, so these tests pin it to the chance baseline and to the pair counts it
rests on, alongside the ablation and combination verdicts and the provenance
check that upgraded the training join from inferred to confirmed.
"""
import glob
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/stability_feature_ablation_v1_2026-10-20.json"
RUNS = sorted(glob.glob(str(ROOT / "results/stability_ablation_runs/*/summary.json")))
BASE = ("energy_per_length", "GC", "aup")


@pytest.fixture(scope="module")
def protocol():
    return json.loads(PROTOCOL.read_text())


@pytest.fixture(scope="module")
def run():
    if not RUNS:
        pytest.skip("ablation not run")
    return json.loads(Path(RUNS[-1]).read_text())


def test_the_protocol_was_declared_first(protocol, run):
    assert "DECLARED BEFORE ANY ABLATION, CONCORDANCE OR COMBINED FIT" in protocol["status"]
    assert hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() == run["protocol_sha256"]
    assert run["workbook_hash_verified"] is True


def test_the_split_is_the_declared_one_and_held_out_was_not_used_to_choose(protocol, run):
    assert run["counts"] == {"rows": 192, "fit": 69, "held_out": 123}
    assert "fitted on the 69 fit rows only" in protocol["data"]["no_tuning_on_held_out"]
    text = " ".join(run["no_claim"])
    assert "scored once per model" in text
    assert "no variant was selected using them" in text
    for label, variant in run["variants"].items():
        assert variant["fit_n"] <= 69, label
        assert variant["held_out_n"] <= 123, label


def test_every_variant_was_fitted_with_the_same_estimator(protocol, run):
    assert run["estimator"]["method"] == "ordinary least squares"
    assert "cannot be reproduced exactly here" in run["estimator"]["why_not_pls"]
    assert "internally apples-to-apples" in run["estimator"]["why_not_pls"]
    for label, variant in run["variants"].items():
        assert set(variant["model"]["coefficients"]) == set(variant["features"]), label
        assert "intercept" in variant["model"], label


def test_the_frozen_model_is_a_labelled_reference_not_a_variant(run):
    reference = run["frozen_pls_reference"]
    assert "labelled reference, not an OLS variant" in reference["note"]
    assert "frozen_pls_reference" not in run["variants"]
    assert reference["held_out_n"] == 123
    text = " ".join(run["no_claim"])
    assert "OLS results do not transfer to it" in text


def test_recomputed_features_reproduce_the_frozen_training_table_exactly(run):
    """This is what upgraded the training-overlap join from inferred to confirmed."""
    provenance = run["feature_provenance_check"]
    assert set(provenance) == set(BASE)
    for name, stats in provenance.items():
        assert stats["n"] == 69, name
        assert stats["max_absolute_difference"] == 0.0, name


def test_the_gc_ablation_verdict_follows_the_declared_criteria(protocol, run):
    block = run["A_gc_ablation"]
    assert block["delta"] == pytest.approx(
        block["without_gc_spearman"] - block["full_spearman"])
    delta = abs(block["delta"])
    if delta <= 0.05:
        assert block["verdict"] == "not_load_bearing"
    elif block["delta"] < -0.10:
        assert block["verdict"] == "load_bearing"
    else:
        assert block["verdict"] == "ambiguous"


def test_gc_could_not_be_dropped_cheaply(run):
    """The hoped-for outcome did not happen; pin that it did not."""
    block = run["A_gc_ablation"]
    assert block["verdict"] != "not_load_bearing"
    assert block["delta"] < -0.05, "dropping GC cost real held-out performance"
    # And GC alone is close to the full model, so it is the strongest single input.
    variants = run["variants"]
    singles = {k: variants[k]["held_out_spearman"]
               for k in ("energy_only", "gc_only", "aup_only")}
    assert max(singles, key=singles.get) == "gc_only"


def test_concordance_is_at_chance_for_the_narrowest_differences(run):
    """The headline. The design space lives in this bin."""
    block = run["B_fine_ordering"]
    narrow = block["pairwise_concordance_by_measured_fold_difference"]["1.00-1.10"]
    assert narrow["pairs"] > 1000, "the claim must rest on many pairs, not a handful"
    assert narrow["concordance"] == pytest.approx(0.50, abs=0.02)
    assert block["verdict"] == "cannot_order_similar"
    assert "3 to 8 percent" in block["why_the_narrowest_bin_matters"]
    assert "Chance is 0.50" in block["why_the_narrowest_bin_matters"]


def test_concordance_rises_with_the_size_of_the_real_difference(run):
    """Coarse discrimination works; that contrast is the point."""
    bands = run["B_fine_ordering"]["pairwise_concordance_by_measured_fold_difference"]
    ordered = [bands[k]["concordance"] for k in
               ("1.00-1.10", "1.10-1.25", "1.25-1.50", "1.50-2.00", "above_2.00")
               if bands[k]["concordance"] is not None]
    assert ordered == sorted(ordered), "concordance must increase with the real difference"
    assert ordered[-1] > 0.9, "the model is genuinely good at large differences"
    assert ordered[-1] - ordered[0] > 0.4


def test_the_fine_ordering_verdict_follows_the_declared_threshold(protocol, run):
    block = run["B_fine_ordering"]
    narrow = block["narrowest_bin_concordance"]
    if narrow <= 0.55:
        assert block["verdict"] == "cannot_order_similar"
    elif narrow >= 0.65:
        assert block["verdict"] == "can_order_similar"
    else:
        assert block["verdict"] == "ambiguous"


def test_ordering_fails_in_the_fast_degrading_quartiles(run):
    quartiles = run["B_fine_ordering"]["spearman_within_measured_quartiles"]
    assert len(quartiles) == 4
    assert quartiles["q1"]["spearman"] < 0.2
    assert quartiles["q4"]["spearman"] > quartiles["q1"]["spearman"]
    for stats in quartiles.values():
        assert stats["n"] > 10
        assert stats["measured_range"][0] <= stats["measured_range"][1]


def test_the_combination_was_worse_and_the_verdict_says_so(run):
    block = run["C_combination"]
    assert block["combined_spearman"] < max(
        block["full_spearman"], block["eternafold_only_spearman"])
    assert block["gain_over_best_single"] < 0
    assert block["verdict"] == "prefer_the_free_predictor"
    assert abs(block["eternafold_only_spearman"] - block["full_spearman"]) <= 0.05


def test_the_limits_are_carried(protocol, run):
    assert run["what_this_cannot_establish"] == protocol["what_this_cannot_establish"]
    text = " ".join(run["what_this_cannot_establish"])
    assert "Absolute accuracy" in text
    assert "gate decision, not an output of this run" in text
    assert "1811 nt" in text


def test_all_nine_declared_variants_were_fitted(protocol, run):
    declared = [v.split(":")[0] for v in protocol["variants_to_fit"]]
    assert set(run["variants"]) == set(declared)
    assert len(declared) == 9
