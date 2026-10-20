"""Tests for the re-scoped requirement 5 checks on the native path.

Requirement 5 is `Pass_constraint_decoder_resource_and_replay_checks`. Its
replay leg originally reloaded learned-model checkpoints, which were deleted
when the model was retired on 2026-10-20. The checks were moved onto LinearFold
and ViennaRNA, and a re-scope is the easiest place for a check to be weakened
into something that cannot fail, so the tests below pin the parts that stop it
being one: that replay compares against frozen values rather than recomputing
both sides, that the constraint legs cover both tools with the correct
per-tool convention, that a constraint which cannot be met is refused rather
than silently dropped, and that passing does not assert the requirement.
"""
import glob
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNS = sorted(glob.glob(str(ROOT / "results/native_path_requirement5_runs/*/summary.json")))

pytestmark = pytest.mark.skipif(not RUNS, reason="requirement 5 checks not run")


@pytest.fixture(scope="module")
def payload():
    return json.loads(Path(RUNS[-1]).read_text())


def test_all_three_legs_are_present_and_passed(payload):
    for leg in ("replay", "constraint_decoder", "refusal_control"):
        assert payload[leg]["passed"] is True, leg
    assert payload["resources"]


def test_replay_covers_the_whole_frozen_cohort_for_both_methods(payload):
    assert payload["cohort"]["records"] == 11
    assert set(payload["methods"]) == {"LinearFold", "ViennaRNA"}
    assert payload["replay"]["checked"] == 22
    assert payload["replay"]["reproduced_exactly"] == 22


def test_replay_compares_structure_and_energy_against_the_frozen_rows(payload):
    """Recomputing both sides would make this leg unfalsifiable."""
    assert "frozen row" in payload["replay"]["criterion"]
    assert "long_native_controls_runs" in payload["cohort"]["frozen_rows"]
    for row in payload["replay"]["rows"]:
        assert row["structure_reproduced"] is True
        assert row["energy_reproduced"] is True
        assert row["frozen_mfe_kcal_mol"] == row["replayed_mfe_kcal_mol"]


def test_constraint_decoder_enforced_real_pairs_on_every_record(payload):
    """An empty constraint string would pass trivially."""
    rows = payload["constraint_decoder"]["rows"]
    assert len(rows) == 22
    for row in rows:
        assert row["enforced_pairs"] > 0
        assert row["enforced_pairs_absent_from_fold"] == 0


def test_each_tool_uses_its_own_unconstrained_convention(payload):
    """'.' means unconstrained to ViennaRNA and forced-unpaired to LinearFold."""
    assert payload["constraint_decoder"]["conventions"] == {
        "ViennaRNA": ".", "LinearFold": "?"}


def test_an_unsatisfiable_constraint_is_refused_by_both_tools(payload):
    """ViennaRNA drops a sub-minimum-hairpin pair and reports a finite energy."""
    rows = {row["method"]: row for row in payload["refusal_control"]["rows"]}
    assert set(rows) == {"LinearFold", "ViennaRNA"}
    for method, row in rows.items():
        assert row["refused"] is True, method
        assert row["outcome"] == "refused", method
        assert row["impossible_pair_reported_as_honoured"] is False, method
    assert "silently dropped" in rows["ViennaRNA"]["error"]


def test_resources_are_measured_against_the_frozen_limits(payload):
    for method in payload["methods"]:
        stats = payload["resources"][method]
        limits = stats["limits_from_frozen_config"]
        assert limits == {"timeout_seconds": 30, "memory_limit_gib": 4}
        for band in stats["unconstrained_by_band"].values():
            assert band["max_wall_seconds"] < limits["timeout_seconds"]
            assert band["max_peak_rss_mib"] < limits["memory_limit_gib"] * 1024
        assert stats["constrained_max_wall_seconds"] < limits["timeout_seconds"]


def test_the_2000_2999_band_still_holds_one_record_here_too(payload):
    """The accepted limitation must stay visible in the resource evidence."""
    for method in payload["methods"]:
        bands = payload["resources"][method]["unconstrained_by_band"]
        assert bands["2000_2999"]["n"] == 1


def test_the_rescope_records_what_was_not_restored(payload):
    record = payload["rescope_record"]
    assert "deleted" in record["original_replay_target"]
    assert "learned-model replay leg" in record["what_was_not_restored"]
    assert "authorises nothing" in record["authorised_by"]


def test_no_learned_component_was_involved(payload):
    assert payload["model_fitted"] is False
    assert payload["learned_model_involved"] is False


def test_it_does_not_assert_that_the_requirement_is_satisfied(payload):
    text = " ".join(payload["no_claim"])
    assert "gate-review judgement, not an output of this script" in text
    assert "determinism, not accuracy" in text
    assert "decoder correctness, not structural correctness" in text
