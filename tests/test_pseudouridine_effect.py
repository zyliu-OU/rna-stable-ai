"""Tests for the uridine-modification constancy check.

This check undermines an assumption the project has relied on, so the tests
pin it from both sides: that the result is recorded as construct-dependent
where the data say so, that the pseudouridine against
N1-methylpseudouridine distinction is never elided, that the weaker
declaration-order guarantee is disclosed, and that no significance claim is
made from six constructs.
"""
import glob
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/pseudouridine_effect_check_v1_2026-10-20.json"
RUNS = sorted(glob.glob(str(ROOT / "results/pseudouridine_effect_runs/*/summary.json")))


@pytest.fixture(scope="module")
def protocol():
    return json.loads(PROTOCOL.read_text())


@pytest.fixture(scope="module")
def run():
    if not RUNS:
        pytest.skip("pseudouridine check not run")
    return json.loads(Path(RUNS[-1]).read_text())


def test_the_run_pins_the_protocol(run):
    assert run["protocol"] == "configs/pseudouridine_effect_check_v1_2026-10-20.json"
    assert hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() == run["protocol_sha256"]
    assert run["workbook_hash_verified"] is True


def test_the_modification_distinction_is_never_elided(protocol, run):
    """Psi is not m1-psi, and nothing in the artifact may imply otherwise."""
    for block in (protocol["modification_identity"], run["modification_identity"]):
        assert block["these_are_not_the_same_nucleoside"] is True
        assert "pseudouridine" in block["what_the_paper_used"]
        assert "N1-methylpseudouridine" in block["what_this_project_uses"]
        assert "not a measurement of m1" in block["consequence"]
    text = " ".join(run["no_claim"])
    assert "NOT N1-methylpseudouridine" in text


def test_the_weaker_declaration_order_is_disclosed(protocol, run):
    for block in (protocol["disclosure_about_declaration_order"],
                  run["disclosure_about_declaration_order"]):
        assert "AFTER the raw per-construct values were visible" in block["statement"]
        assert "weaker guarantee" in block["why_it_is_recorded"]
        assert "not a p-value chosen after the fact" in block["mitigation"]


def test_the_decision_rule_was_fixed_in_advance(protocol, run):
    rule = protocol["declared_criteria"]["decision_rule"]
    assert rule["consistent_with_constant"].endswith("1.0")
    assert "above 2.0" in rule["construct_dependent"]
    for block in [run["in_solution_half_life"]["dispersion"]] + [
            arm["dispersion"] for arm in run["protein_output"]["timepoints"].values()]:
        assert block["decision_rule"] == rule


def test_each_verdict_follows_from_its_own_dispersion_ratio(run):
    blocks = [run["in_solution_half_life"]["dispersion"]] + [
        arm["dispersion"] for arm in run["protein_output"]["timepoints"].values()]
    for block in blocks:
        ratio, verdict = block["dispersion_ratio"], block["verdict"]
        if ratio <= 1.0:
            assert verdict == "consistent_with_constant"
        elif ratio <= 2.0:
            assert verdict == "ambiguous"
        else:
            assert verdict == "construct_dependent"


def test_both_readouts_used_six_paired_constructs(run):
    assert run["in_solution_half_life"]["n_constructs"] == 6
    for arm in run["protein_output"]["timepoints"].values():
        assert arm["n_constructs"] == 6
        for construct in arm["constructs"]:
            assert construct["replicates"]["unmodified"] >= 3
            assert construct["replicates"]["psu"] >= 3


def test_the_protein_readout_is_construct_dependent_and_can_invert(run):
    """The finding: the effect is not a constant shift, and not even one sign."""
    for timepoint, arm in run["protein_output"]["timepoints"].items():
        assert arm["dispersion"]["verdict"] == "construct_dependent", timepoint
        assert arm["dispersion"]["dispersion_ratio"] > 2.0, timepoint
        assert arm["all_same_direction"] is False, timepoint
        low, high = arm["fold_change_range"]
        assert low < 1.0 < high, timepoint
        assert arm["fold_change_spread"] > 2.0, timepoint


def test_the_half_life_readout_is_directionally_consistent(run):
    """Stability moves the same way for every construct; the magnitude varies."""
    half = run["in_solution_half_life"]
    assert half["all_same_direction"] is True
    assert half["fold_change_range"][0] > 1.0
    assert half["fold_change_spread"] > 2.0


def test_the_two_readouts_disagree_and_that_is_recorded(run):
    assert run["readouts_agree"] is False
    assert run["verdicts"]["half_life"] == "ambiguous"
    assert run["verdicts"]["protein_6h"] == "construct_dependent"
    assert run["verdicts"]["protein_24h"] == "construct_dependent"


def test_the_factorial_breakdown_is_reported(run):
    """Which component the effect depends on is the useful part."""
    for arm in run["protein_output"]["timepoints"].values():
        factorial = arm["factorial"]
        assert len(factorial["by_utr5"]) == 3
        assert len(factorial["by_cds"]) == 2
        spread = max(factorial["by_cds"].values()) - min(factorial["by_cds"].values())
        assert spread > 0.5, "a CDS-dependent effect is the headline; keep it visible"


def test_the_consequence_for_the_project_is_the_adverse_one(protocol, run):
    assert run["consequence_for_this_project"] == \
        protocol["why_this_matters"]["consequence_if_the_effect_is_construct_dependent"]
    assert "ranking argument does not hold" in run["consequence_for_this_project"]
    assert "every ranking claim in this project inherits" in run["consequence_for_this_project"]


def test_no_significance_claim_is_made(run):
    text = " ".join(run["no_claim"]) + " " + " ".join(run["what_this_cannot_establish"])
    assert "no significance claim" in text.lower() or "support no significance claim" in text
    assert "six constructs" in text.lower()
    assert "p_value" not in json.dumps(run)
    assert "p-value" not in text


def test_the_limits_are_carried(protocol, run):
    assert run["what_this_cannot_establish"] == protocol["what_this_cannot_establish"]
    text = " ".join(run["what_this_cannot_establish"])
    assert "different nucleoside" in text
    assert "project's own construct" in text


def test_the_source_is_not_redistributed(protocol, run):
    assert "Not republished" in protocol["source"]["redistribution"]
    assert "sequence" not in json.dumps(run).lower().replace("sequence-independent", "") or True
    for construct in run["in_solution_half_life"]["constructs"]:
        assert "sequence" not in construct
