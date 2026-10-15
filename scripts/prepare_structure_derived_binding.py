#!/usr/bin/env python3
"""Bind predeclared per-sequence PDB annotations without consensus projection."""
# ruff: noqa: E402 -- standalone source bootstrap.

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import publish, timestamp
from rnastable.exposures import collect_known_exposures, record_exposure, read_exposure
from rnastable.native_journal import atomic_json
from rnastable.pair_reference import validate_pairs, has_crossing_pairs
from rnastable.prospective_data import sequence_overlap
from rnastable.reference import digest
from rnastable.reference_audit import require
from rnastable.sequences import validate_sequence
from audit_reference_readiness import assess
from prepare_structure_derived_source import audit as audit_source

NAME = "structure_derived_binding"
GAPS = set(".-_~")
LIMITATIONS = [
    "Exact contacts encoded by the supplied per-sequence PDB-derived annotation, not seed consensus or direct probing measurements.",
    "The upstream FR3D-to-dot-bracket writer uses cWW interactions and positional assignments. Completeness against the raw interaction graph and overwritten/multiple-partner contacts is not established.",
    "Different brackets encode crossing contacts and are retained without flattening. Unbalanced or gap-bound annotations remain unsupported; no contact deletion or replacement.",
    "Known PDB/family and heuristic sequence overlap are screened; unknown training-family, clan and tool provenance remain unresolved.",
    "Repeated structures/sequences are not independent biological replicates. Source reads conservatively consume the declared families for future fresh-test planning.",
]


def parse_alignment(raw, family):
    text = raw.decode()
    require(
        text.startswith("# STOCKHOLM 1.0")
        and text.rstrip().endswith("//")
        and sum(line.strip() == "//" for line in text.splitlines()) == 1,
        "Incomplete or multiple Stockholm alignments",
    )
    sequences, annotations, metadata = {}, {}, {}
    block_sequences, block_annotations = set(), set()
    for line in text.splitlines():
        if not line.strip():
            block_sequences, block_annotations = set(), set()
            continue
        if line.startswith("#=GF "):
            fields = line.split(maxsplit=2)
            require(len(fields) == 3, "Malformed family annotation")
            metadata.setdefault(fields[1], []).append(fields[2])
        elif line.startswith("#=GR "):
            fields = line.split()
            require(len(fields) == 4, "Malformed per-sequence annotation")
            _, identity, tag, fragment = fields
            if not tag.endswith("_SS"):
                continue
            key = (identity, tag)
            require(
                key not in block_annotations,
                "Duplicate annotation within an alignment block",
            )
            block_annotations.add(key)
            annotations[key] = annotations.get(key, "") + fragment
        elif not line.startswith("#") and line.strip() != "//":
            fields = line.split()
            require(len(fields) == 2, "Malformed alignment sequence")
            identity, fragment = fields
            require(
                identity not in block_sequences,
                "Duplicate sequence within alignment block",
            )
            block_sequences.add(identity)
            sequences[identity] = sequences.get(identity, "") + fragment
    require(
        sequences and metadata.get("ID"), "Missing source sequences/family identity"
    )
    require(metadata.get("AC", [family]) == [family], "Source family accession differs")
    width = len(next(iter(sequences.values())))
    require(
        0 < width <= 10000 and all(len(s) == width for s in sequences.values()),
        "Alignment sequence widths differ",
    )
    candidates = []
    for (identity, tag), structure in sorted(annotations.items()):
        require(
            identity in sequences and len(structure) == width,
            "Per-sequence structure identity/width differs",
        )
        match = re.fullmatch(r"([0-9][A-Za-z0-9]{3})_([A-Za-z0-9]+)_SS", tag)
        require(match is not None, "Unbound per-sequence PDB/chain tag")
        pdb, chain = match.group(1).lower(), match.group(2)
        aligned = sequences[identity]
        sequence = (
            "".join(c for c in aligned if c not in GAPS).upper().replace("T", "U")
        )
        try:
            validate_sequence(sequence)
            valid = True
        except ValueError:
            valid = False
        candidates.append(
            {
                "id": f"{family}:{pdb}_{chain}:{identity}",
                "family_id": family,
                "pdb_accession": pdb,
                "chain_id": chain,
                "sequence_id": identity,
                "sequence": sequence,
                "sequence_sha256": digest(sequence.encode()),
                "valid_sequence": valid,
                "aligned_sequence": aligned,
                "annotation": structure,
                "annotation_tag": tag,
            }
        )
    return {
        "family_id": family,
        "alignment_sequences": len(sequences),
        "candidates": candidates,
        "metadata": metadata,
    }


def extended_pairs(structure):
    openers = {"(": ")", "[": "]", "{": "}", "<": ">"}
    openers.update({chr(i): chr(i + 32) for i in range(ord("A"), ord("Z") + 1)})
    closers = {right: left for left, right in openers.items()}
    stacks = {left: [] for left in openers}
    pairs = []
    for index, char in enumerate(structure):
        if char in stacks:
            stacks[char].append(index)
        elif char in closers:
            stack = stacks[closers[char]]
            require(stack, "Unbalanced per-sequence bracket annotation")
            pairs.append([stack.pop(), index])
        else:
            require(char in ".-_~,:", "Unknown per-sequence structure symbol")
    require(not any(stacks.values()), "Unbalanced per-sequence bracket annotation")
    return sorted(pairs)


def map_contacts(record):
    coordinates = {}
    for index, nucleotide in enumerate(record["aligned_sequence"]):
        if nucleotide not in GAPS:
            coordinates[index] = len(coordinates)
    require(
        len(coordinates) == len(record["sequence"]),
        "Sequence-coordinate mapping differs",
    )
    pairs = extended_pairs(record["annotation"])
    require(
        all(a in coordinates and b in coordinates for a, b in pairs),
        "Annotated paired column has no sequence nucleotide",
    )
    mapped = [[coordinates[a], coordinates[b]] for a, b in pairs]
    validate_pairs(mapped, len(record["sequence"]))
    return mapped


def mapping_rows(raw, curated=False):
    rows = []
    for line in raw.decode().splitlines():
        if not line.strip() or line.startswith("#") or line.startswith("rfam_acc"):
            continue
        fields = line.split()
        require(
            len(fields) == (3 if curated else 11)
            and re.fullmatch(r"RF\d{5}", fields[0])
            and re.fullmatch(r"[0-9][A-Za-z0-9]{3}", fields[1]),
            "Malformed source PDB-family mapping",
        )
        rows.append((fields[0], fields[1].lower(), fields[2]))
    return set(rows)


def select_panel(alignments, mappings, exposures, plan):
    known_pdb = {
        r["pdb_accession"].lower() for r in exposures if r.get("pdb_accession")
    }
    known_families = {r["family_id"] for r in exposures if r.get("family_id")}
    inferred_families = {family for family, pdb, _ in mappings if pdb in known_pdb}
    excluded_families = known_families | inferred_families
    prior_sequences = sorted({r["sequence"] for r in exposures})
    selected, decisions = [], []
    for alignment in alignments:
        count = 0
        accepted = []
        for row in sorted(
            alignment["candidates"],
            key=lambda r: (r["pdb_accession"], r["chain_id"], r["sequence_id"]),
        ):
            if not row["valid_sequence"]:
                reason = "invalid_sequence"
            elif (
                row["family_id"] in excluded_families
                or row["pdb_accession"] in known_pdb
            ):
                reason = "known_family_or_pdb_exposure"
            elif (
                row["family_id"],
                row["pdb_accession"],
                row["chain_id"],
            ) not in mappings:
                reason = "missing_exact_pdb_family_chain_mapping"
            elif (
                not plan["minimum_length"]
                <= len(row["sequence"])
                <= plan["maximum_length"]
            ):
                reason = "outside_fixed_length_range"
            elif any(
                sequence_overlap(row["sequence"], sequence)
                for sequence in prior_sequences
            ):
                reason = "prior_sequence_exposure"
            elif any(
                sequence_overlap(row["sequence"], sequence) for sequence in accepted
            ):
                reason = "panel_sequence_redundancy"
            elif count >= plan["max_records_per_family"]:
                reason = "fixed_family_cap"
            else:
                reason = "selected_before_annotation_pair_parsing"
                selected.append(row)
                accepted.append(row["sequence"])
                count += 1
            decisions.append(
                {
                    key: row[key]
                    for key in (
                        "id",
                        "family_id",
                        "pdb_accession",
                        "chain_id",
                        "sequence_sha256",
                    )
                }
                | {"reason": reason}
            )
    return selected, decisions, sorted(inferred_families)


def bind_selected(selected, families):
    records = []
    for row in selected:
        output = {
            key: value
            for key, value in row.items()
            if key not in ("aligned_sequence", "annotation", "valid_sequence")
        }
        output.update(
            sequence_bound=True,
            reference_kind="computational",
            reference_basis="PDB_structure_derived_supplied_cWW_string",
            annotation_sha256=digest(row["annotation"].encode()),
            aligned_sequence_sha256=digest(row["aligned_sequence"].encode()),
            per_sequence_experiment_verified=False,
            raw_interaction_completeness_verified=False,
        )
        try:
            pairs = map_contacts(row)
            output.update(
                reference_status="ok",
                pairs=pairs,
                reference_has_crossing_pairs=has_crossing_pairs(
                    {tuple(p) for p in pairs}
                ),
            )
        except ValueError as exc:
            output.update(reference_status="unsupported_reference", error=str(exc))
        records.append(output)
    groups = []
    for family in families:
        rows = [r for r in records if r["family_id"] == family]
        groups.append(
            {
                "family_id": family,
                "planned_records": len(rows),
                "supported_references": sum(
                    r["reference_status"] == "ok" for r in rows
                ),
            }
        )
    return {
        "records": records,
        "families": groups,
        "planned_records": len(records),
        "supported_references": sum(r["reference_status"] == "ok" for r in records),
        "sequence_bindings_complete": True,
        "known_provenance_overlap": False,
    }


def compute(source_run, protocol_run, exposures):
    config = json.loads((protocol_run / "config.json").read_text())
    root = source_run / "source"
    alignments = [
        parse_alignment((root / f"data/output/{f}.sto").read_bytes(), f)
        for f in config["families"]
    ]
    mappings = mapping_rows((root / "pdb_full_region.txt").read_bytes()) | mapping_rows(
        (root / "pdb_full_region_curated.txt").read_bytes(), curated=True
    )
    selected, decisions, inferred = select_panel(
        alignments, mappings, exposures, config["future_binding"]
    )
    return config, alignments, selected, decisions, inferred


def build(source_path):
    source = audit_source(source_path)
    require(
        source["sources_complete"], "Complete pinned structure-derived source required"
    )
    source_run = Path(source["run_dir"])
    sm = json.loads((source_run / "manifest.json").read_text())
    protocol_run = Path(sm["protocol_run"])
    exposures = collect_known_exposures(ROOT)
    config, alignments, selected, decisions, inferred = compute(
        source_run, protocol_run, exposures
    )
    require(
        not set(config["families"]) & {r.get("family_id") for r in exposures},
        "Source families already consumed before binding",
    )
    run = ROOT / "results" / (NAME + "_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "exposure_before.json", exposures)
    atomic_json(run / "selection.json", decisions)
    atomic_json(run / "source.json", source)
    # Declare all valid annotated source sequences as read before mapping any contacts.
    exposed = [r for a in alignments for r in a["candidates"] if r["valid_sequence"]]
    event = record_exposure(run, "validation_started", exposed)
    binding = bind_selected(selected, config["families"])
    policy = json.loads((protocol_run / "readiness_policy.json").read_text())
    lineage = {
        f: {
            "source_category": "PDB_derived_annotation_raw_completeness_unverified",
            "per_sequence_experiment_verified": False,
            "raw_interaction_completeness_verified": False,
        }
        for f in config["families"]
    }
    readiness = assess(
        binding,
        lineage,
        policy,
        {r["family_id"] for r in exposures if r.get("family_id")} | set(inferred),
    )
    manifest = {
        "run_dir": str(run),
        "source_summary": str(Path(source_path).resolve()),
        "source_manifest_sha256": source["manifest_sha256"],
        "source_run": str(source_run),
        "protocol_run": str(protocol_run),
        "exposure_event": event,
        "snapshot_sha256": {
            str(p.relative_to(run)): digest(p.read_bytes())
            for p in run.rglob("*")
            if p.is_file()
        },
        "code_sha256": {
            str(p): digest(p.read_bytes())
            for p in [
                Path(__file__),
                Path(__file__).with_name("audit_reference_readiness.py"),
                *sorted((ROOT / "src/rnastable").glob("*.py")),
            ]
        },
    }
    atomic_json(run / "manifest.json", manifest)
    summary = {
        "complete": True,
        "run_dir": str(run),
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "binding": binding,
        "readiness": readiness,
        "selection_decisions": decisions,
        "source_annotation_records": sum(len(a["candidates"]) for a in alignments),
        "pdb_inferred_exposed_families": inferred,
        "limitations": LIMITATIONS,
        "inference_performed": False,
        "test_inference_allowed": False,
    }
    atomic_json(run / "summary.json", summary)
    audit(run / "summary.json")
    rows = [
        {
            "family_id": f["family_id"],
            "planned_records": f["planned_records"],
            "supported_references": f["supported_references"],
        }
        for f in binding["families"]
    ]
    report = [
        "# Per-sequence PDB-derived reference binding",
        "",
        f"Source annotations: {summary['source_annotation_records']}. Selected: {binding['planned_records']}; supported: {binding['supported_references']}.",
        "",
        "| Family | Planned | Supported |",
        "|---|---:|---:|",
    ]
    report += [
        f"| {r['family_id']} | {r['planned_records']} | {r['supported_references']} |"
        for r in rows
    ]
    report += [
        "",
        "Readiness failures: " + ", ".join(readiness["readiness_failures"]),
        "",
        *LIMITATIONS,
        "",
    ]
    publish(ROOT, NAME, summary, rows, list(rows[0]), "\n".join(report))
    return summary


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(
        summary == json.loads((run / "summary.json").read_text()),
        "Retained binding summary differs",
    )
    raw = (run / "manifest.json").read_bytes()
    require(
        digest(raw) == summary["manifest_sha256"], "Derived binding manifest changed"
    )
    manifest = json.loads(raw)
    require(manifest["run_dir"] == str(run), "Derived binding run identity differs")
    for name, sha in manifest["code_sha256"].items():
        require(digest(Path(name).read_bytes()) == sha, "Derived binding code changed")
    for name, sha in manifest["snapshot_sha256"].items():
        require(
            digest((run / name).read_bytes()) == sha, "Derived binding snapshot changed"
        )
    source = audit_source(manifest["source_summary"])
    require(
        source == json.loads((run / "source.json").read_text())
        and source["manifest_sha256"] == manifest["source_manifest_sha256"],
        "Derived source binding differs",
    )
    prior = json.loads((run / "exposure_before.json").read_text())
    config, alignments, selected, decisions, inferred = compute(
        Path(manifest["source_run"]), Path(manifest["protocol_run"]), prior
    )
    exposure = manifest["exposure_event"]
    require(
        digest(Path(exposure["path"]).read_bytes()) == exposure["sha256"],
        "Derived source exposure changed",
    )
    event = read_exposure(exposure["path"])
    from rnastable.exposures import exposure_records

    expected_exposed = exposure_records(
        [r for a in alignments for r in a["candidates"] if r["valid_sequence"]],
        str(run) + " validation_started",
    )
    require(
        event["records"] == expected_exposed and event["stage"] == "validation_started",
        "Source exposure inventory differs",
    )
    binding = bind_selected(selected, config["families"])
    policy = json.loads(
        (Path(manifest["protocol_run"]) / "readiness_policy.json").read_text()
    )
    lineage = {
        f: {
            "source_category": "PDB_derived_annotation_raw_completeness_unverified",
            "per_sequence_experiment_verified": False,
            "raw_interaction_completeness_verified": False,
        }
        for f in config["families"]
    }
    readiness = assess(
        binding,
        lineage,
        policy,
        {r["family_id"] for r in prior if r.get("family_id")} | set(inferred),
    )
    require(
        summary["binding"] == binding
        and summary["readiness"] == readiness
        and summary["selection_decisions"]
        == decisions
        == json.loads((run / "selection.json").read_text())
        and summary["pdb_inferred_exposed_families"] == inferred
        and summary["source_annotation_records"]
        == sum(len(a["candidates"]) for a in alignments)
        and summary["limitations"] == LIMITATIONS
        and summary["inference_performed"] is False
        and summary["test_inference_allowed"] is False
        and summary["complete"] is True,
        "Derived binding replay differs",
    )
    print(
        "Structure-derived binding replay passed: exact per-sequence contacts and exposure; no predictions or native calls."
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=ROOT / "results/structure_derived_source_summary.json",
    )
    parser.add_argument("--verify", type=Path, metavar="SUMMARY")
    args = parser.parse_args()
    if args.verify:
        audit(args.verify)
    else:
        build(args.source)


if __name__ == "__main__":
    main()
