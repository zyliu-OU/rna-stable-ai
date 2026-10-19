"""Unit tests for the Stage 2 band coverage census logic."""
import json
from pathlib import Path

import pytest

from rnastable.stage2_census import (
    band_census, band_of, baseline_lineage, classify, clan_of, eligible,
    requirement_status, resolution_verdict,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT/"configs/stage2_band_coverage_census_v1_2026-10-19.json"
GATE = ROOT/"configs/stage2_to_stage3_gate_2026-10-18.json"

BANDS = [{"name": "2000_2999", "minimum_inclusive": 2000, "maximum_exclusive": 3000},
         {"name": "1_999", "minimum_inclusive": 1, "maximum_exclusive": 1000},
         {"name": "1000_1999", "minimum_inclusive": 1000, "maximum_exclusive": 2000}]
TAXONOMY = {
    "selected_complete_reference": {"reference_supported": True, "exposed": False},
    "fixed_family_cap": {"reference_supported": True, "exposed": False},
    "prior_exposure_overlap": {"reference_supported": None, "exposed": True},
    "unsupported_reference": {"reference_supported": False, "exposed": False}}
CLANS = {"RF00177": "CL00111", "RF02541": "CL00112", "RF02540": "CL00112",
         "RF02542": "CL00111", "RF02462": "CL00004"}


def test_config_assesses_exactly_the_gate_requirements():
    config = json.loads(CONFIG.read_text())
    gate = json.loads(GATE.read_text())
    assert set(config["gate_requirements_assessed"]) == set(gate["requirements_before_stage3"])
    assert config["band"]["maximum_exclusive"] == gate["active_length_nt"]["maximum_exclusive"]


def test_config_keeps_every_mutation_flag_false():
    config = json.loads(CONFIG.read_text())
    for flag in ("selection_changed", "new_inference_performed", "model_defaults_changed",
                 "new_sequence_scoring_enabled", "expression_candidate_design_enabled",
                 "stage3_ready"):
        assert config[flag] is False


def test_config_records_the_cap_and_visibility_rules():
    rules = json.loads(CONFIG.read_text())["independence_rule"]
    assert "pseudo-replicates" in rules["cap_warning"]
    assert "must not become invisible" in rules["unresolved_visibility_rule"]


@pytest.mark.parametrize("length,expected", [
    (1, "1_999"), (999, "1_999"), (1000, "1000_1999"), (1999, "1000_1999"),
    (2000, "2000_2999"), (2999, "2000_2999"), (3000, None), (5000, None)])
def test_band_of_uses_half_open_intervals(length, expected):
    assert band_of(length, BANDS) == expected


@pytest.mark.parametrize("bad", [0, -5, 2000.0, "2000"])
def test_band_of_rejects_invalid_lengths(bad):
    with pytest.raises(ValueError):
        band_of(bad, BANDS)


def test_classify_maps_support_and_exposure():
    assert classify("fixed_family_cap", TAXONOMY)["reference_supported"] is True
    assert classify("prior_exposure_overlap", TAXONOMY)["exposed"] is True
    assert classify("unsupported_reference", TAXONOMY)["reference_supported"] is False
    with pytest.raises(ValueError):
        classify("made_up_reason", TAXONOMY)


def test_eligible_requires_support_and_no_exposure():
    assert eligible({"reference_supported": True, "exposed": False}) is True
    assert eligible({"reference_supported": True, "exposed": True}) is False
    assert eligible({"reference_supported": False, "exposed": False}) is False
    # An exposed record carries unknown support and must never count as eligible.
    assert eligible({"reference_supported": None, "exposed": True}) is False


def test_clan_of_returns_none_for_unmapped_family():
    assert clan_of("RF02541", CLANS) == "CL00112"
    assert clan_of("RF09999", CLANS) is None


def test_baseline_lineage_reports_unresolved_families():
    selected = [{"family_id": "RF00177"}, {"family_id": "RF02541"}, {"family_id": "RF09999"}]
    baseline = baseline_lineage(selected, CLANS)
    assert baseline["families"] == ["RF00177", "RF02541", "RF09999"]
    assert baseline["clans"] == ["CL00111", "CL00112"]
    assert baseline["clan_unresolved_families"] == ["RF09999"]


def record(family, decision):
    return {"family_id": family, "decision": decision, **classify(decision, TAXONOMY)}


def test_band_census_counts_families_clans_and_blocked_opportunities():
    baseline = baseline_lineage([{"family_id": "RF00177"}, {"family_id": "RF02541"}], CLANS)
    rows = [record("RF02541", "selected_complete_reference"),
            record("RF02540", "fixed_family_cap"), record("RF02540", "fixed_family_cap"),
            record("RF02541", "unsupported_reference"),
            record("RF02462", "prior_exposure_overlap")]
    census = band_census(rows, baseline, CLANS)
    assert census["records"] == 5
    assert census["eligible_records"] == 3
    assert census["eligible_families"] == ["RF02540", "RF02541"]
    assert census["eligible_clans"] == ["CL00112"]
    assert census["new_families_available"] == ["RF02540"]
    assert census["new_clans_available"] == []
    assert census["clan_expansion_possible"] is False
    assert census["family_expansion_possible"] is True
    assert census["eligible_records_by_family"] == {"RF02540": 2, "RF02541": 1}
    # The exposed new-clan family must stay visible rather than vanish.
    assert census["new_clan_opportunities_blocked"]["CL00004"]["family"] == "RF02462"
    assert census["new_clan_opportunities_blocked"]["CL00004"]["reasons"] == {"prior_exposure_overlap": 1}


def test_band_census_reports_all_band_families_even_when_ineligible():
    baseline = baseline_lineage([{"family_id": "RF02541"}], CLANS)
    rows = [record("RF02462", "prior_exposure_overlap"), record("RF09999", "unsupported_reference")]
    census = band_census(rows, baseline, CLANS)
    assert census["band_families"] == ["RF02462", "RF09999"]
    assert census["band_clans"] == ["CL00004"]
    assert census["band_clan_unresolved_families"] == ["RF09999"]
    assert census["eligible_records"] == 0


def test_band_census_credits_a_genuine_new_clan():
    baseline = baseline_lineage([{"family_id": "RF02541"}], CLANS)
    census = band_census([record("RF00177", "fixed_family_cap")], baseline, CLANS)
    assert census["new_clans_available"] == ["CL00111"]
    assert census["clan_expansion_possible"] is True


def test_resolution_verdict_distinguishes_family_from_clan_resolution():
    baseline = baseline_lineage([{"family_id": "RF02541"}], CLANS)
    family_only = resolution_verdict(band_census([record("RF02540", "fixed_family_cap")],
                                                 baseline, CLANS))
    assert family_only["state"] == "resolvable_at_family_level_only_clan_coverage_unchanged"
    clan_level = resolution_verdict(band_census([record("RF00177", "fixed_family_cap")],
                                                baseline, CLANS))
    assert clan_level["state"] == "resolvable_at_clan_level_from_local_material"
    none_left = resolution_verdict(band_census([record("RF02462", "prior_exposure_overlap")],
                                               baseline, CLANS))
    assert none_left["state"] == "no_eligible_band_material_available"


def test_resolution_verdict_flags_same_family_records_only():
    baseline = baseline_lineage([{"family_id": "RF02540"}], CLANS)
    verdict = resolution_verdict(band_census([record("RF02540", "fixed_family_cap")],
                                             baseline, CLANS))
    assert verdict["state"] == "additional_records_available_but_no_new_family_or_clan"
    assert verdict["eligible_records"] == 1


REQUIREMENTS = ["req_a", "req_b"]


def test_requirement_status_requires_evidence_and_blockers():
    rows = requirement_status(REQUIREMENTS, {
        "req_a": {"status": "not_satisfied", "evidence": ["x"], "blockers": ["y"]},
        "req_b": {"status": "partially_satisfied", "evidence": ["x"], "blockers": ["y"]}})
    assert [row["requirement"] for row in rows] == REQUIREMENTS


def test_requirement_status_refuses_to_mark_satisfied():
    with pytest.raises(ValueError, match="may not mark"):
        requirement_status(["req_a"], {
            "req_a": {"status": "satisfied", "evidence": ["x"], "blockers": ["y"]}})


def test_requirement_status_rejects_missing_or_bare_assignments():
    with pytest.raises(ValueError, match="No status assigned"):
        requirement_status(REQUIREMENTS, {"req_a": {"status": "not_satisfied",
                                                    "evidence": ["x"], "blockers": ["y"]}})
    with pytest.raises(ValueError, match="needs evidence"):
        requirement_status(["req_a"], {"req_a": {"status": "not_satisfied",
                                                 "evidence": [], "blockers": ["y"]}})
    with pytest.raises(ValueError, match="needs blockers"):
        requirement_status(["req_a"], {"req_a": {"status": "not_satisfied",
                                                 "evidence": ["x"], "blockers": []}})
    with pytest.raises(ValueError, match="Invalid status"):
        requirement_status(["req_a"], {"req_a": {"status": "looks_fine",
                                                 "evidence": ["x"], "blockers": ["y"]}})
