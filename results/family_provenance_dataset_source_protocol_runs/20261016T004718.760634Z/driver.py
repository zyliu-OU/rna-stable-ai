#!/usr/bin/env python3
"""Acquire and bind the frozen family development split without fitting a model."""
# ruff: noqa: E402 -- standalone source bootstrap.

import argparse
from difflib import SequenceMatcher
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp, write_artifact
from rnastable.exposures import collect_known_exposures
from rnastable.native_journal import atomic_json
from rnastable.pair_reference import validate_pairs
from rnastable.prospective_binding import GAPS, bind_pair_reference, parse_stockholm
from rnastable.prospective_data import bounded_download, sequence_overlap
from rnastable.reference import digest
from rnastable.reference_audit import require
from rnastable.sequences import validate_sequence
from plan_family_provenance_dataset import audit as audit_metadata

NAME = "family_provenance_dataset_source"
MAX_SOURCE_BYTES = 32 * 1024 * 1024
TIMEOUT_SECONDS = 30


def planned(metadata):
    require(metadata["successful_metadata_records"] == metadata["planned_metadata_requests"]
            and metadata["selection"]["metadata_ready"], "Complete frozen metadata required")
    rows = metadata["selection"]["selected_families"]
    require(len(rows) == 16 and sum(r["role"] == "train" for r in rows) == 12
            and sum(r["role"] == "validation" for r in rows) == 4,
            "Fixed family split differs")
    require(len({r["group"] for r in rows}) == len(rows), "Split groups overlap")
    return rows


def freeze(metadata_path):
    metadata = audit_metadata(metadata_path)
    rows = planned(metadata)
    metadata_run = Path(metadata["run_dir"])
    metadata_manifest = json.loads((metadata_run / "manifest.json").read_text())
    protocol_run = Path(metadata_manifest["protocol_run"])
    config = json.loads((protocol_run / "config.json").read_text())
    before = json.loads((protocol_run / "exposure.json").read_text())
    require(collect_known_exposures(ROOT) == before,
            "Exposure ledger changed since metadata freeze; replan before source access")
    run = ROOT / "results" / (NAME + "_protocol_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    requests = [{**row, "filename": row["family_id"] + ".sto",
                 "url": f"https://rfam.org/family/{row['family_id']}/alignment/stockholm"}
                for row in rows]
    atomic_json(run / "metadata.json", metadata)
    atomic_json(run / "config.json", config)
    atomic_json(run / "exposure.json", before)
    atomic_json(run / "requests.json", requests)
    (run / "driver.py").write_bytes(Path(__file__).read_bytes())
    manifest = {
        "run_dir": str(run),
        "metadata_summary_sha256": digest((metadata_run / "summary.json").read_bytes()),
        "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
        "code_sha256": {str(Path(__file__)): digest(Path(__file__).read_bytes())},
    }
    atomic_json(run / "manifest.json", manifest)
    audit_protocol(run / "manifest.json")
    write_artifact(ROOT / "results" / (NAME + "_protocol.json"),
                   json.dumps(manifest, indent=2) + "\n")
    return manifest


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    require(manifest == json.loads((run / "manifest.json").read_text()),
            "Source protocol differs")
    require(set(manifest["snapshot_sha256"]) ==
            {"metadata.json", "config.json", "exposure.json", "requests.json", "driver.py"},
            "Source protocol inventory differs")
    for name, sha in manifest["snapshot_sha256"].items():
        require(digest((run / name).read_bytes()) == sha, "Source protocol snapshot changed")
    for name, sha in manifest["code_sha256"].items():
        require(digest(Path(name).read_bytes()) == sha, "Source builder changed")
    metadata = audit_metadata(Path(json.loads((run / "metadata.json").read_text())["run_dir"]) / "summary.json")
    require(metadata == json.loads((run / "metadata.json").read_text())
            and digest((Path(metadata["run_dir"]) / "summary.json").read_bytes())
            == manifest["metadata_summary_sha256"], "Source metadata changed")
    requests = json.loads((run / "requests.json").read_text())
    require(requests == [{**r, "filename": r["family_id"] + ".sto",
                          "url": f"https://rfam.org/family/{r['family_id']}/alignment/stockholm"}
                         for r in planned(metadata)], "Source request plan differs")
    return manifest


def select_and_bind(run, protocol, attempts):
    pdir = Path(protocol["run_dir"])
    config = json.loads((pdir / "config.json").read_text())
    policy = config["future_binding"]
    exposures = json.loads((pdir / "exposure.json").read_text())
    old_sequences = sorted({r["sequence"] for r in exposures})
    accepted = []
    selected, decisions, records = [], [], []
    for attempt in attempts:
        family, role = attempt["family_id"], attempt["role"]
        alignment = parse_stockholm((run / attempt["filename"]).read_bytes(), family)
        clan = attempt["group"].split(":", 1)[1] if attempt["group"].startswith("clan:") else None
        require(alignment["annotations"].get("CL", []) == ([] if clan is None else [clan]),
                "Stockholm clan differs from frozen metadata")
        cap = policy["train_candidate_cap_per_family"] if role == "train" else policy["validation_candidate_cap_per_family"]
        count = 0
        for identity, aligned in sorted(alignment["sequences"].items()):
            sequence = "".join(c for c in aligned if c not in GAPS).upper().replace("T", "U")
            record = {"id": family + ":" + identity, "family_id": family,
                      "group": attempt["group"], "role": role, "sequence": sequence,
                      "sequence_sha256": digest(sequence.encode())}
            if count >= cap:
                reason = "fixed_family_cap"
            elif not policy["minimum_length"] <= len(sequence) <= policy["maximum_length"]:
                reason = "outside_declared_length_range"
            else:
                try:
                    validate_sequence(sequence)
                    if any(overlap(sequence, old, policy["sequence_similarity_threshold"])
                           for old in old_sequences):
                        reason = "prior_sequence_exposure"
                    elif any(overlap(sequence, old, policy["sequence_similarity_threshold"])
                             for old in accepted):
                        reason = "selected_sequence_redundancy"
                    else:
                        reason = "selected_before_pair_parsing"
                except ValueError:
                    reason = "invalid_sequence"
            decisions.append({"id": record["id"], "family_id": family, "role": role,
                              "reason": reason, "sequence_sha256": record["sequence_sha256"]})
            if reason == "selected_before_pair_parsing":
                count += 1
                accepted.append(sequence)
                selected.append(record)
        # Pair parsing follows fixed sequence selection. Unsupported rows stay in place.
        for record in [r for r in selected if r["family_id"] == family]:
            try:
                bound = bind_pair_reference(record, alignment)
                validate_pairs(bound["pairs"], len(bound["sequence"]))
                records.append({**bound, "group": record["group"], "role": role,
                                "reference_status": "ok"})
            except (ValueError, KeyError, TypeError) as exc:
                records.append({**record, "reference_status": "unsupported_reference",
                                "error": type(exc).__name__ + ": " + str(exc)})
        print(f"Screened {family}: {count} fixed candidates", flush=True)
    require(len(records) == len(selected), "Fixed selection denominator changed")
    counts = {role: sum(r["reference_status"] == "ok" and r["role"] == role
                        for r in records) for role in ("train", "validation")}
    per_family = {a["family_id"]: sum(r["reference_status"] == "ok" and
                                       r["family_id"] == a["family_id"] for r in records)
                  for a in attempts}
    ready = (counts["train"] >= policy["minimum_supported_training_records"]
             and counts["validation"] >= policy["minimum_supported_validation_records"]
             and all(n >= policy["minimum_supported_per_selected_family"]
                     for n in per_family.values()))
    return {"selected": selected, "decisions": decisions, "records": records,
            "supported_by_role": counts, "supported_by_family": per_family,
            "dataset_ready": ready, "model_training_performed": False,
            "model_inference_performed": False,
            "independent_test_or_broad_validation_claim": False}


def overlap(first, second, threshold):
    # quick_ratio is an upper bound on both directed ratios used by the
    # existing heuristic. It can only skip comparisons that cannot pass.
    if 2 * min(len(first), len(second)) < threshold * (len(first) + len(second)):
        return False
    if first == second:
        return True
    if SequenceMatcher(None, first, second, autojunk=False).quick_ratio() < threshold:
        return False
    return sequence_overlap(first, second, threshold)


def acquire(protocol_path, reuse_sources=None):
    protocol = audit_protocol(protocol_path)
    pdir = Path(protocol["run_dir"])
    require(collect_known_exposures(ROOT) == json.loads((pdir / "exposure.json").read_text()),
            "Exposure ledger changed since source freeze")
    run = ROOT / "results" / (NAME + "_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "protocol.json", protocol)
    attempts = [{**r, "status": "not_started"}
                for r in json.loads((pdir / "requests.json").read_text())]
    reused = None
    if reuse_sources is not None:
        source = Path(reuse_sources)
        reused = json.loads((source / "attempts.json").read_text())
        require(len(reused) == len(attempts) and all(
            all(old.get(k) == v for k, v in new.items()) and old["status"] == "ok"
            and digest((source / old["filename"]).read_bytes()) == old["sha256"]
            for old, new in zip(reused, attempts, strict=True)),
            "Retained source requests or response hashes differ")
    atomic_json(run / "attempts.json", attempts)
    for index, attempt in enumerate(attempts):
        attempt["status"] = "started"
        atomic_json(run / "attempts.json", attempts)
        try:
            content = ((Path(reuse_sources) / attempt["filename"]).read_bytes()
                       if reused is not None else
                       bounded_download(attempt["url"], MAX_SOURCE_BYTES, TIMEOUT_SECONDS))
            parse_stockholm(content, attempt["family_id"])
            (run / attempt["filename"]).write_bytes(content)
            attempt["sha256"] = digest(content)
            attempt["status"] = "ok"
        except (OSError, ValueError, KeyError, TypeError) as exc:
            attempt.update(status="error", error=type(exc).__name__ + ": " + str(exc))
        atomic_json(run / "attempts.json", attempts)
        print(attempt["family_id"] + ": " + attempt["status"], flush=True)
    complete = all(a["status"] == "ok" for a in attempts)
    binding = select_and_bind(run, protocol, attempts) if complete else None
    if binding is not None:
        atomic_json(run / "binding.json", binding)
    manifest = {"run_dir": str(run), "protocol_run": str(pdir),
                "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()}}
    atomic_json(run / "manifest.json", manifest)
    summary = {"complete": complete, "run_dir": str(run),
               "manifest_sha256": digest((run / "manifest.json").read_bytes()),
               "planned_sources": len(attempts), "successful_sources": sum(a["status"] == "ok" for a in attempts),
               "selected_records": len(binding["selected"]) if binding else 0,
               "supported_by_role": binding["supported_by_role"] if binding else None,
               "dataset_ready": binding["dataset_ready"] if binding else False,
               "model_training_performed": False, "model_inference_performed": False}
    atomic_json(run / "summary.json", summary)
    audit(run / "summary.json")
    write_artifact(ROOT / "results" / (NAME + "_summary.json"),
                   json.dumps(summary, indent=2) + "\n")
    return summary


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(summary == json.loads((run / "summary.json").read_text()), "Source summary differs")
    raw = (run / "manifest.json").read_bytes()
    require(digest(raw) == summary["manifest_sha256"], "Source manifest changed")
    manifest = json.loads(raw)
    protocol = audit_protocol(Path(manifest["protocol_run"]) / "manifest.json")
    require(protocol == json.loads((run / "protocol.json").read_text()), "Source protocol copy differs")
    attempts = json.loads((run / "attempts.json").read_text())
    requests = json.loads((Path(protocol["run_dir"]) / "requests.json").read_text())
    require(len(attempts) == len(requests) and
            all(all(a.get(k) == v for k, v in r.items()) and a["status"] in ("ok", "error")
                for a, r in zip(attempts, requests, strict=True)), "Source attempts differ")
    expected = {"protocol.json", "attempts.json"} | {a["filename"] for a in attempts if "sha256" in a}
    complete = all(a["status"] == "ok" for a in attempts)
    if complete:
        expected.add("binding.json")
    require(set(manifest["snapshot_sha256"]) == expected, "Source file inventory differs")
    for name, sha in manifest["snapshot_sha256"].items():
        require(digest((run / name).read_bytes()) == sha, "Source snapshot changed: " + name)
    for attempt in attempts:
        if attempt["status"] == "ok":
            require(digest((run / attempt["filename"]).read_bytes()) == attempt["sha256"],
                    "Source response changed")
            parse_stockholm((run / attempt["filename"]).read_bytes(), attempt["family_id"])
    binding = select_and_bind(run, protocol, attempts) if complete else None
    if binding is not None:
        require(binding == json.loads((run / "binding.json").read_text()),
                "Source selection or annotation binding replay differs")
    require(summary == {"complete": complete, "run_dir": str(run),
                        "manifest_sha256": digest(raw), "planned_sources": len(attempts),
                        "successful_sources": sum(a["status"] == "ok" for a in attempts),
                        "selected_records": len(binding["selected"]) if binding else 0,
                        "supported_by_role": binding["supported_by_role"] if binding else None,
                        "dataset_ready": binding["dataset_ready"] if binding else False,
                        "model_training_performed": False, "model_inference_performed": False},
            "Source accounting differs")
    print("Family source replay passed; no model fitting or inference.")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--acquire", action="store_true")
    mode.add_argument("--verify", type=Path)
    parser.add_argument("--metadata", type=Path,
                        default=ROOT / "results/family_provenance_dataset_metadata_summary.json")
    parser.add_argument("--protocol", type=Path,
                        default=ROOT / "results/family_provenance_dataset_source_protocol.json")
    parser.add_argument("--reuse-sources", type=Path,
                        help="Reuse a complete hash-checked response set from an interrupted run")
    args = parser.parse_args()
    if args.verify:
        audit(args.verify)
    elif args.acquire:
        acquire(args.protocol, args.reuse_sources)
    else:
        freeze(args.metadata)


if __name__ == "__main__":
    main()
