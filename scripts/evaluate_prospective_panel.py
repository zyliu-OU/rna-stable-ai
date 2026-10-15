#!/usr/bin/env python3
"""Bind and evaluate a fixed prospective panel, retaining unsupported references."""

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
from rnastable.prospective_binding import build_binding
from rnastable.reference import digest, METRICS, aggregate_rows
from rnastable.reference_audit import require
from rnastable.scoring import structure_agreement
from rnastable.scoring import base_pairs
from rnastable.pair_reference import validate_pairs, pair_agreement, has_crossing_pairs
from download_prospective_evidence import audit as audit_evidence
from prepare_prospective_family_panel import audit_protocol

METHODS = ["baseline", "stack", "helix", "all_unpaired", "ViennaRNA", "LinearFold"]
FOLDING = {
    "temperature_c": 37,
    "beam_size": 100,
    "timeout_seconds": 30,
    "memory_limit_gib": 4,
}
LEGACY_FORMAT = "dot_bracket_v1"
PAIR_FORMAT = "pair_set_zero_based_v1"


def publication_name(reference_format, phase):
    require(
        reference_format in (LEGACY_FORMAT, PAIR_FORMAT),
        "Unknown prospective reference format",
    )
    return (
        "prospective_pair_" if reference_format == PAIR_FORMAT else "prospective_"
    ) + phase


def require_protocol_format(acquisition, reference_format):
    protocol = json.loads((Path(acquisition["run_dir"]) / "protocol.json").read_text())
    retained = audit_protocol(Path(protocol["run_dir"]) / "manifest.json")
    require(protocol == retained, "Acquisition protocol differs")
    config = json.loads((Path(protocol["run_dir"]) / "config.json").read_text())
    require(
        config.get("reference_format", LEGACY_FORMAT) == reference_format,
        "Reference format was not frozen in the source protocol",
    )
    return protocol


def prepare(reference_format=LEGACY_FORMAT):
    evidence = audit_evidence(ROOT / "results/prospective_evidence_summary.json")
    require(evidence["sources_complete"] is True, "Complete evidence download required")
    evidence_run = Path(evidence["run_dir"])
    acquisition = json.loads((evidence_run / "acquisition.json").read_text())
    require_protocol_format(acquisition, reference_format)
    exposed = collect_known_exposures(ROOT)
    binding = build_binding(evidence_run, acquisition, exposed, reference_format)
    name = publication_name(reference_format, "binding")
    run = ROOT / ("results/" + name + "_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "exposure.json", exposed)
    atomic_json(run / "acquisition.json", acquisition)
    source_files = [
        evidence_run / p
        for p in json.loads((evidence_run / "manifest.json").read_text())[
            "snapshot_sha256"
        ]
    ]
    source_files += [
        Path(acquisition["run_dir"]) / (f + "_description.json")
        for f in acquisition["families_downloaded"]
    ]
    manifest = {
        "run_dir": str(run),
        "evidence_run": str(evidence_run),
        "source_sha256": {str(p): digest(p.read_bytes()) for p in source_files},
        "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
        "policy": "Fixed metadata panel; exact consensus contact mapping. Unsupported reference outcomes retain all planned method denominators. Known source overlap screening does not certify complete biological independence.",
    }
    if reference_format != LEGACY_FORMAT:
        manifest["reference_format"] = reference_format
    atomic_json(run / "manifest.json", manifest)
    summary = {
        "complete": True,
        "run_dir": str(run),
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "binding": binding,
    }
    atomic_json(run / "summary.json", summary)
    report = [
        "# Prospective panel annotation binding",
        "",
        manifest["policy"],
        "",
        f"Planned: {binding['planned_records']}; supported: {binding['supported_references']}; sequence bindings complete: {binding['sequence_bindings_complete']}.",
        "",
        "| Reference | Family | Status | Reason |",
        "|---|---|---|---|",
    ]
    for r in binding["records"]:
        report.append(
            f"| {r['id']} | {r['family_id']} | {r['reference_status']} | {r.get('error', '')} |"
        )
    report += ["", *binding["limitations"], ""]
    publish(
        ROOT,
        name,
        summary,
        binding["records"],
        ["id", "family_id", "sequence_bound", "reference_status", "error"],
        "\n".join(report),
    )
    return summary


def audit_binding(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(
        summary == json.loads((run / "summary.json").read_text()),
        "Retained binding differs",
    )
    manifest_bytes = (run / "manifest.json").read_bytes()
    require(
        digest(manifest_bytes) == summary["manifest_sha256"], "Binding manifest changed"
    )
    manifest = json.loads(manifest_bytes)
    require(manifest["run_dir"] == str(run), "Binding directory differs")
    for name, sha in manifest["snapshot_sha256"].items():
        require(
            Path(name).name == name and digest((run / name).read_bytes()) == sha,
            "Binding snapshot changed",
        )
    for name, sha in manifest["source_sha256"].items():
        require(digest(Path(name).read_bytes()) == sha, "Binding source changed")
    expected = build_binding(
        Path(manifest["evidence_run"]),
        json.loads((run / "acquisition.json").read_text()),
        json.loads((run / "exposure.json").read_text()),
        manifest.get("reference_format", LEGACY_FORMAT),
    )
    require(summary["binding"] == expected, "Annotation binding replay differs")
    return summary


def models(protocol):
    import torch
    from rnastable.global_sparse_pairs import make_global_model
    from rnastable.stack_pairs import make_stack_model
    from rnastable.helix_pairs import make_helix_model

    run = Path(protocol["run_dir"])
    output = {}
    for name, factory in [
        ("baseline", make_global_model),
        ("stack", make_stack_model),
        ("helix", make_helix_model),
    ]:
        config = protocol["models"][name]["config"]
        torch.set_num_threads(config["cpu_threads"])
        model = factory(config)
        model.load_state_dict(
            torch.load(
                run / (name + "_checkpoint.pt"), weights_only=True, map_location="cpu"
            )
        )
        model.eval()
        output[name] = (model, config)
    return output


def score(records, predictions, reference_format=LEGACY_FORMAT):
    require(
        reference_format in (LEGACY_FORMAT, PAIR_FORMAT),
        "Unknown prospective reference format",
    )
    require(
        len(predictions) == len(records) * len(METHODS),
        "Prediction denominator differs",
    )
    lookup = {(p["id"], p["method"]): p for p in predictions}
    require(len(lookup) == len(predictions), "Duplicate prediction")
    require(
        set(lookup) == {(r["id"], m) for r in records for m in METHODS},
        "Prediction method/reference inventory differs",
    )
    rows = []
    for r in records:
        for method in METHODS:
            p = lookup[(r["id"], method)]
            require(
                p["sequence_sha256"] == r["sequence_sha256"],
                "Prediction sequence differs",
            )
            row = {key: None for key in METRICS}
            row.update(
                reference_id=r["id"],
                family_id=r["family_id"],
                method=method,
                reference_kind=r.get("reference_kind", "computational"),
                status=p["status"],
                error=p.get("error", ""),
            )
            if r["reference_status"] != "ok":
                require(
                    p["status"] == r["reference_status"]
                    and "structure" not in p
                    and "pairs" not in p,
                    "Unsupported reference was scored",
                )
            elif p["status"] == "ok":
                if reference_format == PAIR_FORMAT:
                    actual = validate_pairs(r["pairs"], len(r["sequence"]))
                    require(
                        sum(key in p for key in ("pairs", "structure")) == 1,
                        "Prediction contact representation differs",
                    )
                    if "pairs" in p:
                        proposed = validate_pairs(p["pairs"], len(r["sequence"]))
                    else:
                        require(
                            isinstance(p["structure"], str)
                            and len(p["structure"]) == len(r["sequence"]),
                            "Prediction structure length differs",
                        )
                        proposed = base_pairs(p["structure"])
                    row.update(pair_agreement(proposed, actual))
                else:
                    row.update(structure_agreement(p["structure"], r["structure"]))
            elif reference_format == PAIR_FORMAT:
                require(
                    p["status"]
                    in ("error", "parse_error", "timeout", "unavailable", "missing")
                    and "pairs" not in p
                    and "structure" not in p,
                    "Failed prediction must not contain contacts or an unknown status",
                )
            if reference_format == PAIR_FORMAT:
                row["reference_has_crossing_pairs"] = (
                    has_crossing_pairs(validate_pairs(r["pairs"], len(r["sequence"])))
                    if r["reference_status"] == "ok"
                    else None
                )
            rows.append(row)
    aggregates = aggregate_rows(rows)
    by_family = [
        {"family_id": family, **a}
        for family in sorted({r["family_id"] for r in rows})
        for a in aggregate_rows([r for r in rows if r["family_id"] == family])
    ]
    return rows, aggregates, by_family


def native_accounting(run, manifest, records):
    require((run / "native_journal").is_dir(), "Native request journal missing")
    journal = NativeJournal(run / "native_journal", digest(canonical(manifest)))
    expected = {
        f"record_{index:02d}_{method}"
        for index, r in enumerate(records)
        if r["reference_status"] == "ok"
        for method in ("ViennaRNA", "LinearFold")
    }
    require(
        {p.stem for p in (run / "native_journal").glob("*.json")} == expected,
        "Native request inventory differs",
    )
    payloads = [journal.read(key) for key in sorted(expected)]
    return {
        "planned_requests": len(expected),
        "completed_requests": sum(p["state"] == "complete" for p in payloads),
        "unknown_requests": sum(p["state"] != "complete" for p in payloads),
        "known_wall_seconds": sum(
            p.get("result", {}).get("wall_seconds", 0) for p in payloads
        ),
    }


def evaluate(resume=None, reference_format=LEGACY_FORMAT):
    if resume:
        run = resume.resolve()
        manifest = json.loads((run / "manifest.json").read_text())
        require(
            manifest.get("reference_format", LEGACY_FORMAT) == reference_format,
            "Resume reference format differs",
        )
    else:
        name = publication_name(reference_format, "binding")
        binding = audit_binding(ROOT / ("results/" + name + "_summary.json"))
        require(
            binding["binding"]["sequence_bindings_complete"]
            and not binding["binding"]["known_provenance_overlap"]
            and binding["binding"]["supported_references"] > 0,
            "Binding/provenance gate failed",
        )
        # Final planning checks live exposures again before creating the test event.
        bm = json.loads((Path(binding["run_dir"]) / "manifest.json").read_text())
        acquisition = json.loads(
            (Path(binding["run_dir"]) / "acquisition.json").read_text()
        )
        require_protocol_format(acquisition, reference_format)
        require(
            build_binding(
                Path(bm["evidence_run"]),
                acquisition,
                collect_known_exposures(ROOT),
                reference_format,
            )
            == binding["binding"],
            "Exposure ledger changed since binding",
        )
        protocol_path = (
            Path(
                json.loads(
                    (Path(acquisition["run_dir"]) / "protocol.json").read_text()
                )["run_dir"]
            )
            / "manifest.json"
        )
        protocol = audit_protocol(protocol_path)
        name = publication_name(reference_format, "evaluation")
        run = ROOT / ("results/" + name + "_runs") / timestamp()
        run.mkdir(parents=True, exist_ok=False)
        atomic_json(run / "binding.json", binding)
        atomic_json(run / "protocol.json", protocol)
        manifest = {
            "run_dir": str(run),
            "methods": METHODS,
            "folding": FOLDING,
            "binding_sha256": digest((run / "binding.json").read_bytes()),
            "protocol_sha256": digest((run / "protocol.json").read_bytes()),
            "native_runtime": native_runtime(ROOT, FOLDING),
            "code_sha256": {
                str(p): digest(p.read_bytes())
                for p in [
                    Path(__file__),
                    *sorted((ROOT / "src/rnastable").glob("*.py")),
                ]
            },
            "policy": "All selected metadata records and six methods retain planned outcomes. Exact sparse decoder and zero penalty. No fitting, model/decoder selection or biological stability claim. Unsupported references receive unknown metrics and no inference.",
        }
        if reference_format != LEGACY_FORMAT:
            manifest["reference_format"] = reference_format
        atomic_json(run / "manifest.json", manifest)
    with exclusive_driver(run / ".driver.lock"):
        require(
            manifest["run_dir"] == str(run)
            and manifest["methods"] == METHODS
            and manifest["folding"] == FOLDING,
            "Evaluation plan differs",
        )
        for name, sha in manifest["code_sha256"].items():
            require(
                digest(Path(name).read_bytes()) == sha,
                "Evaluation code changed before resume",
            )
        require(
            native_runtime(ROOT, FOLDING) == manifest["native_runtime"],
            "Evaluation native runtime differs",
        )
        for name, sha in [
            ("binding.json", manifest["binding_sha256"]),
            ("protocol.json", manifest["protocol_sha256"]),
        ]:
            require(
                digest((run / name).read_bytes()) == sha, "Evaluation input changed"
            )
        binding = json.loads((run / "binding.json").read_text())
        protocol = audit_protocol(
            Path(json.loads((run / "protocol.json").read_text())["run_dir"])
            / "manifest.json"
        )
        require(
            protocol == json.loads((run / "protocol.json").read_text()),
            "Evaluation protocol changed",
        )
        protocol_config = json.loads(
            (Path(protocol["run_dir"]) / "config.json").read_text()
        )
        require(
            protocol_config.get("reference_format", LEGACY_FORMAT) == reference_format,
            "Evaluation format differs from frozen protocol",
        )
        records = binding["binding"]["records"]
        require(
            binding["binding"].get("reference_format", LEGACY_FORMAT)
            == reference_format,
            "Binding/evaluation reference format differs",
        )
        event_file = run / "test_event.json"
        if not event_file.exists():
            require(
                not list((run / "exposures").glob("*.json")),
                "Orphan test exposure exists; refusing a duplicate event",
            )
            atomic_json(event_file, record_exposure(run, "test_started", records))
        else:
            event = json.loads(event_file.read_text())
            require(
                digest(Path(event["path"]).read_bytes()) == event["sha256"],
                "Test event changed",
            )
            require(
                read_exposure(event["path"])["records"]
                == exposure_records(records, str(run) + " test_started"),
                "Test exposure records differ",
            )
        loaded = models(protocol)
        journal = NativeJournal(run / "native_journal", digest(canonical(manifest)))
        predictions = []
        for index, r in enumerate(records):
            for method in METHODS:
                p = {
                    "id": r["id"],
                    "method": method,
                    "sequence_sha256": r["sequence_sha256"],
                }
                if r["reference_status"] != "ok":
                    p.update(
                        status=r["reference_status"],
                        error=r.get("error", "unsupported reference"),
                    )
                elif method in loaded:
                    model, config = loaded[method]
                    p.update(
                        status="ok",
                        structure=decode_loaded(
                            model, r["sequence"], config, "exact_sparse", 0
                        )["structure"],
                    )
                elif method == "all_unpaired":
                    p.update(status="ok", structure="." * len(r["sequence"]))
                else:
                    key = f"record_{index:02d}_{method}"
                    raw = run / "raw" / (key + ".txt")
                    result = journal.run(
                        key,
                        r["sequence"],
                        {"tool": method, "folding": FOLDING, "raw_output": str(raw)},
                        lambda: fold_sequence(
                            ROOT, r["sequence"], FOLDING, method, raw
                        ),
                    )
                    p.update(status=result["status"])
                    if result["status"] == "ok":
                        p["structure"] = result["structure"]
                    else:
                        p["error"] = result.get("error") or result["status"]
                predictions.append(p)
                atomic_json(run / "predictions.json", predictions)
            print(
                f"Prospective reference {index + 1}/{len(records)}: {r['reference_status']}",
                flush=True,
            )
        rows, aggregates, families = score(records, predictions, reference_format)
        artifacts = {
            str(p.relative_to(run)): digest(p.read_bytes())
            for p in sorted(run.rglob("*"))
            if p.is_file()
            and (
                p.name in ("predictions.json", "test_event.json")
                or p.parent.name in ("raw", "exposures", "native_journal")
                and not p.name.startswith(".")
            )
        }
        summary = {
            "complete": True,
            "run_dir": str(run),
            "manifest_sha256": digest((run / "manifest.json").read_bytes()),
            "artifact_sha256": artifacts,
            "rows": rows,
            "aggregates": aggregates,
            "by_family": families,
            "planned_predictions": len(rows),
            "unsupported_references": sum(
                r["reference_status"] != "ok" for r in records
            ),
            "native_accounting": native_accounting(run, manifest, records),
            "model_fitted": False,
            "checkpoint_selected_from_test": False,
            "independence_certified": False,
            "limitations": binding["binding"]["limitations"],
        }
        if reference_format != LEGACY_FORMAT:
            summary["reference_format"] = reference_format
            summary["crossing_reference_records"] = sum(
                r["reference_status"] == "ok"
                and has_crossing_pairs(validate_pairs(r["pairs"], len(r["sequence"])))
                for r in records
            )
        atomic_json(run / "summary.json", summary)
        report = [
            "# Prospective frozen-model comparative evaluation",
            "",
            manifest["policy"],
            "",
            *summary["limitations"],
            "",
            "| Family | Method | Planned | Measured | Mean pair F1 |",
            "|---|---|---:|---:|---:|",
        ]
        for a in families:
            report.append(
                f"| {a['family_id']} | {a['method']} | {a['planned_inputs']} | {a['measured_inputs']} | {a['mean_pair_f1']} |"
            )
        publish(
            ROOT,
            publication_name(reference_format, "evaluation"),
            summary,
            rows,
            ["reference_id", "family_id", "method", "status", "error", *METRICS]
            + (
                ["reference_has_crossing_pairs"]
                if reference_format == PAIR_FORMAT
                else []
            ),
            "\n".join(report) + "\n",
        )
        return summary


def audit_evaluation(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(
        summary == json.loads((run / "summary.json").read_text()),
        "Retained evaluation differs",
    )
    raw = (run / "manifest.json").read_bytes()
    require(digest(raw) == summary["manifest_sha256"], "Evaluation manifest changed")
    manifest = json.loads(raw)
    reference_format = manifest.get("reference_format", LEGACY_FORMAT)
    publication_name(reference_format, "evaluation")
    require(
        manifest["run_dir"] == str(run)
        and manifest["methods"] == METHODS
        and manifest["folding"] == FOLDING,
        "Retained evaluation plan differs",
    )
    for name, sha in summary["artifact_sha256"].items():
        require(digest((run / name).read_bytes()) == sha, "Evaluation artifact changed")
    require(
        digest((run / "binding.json").read_bytes()) == manifest["binding_sha256"]
        and digest((run / "protocol.json").read_bytes()) == manifest["protocol_sha256"],
        "Evaluation binding changed",
    )
    binding = json.loads((run / "binding.json").read_text())
    require(
        audit_binding(Path(binding["run_dir"]) / "summary.json") == binding,
        "Source binding differs",
    )
    protocol = json.loads((run / "protocol.json").read_text())
    require(
        audit_protocol(Path(protocol["run_dir"]) / "manifest.json") == protocol,
        "Frozen protocol differs",
    )
    records = binding["binding"]["records"]
    require(
        binding["binding"].get("reference_format", LEGACY_FORMAT) == reference_format,
        "Binding/evaluation reference format differs",
    )
    if reference_format == PAIR_FORMAT:
        config = json.loads((Path(protocol["run_dir"]) / "config.json").read_text())
        require(
            config.get("reference_format", LEGACY_FORMAT) == reference_format,
            "Reference format was not frozen before source acquisition",
        )
        require(
            summary["reference_format"] == reference_format
            and summary["crossing_reference_records"]
            == sum(
                r["reference_status"] == "ok"
                and has_crossing_pairs(validate_pairs(r["pairs"], len(r["sequence"])))
                for r in records
            ),
            "Crossing reference accounting differs",
        )
    event = json.loads((run / "test_event.json").read_text())
    require(
        digest(Path(event["path"]).read_bytes()) == event["sha256"]
        and read_exposure(event["path"])["records"]
        == exposure_records(records, str(run) + " test_started"),
        "Test event differs",
    )
    predictions = json.loads((run / "predictions.json").read_text())
    rows, aggregates, families = score(records, predictions, reference_format)
    require(
        (rows, aggregates, families)
        == (summary["rows"], summary["aggregates"], summary["by_family"]),
        "Evaluation score replay differs",
    )
    require(
        summary["complete"] is True
        and summary["planned_predictions"] == len(rows)
        and summary["unsupported_references"]
        == sum(r["reference_status"] != "ok" for r in records)
        and summary["model_fitted"] is False
        and summary["checkpoint_selected_from_test"] is False
        and summary["independence_certified"] is False,
        "Evaluation interpretation differs",
    )
    loaded = models(protocol)
    for r in records:
        if r["reference_status"] != "ok":
            continue
        for method in ("baseline", "stack", "helix", "all_unpaired"):
            p = next(
                p for p in predictions if p["id"] == r["id"] and p["method"] == method
            )
            if method == "all_unpaired":
                expected_structure = "." * len(r["sequence"])
            else:
                model, config = loaded[method]
                expected_structure = decode_loaded(
                    model, r["sequence"], config, "exact_sparse", 0
                )["structure"]
            require(
                p["status"] == "ok" and p["structure"] == expected_structure,
                "Frozen model prediction replay differs",
            )
    accounting = native_accounting(run, manifest, records)
    if "native_accounting" in summary:
        require(summary["native_accounting"] == accounting, "Native accounting differs")
    journal = NativeJournal(run / "native_journal", digest(canonical(manifest)))
    for index, r in enumerate(records):
        if r["reference_status"] != "ok":
            continue
        for method in ("ViennaRNA", "LinearFold"):
            key = f"record_{index:02d}_{method}"
            payload = journal.read(key)
            require(
                payload["sequence_sha256"] == r["sequence_sha256"]
                and payload["parameters"]
                == {
                    "tool": method,
                    "folding": FOLDING,
                    "raw_output": str(run / "raw" / (key + ".txt")),
                },
                "Native journal request differs",
            )
            p = next(
                p for p in predictions if p["id"] == r["id"] and p["method"] == method
            )
            result = payload["result"]
            require(
                p["status"] == result["status"]
                and p.get("structure") == result.get("structure"),
                "Native journal prediction differs",
            )
    print(
        "Prospective evaluation audit passed: all planned outcomes, exact reference scores, model/input hashes, exposure and native journals; no new test or native callbacks."
    )
    print("Native accounting: " + json.dumps(accounting, sort_keys=True))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--evaluate", action="store_true")
    group.add_argument("--verify", action="store_true")
    group.add_argument("--resume", type=Path)
    parser.add_argument(
        "--reference-format",
        choices=(LEGACY_FORMAT, PAIR_FORMAT),
        default=LEGACY_FORMAT,
    )
    args = parser.parse_args()
    if args.verify:
        name = publication_name(args.reference_format, "evaluation")
        return audit_evaluation(ROOT / ("results/" + name + "_summary.json"))
    if args.evaluate or args.resume:
        return evaluate(args.resume, args.reference_format)
    return prepare(args.reference_format)


if __name__ == "__main__":
    main()
