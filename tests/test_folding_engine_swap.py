"""Tests for folding_engine_swap_v1 and the correction it forced.

Three things happened and all three are easy to lose:

  1. the engine-swap hypothesis died -- the engines agree once properly normalised
  2. a baseline recorded in gate v14 as its headline adverse finding turned out to
     be a length-composition artifact, and had to be corrected
  3. refitting on more features made the objective strictly worse out of sample

The second is the one these tests guard hardest. A project that records adverse
findings loudly and quietly drops them when they turn out to be its own
measurement error is not keeping a record. The correction is pinned, its scope is
pinned, and the fact that the adverse conclusion SURVIVES in another form is
pinned too, so the correction cannot be read as an exoneration.
"""
import glob
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/folding_engine_swap_v1_2026-10-20.json"
PANEL = sorted(glob.glob(str(ROOT / "results/free_baseline_panel_runs/*/summary.json")))
REFIT = sorted(glob.glob(str(ROOT / "results/feature_refit_runs/*/summary.json")))

pytestmark = pytest.mark.skipif(not (PANEL and REFIT), reason="engine-swap steps not run")


@pytest.fixture(scope="module")
def panel():
    return json.loads(Path(PANEL[-1]).read_text())


@pytest.fixture(scope="module")
def refit():
    return json.loads(Path(REFIT[-1]).read_text())


def test_the_protocol_is_pinned_at_its_hash(panel, refit):
    digest = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    assert panel["protocol_sha256"] == digest
    assert refit["protocol_sha256"] == digest


def test_the_decision_rule_and_success_criterion_were_declared_in_advance():
    declared = " ".join(json.loads(PROTOCOL.read_text())["declared_before_any_number_was_seen"])
    assert "Step 1 decision rule" in declared
    assert "must beat BOTH" in declared
    assert "Beating only the frozen arm is not success" in declared
    assert "should be reduced to that feature rather than defended" in declared


def test_step_1_fitted_and_installed_nothing(panel):
    assert panel["fitting_performed"] == "none"
    assert panel["engine_installed"] == "none"


def test_the_engines_agree_once_properly_normalised(panel):
    """The AUP columns are the paper's own averages and need no normalisation."""
    columns = panel["panel"]
    aup = {name: columns[name]["spearman_vs_in_solution"]
           for name in ("AUP EternaFold", "AUP Vienna", "AUP DegScore 2.1")}
    assert max(aup.values()) - min(aup.values()) < 0.06, (
        "if the engines ever separate here, the engine-swap hypothesis is back open")
    assert all(v < 0 for v in aup.values()), "more unpaired means less stable in solution"


def test_the_defective_baseline_is_recorded_with_its_decomposition(refit):
    block = refit["the_defective_baseline_that_prompted_this"]
    decomposition = block["decomposition_on_the_122"]
    assert abs(decomposition["region_fraction_alone"]) > abs(decomposition["aup_alone"]), (
        "the length ratio must be recorded as the dominant factor")
    assert decomposition["the_product_as_reported"] == pytest.approx(-0.4190, abs=1e-3)
    assert "does not yield a per-nucleotide structure score" in block["what_it_actually_was"]
    assert "sub-region" in block["what_it_actually_was"]
    assert "wrong for the right numbers" in block["why_all_three_engines_clustered"]


def test_the_scope_of_the_error_is_bounded_and_the_earlier_result_is_defended(refit):
    """The 123-record correction was correct. Over-correcting would also be an error."""
    scope = refit["the_defective_baseline_that_prompted_this"]["scope_of_the_error"]
    assert "Confined to two_axis_comparison_v1" in scope
    assert "123 of 123 records" in scope
    assert "was correct" in scope and "-0.3248" in scope


def test_the_correction_does_not_become_an_exoneration(refit):
    """Against clean structure scores we win; against GC content (CDS) we still lose."""
    block = refit["the_defective_baseline_that_prompted_this"]
    assert "WINS" in block["corrected_comparison"]
    gc_cds = refit["reference_points"]["gc_content_cds_alone"]
    frozen = refit["reference_points"]["frozen_vienna_arm_in_solution"]
    assert gc_cds > frozen, "the adverse conclusion must survive in its corrected form"


def test_step_2_was_skipped_with_a_recorded_reason(refit):
    block = refit["step_2_skipped"]
    assert "installing EternaFold" in block["what_was_skipped"]
    assert "dead hypothesis" in block["why"]


def test_the_refit_overfits_monotonically(refit):
    """Train up, test down, as features are added. The core negative result."""
    arms = [e for e in refit["arms"].values() if e.get("available")]
    by_features = sorted(arms, key=lambda e: e["n_features"])
    single = by_features[0]
    widest = max(arms, key=lambda e: e["n_features"])
    assert single["n_features"] == 1
    assert widest["train_spearman"] > single["train_spearman"], "train must improve"
    assert widest["test_spearman_vs_in_solution"] < single["test_spearman_vs_in_solution"], (
        "held-out must degrade; this is the finding")
    assert abs(widest["test_spearman_vs_in_solution"]) < 0.10, (
        "the widest arm must have essentially no out-of-sample signal")


def test_no_in_cell_label_touched_a_coefficient(refit):
    assert refit["estimator"]["no_in_cell_label_used"] is True
    assert refit["counts"] == {"train": 69, "test": 122}


def test_the_declared_criterion_failed_and_is_recorded_as_failed(refit):
    verdict = refit["verdict"]
    assert verdict["beats_frozen_arm"] is True
    assert verdict["beats_best_free_single_column"] is False
    assert verdict["success"] is False
    assert verdict["best_arm"] == "gc_cds_only"


def test_the_criterion_amendment_is_recorded_and_admits_it_lowers_the_bar(refit):
    """The declared bar referenced the defective score, so it had to be restated."""
    text = refit["verdict"]["criterion_amended"]
    assert "defective" in text
    assert "lowers the bar, so it is stated explicitly" in text
