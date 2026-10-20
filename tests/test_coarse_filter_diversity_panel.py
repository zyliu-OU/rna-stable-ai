"""Tests for the reframed selection: coarse filter plus diversity, no ranking.

The reframe exists because the objective was measured to order at chance in this
design space. Its whole value is that it refuses to rank, so the tests pin the
refusals: that no predicted value touched the panel choice, that the filter is
applied to the stability side only, that translation differences exceeding the
stability floor are STILL unresolved, and that a run resolving nothing says so
rather than producing a ranking anyway.
"""
import glob
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/coarse_filter_diversity_panel_v1_2026-10-20.json"
RUNS = sorted(glob.glob(str(ROOT / "results/coarse_filter_panel_runs/*/summary.json")))


@pytest.fixture(scope="module")
def protocol():
    return json.loads(PROTOCOL.read_text())


@pytest.fixture(scope="module")
def runs():
    if not RUNS:
        pytest.skip("reframed selection not run")
    return [json.loads(Path(p).read_text()) for p in RUNS]


def test_the_protocol_states_what_it_replaces_and_why(protocol):
    block = protocol["what_this_replaces"]
    assert "maximising dominated hypervolume" in block["previous_output"]
    assert "0.5007 over 2958 held-out pairs" in block["why_it_is_replaced"]
    assert "Selecting the top of that ordering is selecting noise" in block["why_it_is_replaced"]
    assert "Only the SELECTION changes" in block["what_is_kept"]


def test_the_resolution_floor_comes_from_a_measurement(protocol):
    floor = protocol["resolution_floor"]
    assert floor["chance_floor"] == 1.10
    assert floor["resolvable_threshold"] == 1.25
    measured = json.loads((ROOT / floor["measured_from"]).read_text())
    bands = measured["B_fine_ordering"]["pairwise_concordance_by_measured_fold_difference"]
    for key, value in floor["concordance_by_measured_fold_difference"].items():
        assert bands[key]["concordance"] == pytest.approx(value, abs=1e-4), key
    assert "would license treating a 1.15-fold difference as real" in floor["why_two_numbers"]
    assert floor["applies_to"].endswith("ONLY")


def test_no_ranking_or_hypervolume_was_used(runs):
    for run in runs:
        assert run["ranking_used"] is False
        assert run["hypervolume_used"] is False
        assert run["panel"]["selection_used_no_predicted_values"] is True
        assert run["selection_method"].startswith("coarse filter then deterministic")


def test_the_filter_is_stability_only(protocol, runs):
    assert protocol["resolution_floor"]["applies_to"] == "the stability objective ONLY"
    for run in runs:
        assert run["resolution_floor_applied"]["applies_to"] == "stability only"
        assert run["translation_side"]["filter_applied"] is False
        assert "never used to rank or to filter" in \
            protocol["the_translation_side_has_no_measured_resolution"]["not_a_reason_to_drop_the_score"]


def test_translation_differences_beyond_the_stability_floor_remain_unresolved(runs):
    """The trap the protocol names: the floor does not transfer to RiboNN."""
    wide = [r for r in runs
            if r["translation_side"]["members_exceeding_the_stability_chance_floor"] > 0]
    assert wide, "at least one pool must exercise this case"
    for run in wide:
        assert run["translation_side"]["filter_applied"] is False
        assert "does not transfer to RiboNN" in run["translation_side"]["note"]
        assert run["stability_classification"]["everything_unresolved"] is True


def test_every_pool_came_out_entirely_unresolved(runs):
    """The finding. If this ever changes, the headline must change with it."""
    for run in runs:
        classification = run["stability_classification"]
        assert classification["resolvably_better"] == []
        assert classification["resolvably_worse"] == []
        assert classification["unresolved_count"] == run["pool"]["size"]
        assert classification["everything_unresolved"] is True
        assert classification["widest_fold_difference_from_reference"] < \
            run["resolution_floor_applied"]["resolvable_threshold"]


def test_a_run_that_resolves_nothing_says_so(runs):
    for run in runs:
        assert "lies entirely inside the objective's noise floor" in run["finding"]
        assert "diversity panel over ties, not a selection of better candidates" in run["finding"]


def test_the_widest_difference_is_below_even_the_chance_floor_for_stability(runs):
    """Not a near miss: the design space does not reach the chance floor either."""
    for run in runs:
        assert run["stability_classification"]["widest_fold_difference_from_reference"] < \
            run["resolution_floor_applied"]["chance_floor"]


def test_the_reference_anchors_every_panel(runs):
    for run in runs:
        assert run["panel"]["reference_included"] is True
        assert run["panel"]["members"][0] == run["reference"]["member"]


def test_the_panel_spans_the_design_space(runs):
    for run in runs:
        panel = run["panel"]
        assert panel["minimum_pairwise_hamming"] > 0
        assert panel["mean_pairwise_hamming"] >= panel["minimum_pairwise_hamming"]
        assert panel["minimum_pairwise_hamming"] <= panel["maximum_possible_hamming"]
        # Spread should be a real fraction of the available positions.
        assert panel["minimum_pairwise_hamming"] >= panel["maximum_possible_hamming"] * 0.1


def test_the_panel_size_is_still_a_placeholder(runs):
    for run in runs:
        assert run["panel"]["size_is_a_placeholder"] is True
        assert run["panel"]["size"] <= run["panel"]["size_requested"]


def test_the_selection_is_deterministic(protocol):
    algorithm = protocol["diversity_rule"]["algorithm"]
    assert "deterministic" in algorithm
    assert "breaking ties by lowest member index" in algorithm
    assert "no objective values" in protocol["diversity_rule"]["why_farthest_point"]


def test_the_permitted_and_prohibited_claims_are_carried(protocol, runs):
    for run in runs:
        assert run["what_the_output_may_claim"] == protocol["what_the_output_may_claim"]
        assert run["what_the_output_may_not_claim"] == protocol["what_the_output_may_not_claim"]
    prohibited = " ".join(protocol["what_the_output_may_not_claim"])
    assert "is ranked" in prohibited
    assert "translation score distinguishes" in prohibited
    assert "absence of resolvable members means the design space is bad" in prohibited


def test_the_run_requires_the_gate_that_prohibits_ranking(runs):
    for run in runs:
        assert run["gate"] == "configs/stage2_to_stage3_gate_v10_2026-10-20.json"
        gate = json.loads((ROOT / run["gate"]).read_text())
        assert "MUST NOT be presented as a ranking" in \
            gate["prohibition_added_here"]["prohibition"]


def test_the_protocol_hash_is_pinned_in_every_run(runs):
    digest = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    for run in runs:
        assert run["protocol_sha256"] == digest


def test_all_three_window_widths_were_processed(runs):
    widths = {run["pool"]["window_codons"] for run in runs}
    assert widths == {30, 50, 549}
