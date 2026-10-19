"""Census locally available 2000-2999 nt Stage 2 validation material.

Reads the frozen candidate pool, selection decisions and family-clan map,
reports band coverage by record, family and clan, and binds each gate
requirement to a status with evidence and blockers. Runs no inference, changes
no selection and marks no requirement satisfied.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

from rnastable.stage2_census import (
    band_census, band_of, baseline_lineage, classify, clan_of, requirement_status,
    resolution_verdict,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT/"configs/stage2_band_coverage_census_v1_2026-10-19.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, obj):
    with Path(path).open("x") as f:
        f.write(json.dumps(obj, indent=2, allow_nan=False)+"\n")


def source(config, role):
    for entry in config["sources"]:
        if entry["role"] == role:
            path = ROOT/entry["path"]
            if sha(path) != entry["sha256"]:
                raise ValueError(f"Pinned census source changed: {entry['path']}")
            return path
    raise ValueError(f"Config declares no source for role {role}")


def load_clan_map(paths):
    """Merge family-to-clan assignments from the pinned sources.

    The primary map does not cover every family in the candidate pool, so
    assignments are merged and each family keeps the source it came from.
    Disagreement between sources is an error rather than a silent pick.
    """
    mapping, provenance = {}, {}
    for label, path in paths:
        def walk(node):
            if isinstance(node, dict):
                family = node.get("family_id") or node.get("family")
                clan = node.get("clan_id") or node.get("clan")
                if (isinstance(family, str) and family.startswith("RF")
                        and isinstance(clan, str) and clan.startswith("CL")):
                    if family in mapping and mapping[family] != clan:
                        raise ValueError(
                            f"Conflicting clan for {family}: {mapping[family]} "
                            f"({provenance[family]}) vs {clan} ({label})")
                    mapping.setdefault(family, clan)
                    provenance.setdefault(family, label)
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)
        walk(json.loads(Path(path).read_text()))
    if not mapping:
        raise ValueError("Pinned clan sources carry no assignments")
    return mapping, provenance


def secondary_band_families(path, band):
    """Families seen in the band by the secondary survey, with support unknown."""
    seen = {}
    def walk(node):
        if isinstance(node, dict):
            length = node.get("length_nt") or node.get("length")
            sequence = node.get("sequence")
            if isinstance(sequence, str) and sequence:
                length = len(sequence)
            family = node.get("family_id") or node.get("family")
            if (isinstance(length, int) and isinstance(family, str) and family.startswith("RF")
                    and band["minimum_inclusive"] <= length < band["maximum_exclusive"]):
                seen.setdefault(family, 0)
                seen[family] += 1
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(json.loads(Path(path).read_text()))
    return dict(sorted(seen.items()))


def verify(run):
    """Re-check artifact hashes and replay the verdict from stored census counts."""
    manifest = json.loads((run/"manifest.json").read_text())
    for name, expected in manifest["artifacts"].items():
        path = run/name
        if not path.resolve().is_relative_to(run.resolve()) or sha(path) != expected:
            raise ValueError(f"Artifact checksum mismatch: {name}")
    summary = json.loads((run/"summary.json").read_text())
    replayed = resolution_verdict(summary["band_census"])
    if replayed != summary["band_resolution"]:
        raise ValueError("Stored band verdict does not replay from stored census")
    if any(row["status"] == "satisfied" for row in summary["gate_requirement_status"]):
        raise ValueError("A stored requirement is marked satisfied")
    result = {"artifacts_verified": len(manifest["artifacts"]),
              "band": summary["band"]["name"],
              "band_resolution": replayed["state"],
              "requirements_satisfied": 0,
              "mode": "artifact and stored-census audit; no new inference"}
    print(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT)
    parser.add_argument("--verify-run", type=Path)
    args = parser.parse_args()
    if args.verify_run:
        verify(args.verify_run.resolve())
        return
    config = json.loads(args.config.read_text())
    for flag in ("selection_changed", "new_inference_performed", "model_defaults_changed",
                 "new_sequence_scoring_enabled", "expression_candidate_design_enabled",
                 "stage3_ready"):
        if config[flag]:
            raise ValueError(f"Census must not set {flag}")
    gate = json.loads((ROOT/config["gate"]).read_text())
    band = config["band"]
    bands = [band, *config["other_bands"]]
    if gate["active_length_nt"]["maximum_exclusive"] != band["maximum_exclusive"]:
        raise ValueError("Census band must end at the active scope boundary")
    if set(config["gate_requirements_assessed"]) != set(gate["requirements_before_stage3"]):
        raise ValueError("Census must assess exactly the gate's requirements")

    candidates = {row["id"]: row for row in json.loads(source(config, "candidate_pool").read_text())}
    selection = json.loads(source(config, "frozen_selection_decisions").read_text())
    secondary_path = source(config, "secondary_band_survey")
    clan_map, clan_provenance = load_clan_map(
        [("family_clan_map", source(config, "family_clan_map")),
         ("secondary_band_survey", secondary_path)])
    secondary = secondary_band_families(secondary_path, band)

    rows = []
    for decision in selection["decisions"]:
        record = candidates[decision["id"]]
        length = len(record["sequence"])
        rows.append({"id": decision["id"], "family_id": record["family_id"],
                     "clan_id": clan_of(record["family_id"], clan_map),
                     "length_nt": length, "band": band_of(length, bands),
                     **classify(decision["reason"], config["decision_taxonomy"])})
    in_scope_selected = [row for row in rows
                         if row["decision"] == "selected_complete_reference"
                         and row["length_nt"] < gate["active_length_nt"]["maximum_exclusive"]]
    baseline = baseline_lineage(in_scope_selected, clan_map)
    band_rows = [row for row in rows if row["band"] == band["name"]]
    census = band_census(band_rows, baseline, clan_map)
    verdict = resolution_verdict(census)

    coverage_by_band = {}
    for entry in bands:
        subset = [row for row in rows if row["band"] == entry["name"]]
        selected = [row for row in in_scope_selected if row["band"] == entry["name"]]
        coverage_by_band[entry["name"]] = {
            "candidates": len(subset),
            "selected_in_scope": len(selected),
            "selected_families": sorted({row["family_id"] for row in selected}),
            "selected_clans": sorted({row["clan_id"] for row in selected}-{None}),
            "eligible_records": sum(1 for row in subset
                                    if row["reference_supported"] is True and not row["exposed"])}

    evidence = {"census": "this run",
                "stage2_audit": "results/stage2_under3000_audit_runs/20261018T223708.786045Z/summary.json",
                "selection": config["sources"][1]["path"],
                "clan_map": config["sources"][2]["path"]}
    assignments = {
        "Frozen independent sequence_and_family_clan_separated_validation_within_scope": {
            "status": "not_satisfied",
            "evidence": [evidence["selection"], evidence["clan_map"], evidence["stage2_audit"]],
            "blockers": [
                f"The in-scope frozen selection holds {len(in_scope_selected)} records across "
                f"{len(baseline['families'])} families and {len(baseline['clans'])} clans "
                f"({', '.join(baseline['clans'])}).",
                "Every available reference is a computational Rfam-consensus reference, not an "
                "experimental structure.",
                "The prior audit records independent complete-reference validation as "
                "unestablished and existing checkpoints as trained with now-deferred sequences."]},
        "Reported_accuracy_and_failures_by_length_band_and_family_against_native_controls": {
            "status": "partially_satisfied",
            "evidence": [evidence["stage2_audit"]],
            "blockers": [
                "Accuracy is reported by band, family and seed against LinearFold and ViennaRNA, "
                "but the 2000-2999 nt band rests on a single record, so its per-band figure "
                "carries no dispersion and no family contrast.",
                "The learned model remains below both native controls on development references."]},
        "Resolve_sparse_2000_2999_nt_coverage_before_claiming_the_full_length_range": {
            "status": "blocked_on_acquisition",
            "evidence": [evidence["census"], evidence["selection"], evidence["clan_map"]],
            "blockers": [
                f"Band verdict: {verdict['state']}.",
                f"Eligible band records available locally: {census['eligible_records']} across "
                f"families {census['eligible_families']}.",
                f"New families available locally: {census['new_families_available'] or 'none'}; "
                f"new clans available locally: {census['new_clans_available'] or 'none'}.",
                f"Band families seen: {census['band_families']}; band clans: {census['band_clans']}; "
                f"clan-unresolved band families: {census['band_clan_unresolved_families'] or 'none'}.",
                f"New-clan opportunities present but ineligible: "
                f"{census['new_clan_opportunities_blocked'] or 'none'}.",
                "Clan-separated band coverage therefore needs acquisition of band-length "
                "references from a clan outside the selected baseline."]},
        "Demonstrate_credible_structure_accuracy_with_explicit_review_of_native_baseline_gaps": {
            "status": "not_satisfied",
            "evidence": [evidence["stage2_audit"]],
            "blockers": [
                "The prior audit's first blocking reason is that the learned model remains below "
                "both native controls on development references.",
                "No native experimental-structure control exists for the 2000-2999 nt band."]},
        "Pass_constraint_decoder_resource_and_replay_checks": {
            "status": "partially_satisfied",
            "evidence": [evidence["stage2_audit"],
                         "results/long_candidate_budget_matched_runs/20261017T183356.669629Z",
                         "results/long_native_controls_runs/20261017T034318.804594Z",
                         "results/bprna_five_clan_feasibility_evaluation_runs/20261017T191445.852927Z"],
            "blockers": [
                "The budget-matched, native-control and five-clan feasibility replays were "
                "re-verified on 2026-10-19 and passed, so replay evidence exists for these runs.",
                "Those replays cover the existing development runs only; no constraint, decoder or "
                "resource check exists for any expanded 2000-2999 nt cohort, which does not yet exist."]},
        "Document_remaining_limitations_before_expression_candidate_design": {
            "status": "partially_satisfied",
            "evidence": [evidence["census"], evidence["stage2_audit"],
                         "reports/RNA-StableAI_HANDOFF_2026-10-18_V13.md"],
            "blockers": [
                "Limitations are documented across handoffs and this census, but the documentation "
                "is not frozen as a gate-review artifact and no gate review has occurred.",
                "Expression candidate design remains disabled and must stay so."]},
    }
    statuses = requirement_status(gate["requirements_before_stage3"], assignments)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out = ROOT/"results/stage2_band_coverage_census_runs"/stamp
    out.mkdir(parents=True, exist_ok=False)
    print(out, flush=True)
    write(out/"protocol.json", config)
    write(out/"band_records.json", sorted(band_rows, key=lambda row: (row["family_id"], row["id"])))
    write(out/"all_candidate_lineage.json", sorted(rows, key=lambda row: (row["family_id"], row["id"])))
    write(out/"family_clan_map.json",
          {family: {"clan_id": clan, "source_role": clan_provenance[family]}
           for family, clan in sorted(clan_map.items())})

    implementations = [Path(__file__), ROOT/"src/rnastable/stage2_census.py"]
    identities = {}
    for path in implementations:
        target = out/"source"/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        identities[str(path.relative_to(ROOT))] = sha(path)
    write(out/"identity.json",
          {"implementation": identities, "config_sha256": sha(args.config),
           "gate_sha256": sha(ROOT/config["gate"]),
           "sources": {entry["role"]: {"path": entry["path"], "sha256": entry["sha256"]}
                       for entry in config["sources"]}})

    summary = {"band": band, "scope": gate["active_length_nt"],
               "stage3_target": gate["stage3_target"], "ready_for_stage3": False,
               "in_scope_selected_records": len(in_scope_selected),
               "baseline_lineage": baseline,
               "coverage_by_band": coverage_by_band,
               "band_census": census, "band_resolution": verdict,
               "secondary_survey_band_families": secondary,
               "secondary_survey_note": "Family counts seen in the band by a second local survey. "
                                        "Their reference support was never screened by the frozen "
                                        "selection, so they are leads, not eligible records.",
               "gate_requirement_status": statuses,
               "requirements_satisfied": 0,
               "selection_changed": False, "new_inference_performed": False,
               "model_defaults_changed": False,
               "no_claim_permitted": config["no_claim_permitted"],
               "new_sequence_scoring_enabled": False, "stage3_ready": False,
               "interpretation": "Availability census over existing artifacts. No accuracy was "
                                 "measured and no gate requirement is satisfied."}
    write(out/"summary.json", summary)
    artifacts = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob("*")) if p.is_file()}
    write(out/"manifest.json", {"run": stamp, "artifacts": artifacts})
    print(json.dumps({"in_scope_selected_records": len(in_scope_selected),
                      "baseline_lineage": baseline,
                      "coverage_by_band": coverage_by_band,
                      "band_census": census, "band_resolution": verdict,
                      "secondary_survey_band_families": secondary,
                      "requirement_status": {row["requirement"][:48]: row["status"]
                                             for row in statuses}}, indent=2))


if __name__ == "__main__":
    main()
