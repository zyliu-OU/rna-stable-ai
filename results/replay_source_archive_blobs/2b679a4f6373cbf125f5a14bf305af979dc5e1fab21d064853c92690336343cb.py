#!/usr/bin/env python3
"""Freeze a comparison protocol, then acquire and screen sequence-only Rfam metadata."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import publish, timestamp
from rnastable.context_inference import load_checkpoint
from rnastable.exposures import collect_known_exposures
from rnastable.family_readiness import screen_families
from rnastable.native_journal import atomic_json
from rnastable.prospective_data import (
    bounded_download,
    family_urls,
    fastau_records,
    select_metadata_panel,
    validate_description,
)
from rnastable.reference import digest
from rnastable.reference_audit import require


def validate_config(config):
    require(
        config.get("reference_format", "dot_bracket_v1")
        in ("dot_bracket_v1", "pair_set_zero_based_v1"),
        "Invalid prospective reference format",
    )
    require(
        config["schema_version"] == 1 and type(config["schema_version"]) is int,
        "Invalid protocol schema",
    )
    require(
        config["stage"] == "metadata_screening_only"
        and config["test_inference_authorized_by_this_protocol"] is False,
        "Protocol must remain metadata-only",
    )
    require(
        config["decoder"] == "exact_sparse" and config["pair_penalty"] == 0,
        "Fixed decoder/penalty differs",
    )
    require(
        config["similarity_threshold"] == 0.8
        and config["selection_order"] == "family_then_sequence_id",
        "Fixed selection rules differ",
    )
    require(
        type(config["minimum_length"]) is int
        and type(config["maximum_length"]) is int
        and 1 <= config["minimum_length"] <= config["maximum_length"] <= 1024,
        "Invalid protocol length bound",
    )
    require(
        type(config["max_records_per_family"]) is int
        and 1 <= config["max_records_per_family"] <= 5,
        "Invalid family cap",
    )
    require(
        config["annotation_binding_required"] is True
        and config["family_clan_provenance_required"] is True,
        "Required evidence gates differ",
    )
    require(
        isinstance(config["families"], list)
        and 1 <= len(config["families"]) <= 3
        and len(set(config["families"])) == len(config["families"]),
        "Invalid family list",
    )
    for family in config["families"]:
        family_urls(family)
    require(
        set(config["model_sources"]) == {"baseline", "stack", "helix"},
        "Expected all three comparison models",
    )


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    require(
        manifest == json.loads((run / "manifest.json").read_text()),
        "Retained protocol differs",
    )
    config = json.loads((run / "config.json").read_text())
    validate_config(config)
    require(
        set(manifest["models"]) == set(config["model_sources"]),
        "Protocol model inventory differs",
    )
    expected = {"config.json", "exposure.json"} | {
        f"{name}_{kind}"
        for name in config["model_sources"]
        for kind in ("summary.json", "checkpoint.pt")
    }
    require(
        set(manifest["snapshot_sha256"]) == expected,
        "Protocol snapshot inventory differs",
    )
    for name, sha in manifest["snapshot_sha256"].items():
        require(
            digest((run / name).read_bytes()) == sha,
            "Protocol snapshot changed: " + name,
        )
    for name, binding in manifest["models"].items():
        source = json.loads((run / (name + "_summary.json")).read_text())
        require(
            source["complete"] is True
            and source["config"]["seed"] == config["model_seed"],
            "Model seed/completeness differs",
        )
        require(
            binding["config"] == source["config"]
            and binding["checkpoint_sha256"]
            == source["checkpoint_sha256"]["best_context_model.pt"]
            == manifest["snapshot_sha256"][name + "_checkpoint.pt"],
            "Frozen model binding differs",
        )
    return manifest


def freeze(config_path):
    raw = config_path.read_bytes()
    config = json.loads(raw)
    validate_config(config)
    exposures = collect_known_exposures(ROOT)
    require(
        not set(config["families"]).intersection(r.get("family_id") for r in exposures),
        "Proposed screening family already exposed",
    )
    sources = {}
    for name, relative in config["model_sources"].items():
        source_bytes, settings, checkpoint, _ = load_checkpoint(ROOT / relative)
        require(
            settings["seed"] == config["model_seed"]
            and settings["inference_decoder"] == config["decoder"],
            "Source seed/decoder differs",
        )
        expected_feature = {
            "baseline": None,
            "stack": "adjacent_stackability",
            "helix": "local_helix_context_v1",
        }[name]
        require(
            settings.get("pair_features") == expected_feature,
            "Comparison model feature identity differs",
        )
        sources[name] = (source_bytes, settings, checkpoint.read_bytes())
    run = ROOT / "results/prospective_family_protocol_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    (run / "config.json").write_bytes(raw)
    atomic_json(run / "exposure.json", exposures)
    for name, (source_bytes, settings, weights) in sources.items():
        (run / (name + "_summary.json")).write_bytes(source_bytes)
        (run / (name + "_checkpoint.pt")).write_bytes(weights)
    manifest = {
        "run_dir": str(run),
        "models": {
            name: {"config": item[1], "checkpoint_sha256": digest(item[2])}
            for name, item in sources.items()
        },
        "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
        "policy": "Prospective comparison protocol frozen before new metadata outcomes. Three development checkpoints retained without test-driven model selection. Metadata screening only; annotation binding, family/clan evidence and a final exposure-aware evaluation plan remain required.",
    }
    atomic_json(run / "manifest.json", manifest)
    audit_protocol(run / "manifest.json")
    atomic_json(ROOT / "results/prospective_family_protocol.json", manifest)
    print("Frozen prospective protocol: " + str(run / "manifest.json"))
    return manifest


def acquisition_screen(run, config, attempts, exposures):
    records = []
    ready = []
    for family in config["families"]:
        family_attempts = [a for a in attempts if a["family_id"] == family]
        if all(a["status"] == "ok" for a in family_attempts):
            validate_description(
                (run / (family + "_description.json")).read_bytes(), family
            )
            records.extend(
                fastau_records(
                    (run / (family + "_sequences.fasta")).read_bytes(), family
                )
            )
            ready.append(family)
    screening = screen_families(
        records, exposures, config["minimum_length"], config["maximum_length"]
    )
    panel = select_metadata_panel(records, screening, config["max_records_per_family"])
    return {
        "families_downloaded": ready,
        "screening": screening,
        "metadata_panel": panel,
        "sources_complete": len(ready) == len(config["families"]),
        "test_inference_allowed": False,
    }


def acquire(protocol_path):
    protocol = audit_protocol(protocol_path)
    protocol_run = Path(protocol["run_dir"])
    config_bytes = (protocol_run / "config.json").read_bytes()
    config = json.loads(config_bytes)
    exposures = collect_known_exposures(ROOT)
    require(
        not set(config["families"]).intersection(r.get("family_id") for r in exposures),
        "Screening family exposed since protocol freeze",
    )
    run = ROOT / "results/prospective_family_acquisition_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    (run / "config.json").write_bytes(config_bytes)
    atomic_json(run / "exposure.json", exposures)
    atomic_json(run / "protocol.json", protocol)
    attempts = [
        {"family_id": f, "resource": kind, "url": url, "status": "not_started"}
        for f in config["families"]
        for kind, url in family_urls(f).items()
    ]
    atomic_json(run / "attempts.json", attempts)
    for attempt in attempts:
        family, kind = attempt["family_id"], attempt["resource"]
        if (
            kind == "sequences"
            and next(
                a
                for a in attempts
                if a["family_id"] == family and a["resource"] == "description"
            )["status"]
            != "ok"
        ):
            attempt.update(
                status="not_started", reason="description_binding_unavailable"
            )
            atomic_json(run / "attempts.json", attempts)
            continue
        attempt["status"] = "started"
        atomic_json(run / "attempts.json", attempts)
        try:
            content = bounded_download(
                attempt["url"],
                1024 * 1024 if kind == "description" else 10 * 1024 * 1024,
            )
            filename = family + (
                "_description.json" if kind == "description" else "_sequences.fasta"
            )
            (run / filename).write_bytes(content)
            attempt.update(filename=filename, sha256=digest(content))
            if kind == "description":
                validate_description(content, family)
            else:
                fastau_records(content, family)
            attempt["status"] = "ok"
        except (OSError, ValueError) as exc:
            attempt.update(status="error", error=type(exc).__name__ + ": " + str(exc))
        atomic_json(run / "attempts.json", attempts)
        print(f"{family} {kind}: {attempt['status']}", flush=True)
    result = acquisition_screen(run, config, attempts, exposures)
    manifest = {
        "run_dir": str(run),
        "protocol_sha256": digest((run / "protocol.json").read_bytes()),
        "snapshot_sha256": {
            p.name: digest(p.read_bytes()) for p in run.iterdir() if p.is_file()
        },
    }
    atomic_json(run / "manifest.json", manifest)
    summary = {
        "complete": True,
        "run_dir": str(run),
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        **result,
    }
    atomic_json(run / "summary.json", summary)
    rows = [
        {
            k: a.get(k)
            for k in ("family_id", "resource", "status", "error", "reason", "url")
        }
        for a in attempts
    ]
    report = [
        "# Prospective family source acquisition",
        "",
        protocol["policy"],
        "",
        f"Source acquisition complete: {result['sources_complete']}. Selected metadata entries: {len(result['metadata_panel']['records'])}.",
        "",
        "| Family | Resource | Status | Detail |",
        "|---|---|---|---|",
    ]
    for row in rows:
        report.append(
            f"| {row['family_id']} | {row['resource']} | {row['status']} | {row['error'] or row['reason'] or ''} |"
        )
    report += [
        "",
        "A completed attempt ledger does not mean successful data acquisition. No new structure labels or test inference were performed. Missing sources are not imputed as an empty biological cohort.",
        "",
    ]
    publish(
        ROOT,
        "prospective_family_acquisition",
        summary,
        rows,
        list(rows[0]),
        "\n".join(report),
    )
    return summary


def screening_replay(run, config, attempts, summary, recompute=False):
    """Reuse a previously verified deterministic replay, with all inputs bound.

    Snapshot, protocol and attempt validation must precede this call. The cache
    is outside immutable source runs; a changed summary, input or implementation
    needs a fresh full replay. Live exposure checks at binding remain separate.
    """
    project = Path(__file__).resolve().parents[1]
    paths = [Path(__file__), *sorted((project / "src/rnastable").glob("*.py"))]
    binding = {
        "summary_sha256": digest((run / "summary.json").read_bytes()),
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "code_sha256": {str(p): digest(p.read_bytes()) for p in paths},
    }
    key = digest(json.dumps(binding, sort_keys=True).encode())
    cache = ROOT / "results/prospective_acquisition_replay_cache" / (key + ".json")
    if cache.exists() and not recompute:
        saved = json.loads(cache.read_text())
        require(
            set(saved) == {"binding", "screening"} and saved["binding"] == binding,
            "Screening replay cache binding differs",
        )
        expected = saved["screening"]
        require(
            isinstance(expected, dict)
            and set(expected)
            == {
                "families_downloaded",
                "screening",
                "metadata_panel",
                "sources_complete",
                "test_inference_allowed",
            },
            "Screening replay cache inventory differs",
        )
    else:
        expected = acquisition_screen(
            run, config, attempts, json.loads((run / "exposure.json").read_text())
        )
    require(
        all(summary[k] == v for k, v in expected.items()),
        "Acquisition screening replay differs",
    )
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        atomic_json(cache, {"binding": binding, "screening": expected})
    elif recompute:
        require(
            json.loads(cache.read_text())
            == {"binding": binding, "screening": expected},
            "Full replay disagrees with retained screening cache",
        )
    return expected


def audit_acquisition(path, recompute=False):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(
        summary == json.loads((run / "summary.json").read_text()),
        "Retained acquisition differs",
    )
    manifest_bytes = (run / "manifest.json").read_bytes()
    require(
        digest(manifest_bytes) == summary["manifest_sha256"],
        "Acquisition manifest changed",
    )
    manifest = json.loads(manifest_bytes)
    require(manifest["run_dir"] == str(run), "Acquisition directory differs")
    for name, sha in manifest["snapshot_sha256"].items():
        require(
            Path(name).name == name and digest((run / name).read_bytes()) == sha,
            "Acquisition snapshot changed: " + name,
        )
    protocol_bytes = (run / "protocol.json").read_bytes()
    require(
        digest(protocol_bytes) == manifest["protocol_sha256"],
        "Acquisition protocol changed",
    )
    protocol = audit_protocol(
        Path(json.loads(protocol_bytes)["run_dir"]) / "manifest.json"
    )
    require(protocol == json.loads(protocol_bytes), "Source protocol differs")
    config = json.loads((run / "config.json").read_text())
    require(
        config == json.loads((Path(protocol["run_dir"]) / "config.json").read_text()),
        "Acquisition selection rules differ",
    )
    attempts = json.loads((run / "attempts.json").read_text())
    require(
        set(manifest["snapshot_sha256"])
        == {"config.json", "exposure.json", "protocol.json", "attempts.json"}
        | {a["filename"] for a in attempts if "filename" in a},
        "Acquisition snapshot inventory differs",
    )
    require(
        [(a["family_id"], a["resource"], a["url"]) for a in attempts]
        == [(f, k, u) for f in config["families"] for k, u in family_urls(f).items()],
        "Acquisition request plan differs",
    )
    for attempt in attempts:
        require(
            attempt["status"] in ("ok", "error", "not_started"),
            "Unfinished acquisition outcome",
        )
        if "filename" in attempt:
            require(
                attempt["filename"]
                == attempt["family_id"]
                + (
                    "_description.json"
                    if attempt["resource"] == "description"
                    else "_sequences.fasta"
                ),
                "Downloaded source filename differs",
            )
            require(
                digest((run / attempt["filename"]).read_bytes()) == attempt["sha256"],
                "Downloaded source changed",
            )
    screening_replay(run, config, attempts, summary, recompute)
    print(
        "Prospective acquisition audit passed: protocol, source/failure ledger and metadata screening; no network or inference."
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=ROOT / "configs/prospective_family_panel.json"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--acquire", action="store_true")
    group.add_argument("--verify", action="store_true")
    parser.add_argument("--protocol", type=Path)
    parser.add_argument(
        "--recompute-screening",
        action="store_true",
        help="Force a full deterministic screening replay during --verify",
    )
    args = parser.parse_args()
    require(
        not args.recompute_screening or args.verify,
        "Screening recomputation requires --verify",
    )
    if args.verify:
        return audit_acquisition(
            ROOT / "results/prospective_family_acquisition_summary.json",
            args.recompute_screening,
        )
    if args.acquire:
        protocol = (
            args.protocol
            or Path(
                json.loads(
                    (ROOT / "results/prospective_family_protocol.json").read_text()
                )["run_dir"]
            )
            / "manifest.json"
        )
        return acquire(protocol)
    return freeze(args.config)


if __name__ == "__main__":
    main()
