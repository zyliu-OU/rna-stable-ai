"""Unit tests for upstream band clan-availability logic."""
import gzip
import json
from pathlib import Path

import pytest

from rnastable.band_availability import (
    achievability_verdict, classify_description, parse_clan_membership,
    parse_family_metadata, rfam_band_availability, scan_seed_band, summarize_rcsb,
    validate_consensus_lengths,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT/"configs/stage2_band_clan_availability_census_v2_2026-10-19.json"
BAND = {"name": "2000_2999", "minimum_inclusive": 2000, "maximum_exclusive": 3000}
RIB = ["ribosom", "rrna", "23s", "50s"]
GENERIC = ["-mer)", "chains:", "complete genome"]


def test_config_is_gated_and_cannot_amend_the_gate():
    config = json.loads(CONFIG.read_text())
    for flag in ("selection_changed", "new_inference_performed", "model_defaults_changed",
                 "gate_amended", "new_sequence_scoring_enabled",
                 "expression_candidate_design_enabled", "stage3_ready"):
        assert config[flag] is False
    assert any("may not amend" in claim for claim in config["no_claim_permitted"])
    assert any("full alignments were not surveyed" in claim for claim in config["no_claim_permitted"])


def test_config_requires_consensus_length_validation():
    method = json.loads(CONFIG.read_text())["rfam_method"]
    assert method["validation_tolerance_nt"] == 0
    assert len(method["validation_families"]) >= 8
    assert method["parse_integrity_requirement"]


def test_config_declares_baseline_clans_and_the_pseudo_replicate_rule():
    baseline = json.loads(CONFIG.read_text())["baseline_clans"]
    assert baseline["clans"] == ["CL00111", "CL00112"]
    assert "pseudo-replicates" in baseline["rule"]


def gz(path, text):
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        fh.write(text)
    return path


def test_parse_clan_membership_reads_pairs(tmp_path):
    p = gz(tmp_path/"c.gz", "CL00112\tRF02541\nCL00111\tRF00177\njunk line\n")
    assert parse_clan_membership(p) == {"RF02541": "CL00112", "RF00177": "CL00111"}


def test_parse_clan_membership_rejects_conflict_and_empty(tmp_path):
    p = gz(tmp_path/"a.gz", "CL00112\tRF02541\nCL00004\tRF02541\n")
    with pytest.raises(ValueError, match="Conflicting clan"):
        parse_clan_membership(p)
    with pytest.raises(ValueError, match="No clan memberships"):
        parse_clan_membership(gz(tmp_path/"b.gz", "nothing useful\n"))


def family_row(acc, fid, clen):
    # clen sits at index -6, so it leads a six-field tail: five columns follow it.
    tail = [str(clen), "a", "b", "c", "d", "e"]
    return "\t".join([acc, fid, "wiki", "desc", "author"] + tail)


def test_parse_family_metadata_locates_clen_and_counts_skips(tmp_path):
    text = family_row("RF00005", "tRNA", 71)+"\n"+family_row("RF02541", "LSU", 2925)+"\nbroken\n"
    families, skipped = parse_family_metadata(gz(tmp_path/"f.gz", text))
    assert families["RF00005"] == {"id": "tRNA", "clen": 71}
    assert families["RF02541"]["clen"] == 2925
    assert skipped == 1


def test_parse_family_metadata_rejects_empty(tmp_path):
    with pytest.raises(ValueError, match="No families"):
        parse_family_metadata(gz(tmp_path/"e.gz", "nope\n"))


FAMS = {"RF00005": {"id": "tRNA", "clen": 71}, "RF02541": {"id": "LSU", "clen": 2925}}


def test_validate_consensus_lengths_passes_on_exact_match():
    checks = validate_consensus_lengths(FAMS, {"RF00005": 71, "RF02541": 2925}, 0)
    assert [c["difference"] for c in checks] == [0, 0]


def test_validate_consensus_lengths_catches_a_shifted_column():
    with pytest.raises(ValueError, match="clen validation failed"):
        validate_consensus_lengths(FAMS, {"RF00005": 71, "RF02541": 9999}, 0)


def test_validate_consensus_lengths_requires_the_validation_family_present():
    with pytest.raises(ValueError, match="absent from metadata"):
        validate_consensus_lengths(FAMS, {"RF99999": 100}, 0)


def test_validate_consensus_lengths_rejects_negative_tolerance():
    with pytest.raises(ValueError, match="non-negative"):
        validate_consensus_lengths(FAMS, {"RF00005": 71}, -1)


def test_scan_seed_band_uses_ungapped_length_and_joins_blocks(tmp_path):
    # Two interleaved blocks totalling 2001 ungapped characters, plus gaps.
    first = "A"*1000
    second = "C"*1001
    text = ("# STOCKHOLM 1.0\n#=GF AC RF00001\n"
            f"seqA/1-2001 {first}--\n"
            f"seqA/1-2001 {second}..\n//\n"
            "# STOCKHOLM 1.0\n#=GF AC RF00002\n"
            "seqB/1-10 ACGUACGUAC\n//\n")
    found = scan_seed_band(gz(tmp_path/"s.gz", text), BAND)
    assert list(found) == ["RF00001"]
    assert found["RF00001"] == [{"name": "seqA/1-2001", "length_nt": 2001}]


def test_scan_seed_band_excludes_out_of_band_lengths(tmp_path):
    text = ("# STOCKHOLM 1.0\n#=GF AC RF00001\n" + f"s/1-1999 {'A'*1999}\n//\n"
            "# STOCKHOLM 1.0\n#=GF AC RF00002\n" + f"t/1-3000 {'A'*3000}\n//\n")
    assert scan_seed_band(gz(tmp_path/"o.gz", text), BAND) == {}


@pytest.mark.parametrize("label,expected", [
    ("23S ribosomal RNA", "ribosomal"),
    ("50S subunit", "ribosomal"),
    ("23S rRNA", "ribosomal"),
    ("RNA (2912-MER)", "generically_named"),
    ("Chains: A", "generically_named"),
    ("Escherichia coli strain K-12 chromosome, complete genome", "generically_named"),
    ("35s rna", "other"),
    ("Telomerase RNA", "other")])
def test_classify_description(label, expected):
    assert classify_description(label, RIB, GENERIC) == expected


def rcsb_response(buckets, total):
    return {"total_count": total,
            "facets": [{"name": "descriptions",
                        "buckets": [{"label": l, "population": n} for l, n in buckets]}]}


def test_summarize_rcsb_counts_classes_and_flags_leads():
    response = rcsb_response([("23S rRNA", 100), ("RNA (2912-MER)", 5), ("Telomerase RNA", 2)], 107)
    out = summarize_rcsb(response, RIB, GENERIC)
    assert out["total_band_entities"] == 107
    assert out["facet_covers_all"] is True
    assert out["by_class"]["ribosomal"]["entities"] == 100
    assert out["unresolved_generic_entities"] == 5
    assert out["new_clan_leads"] == 2


def test_summarize_rcsb_detects_incomplete_facet_coverage():
    out = summarize_rcsb(rcsb_response([("23S rRNA", 100)], 150), RIB, GENERIC)
    assert out["facet_covers_all"] is False


def test_summarize_rcsb_requires_the_facet():
    with pytest.raises(ValueError, match="no descriptions facet"):
        summarize_rcsb({"total_count": 1, "facets": []}, RIB, GENERIC)


CLANS = {"RF02541": "CL00112", "RF02540": "CL00112", "RF01960": "CL00111", "RF02462": "CL00004"}


def test_rfam_band_availability_subtracts_already_held_records():
    seed = {"RF02541": [{"name": "x/1-2500", "length_nt": 2500}],
            "RF02462": [{"name": "AL355930.2/32605-30557", "length_nt": 2049},
                        {"name": "NEW1/1-2100", "length_nt": 2100}]}
    held = {"AL355930.2/32605-30557": {"id": "RF02462:AL355930.2/32605-30557",
                                      "decision": "prior_exposure_overlap",
                                      "exposed": True, "family_id": "RF02462"}}
    out = rfam_band_availability(seed, CLANS, ["CL00111", "CL00112"], held)
    assert out["band_sequences_total"] == 3
    assert out["band_sequences_outside_baseline"] == 2
    assert out["newly_available_outside_baseline"] == 1
    assert out["families_outside_baseline"]["RF02462"]["already_held_locally"] == 1
    assert out["band_families"]["RF02541"]["outside_baseline"] is False
    assert out["clan_unresolved_families"] == []


def test_rfam_band_availability_reports_unresolved_clans_and_never_credits_them():
    seed = {"RF09999": [{"name": "y/1-2200", "length_nt": 2200}]}
    out = rfam_band_availability(seed, CLANS, ["CL00111", "CL00112"], {})
    assert out["clan_unresolved_families"] == ["RF09999"]
    assert out["newly_available_outside_baseline"] == 0
    assert out["families_outside_baseline"] == {}


def test_achievability_verdict_three_states_and_never_satisfies():
    rcsb_clean = {"new_clan_leads": 0, "unresolved_generic_entities": 0}
    rcsb_leads = {"new_clan_leads": 3, "unresolved_generic_entities": 21}
    resolvable = achievability_verdict({"newly_available_outside_baseline": 2}, rcsb_clean, "req")
    assert resolvable["state"] == "resolvable"
    assert resolvable["achievable_from_surveyed_sources"] is True
    leads = achievability_verdict({"newly_available_outside_baseline": 0}, rcsb_leads, "req")
    assert leads["state"] == "not_resolvable_from_surveyed_sources_unresolved_leads_present"
    none = achievability_verdict({"newly_available_outside_baseline": 0}, rcsb_clean, "req")
    assert none["state"] == "not_resolvable_from_surveyed_sources"
    for verdict in (resolvable, leads, none):
        assert verdict["requirement_satisfied"] is False
        assert verdict["gate_amended"] is False
        assert "full alignments were not surveyed" in verdict["scope_of_verdict"]
