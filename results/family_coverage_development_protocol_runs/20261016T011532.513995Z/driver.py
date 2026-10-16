#!/usr/bin/env python3
"""Derive a disclosed, label-informed development corpus from retained sources."""
# ruff: noqa: E402 -- standalone source bootstrap.

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp, write_artifact
from rnastable.native_journal import atomic_json
from rnastable.pair_reference import validate_pairs
from rnastable.prospective_binding import GAPS, bind_pair_reference, parse_stockholm, wuss_pairs
from rnastable.reference import digest
from rnastable.reference_audit import require
from rnastable.sequences import validate_sequence
from extend_family_provenance_dataset import audit as audit_extension
from prepare_family_provenance_dataset import overlap

NAME = "family_coverage_development"
FAMILY = "RF00022"


def freeze(extension_path):
    extension = audit_extension(extension_path)
    require(extension["complete"] and not extension["dataset_ready"]
            and extension["replacement_family"] == FAMILY,
            "Completed failed RF00022 development extension required")
    old_run = Path(extension["run_dir"])
    old_binding = json.loads((old_run / "binding.json").read_text())
    require(old_binding["supported_by_family"][FAMILY] == 0,
            "RF00022 failure must be recorded before this revision")
    extension_protocol = json.loads((old_run / "protocol.json").read_text())
    protocol_dir = Path(extension_protocol["run_dir"])
    config = json.loads((protocol_dir / "config.json").read_text())
    screening = json.loads((protocol_dir / "exposure.json").read_text())
    source = old_run / (FAMILY + ".sto")
    parse_stockholm(source.read_bytes(), FAMILY)
    run = ROOT / "results" / (NAME + "_protocol_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "extension.json", extension)
    atomic_json(run / "config.json", config)
    atomic_json(run / "exposure.json", screening)
    atomic_json(run / "policy.json", {
        "schema_version": 1,
        "stage": "development_label_informed_coverage_selection",
        "source_family": FAMILY,
        "observed_failure": "seven_fixed_sequence_first_candidates_lacked_complete_consensus_pairs",
        "candidate_order": "complete_coverage_then_lexicographic_sequence_id",
        "sequence_screen": "frozen_prior_exposure_and_selected_sequences_at_0.8",
        "candidate_cap": config["future_binding"]["train_candidate_cap_per_family"],
        "retain_prior_failed_runs": True,
        "source_retrieval": "already_hash_bound_in_extension_run",
        "new_downloads": False,
        "development_only": True,
        "independent_test_claim": False,
        "model_training_performed": False,
    })
    (run / "driver.py").write_bytes(Path(__file__).read_bytes())
    manifest = {"run_dir": str(run), "source_sha256": digest(source.read_bytes()),
                "extension_manifest_sha256": extension["manifest_sha256"],
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
            "Coverage protocol differs")
    require(set(manifest["snapshot_sha256"]) ==
            {"extension.json", "config.json", "exposure.json", "policy.json", "driver.py"},
            "Coverage protocol inventory differs")
    for name, sha in manifest["snapshot_sha256"].items():
        require(digest((run / name).read_bytes()) == sha, "Coverage snapshot changed")
    for name, sha in manifest["code_sha256"].items():
        require(digest(Path(name).read_bytes()) == sha, "Coverage builder changed")
    extension = audit_extension(Path(json.loads((run / "extension.json").read_text())["run_dir"]) / "summary.json")
    require(extension == json.loads((run / "extension.json").read_text())
            and extension["manifest_sha256"] == manifest["extension_manifest_sha256"],
            "Coverage extension changed")
    old_run = Path(extension["run_dir"])
    source = old_run / (FAMILY + ".sto")
    require(digest(source.read_bytes()) == manifest["source_sha256"],
            "Coverage source changed")
    extension_protocol = json.loads((old_run / "protocol.json").read_text())
    extension_dir = Path(extension_protocol["run_dir"])
    config = json.loads((extension_dir / "config.json").read_text())
    screening = json.loads((extension_dir / "exposure.json").read_text())
    require(config == json.loads((run / "config.json").read_text())
            and screening == json.loads((run / "exposure.json").read_text()),
            "Coverage inputs changed")
    policy = json.loads((run / "policy.json").read_text())
    require(policy == {
        "schema_version": 1, "stage": "development_label_informed_coverage_selection",
        "source_family": FAMILY,
        "observed_failure": "seven_fixed_sequence_first_candidates_lacked_complete_consensus_pairs",
        "candidate_order": "complete_coverage_then_lexicographic_sequence_id",
        "sequence_screen": "frozen_prior_exposure_and_selected_sequences_at_0.8",
        "candidate_cap": config["future_binding"]["train_candidate_cap_per_family"],
        "retain_prior_failed_runs": True,
        "source_retrieval": "already_hash_bound_in_extension_run",
        "new_downloads": False, "development_only": True,
        "independent_test_claim": False, "model_training_performed": False,
    }, "Coverage policy changed")
    return manifest


def coverage_selection(alignment, screening, policy):
    pairs, _ = wuss_pairs(alignment["consensus"])
    prior = sorted({r["sequence"] for r in screening})
    candidates, decisions = [], []
    for identity, aligned in sorted(alignment["sequences"].items()):
        sequence = "".join(c for c in aligned if c not in GAPS).upper().replace("T", "U")
        record = {"id": FAMILY + ":" + identity, "family_id": FAMILY,
                  "group": "family:" + FAMILY, "role": "train",
                  "sequence": sequence, "sequence_sha256": digest(sequence.encode())}
        missing = sum(aligned[i] in GAPS or aligned[j] in GAPS for i, j in pairs)
        if not policy["minimum_length"] <= len(sequence) <= policy["maximum_length"]:
            reason = "outside_declared_length_range"
        else:
            try:
                validate_sequence(sequence)
                reason = ("prior_sequence_exposure" if any(
                    overlap(sequence, old, policy["sequence_similarity_threshold"])
                    for old in prior) else "coverage_candidate")
            except ValueError:
                reason = "invalid_sequence"
        if reason == "coverage_candidate" and missing:
            reason = "incomplete_consensus_coverage"
        decisions.append({"id": record["id"], "reason": reason,
                          "missing_paired_columns": missing,
                          "sequence_sha256": record["sequence_sha256"]})
        if reason == "coverage_candidate":
            candidates.append(record)
    selected, selected_sequences = [], []
    cap = policy["train_candidate_cap_per_family"]
    for record in candidates:
        decision = next(r for r in decisions if r["id"] == record["id"])
        if len(selected) >= cap:
            decision["reason"] = "fixed_family_cap"
        elif any(overlap(record["sequence"], old, policy["sequence_similarity_threshold"])
                 for old in selected_sequences):
            decision["reason"] = "selected_sequence_redundancy"
        else:
            decision["reason"] = "selected_after_declared_coverage_filter"
            selected.append(record)
            selected_sequences.append(record["sequence"])
    return selected, decisions


def derive(protocol):
    pdir = Path(protocol["run_dir"])
    extension = json.loads((pdir / "extension.json").read_text())
    extension_run = Path(extension["run_dir"])
    source = (extension_run / (FAMILY + ".sto")).read_bytes()
    alignment = parse_stockholm(source, FAMILY)
    config = json.loads((pdir / "config.json").read_text())
    policy = config["future_binding"]
    screening = json.loads((pdir / "exposure.json").read_text())
    selected, decisions = coverage_selection(alignment, screening, policy)
    new_records = []
    for record in selected:
        bound = bind_pair_reference(record, alignment)
        validate_pairs(bound["pairs"], len(bound["sequence"]))
        new_records.append({**bound, "group": record["group"], "role": "train",
                            "reference_status": "ok"})
    old_protocol = json.loads((extension_run / "protocol.json").read_text())
    previous = json.loads((Path(old_protocol["run_dir"]) / "previous.json").read_text())
    original = json.loads((Path(previous["run_dir"]) / "binding.json").read_text())
    retained = [r for r in original["records"] if r["family_id"] != "RF00024"]
    retained_selected = [r for r in original["selected"] if r["family_id"] != "RF00024"]
    records = retained + new_records
    families = {f: n for f, n in original["supported_by_family"].items()
                if f != "RF00024"} | {FAMILY: len(new_records)}
    counts = {role: sum(r["reference_status"] == "ok" and r["role"] == role
                        for r in records) for role in ("train", "validation")}
    ready = (counts["train"] >= policy["minimum_supported_training_records"]
             and counts["validation"] >= policy["minimum_supported_validation_records"]
             and len(families) == 16
             and all(n >= policy["minimum_supported_per_selected_family"]
                     for n in families.values()))
    binding = {"selected": retained_selected + selected,
               "decisions": [r for r in original["decisions"] if r["family_id"] != "RF00024"]
               + [{**r, "family_id": FAMILY} for r in decisions],
               "records": records, "supported_by_role": counts,
               "supported_by_family": families, "dataset_ready": ready,
               "development_only": True, "label_informed_selection": True,
               "model_training_performed": False, "model_inference_performed": False,
               "independent_test_or_broad_validation_claim": False}
    require(len(binding["selected"]) == len(records), "Coverage denominator differs")
    datasets = {}
    for role in ("train", "validation"):
        datasets[role] = {"schema_version": 1, "format": "pair_set_zero_based_v1",
                          "dataset_id": "rfam_family_coverage_development_v1_" + role,
                          "role": role, "development_only": True,
                          "label_informed_selection": True,
                          "records": [{k: r[k] for k in ("id", "sequence", "pairs",
                                                        "family_id", "reference_kind", "source")}
                                      for r in records if r["role"] == role
                                      and r["reference_status"] == "ok"]}
    return binding, datasets


def build(protocol_path):
    protocol = audit_protocol(protocol_path)
    run = ROOT / "results" / (NAME + "_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "protocol.json", protocol)
    binding, datasets = derive(protocol)
    atomic_json(run / "binding.json", binding)
    for role, dataset in datasets.items():
        atomic_json(run / (role + ".json"), dataset)
    manifest = {"run_dir": str(run), "protocol_run": protocol["run_dir"],
                "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()}}
    atomic_json(run / "manifest.json", manifest)
    summary = {"complete": True, "run_dir": str(run),
               "manifest_sha256": digest((run / "manifest.json").read_bytes()),
               "selected_records": len(binding["selected"]),
               "supported_by_role": binding["supported_by_role"],
               "supported_replacement_family": binding["supported_by_family"][FAMILY],
               "dataset_ready": binding["dataset_ready"],
               "development_only": True, "label_informed_selection": True,
               "model_training_performed": False}
    atomic_json(run / "summary.json", summary)
    audit(run / "summary.json")
    write_artifact(ROOT / "results" / (NAME + "_summary.json"),
                   json.dumps(summary, indent=2) + "\n")
    return summary


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(summary == json.loads((run / "summary.json").read_text()),
            "Coverage summary differs")
    raw = (run / "manifest.json").read_bytes()
    require(digest(raw) == summary["manifest_sha256"], "Coverage manifest changed")
    manifest = json.loads(raw)
    protocol = audit_protocol(Path(manifest["protocol_run"]) / "manifest.json")
    require(protocol == json.loads((run / "protocol.json").read_text()),
            "Coverage protocol copy changed")
    require(set(manifest["snapshot_sha256"]) ==
            {"protocol.json", "binding.json", "train.json", "validation.json"},
            "Coverage output inventory differs")
    for name, sha in manifest["snapshot_sha256"].items():
        require(digest((run / name).read_bytes()) == sha,
                "Coverage output changed")
    binding, datasets = derive(protocol)
    require(binding == json.loads((run / "binding.json").read_text()),
            "Coverage selection replay differs")
    for role, dataset in datasets.items():
        require(dataset == json.loads((run / (role + ".json")).read_text()),
                "Coverage dataset differs")
    require(summary == {"complete": True, "run_dir": str(run),
                        "manifest_sha256": digest(raw),
                        "selected_records": len(binding["selected"]),
                        "supported_by_role": binding["supported_by_role"],
                        "supported_replacement_family": binding["supported_by_family"][FAMILY],
                        "dataset_ready": binding["dataset_ready"],
                        "development_only": True, "label_informed_selection": True,
                        "model_training_performed": False},
            "Coverage accounting differs")
    print("Coverage development dataset replay passed; no model fitting.")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--verify", type=Path)
    parser.add_argument("--extension", type=Path,
                        default=ROOT / "results/family_provenance_extension_summary.json")
    parser.add_argument("--protocol", type=Path,
                        default=ROOT / "results/family_coverage_development_protocol.json")
    args = parser.parse_args()
    if args.verify:
        audit(args.verify)
    elif args.build:
        build(args.protocol)
    else:
        freeze(args.extension)


if __name__ == "__main__":
    main()
