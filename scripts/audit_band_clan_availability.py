"""Decide whether clan-separated 2000-2999 nt coverage is achievable upstream.

Reads pinned Rfam and RCSB sources, validates the Rfam consensus-length column
against independently known family sizes, scans every seed alignment by
ungapped sequence length, classifies the RCSB band by description, and reports
whether the gate's sparse-band requirement is achievable from those sources.
Runs no inference, selects no sequence and cannot satisfy or amend a gate.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

from rnastable.band_availability import (
    achievability_verdict, parse_clan_membership, parse_family_metadata,
    rfam_band_availability, scan_seed_band, summarize_rcsb, validate_consensus_lengths,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT/"configs/stage2_band_clan_availability_census_v2_2026-10-19.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, obj):
    with Path(path).open("x") as f:
        f.write(json.dumps(obj, indent=2, allow_nan=False)+"\n")


def source(config, role):
    run = ROOT/config["source_run"]
    for entry in config["sources"]:
        if entry["role"] == role:
            path = run/entry["file"]
            if sha(path) != entry["sha256"]:
                raise ValueError(f"Pinned source changed: {entry['file']}")
            return path
    raise ValueError(f"Config declares no source for role {role}")


def locally_held_band_records(config):
    """Band record identities the v1 census already held, by sequence accession.

    The v1 ids are 'RF#####:accession/range'; the Rfam seed names carry the
    accession part alone, so compare on that.
    """
    run = ROOT/config["local_comparison"]["v1_census_run"]
    manifest = json.loads((run/"manifest.json").read_text())["artifacts"]
    relative = "band_records.json"
    if sha(run/relative) != manifest[relative]:
        raise ValueError("v1 census band records altered")
    held = {}
    for row in json.loads((run/relative).read_text()):
        identity = row["id"]
        accession = identity.split(":", 1)[1] if ":" in identity else identity
        held[accession] = {"id": identity, "decision": row["decision"],
                           "exposed": row["exposed"], "family_id": row["family_id"]}
    return held


def verify(run):
    """Re-check artifact hashes and replay the verdict from stored counts."""
    manifest = json.loads((run/"manifest.json").read_text())
    for name, expected in manifest["artifacts"].items():
        path = run/name
        if not path.resolve().is_relative_to(run.resolve()) or sha(path) != expected:
            raise ValueError(f"Artifact checksum mismatch: {name}")
    summary = json.loads((run/"summary.json").read_text())
    replayed = achievability_verdict(summary["rfam"], summary["rcsb"],
                                     summary["gate_requirement_under_test"])
    if replayed != summary["verdict"]:
        raise ValueError("Stored verdict does not replay from stored counts")
    if summary["verdict"]["requirement_satisfied"] or summary["verdict"]["gate_amended"]:
        raise ValueError("A census must not satisfy or amend a gate requirement")
    result = {"artifacts_verified": len(manifest["artifacts"]),
              "state": replayed["state"],
              "achievable_from_surveyed_sources": replayed["achievable_from_surveyed_sources"],
              "mode": "artifact and stored-count audit; no new download or inference"}
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
                 "gate_amended", "new_sequence_scoring_enabled",
                 "expression_candidate_design_enabled", "stage3_ready"):
        if config[flag]:
            raise ValueError(f"Census must not set {flag}")
    gate = json.loads((ROOT/config["gate"]).read_text())
    requirement = config["gate_requirement_under_test"]
    if requirement not in gate["requirements_before_stage3"]:
        raise ValueError("Requirement under test is not a gate requirement")
    band = config["band"]
    if band["maximum_exclusive"] != gate["active_length_nt"]["maximum_exclusive"]:
        raise ValueError("Census band must end at the active scope boundary")

    rfam_method = config["rfam_method"]
    clan_map = parse_clan_membership(source(config, "rfam_clan_membership"))
    families, skipped = parse_family_metadata(source(config, "rfam_family_metadata"))
    if skipped and rfam_method["parse_integrity_requirement"]:
        raise ValueError(f"Family metadata parse skipped {skipped} rows")
    checks = validate_consensus_lengths(families, rfam_method["validation_families"],
                                        rfam_method["validation_tolerance_nt"])
    seed_band = scan_seed_band(source(config, "rfam_seed_alignments"), band)
    held = locally_held_band_records(config)
    rfam = rfam_band_availability(seed_band, clan_map, config["baseline_clans"]["clans"], held)

    rcsb_method = config["rcsb_method"]
    response = json.loads(source(config, "rcsb_band_response").read_text())
    rcsb = summarize_rcsb(response, rcsb_method["ribosomal_keywords"],
                          rcsb_method["generic_patterns"])
    verdict = achievability_verdict(rfam, rcsb, requirement)

    band_families = {a: f for a, f in families.items()
                     if band["minimum_inclusive"] <= f["clen"] < band["maximum_exclusive"]}
    over_1000 = {a: dict(f, clan_id=clan_map.get(a)) for a, f in families.items()
                 if f["clen"] >= 1000}
    buckets = {"<500": 0, "500-999": 0, "1000-1999": 0, "2000-2999": 0, ">=3000": 0}
    for f in families.values():
        c = f["clen"]
        key = ("<500" if c < 500 else "500-999" if c < 1000 else "1000-1999" if c < 2000
               else "2000-2999" if c < 3000 else ">=3000")
        buckets[key] += 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out = ROOT/"results/band_clan_availability_runs"/stamp
    out.mkdir(parents=True, exist_ok=False)
    print(out, flush=True)
    write(out/"protocol.json", config)
    write(out/"rfam_consensus_length_validation.json", checks)
    write(out/"rfam_families_over_1000nt.json", dict(sorted(over_1000.items())))
    write(out/"rfam_seed_band_sequences.json", seed_band)
    write(out/"rcsb_band_classification.json", rcsb)

    implementations = [Path(__file__), ROOT/"src/rnastable/band_availability.py"]
    identities = {}
    for path in implementations:
        target = out/"source"/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        identities[str(path.relative_to(ROOT))] = sha(path)
    write(out/"identity.json",
          {"implementation": identities, "config_sha256": sha(args.config),
           "gate_sha256": sha(ROOT/config["gate"]),
           "source_run": config["source_run"],
           "source_manifest_sha256": sha(ROOT/config["source_run"]/"manifest.json"),
           "sources": {e["role"]: {"file": e["file"], "sha256": e["sha256"]}
                       for e in config["sources"]},
           "v1_census_run": config["local_comparison"]["v1_census_run"]})

    summary = {"band": band, "gate_requirement_under_test": requirement,
               "baseline_clans": config["baseline_clans"]["clans"],
               "rfam": rfam, "rcsb": rcsb, "verdict": verdict,
               "rfam_families_parsed": len(families),
               "rfam_rows_skipped": skipped,
               "rfam_clan_memberships": len(clan_map),
               "rfam_distinct_clans": len(set(clan_map.values())),
               "rfam_consensus_length_buckets": buckets,
               "rfam_band_length_families": {a: dict(f, clan_id=clan_map.get(a))
                                             for a, f in sorted(band_families.items())},
               "rfam_consensus_length_validation_passed": len(checks),
               "locally_held_band_records": len(held),
               "surveyed_sources": [e["role"] for e in config["sources"]],
               "not_surveyed": ["Rfam full alignments",
                                "RCSB entities outside the queried length range",
                                "sources other than Rfam and RCSB"],
               "requirement_satisfied": False, "gate_amended": False,
               "selection_changed": False, "new_inference_performed": False,
               "new_sequence_scoring_enabled": False, "stage3_ready": False,
               "no_claim_permitted": config["no_claim_permitted"],
               "interpretation": "Availability census across pinned upstream sources. No accuracy "
                                 "was measured, no gate requirement is satisfied, and no gate was "
                                 "amended."}
    write(out/"summary.json", summary)
    artifacts = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob("*")) if p.is_file()}
    write(out/"manifest.json", {"run": stamp, "artifacts": artifacts})
    print(json.dumps({k: summary[k] for k in
                      ("rfam_families_parsed", "rfam_rows_skipped",
                       "rfam_consensus_length_buckets", "rfam_band_length_families",
                       "locally_held_band_records", "verdict")}, indent=2))


if __name__ == "__main__":
    main()
