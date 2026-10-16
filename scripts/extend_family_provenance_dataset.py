#!/usr/bin/env python3
"""Version the failed development split and screen one declared replacement family."""
# ruff: noqa: E402 -- standalone source bootstrap.

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp, write_artifact
from rnastable.native_journal import atomic_json
from rnastable.prospective_data import bounded_download
from rnastable.prospective_binding import parse_stockholm
from rnastable.reference import digest
from rnastable.reference_audit import require
from prepare_family_provenance_dataset import (
    MAX_SOURCE_BYTES,
    TIMEOUT_SECONDS,
    audit as audit_source,
    select_and_bind,
)

NAME = "family_provenance_extension"
EXCLUDED_FAMILY = "RF00024"


def extension_plan(previous, metadata):
    """Use the first previously ranked unused group; label feedback is explicit."""
    require(previous["complete"] and not previous["dataset_ready"],
            "Extension requires completed failed development source run")
    prior = json.loads((Path(previous["run_dir"]) / "binding.json").read_text())
    selected = metadata["selection"]["selected_families"]
    require(len(selected) == 16 and {r["family_id"] for r in selected}
            == set(prior["supported_by_family"]), "Prior split differs")
    failed = next((r for r in selected if r["family_id"] == EXCLUDED_FAMILY), None)
    require(failed is not None and failed["role"] == "train"
            and prior["supported_by_family"][EXCLUDED_FAMILY] == 0,
            "Declared failure not observed")
    used = {r["group"] for r in selected}
    group = next((g for g in metadata["selection"]["ranked_groups"] if g not in used), None)
    require(group is not None, "No unused ranked metadata group")
    candidates = [d["family_id"] for d in metadata["selection"]["decisions"]
                  if d["group"] == group and d["reason"] == "metadata_eligible"]
    require(candidates, "Replacement group has no eligible representative")
    row = {"group": group, "family_id": min(candidates), "role": "train"}
    require(row == {"group": "family:RF00022", "family_id": "RF00022", "role": "train"},
            "Ranked replacement changed")
    return row


def freeze(previous_path, metadata_path):
    previous = audit_source(previous_path)
    metadata = json.loads(Path(metadata_path).read_text())
    row = extension_plan(previous, metadata)
    old_run = Path(previous["run_dir"])
    old_protocol = json.loads((old_run / "protocol.json").read_text())
    old_protocol_dir = Path(old_protocol["run_dir"])
    require(metadata == json.loads((old_protocol_dir / "metadata.json").read_text()),
            "Extension metadata differs from audited prior split")
    config = json.loads((old_protocol_dir / "config.json").read_text())
    exposure = json.loads((old_protocol_dir / "exposure.json").read_text())
    old_binding = json.loads((old_run / "binding.json").read_text())
    retained = [r for r in old_binding["selected"] if r["family_id"] != EXCLUDED_FAMILY]
    require(len(retained) == len(old_binding["selected"]) - 12,
            "Excluded family candidate denominator changed")
    screening = exposure + [{"sequence": r["sequence"], "family_id": r["family_id"],
                             "source": "fixed_previous_development_selection"} for r in retained]
    run = ROOT / "results" / (NAME + "_protocol_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    request = {**row, "filename": row["family_id"] + ".sto",
               "url": f"https://rfam.org/family/{row['family_id']}/alignment/stockholm"}
    atomic_json(run / "previous.json", previous)
    atomic_json(run / "metadata.json", metadata)
    atomic_json(run / "config.json", config)
    atomic_json(run / "exposure.json", screening)
    atomic_json(run / "request.json", request)
    atomic_json(run / "policy.json", {
        "schema_version": 1,
        "excluded_family": EXCLUDED_FAMILY,
        "exclusion_reason": "observed_zero_complete_references_in_prior_development_run",
        "replacement_order": "first_unused_ranked_metadata_group",
        "retained_prior_records_unchanged": True,
        "new_label_outcomes_cannot_trigger_replacement": True,
        "development_only": True,
        "independent_test_claim": False,
        "model_training_performed": False,
    })
    (run / "driver.py").write_bytes(Path(__file__).read_bytes())
    manifest = {"run_dir": str(run),
                "prior_manifest_sha256": previous["manifest_sha256"],
                "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
                "code_sha256": {str(Path(__file__)): digest(Path(__file__).read_bytes())}}
    atomic_json(run / "manifest.json", manifest)
    audit_protocol(run / "manifest.json")
    write_artifact(ROOT / "results" / (NAME + "_protocol.json"),
                   json.dumps(manifest, indent=2) + "\n")
    return manifest


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    require(manifest == json.loads((run / "manifest.json").read_text()),
            "Extension protocol differs")
    require(set(manifest["snapshot_sha256"]) ==
            {"previous.json", "metadata.json", "config.json", "exposure.json",
             "request.json", "policy.json", "driver.py"},
            "Extension protocol inventory differs")
    for name, sha in manifest["snapshot_sha256"].items():
        require(digest((run / name).read_bytes()) == sha, "Extension snapshot changed")
    for name, sha in manifest["code_sha256"].items():
        require(digest(Path(name).read_bytes()) == sha, "Extension builder changed")
    previous = audit_source(Path(json.loads((run / "previous.json").read_text())["run_dir"]) / "summary.json")
    require(previous == json.loads((run / "previous.json").read_text())
            and previous["manifest_sha256"] == manifest["prior_manifest_sha256"],
            "Extension prior run changed")
    metadata = json.loads((run / "metadata.json").read_text())
    row = extension_plan(previous, metadata)
    request = {**row, "filename": row["family_id"] + ".sto",
               "url": f"https://rfam.org/family/{row['family_id']}/alignment/stockholm"}
    require(json.loads((run / "request.json").read_text()) == request,
            "Extension request changed")
    policy = json.loads((run / "policy.json").read_text())
    require(policy == {"schema_version": 1, "excluded_family": EXCLUDED_FAMILY,
                       "exclusion_reason": "observed_zero_complete_references_in_prior_development_run",
                       "replacement_order": "first_unused_ranked_metadata_group",
                       "retained_prior_records_unchanged": True,
                       "new_label_outcomes_cannot_trigger_replacement": True,
                       "development_only": True, "independent_test_claim": False,
                       "model_training_performed": False}, "Extension policy changed")
    old_run = Path(previous["run_dir"])
    old_protocol = json.loads((old_run / "protocol.json").read_text())
    old_dir = Path(old_protocol["run_dir"])
    require(metadata == json.loads((old_dir / "metadata.json").read_text()),
            "Extension metadata differs from prior split")
    config = json.loads((old_dir / "config.json").read_text())
    before = json.loads((old_dir / "exposure.json").read_text())
    binding = json.loads((old_run / "binding.json").read_text())
    retained = [r for r in binding["selected"] if r["family_id"] != EXCLUDED_FAMILY]
    screening = before + [{"sequence": r["sequence"], "family_id": r["family_id"],
                           "source": "fixed_previous_development_selection"} for r in retained]
    require(config == json.loads((run / "config.json").read_text())
            and screening == json.loads((run / "exposure.json").read_text()),
            "Extension screening inputs changed")
    return manifest


def combine(previous_binding, added, policy):
    retained_records = [r for r in previous_binding["records"]
                        if r["family_id"] != EXCLUDED_FAMILY]
    retained_selected = [r for r in previous_binding["selected"]
                         if r["family_id"] != EXCLUDED_FAMILY]
    retained_decisions = [r for r in previous_binding["decisions"]
                          if r["family_id"] != EXCLUDED_FAMILY]
    records = retained_records + added["records"]
    families = {k: v for k, v in previous_binding["supported_by_family"].items()
                if k != EXCLUDED_FAMILY} | added["supported_by_family"]
    counts = {role: sum(r["reference_status"] == "ok" and r["role"] == role
                        for r in records) for role in ("train", "validation")}
    require(len(families) == 16 and len(records) == len(retained_selected) + len(added["selected"]),
            "Extension fixed denominator differs")
    return {"selected": retained_selected + added["selected"],
            "decisions": retained_decisions + added["decisions"],
            "records": records, "supported_by_role": counts,
            "supported_by_family": families,
            "dataset_ready": counts["train"] >= policy["minimum_supported_training_records"]
            and counts["validation"] >= policy["minimum_supported_validation_records"]
            and all(n >= policy["minimum_supported_per_selected_family"]
                    for n in families.values()),
            "development_only": True, "model_training_performed": False,
            "model_inference_performed": False,
            "independent_test_or_broad_validation_claim": False}


def acquire(protocol_path):
    protocol = audit_protocol(protocol_path)
    pdir = Path(protocol["run_dir"])
    request = json.loads((pdir / "request.json").read_text())
    run = ROOT / "results" / (NAME + "_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "protocol.json", protocol)
    attempt = {**request, "status": "started"}
    atomic_json(run / "attempt.json", attempt)
    try:
        content = bounded_download(request["url"], MAX_SOURCE_BYTES, TIMEOUT_SECONDS)
        parse_stockholm(content, request["family_id"])
        (run / request["filename"]).write_bytes(content)
        attempt.update(status="ok", sha256=digest(content))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        attempt.update(status="error", error=type(exc).__name__ + ": " + str(exc))
    atomic_json(run / "attempt.json", attempt)
    print(request["family_id"] + ": " + attempt["status"], flush=True)
    binding = None
    if attempt["status"] == "ok":
        added = select_and_bind(run, protocol, [attempt])
        previous = json.loads((pdir / "previous.json").read_text())
        old = json.loads((Path(previous["run_dir"]) / "binding.json").read_text())
        config = json.loads((pdir / "config.json").read_text())
        binding = combine(old, added, config["future_binding"])
        atomic_json(run / "binding.json", binding)
    manifest = {"run_dir": str(run), "protocol_run": str(pdir),
                "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()}}
    atomic_json(run / "manifest.json", manifest)
    summary = {"complete": attempt["status"] == "ok", "run_dir": str(run),
               "manifest_sha256": digest((run / "manifest.json").read_bytes()),
               "replacement_family": request["family_id"],
               "selected_records": len(binding["selected"]) if binding else 0,
               "supported_by_role": binding["supported_by_role"] if binding else None,
               "dataset_ready": binding["dataset_ready"] if binding else False,
               "development_only": True, "model_training_performed": False}
    atomic_json(run / "summary.json", summary)
    audit(run / "summary.json")
    write_artifact(ROOT / "results" / (NAME + "_summary.json"),
                   json.dumps(summary, indent=2) + "\n")
    return summary


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(summary == json.loads((run / "summary.json").read_text()),
            "Extension summary differs")
    raw = (run / "manifest.json").read_bytes()
    require(digest(raw) == summary["manifest_sha256"], "Extension manifest changed")
    manifest = json.loads(raw)
    protocol = audit_protocol(Path(manifest["protocol_run"]) / "manifest.json")
    pdir = Path(protocol["run_dir"])
    require(protocol == json.loads((run / "protocol.json").read_text()),
            "Extension protocol copy changed")
    request = json.loads((pdir / "request.json").read_text())
    attempt = json.loads((run / "attempt.json").read_text())
    require(all(attempt.get(k) == v for k, v in request.items())
            and attempt["status"] in ("ok", "error"), "Extension attempt differs")
    complete = attempt["status"] == "ok"
    expected = {"protocol.json", "attempt.json"}
    if complete:
        expected |= {request["filename"], "binding.json"}
    require(set(manifest["snapshot_sha256"]) == expected,
            "Extension response inventory differs")
    for name, sha in manifest["snapshot_sha256"].items():
        require(digest((run / name).read_bytes()) == sha,
                "Extension response or binding changed")
    binding = None
    if complete:
        content = (run / request["filename"]).read_bytes()
        require(digest(content) == attempt["sha256"], "Extension source changed")
        parse_stockholm(content, request["family_id"])
        added = select_and_bind(run, protocol, [attempt])
        previous = json.loads((pdir / "previous.json").read_text())
        old = json.loads((Path(previous["run_dir"]) / "binding.json").read_text())
        config = json.loads((pdir / "config.json").read_text())
        binding = combine(old, added, config["future_binding"])
        require(binding == json.loads((run / "binding.json").read_text()),
                "Extension binding replay differs")
    require(summary == {"complete": complete, "run_dir": str(run),
                        "manifest_sha256": digest(raw),
                        "replacement_family": request["family_id"],
                        "selected_records": len(binding["selected"]) if binding else 0,
                        "supported_by_role": binding["supported_by_role"] if binding else None,
                        "dataset_ready": binding["dataset_ready"] if binding else False,
                        "development_only": True, "model_training_performed": False},
            "Extension accounting differs")
    print("Development-only extension replay passed; no model fitting.")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--acquire", action="store_true")
    mode.add_argument("--verify", type=Path)
    parser.add_argument("--previous", type=Path,
                        default=ROOT / "results/family_provenance_dataset_source_summary.json")
    parser.add_argument("--metadata", type=Path,
                        default=ROOT / "results/family_provenance_dataset_metadata_summary.json")
    parser.add_argument("--protocol", type=Path,
                        default=ROOT / "results/family_provenance_extension_protocol.json")
    args = parser.parse_args()
    if args.verify:
        audit(args.verify)
    elif args.acquire:
        acquire(args.protocol)
    else:
        freeze(args.previous, args.metadata)


if __name__ == "__main__":
    main()
