#!/usr/bin/env python3
"""Frozen descriptive assay-proxy comparison; no fitting or new assay selection."""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from prepare_degradation_binding import (
    PLAN,
    LIMITATIONS as BINDING_LIMITATIONS,
    audit as audit_binding,
)
from prepare_degradation_source import audit_protocol
from evaluate_prospective_panel import models
from rnastable.artifacts import timestamp, publish, write_artifact
from rnastable.context_inference import decode_loaded
from rnastable.exposures import record_exposure, read_exposure, exposure_records
from rnastable.folding import fold_sequence
from rnastable.native_journal import (
    NativeJournal,
    atomic_json,
    canonical,
    exclusive_driver,
)
from rnastable.pooled_native import native_runtime
from rnastable.reference import digest
from rnastable.reference_audit import require
from rnastable.scoring import paired_fraction

NAME = "degradation_pilot"
LIMITATIONS = [
    *BINDING_LIMITATIONS,
    "Native energy is the returned per-method folding objective; LinearFold beam search need not reach the exact global minimum.",
    "Assay errors are retained without noise weighting; all/quality1 slices duplicate the same cohort when every selected quality flag is1.",
]
METHODS = PLAN["methods"]
NATIVE = ("ViennaRNA", "LinearFold")
FOLDING = {
    "temperature_c": PLAN["native_temperature_c"],
    "timeout_seconds": PLAN["native_timeout_seconds"],
    "memory_limit_gib": PLAN["native_memory_limit_gib"],
    "beam_size": PLAN["native_beam_size"],
}
FEATURES = (
    [(m, "unpaired_fraction_of_scored_prefix") for m in METHODS]
    + [(m, "native_mfe_per_nt") for m in NATIVE]
    + [("sequence_only", "gc_fraction_of_scored_prefix")]
)


def environment():
    import numpy
    import scipy
    import torch

    return {
        "python": sys.version,
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "torch": torch.__version__,
    }


def eligible(record):
    return record["prediction_allowed"] and any(
        a["status"] == "ok" for a in record["assays"].values()
    )


def skipped(record):
    return "prior_overlap" if not record["prediction_allowed"] else "unsupported_assays"


def validate_prediction(record, prediction):
    require(
        prediction["id"] == record["id"]
        and prediction["method"] in METHODS
        and prediction["sequence_sha256"]
        == digest(record["sequence"].encode())
        == record["sequence_sha256"],
        "Prediction input binding differs",
    )
    if prediction["status"] == "ok":
        paired_fraction(prediction["structure"], len(record["sequence"]))
        require(eligible(record), "Unsupported or overlapping input was predicted")
        if prediction["method"] in NATIVE:
            energy = prediction["mfe_kcal_mol"]
            require(
                type(energy) in (int, float) and math.isfinite(energy),
                "Invalid native energy",
            )
        else:
            require(
                "mfe_kcal_mol" not in prediction,
                "Learned logits must not be stored as native energy",
            )
    else:
        require(
            prediction["status"]
            in (
                "prior_overlap",
                "unsupported_assays",
                "error",
                "timeout",
                "parse_error",
                "unavailable",
            )
            and isinstance(prediction.get("error"), str)
            and prediction["error"]
            and "structure" not in prediction
            and "mfe_kcal_mol" not in prediction,
            "Failed prediction retained an invalid or stale result",
        )
        require(
            eligible(record) or prediction["status"] == skipped(record),
            "Skipped input status differs",
        )
        require(
            prediction["status"] not in ("prior_overlap", "unsupported_assays")
            or not eligible(record),
            "Eligible input was incorrectly skipped",
        )


def score(records, predictions):
    from scipy.stats import spearmanr

    index = {(p["id"], p["method"]): p for p in predictions}
    require(
        len(index) == len(predictions) == len(records) * len(METHODS)
        and len({r["id"] for r in records}) == len(records)
        and set(index) == {(r["id"], m) for r in records for m in METHODS},
        "Prediction denominator differs",
    )
    rows = []
    for r in records:
        for method in METHODS:
            p = index[r["id"], method]
            validate_prediction(r, p)
        prefix = r["sequence"][: r["seq_scored"]]
        for method, feature in FEATURES:
            p = index.get((r["id"], method))
            if method == "sequence_only":
                proxy = (
                    (prefix.count("G") + prefix.count("C")) / len(prefix)
                    if eligible(r)
                    else None
                )
                prediction_status = "ok" if eligible(r) else skipped(r)
            else:
                prediction_status = p["status"]
                proxy = (
                    None
                    if p["status"] != "ok"
                    else (
                        p["structure"][: r["seq_scored"]].count(".") / r["seq_scored"]
                        if feature == "unpaired_fraction_of_scored_prefix"
                        else p["mfe_kcal_mol"] / r["seq_length"]
                    )
                )
            for target in PLAN["targets"]:
                a = r["assays"][target]
                measurement = a["mean"] if a["status"] == "ok" else None
                rows.append(
                    {
                        "id": r["id"],
                        "SN_filter": r["SN_filter"],
                        "method": method,
                        "proxy_name": feature,
                        "target": target,
                        "prediction_status": prediction_status,
                        "assay_status": a["status"],
                        "proxy": proxy,
                        "measurement_mean": measurement,
                        "paired_complete": proxy is not None
                        and measurement is not None,
                    }
                )
    aggregates = []
    for method, feature in FEATURES:
        for target in PLAN["targets"]:
            for group in PLAN["quality_slices"]:
                chosen = [
                    r
                    for r in rows
                    if r["method"] == method
                    and r["proxy_name"] == feature
                    and r["target"] == target
                    and (
                        group == "all"
                        or group
                        == "SN_filter_"
                        + (
                            str(r["SN_filter"])
                            if r["SN_filter"] is not None
                            else "unknown"
                        )
                    )
                ]
                complete = [r for r in chosen if r["paired_complete"]]
                x, y = (
                    [r["proxy"] for r in complete],
                    [r["measurement_mean"] for r in complete],
                )
                reason = (
                    "fewer_than_three_complete_records"
                    if len(complete) < PLAN["minimum_complete_records"]
                    else (
                        "constant_proxy"
                        if len(set(x)) == 1
                        else "constant_measurement"
                        if len(set(y)) == 1
                        else None
                    )
                )
                rho = None if reason else float(spearmanr(x, y).statistic)
                require(rho is None or math.isfinite(rho), "Nonfinite correlation")
                aggregates.append(
                    {
                        "method": method,
                        "proxy_name": feature,
                        "target": target,
                        "quality_slice": group,
                        "planned_records": len(chosen),
                        "complete_records": len(complete),
                        "missing_prediction_records": sum(
                            r["proxy"] is None for r in chosen
                        ),
                        "unsupported_assay_records": sum(
                            r["measurement_mean"] is None for r in chosen
                        ),
                        "missing_paired_records": len(chosen) - len(complete),
                        "spearman_rho": rho,
                        "null_reason": reason,
                    }
                )
    return rows, aggregates


def parameters(run, index, method):
    key = f"record_{index:03d}_{method}"
    return key, {
        "tool": method,
        "folding": FOLDING,
        "raw_output": str(run / "raw" / (key + ".txt")),
    }


def native_prediction(run, journal, record, index, method, execute):
    key, params = parameters(run, index, method)
    if execute:

        def callback():
            raw = Path(params["raw_output"])
            result = fold_sequence(ROOT, record["sequence"], FOLDING, method, raw)
            if raw.exists():
                result.update(raw_output=str(raw), raw_sha256=digest(raw.read_bytes()))
            return result

        result = journal.run(key, record["sequence"], params, callback)
    else:
        payload = journal.read(key)
        require(
            payload["sequence_sha256"] == record["sequence_sha256"]
            and payload["parameters"] == params
            and payload["state"] in ("complete", "interrupted"),
            "Native request binding/state differs",
        )
        result = payload["result"]
        journal.validate_result(result, len(record["sequence"]))
    if "raw_output" in result:
        require(
            result["raw_output"] == params["raw_output"]
            and digest(Path(result["raw_output"]).read_bytes()) == result["raw_sha256"],
            "Native raw output changed",
        )
    return {
        "status": result["status"],
        **(
            {"structure": result["structure"], "mfe_kcal_mol": result["mfe_kcal_mol"]}
            if result["status"] == "ok"
            else {"error": result.get("error") or result["status"]}
        ),
    }


def load_models(protocol):
    import torch

    torch.use_deterministic_algorithms(True)
    return models(
        {
            "run_dir": protocol["run_dir"],
            "models": {
                name: {"config": settings}
                for name, settings in protocol["models"].items()
            },
        }
    )


def predictions(run, records, loaded, journal, execute):
    output = []
    previous = (
        json.loads((run / "predictions.json").read_text())
        if execute and (run / "predictions.json").exists()
        else []
    )
    order = [(r["id"], method) for r in records for method in METHODS]
    require(
        len(previous) <= len(order)
        and [(r["id"], r["method"]) for r in previous] == order[: len(previous)],
        "Partial prediction order differs",
    )
    for i, r in enumerate(records):
        for method in METHODS:
            if not eligible(r):
                result = {"status": skipped(r), "error": skipped(r)}
            elif method in NATIVE:
                result = native_prediction(run, journal, r, i, method, execute)
            elif method == "all_unpaired":
                result = {"status": "ok", "structure": "." * len(r["sequence"])}
            else:
                try:
                    model, config = loaded[method]
                    result = {
                        "status": "ok",
                        "structure": decode_loaded(
                            model, r["sequence"], config, "exact_sparse", 0
                        )["structure"],
                    }
                    paired_fraction(result["structure"], len(r["sequence"]))
                except (ValueError, RuntimeError) as exc:
                    result = {
                        "status": "error",
                        "error": type(exc).__name__ + ": " + str(exc),
                    }
            p = {
                "id": r["id"],
                "method": method,
                "sequence_sha256": r["sequence_sha256"],
                **result,
            }
            validate_prediction(r, p)
            require(
                len(output) >= len(previous) or p == previous[len(output)],
                "Retained partial prediction changed",
            )
            output.append(p)
            if execute:
                atomic_json(run / "predictions.json", output)
        print(
            f"{'Measured' if execute else 'Replayed'} assay pilot {i + 1}/{len(records)}",
            flush=True,
        )
    return output


def accounting(run, manifest, records):
    journal = NativeJournal(run / "native_journal", digest(canonical(manifest)))
    expected = {
        parameters(run, i, m)[0]
        for i, r in enumerate(records)
        if eligible(r)
        for m in NATIVE
    }
    require(
        {p.stem for p in journal.directory.glob("*.json")} == expected,
        "Native request denominator differs",
    )
    entries = [journal.read(k) for k in sorted(expected)]
    return {
        "planned_requests": len(expected),
        "completed_requests": sum(e["state"] == "complete" for e in entries),
        "unknown_requests": sum(e["state"] != "complete" for e in entries),
        "known_wall_seconds": sum(
            e.get("result", {}).get("wall_seconds", 0) for e in entries
        ),
    }


def context(run):
    manifest = json.loads((run / "manifest.json").read_text())
    require(
        manifest["run_dir"] == str(run)
        and manifest["analysis_plan"] == PLAN
        and manifest["folding"] == FOLDING
        and manifest["environment"] == environment()
        and manifest["limitations"] == LIMITATIONS,
        "Evaluation plan/environment differs",
    )
    for name, sha in manifest["snapshot_sha256"].items():
        require(
            Path(name).name == name and digest((run / name).read_bytes()) == sha,
            "Evaluation snapshot changed",
        )
    require(
        set(manifest["snapshot_sha256"]) == {"binding.json", "protocol.json"},
        "Evaluation input inventory differs",
    )
    for name, sha in manifest["code_sha256"].items():
        require(digest(Path(name).read_bytes()) == sha, "Evaluation code changed")
    require(
        native_runtime(ROOT, FOLDING) == manifest["native_runtime"],
        "Native runtime changed",
    )
    binding = json.loads((run / "binding.json").read_text())
    require(
        binding == audit_binding(Path(binding["run_dir"]) / "summary.json"),
        "Assay binding differs",
    )
    protocol = json.loads((run / "protocol.json").read_text())
    require(
        protocol == audit_protocol(Path(protocol["run_dir"]) / "manifest.json"),
        "Model protocol differs",
    )
    source = json.loads((Path(binding["run_dir"]) / "source.json").read_text())
    require(
        protocol == json.loads((Path(source["run_dir"]) / "protocol.json").read_text()),
        "Evaluation source-model association differs",
    )
    return manifest, binding, protocol


def freeze():
    binding = audit_binding(ROOT / "results/degradation_binding_summary.json")
    require(
        binding["planned_records"] == PLAN["record_cap"],
        "Expected declared 64-record pilot",
    )
    source = json.loads((Path(binding["run_dir"]) / "source.json").read_text())
    protocol = json.loads((Path(source["run_dir"]) / "protocol.json").read_text())
    root = ROOT / "results" / (NAME + "_runs")
    for p in sorted(root.glob("*/binding.json")):
        if json.loads(p.read_text()) == binding:
            context(p.parent)
            write_artifact(
                ROOT / "results" / (NAME + "_plan.json"),
                json.dumps({"run_dir": str(p.parent)}, indent=2) + "\n",
            )
            print("Existing frozen pilot: " + str(p.parent))
            return p.parent
    run = root / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "binding.json", binding)
    atomic_json(run / "protocol.json", protocol)
    paths = [
        Path(__file__),
        *[
            ROOT / "scripts" / name
            for name in (
                "prepare_degradation_binding.py",
                "prepare_degradation_source.py",
                "evaluate_prospective_panel.py",
            )
        ],
        *sorted((ROOT / "src/rnastable").glob("*.py")),
    ]
    manifest = {
        "run_dir": str(run),
        "analysis_plan": PLAN,
        "folding": FOLDING,
        "environment": environment(),
        "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
        "code_sha256": {str(p): digest(p.read_bytes()) for p in paths},
        "native_runtime": native_runtime(ROOT, FOLDING),
        "limitations": LIMITATIONS,
    }
    atomic_json(run / "manifest.json", manifest)
    context(run)
    write_artifact(
        ROOT / "results" / (NAME + "_plan.json"),
        json.dumps({"run_dir": str(run)}, indent=2) + "\n",
    )
    print("Frozen empirical pilot: " + str(run / "manifest.json"))
    return run


def exposure(run, records, create):
    p = run / "test_event.json"
    if not p.exists() and create:
        require(
            not list((run / "exposures").glob("*.json")), "Orphan pilot exposure exists"
        )
        require(
            not (run / "predictions.json").exists()
            and not list((run / "native_journal").glob("*.json")),
            "Prediction/native work exists before test exposure",
        )
        atomic_json(p, record_exposure(run, "test_started", records))
    event = json.loads(p.read_text())
    path = Path(event["path"])
    observed = read_exposure(path)
    require(
        path.resolve().parent == (run / "exposures").resolve()
        and set((run / "exposures").glob("*.json")) == {path}
        and digest(path.read_bytes()) == event["sha256"]
        and observed["stage"] == event["stage"] == "test_started"
        and observed["records"]
        == exposure_records(records, str(run) + " test_started"),
        "Pilot exposure differs",
    )
    return event


def summary_for(run, manifest, binding, outcomes, rows, aggregates):
    return {
        "complete": True,
        "run_dir": str(run),
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "artifact_sha256": {
            str(p.relative_to(run)): digest(p.read_bytes())
            for p in [
                run / "predictions.json",
                run / "test_event.json",
                *sorted((run / "exposures").glob("*.json")),
                *sorted((run / "native_journal").glob("*.json")),
            ]
        },
        "planned_predictions": len(binding["records"]) * len(METHODS),
        "successful_predictions": sum(p["status"] == "ok" for p in outcomes),
        "planned_assay_proxy_outcomes": len(rows),
        "complete_assay_proxy_outcomes": sum(r["paired_complete"] for r in rows),
        "native_accounting": accounting(run, manifest, binding["records"]),
        "rows": rows,
        "aggregates": aggregates,
        "model_fitted": False,
        "checkpoint_selected": False,
        "defaults_changed": False,
        "independence_certified": False,
        "limitations": LIMITATIONS,
    }


def evaluate(run):
    run = Path(run).resolve()
    with exclusive_driver(run / ".driver.lock"):
        if (run / "summary.json").exists():
            return audit(run / "summary.json")
        manifest, binding, protocol = context(run)
        exposure(run, binding["records"], True)
        loaded = load_models(protocol)
        journal = NativeJournal(run / "native_journal", digest(canonical(manifest)))
        outcomes = predictions(run, binding["records"], loaded, journal, True)
        rows, aggregates = score(binding["records"], outcomes)
        summary = summary_for(run, manifest, binding, outcomes, rows, aggregates)
        atomic_json(run / "summary.json", summary)
        fields = list(aggregates[0])
        report = [
            "# External measured-assay proxy pilot",
            "",
            *LIMITATIONS,
            "",
            "Only descriptive Spearman rho is reported. Empty/constant/unsupported pairs retain null coefficients and explicit counts.",
            "",
            "| " + " | ".join(fields) + " |",
            "|" + "---|" * len(fields),
        ]
        report.extend(
            "| " + " | ".join(str(r[k]) for k in fields) + " |" for r in aggregates
        )
        publish(ROOT, NAME, summary, rows, list(rows[0]), "\n".join(report) + "\n")
        return summary


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(
        summary == json.loads((run / "summary.json").read_text()),
        "Retained pilot summary differs",
    )
    for name, sha in summary["artifact_sha256"].items():
        require(
            not Path(name).is_absolute()
            and ".." not in Path(name).parts
            and digest((run / name).read_bytes()) == sha,
            "Pilot artifact changed",
        )
    manifest, binding, protocol = context(run)
    exposure(run, binding["records"], False)
    journal = NativeJournal(run / "native_journal", digest(canonical(manifest)))
    expected = predictions(
        run, binding["records"], load_models(protocol), journal, False
    )
    require(
        expected == json.loads((run / "predictions.json").read_text()),
        "Pilot prediction replay differs",
    )
    rows, aggregates = score(binding["records"], expected)
    require(
        summary_for(run, manifest, binding, expected, rows, aggregates) == summary,
        "Pilot metrics/denominators differ",
    )
    print(
        "Empirical pilot replay passed:all planned predictions/proxies, exact assay coordinates, source/model/runtime bindings and native journals; no new native calls or exposure."
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--evaluate", action="store_true")
    group.add_argument("--verify", action="store_true")
    group.add_argument("--resume", type=Path)
    args = parser.parse_args()
    if args.verify:
        return audit(ROOT / "results" / (NAME + "_summary.json"))
    if args.evaluate or args.resume:
        run = args.resume or Path(
            json.loads((ROOT / "results" / (NAME + "_plan.json")).read_text())[
                "run_dir"
            ]
        )
        return evaluate(run)
    return freeze()


if __name__ == "__main__":
    main()
