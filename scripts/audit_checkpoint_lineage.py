#!/usr/bin/env python3
"""Inventory exact checkpoint training/validation metadata without changing exposures."""
# ruff: noqa: E402 -- standalone source bootstrap.

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import publish, timestamp
from rnastable.context_inference import load_checkpoint
from rnastable.exposures import read_exposure
from rnastable.native_journal import atomic_json
from rnastable.reference import digest
from rnastable.reference_audit import require
from rnastable.sequences import validate_sequence
from prepare_structure_derived_binding import mapping_rows
from prepare_structure_derived_source import audit as audit_mapping_source

NAME = "checkpoint_lineage"
SOURCES = {
    "baseline": "results/exact_comparative_development_summary.json",
    "stack": "results/stack_comparative_development_summary.json",
    "helix": "results/helix_comparative_development_summary.json",
}
LIMITATIONS = [
    "PDB-level family matches are conservative any-chain candidates, not exact sequence/chain family assignments.",
    "RNA type, organism and accession text are retained metadata; unknown Rfam accessions are not invented from those labels.",
    "Original upstream train/holdout/test names are provenance, not this project's model roles. Source-test rows reused as development validation are exposed, not fresh tests.",
    "Input byte bindings do not reproduce historical training or establish legacy native-tool training independence.",
]


def keys(rows):
    return Counter(
        (r["sequence"], r.get("family_id"), r.get("pdb_accession", "").lower())
        for r in rows
    )


def describe_records(records, mappings, model, role):
    require(
        isinstance(records, list) and len({r["id"] for r in records}) == len(records),
        "Duplicate or missing lineage record identity",
    )
    by_pdb = defaultdict(set)
    for family, pdb, chain in mappings:
        by_pdb[pdb].add(family)
    output = []
    for record in records:
        sequence = validate_sequence(record["sequence"])
        family = record.get("family_id")
        pdb = record.get("pdb_accession")
        require(
            family is None
            or isinstance(family, str)
            and re.fullmatch(r"RF\d{5}", family),
            "Invalid supplied lineage family",
        )
        require(
            pdb is None
            or isinstance(pdb, str)
            and re.fullmatch(r"[0-9][A-Za-z0-9]{3}", pdb),
            "Invalid supplied lineage PDB",
        )
        candidates = sorted(by_pdb.get(pdb.lower(), set())) if pdb else []
        status = (
            "supplied_family_accession"
            if family
            else "pdb_family_candidates_only"
            if candidates
            else "family_unresolved"
        )
        output.append(
            {
                "model": model,
                "role": role,
                "id": record["id"],
                "length": len(sequence),
                "sequence_sha256": digest(sequence.encode()),
                "supplied_family_id": family,
                "pdb_accession": pdb,
                "pdb_candidate_families": candidates,
                "family_provenance_status": status,
                "rna_type": record.get("rna_type"),
                "organism": record.get("organism"),
                "upstream_split": record.get("upstream_split"),
                "source": record.get("source"),
                "reference_kind": record.get("reference_kind"),
                "bpseq_sha256": record.get("bpseq_sha256"),
                "rna_strand_id": record.get("rna_strand_id"),
            }
        )
    return output


def inspect_models(sources, mappings):
    rows, models, inputs = [], {}, {}
    for name, path in sorted(sources.items()):
        raw, config, checkpoint, _ = load_checkpoint(Path(path))
        summary = json.loads(raw)
        require(
            config["seed"] == 20261006 and summary["complete"] is True,
            "Expected frozen original model seed",
        )
        run = Path(summary["run_dir"])
        retained = run / "summary.json"
        require(
            json.loads(retained.read_text()) == summary,
            "Model summary differs from retained run",
        )
        manifest_path = run / "manifest.json"
        require(
            digest(manifest_path.read_bytes()) == summary["manifest_sha256"],
            "Model training manifest changed",
        )
        manifest = json.loads(manifest_path.read_text())
        require(
            set(manifest["snapshot_sha256"]) == {"train.json", "validation.json"},
            "Model dataset snapshot inventory differs",
        )
        for p in (retained, manifest_path, checkpoint):
            inputs[str(p)] = digest(p.read_bytes())
        events = {}
        for event in summary["exposure_events"]:
            p = Path(event["path"])
            require(
                digest(p.read_bytes()) == event["sha256"],
                "Historical model exposure changed",
            )
            data = read_exposure(p)
            require(
                data["run_dir"] == str(run) and data["stage"] not in events,
                "Model exposure role/run differs",
            )
            events[data["stage"]] = data["records"]
            inputs[str(p)] = event["sha256"]
        require(
            set(events) == {"training_started", "validation_started"},
            "Model exposure inventory differs",
        )
        corpora = {}
        for role, stage in (
            ("train", "training_started"),
            ("validation", "validation_started"),
        ):
            p = run / (role + ".json")
            require(
                digest(p.read_bytes()) == manifest["snapshot_sha256"][p.name],
                "Frozen model data changed",
            )
            inputs[str(p)] = digest(p.read_bytes())
            records = json.loads(p.read_text())["records"]
            require(
                keys(records) == keys(events[stage]),
                "Model record/exposure sequence or family identity differs",
            )
            described = describe_records(records, mappings, name, role)
            rows.extend(described)
            corpora[role] = {
                "records": len(records),
                "dataset_sha256": digest(p.read_bytes()),
                "family_status_counts": dict(
                    Counter(r["family_provenance_status"] for r in described)
                ),
                "supplied_family_counts": dict(
                    Counter(
                        r["supplied_family_id"]
                        for r in described
                        if r["supplied_family_id"]
                    )
                ),
                "upstream_split_counts": dict(
                    Counter(r["upstream_split"] or "unknown" for r in described)
                ),
                "reference_kind_counts": dict(
                    Counter(r["reference_kind"] or "unknown" for r in described)
                ),
                "unresolved_rna_type_counts": dict(
                    Counter(
                        r["rna_type"] or "unknown"
                        for r in described
                        if r["family_provenance_status"] == "family_unresolved"
                    )
                ),
            }
        models[name] = {
            "run_dir": str(run),
            "checkpoint_sha256": digest(checkpoint.read_bytes()),
            "corpora": corpora,
        }
    matched = all(
        len({m["corpora"][role]["dataset_sha256"] for m in models.values()}) == 1
        for role in ("train", "validation")
    )
    return {
        "models": models,
        "rows": rows,
        "matched_corpus_bytes": matched,
        "training_tool_independence_certified": False,
        "new_exposure_recorded": False,
        "model_fitted": False,
        "limitations": LIMITATIONS,
    }, inputs


def build(mapping_path):
    source = audit_mapping_source(mapping_path)
    require(
        source["sources_complete"], "Complete retained family mapping source required"
    )
    root = Path(source["run_dir"]) / "source"
    mappings = mapping_rows((root / "pdb_full_region.txt").read_bytes()) | mapping_rows(
        (root / "pdb_full_region_curated.txt").read_bytes(), curated=True
    )
    sources = {name: str(ROOT / value) for name, value in SOURCES.items()}
    result, inputs = inspect_models(sources, mappings)
    for filename in ("pdb_full_region.txt", "pdb_full_region_curated.txt"):
        p = root / filename
        inputs[str(p)] = digest(p.read_bytes())
    run = ROOT / "results" / (NAME + "_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(
        run / "sources.json",
        {
            name: str(Path(value["run_dir"]) / "summary.json")
            for name, value in result["models"].items()
        },
    )
    atomic_json(run / "mappings.json", sorted(mappings))
    (run / "driver.py").write_bytes(Path(__file__).read_bytes())
    manifest = {
        "run_dir": str(run),
        "input_sha256": inputs,
        "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
        "code_sha256": {
            str(p): digest(p.read_bytes())
            for p in [
                Path(__file__),
                ROOT / "src/rnastable/context_inference.py",
                ROOT / "src/rnastable/exposures.py",
            ]
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
    audit(run / "summary.json")
    report = [
        "# Frozen checkpoint source lineage",
        "",
        *LIMITATIONS,
        "",
        "| Model | Project role | Records | Supplied family IDs | PDB candidates only | Family unresolved | Upstream splits |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for name, item in summary["models"].items():
        for role, corpus in item["corpora"].items():
            counts = corpus["family_status_counts"]
            report.append(
                f"| {name} | {role} | {corpus['records']} | {counts.get('supplied_family_accession', 0)} | {counts.get('pdb_family_candidates_only', 0)} | {counts.get('family_unresolved', 0)} | {corpus['upstream_split_counts']} |"
            )
    report += [
        "",
        "All three models use identical train/validation corpus bytes: "
        + str(summary["matched_corpus_bytes"]),
        "",
    ]
    publish(
        ROOT,
        NAME,
        summary,
        result["rows"],
        [
            "model",
            "role",
            "id",
            "length",
            "sequence_sha256",
            "supplied_family_id",
            "pdb_accession",
            "pdb_candidate_families",
            "family_provenance_status",
            "upstream_split",
            "rna_type",
            "reference_kind",
        ],
        "\n".join(report),
    )
    return summary


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(
        summary == json.loads((run / "summary.json").read_text()),
        "Retained lineage summary differs",
    )
    raw = (run / "manifest.json").read_bytes()
    require(digest(raw) == summary["manifest_sha256"], "Lineage manifest changed")
    manifest = json.loads(raw)
    require(
        manifest["run_dir"] == str(run)
        and set(manifest["snapshot_sha256"])
        == {"sources.json", "mappings.json", "driver.py"},
        "Lineage run/inventory differs",
    )
    for field in ("input_sha256", "code_sha256"):
        for name, sha in manifest[field].items():
            require(
                digest(Path(name).read_bytes()) == sha, "Lineage input/code changed"
            )
    for name, sha in manifest["snapshot_sha256"].items():
        require(digest((run / name).read_bytes()) == sha, "Lineage snapshot changed")
    mappings = {tuple(row) for row in json.loads((run / "mappings.json").read_text())}
    result, _ = inspect_models(json.loads((run / "sources.json").read_text()), mappings)
    require(
        summary
        == {
            "complete": True,
            "run_dir": str(run),
            "manifest_sha256": digest(raw),
            **result,
        },
        "Lineage metadata replay differs",
    )
    print(
        "Checkpoint lineage replay passed: exact dataset/exposure/weight bindings; no fitting, inference or exposure."
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mapping-source",
        type=Path,
        default=ROOT
        / "results/structure_derived_source_runs/20261015T021501.529110Z/summary.json",
    )
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        audit(args.verify)
    else:
        build(args.mapping_source)


if __name__ == "__main__":
    main()
