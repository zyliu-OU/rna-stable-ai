#!/usr/bin/env python3
"""Run the predeclared six-method, six-family raw-contact feasibility comparison."""
# ruff: noqa: E402 -- standalone source bootstrap.

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import publish, timestamp
from rnastable.context_inference import decode_loaded
from rnastable.exposures import (
    collect_known_exposures,
    record_exposure,
    read_exposure,
    exposure_records,
)
from rnastable.folding import fold_sequence
from rnastable.native_journal import (
    NativeJournal,
    atomic_json,
    canonical,
    exclusive_driver,
)
from rnastable.pooled_native import native_runtime
from rnastable.reference import digest, METRICS
from rnastable.reference_audit import require
from evaluate_prospective_panel import (
    models,
    score,
    native_accounting,
    METHODS,
    FOLDING,
    PAIR_FORMAT,
)
from evaluate_degradation_pilot import environment
from prepare_raw_structure_references import audit as audit_references
from verify_raw_structure_identity import audit as audit_identity

NAME = "raw_structure_feasibility"
POLICY = (
    "Predeclared six-family structure-derived feasibility only. Original three seed-20261006 "
    "checkpoints, exact top16 decoding and zero penalty; all-unpaired and two bounded native controls. "
    "All selected records and six methods remain in denominators; source exclusions stay separate. "
    "No fitting, calibration, checkpoint selection, contact projection, or broad validation/stability claim."
)


def exposure_keys(rows):
    return {
        (r["sequence"], r.get("family_id"), r.get("pdb_accession", "").lower())
        for r in rows
    }


def live_source_gate(source):
    run = Path(source["run_dir"])
    prior = json.loads((run / "exposure_before.json").read_text())
    manifest = json.loads((run / "manifest.json").read_text())
    event = manifest["exposure_event"]
    require(event is not None, "Feasibility source exposure missing")
    own = read_exposure(event["path"])["records"]
    require(
        exposure_keys(collect_known_exposures(ROOT))
        == exposure_keys(prior) | exposure_keys(own),
        "External exposure changed since source binding; cannot start this test",
    )


def source_graph(source, identity):
    paths = [
        Path(source["run_dir"]) / "summary.json",
        Path(identity["run_dir"]) / "summary.json",
    ]
    source_run = Path(source["run_dir"])
    source_manifest = json.loads((source_run / "manifest.json").read_text())
    source_protocol_run = Path(source_manifest["protocol_run"])
    source_protocol = json.loads((source_protocol_run / "manifest.json").read_text())
    identity_run = Path(identity["run_dir"])
    result = {str(p): digest(p.read_bytes()) for p in paths}
    for run in (source_run, source_protocol_run, identity_run):
        p = run / "manifest.json"
        result[str(p)] = digest(p.read_bytes())
        manifest = json.loads(p.read_text())
        result.update(
            {str(run / name): sha for name, sha in manifest["snapshot_sha256"].items()}
        )
        result.update(manifest.get("input_sha256", {}))
        result.update(manifest.get("code_sha256", {}))
    return result, Path(source_protocol["planning_run"])


def freeze(source_path, identity_path):
    source = audit_references(source_path)
    identity = audit_identity(identity_path)
    require(
        source["readiness"]["feasibility_coverage_met"]
        and source["readiness"]["scope"]
        == "six_family_structure_derived_feasibility_only"
        and identity["selected_supported_identity_verified"]
        and identity["selected_supported_references"]
        == source["binding"]["supported_references"],
        "Feasibility coverage/identity gate failed",
    )
    require(
        json.loads((Path(identity["run_dir"]) / "source.json").read_text()) == source,
        "Identity audit belongs to another reference binding",
    )
    for p in sorted((ROOT / "results" / (NAME + "_runs")).glob("*/binding.json")):
        if json.loads(p.read_text()) == source:
            context(p.parent)
            return p.parent
    live_source_gate(source)
    inputs, planning = source_graph(source, identity)
    original = json.loads((planning / "model_protocol.json").read_text())
    run = ROOT / "results" / (NAME + "_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    model_run = run / "models"
    model_run.mkdir()
    for name in METHODS[:3]:
        config = original["models"][name]["config"]
        require(
            config["seed"] == 20261006
            and config["top_k"] == 16
            and config["inference_decoder"] == "exact_sparse",
            "Feasibility model config differs",
        )
        for kind in ("checkpoint.pt", "summary.json"):
            filename = name + "_" + kind
            (model_run / filename).write_bytes((planning / filename).read_bytes())
        require(
            digest((model_run / (name + "_checkpoint.pt")).read_bytes())
            == original["models"][name]["checkpoint_sha256"],
            "Feasibility checkpoint differs",
        )
    atomic_json(run / "binding.json", source)
    atomic_json(run / "identity.json", identity)
    atomic_json(
        run / "model_protocol.json",
        {"run_dir": str(model_run), "models": original["models"]},
    )
    (run / "driver.py").write_bytes(Path(__file__).read_bytes())
    scripts = [
        "evaluate_prospective_panel.py",
        "evaluate_degradation_pilot.py",
        "prepare_raw_structure_references.py",
        "verify_raw_structure_identity.py",
    ]
    manifest = {
        "run_dir": str(run),
        "policy": POLICY,
        "methods": METHODS,
        "folding": FOLDING,
        "environment": environment(),
        "native_runtime": native_runtime(ROOT, FOLDING),
        "reference_format": PAIR_FORMAT,
        "source_input_sha256": inputs,
        "snapshot_sha256": {
            str(p.relative_to(run)): digest(p.read_bytes())
            for p in run.rglob("*")
            if p.is_file()
        },
        "code_sha256": {
            str(p): digest(p.read_bytes())
            for p in [
                Path(__file__),
                *[ROOT / "scripts" / name for name in scripts],
                *sorted((ROOT / "src/rnastable").glob("*.py")),
            ]
        },
    }
    atomic_json(run / "manifest.json", manifest)
    context(run)
    print("Frozen raw structure feasibility evaluation: " + str(run), flush=True)
    return run


def context(run):
    run = Path(run).resolve()
    manifest = json.loads((run / "manifest.json").read_text())
    require(
        manifest["run_dir"] == str(run)
        and manifest["policy"] == POLICY
        and manifest["methods"] == METHODS
        and manifest["folding"] == FOLDING
        and manifest["reference_format"] == PAIR_FORMAT
        and manifest["environment"] == environment()
        and manifest["native_runtime"] == native_runtime(ROOT, FOLDING),
        "Feasibility plan/environment/runtime differs",
    )
    expected = {"binding.json", "identity.json", "model_protocol.json", "driver.py"} | {
        "models/" + name + "_" + kind
        for name in METHODS[:3]
        for kind in ("summary.json", "checkpoint.pt")
    }
    require(
        set(manifest["snapshot_sha256"]) == expected,
        "Feasibility model/input inventory differs",
    )
    for name, sha in manifest["snapshot_sha256"].items():
        require(
            digest((run / name).read_bytes()) == sha, "Feasibility snapshot changed"
        )
    for field in ("source_input_sha256", "code_sha256"):
        for name, sha in manifest[field].items():
            require(
                digest(Path(name).read_bytes()) == sha,
                "Feasibility source/code changed",
            )
    source = json.loads((run / "binding.json").read_text())
    identity = json.loads((run / "identity.json").read_text())
    require(
        source["readiness"]["feasibility_coverage_met"]
        and identity["selected_supported_identity_verified"]
        and identity["selected_supported_references"]
        == source["binding"]["supported_references"],
        "Retained feasibility coverage/identity gate differs",
    )
    protocol = json.loads((run / "model_protocol.json").read_text())
    require(
        protocol["run_dir"] == str(run / "models")
        and set(protocol["models"]) == set(METHODS[:3]),
        "Feasibility model identity differs",
    )
    return manifest, source, protocol


def test_event(run, records, create):
    path = run / "test_event.json"
    if not path.exists():
        require(
            create
            and not list((run / "exposures").glob("*.json"))
            and not list((run / "native_journal").glob("*.json"))
            and not (run / "predictions.json").exists(),
            "Missing/orphan feasibility test exposure",
        )
        atomic_json(path, record_exposure(run, "test_started", records))
    event = json.loads(path.read_text())
    exposure = Path(event["path"])
    require(
        digest(exposure.read_bytes()) == event["sha256"]
        and event["stage"] == "test_started"
        and read_exposure(exposure)["records"]
        == exposure_records(records, str(run) + " test_started")
        and set((run / "exposures").glob("*.json")) == {exposure},
        "Feasibility test event changed",
    )


def native_result(run, journal, record, index, method, execute):
    key = f"record_{index:02d}_{method}"
    raw = run / "raw" / (key + ".txt")
    params = {"tool": method, "folding": FOLDING, "raw_output": str(raw)}
    if execute:
        return journal.run(
            key,
            record["sequence"],
            params,
            lambda: fold_sequence(ROOT, record["sequence"], FOLDING, method, raw),
        )
    payload = journal.read(key)
    require(
        payload["sequence_sha256"] == record["sequence_sha256"]
        and payload["parameters"] == params,
        "Feasibility native identity differs",
    )
    result = (
        payload["result"]
        if payload["state"] != "started"
        else journal.unknown_result(params)
    )
    NativeJournal.validate_result(result, len(record["sequence"]))
    return result


def predictions(run, manifest, source, protocol, execute):
    records = source["binding"]["records"]
    test_event(run, records, create=False)
    loaded = models(protocol)
    journal = NativeJournal(run / "native_journal", digest(canonical(manifest)))
    output = []
    for index, record in enumerate(records):
        for method in METHODS:
            row = {
                "id": record["id"],
                "method": method,
                "sequence_sha256": record["sequence_sha256"],
            }
            if record["reference_status"] != "ok":
                row.update(
                    status=record["reference_status"],
                    error=record.get("error", "unsupported reference"),
                )
            elif method in loaded:
                try:
                    model, config = loaded[method]
                    row.update(
                        status="ok",
                        structure=decode_loaded(
                            model, record["sequence"], config, "exact_sparse", 0
                        )["structure"],
                    )
                except (ValueError, RuntimeError, MemoryError) as exc:
                    row.update(
                        status="error", error=type(exc).__name__ + ": " + str(exc)
                    )
            elif method == "all_unpaired":
                row.update(status="ok", structure="." * len(record["sequence"]))
            else:
                result = native_result(run, journal, record, index, method, execute)
                row.update(status=result["status"])
                if result["status"] == "ok":
                    row["structure"] = result["structure"]
                else:
                    row["error"] = result.get("error") or result["status"]
            output.append(row)
            if execute:
                atomic_json(run / "predictions.json", output)
        if execute:
            print(f"Raw structure feasibility {index + 1}/{len(records)}", flush=True)
    return output


def artifacts(run):
    return {
        str(p.relative_to(run)): digest(p.read_bytes())
        for p in sorted(run.rglob("*"))
        if p.is_file()
        and p.name not in (".lock", ".driver.lock")
        and (
            p.name in ("predictions.json", "test_event.json")
            or p.parent.name in ("raw", "native_journal", "exposures")
        )
    }


def result_summary(run, manifest, source, predicted):
    records = source["binding"]["records"]
    rows, aggregate, families = score(records, predicted, PAIR_FORMAT)
    return {
        "complete": True,
        "run_dir": str(run),
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "artifact_sha256": artifacts(run),
        "rows": rows,
        "aggregates": aggregate,
        "by_family": families,
        "planned_predictions": len(records) * len(METHODS),
        "source_requests": source["planned_source_requests"],
        "supported_references": source["binding"]["supported_references"],
        "native_accounting": native_accounting(run, manifest, records),
        "model_fitted": False,
        "checkpoint_selected_from_test": False,
        "broad_validation_gate_satisfied": False,
        "independence_certified": False,
        "limitations": source["limitations"],
        "policy": POLICY,
    }


def evaluate(run):
    run = Path(run).resolve()
    with exclusive_driver(run / ".driver.lock"):
        manifest, source, protocol = context(run)
        if not (run / "test_event.json").exists():
            live_source_gate(source)
        test_event(run, source["binding"]["records"], create=True)
        predicted = predictions(run, manifest, source, protocol, execute=True)
        summary = result_summary(run, manifest, source, predicted)
        atomic_json(run / "summary.json", summary)
    audit(run / "summary.json")
    report = [
        "# Six-family raw structure feasibility evaluation",
        "",
        POLICY,
        "",
        "Means are descriptive per-record macro scores; source-level and prediction denominators are distinct.",
        "",
        "| Method | Planned | Measured | Mean pair F1 |",
        "|---|---:|---:|---:|",
    ]
    report += [
        f"| {r['method']} | {r['planned_inputs']} | {r['measured_inputs']} | {r['mean_pair_f1']} |"
        for r in summary["aggregates"]
    ]
    report += ["", *summary["limitations"], ""]
    publish(
        ROOT,
        NAME,
        summary,
        summary["rows"],
        [
            "reference_id",
            "family_id",
            "method",
            "status",
            "error",
            *METRICS,
            "reference_has_crossing_pairs",
        ],
        "\n".join(report),
    )
    return summary


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(
        summary == json.loads((run / "summary.json").read_text()),
        "Retained feasibility summary differs",
    )
    manifest, source, protocol = context(run)
    require(
        summary["artifact_sha256"] == artifacts(run),
        "Feasibility artifact inventory/hash differs",
    )
    predicted = predictions(run, manifest, source, protocol, execute=False)
    require(
        predicted == json.loads((run / "predictions.json").read_text()),
        "Feasibility predictions differ from replay",
    )
    require(
        summary == result_summary(run, manifest, source, predicted),
        "Feasibility scores/accounting differ from replay",
    )
    print(
        "Raw structure feasibility replay passed; frozen models and retained native journals, no new folds or exposure."
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=ROOT / "results/raw_structure_references_summary.json",
    )
    parser.add_argument(
        "--identity",
        type=Path,
        default=ROOT / "results/raw_structure_identity_summary.json",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--evaluate", type=Path, metavar="RUN")
    mode.add_argument("--verify", type=Path, metavar="SUMMARY")
    args = parser.parse_args()
    if args.verify:
        audit(args.verify)
    elif args.evaluate:
        evaluate(args.evaluate)
    else:
        freeze(args.source, args.identity)


if __name__ == "__main__":
    main()
