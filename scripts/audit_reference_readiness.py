#!/usr/bin/env python3
"""Audit fixed-panel reference coverage and annotation provenance before inference."""
# ruff: noqa: E402 -- standalone script adds the project source tree before imports.

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import publish, timestamp
from rnastable.exposures import collect_known_exposures
from rnastable.native_journal import atomic_json
from rnastable.prospective_binding import parse_stockholm
from rnastable.reference import digest
from rnastable.reference_audit import require
from evaluate_prospective_panel import audit_binding

NAME = "reference_readiness"
ANNOTATION_POLICY = (
    "retain_exact_source_text_never_infer_experimental_truth_from_citation"
)
SELECTION_POLICY = "fixed_panel_no_replacement_no_model_metrics"
STATUSES = {"ok", "unsupported_reference", "binding_error", "provenance_rejected"}


def validate_policy(policy):
    require(
        type(policy.get("schema_version")) is int and policy["schema_version"] == 1,
        "Readiness policy schema differs",
    )
    for field in (
        "minimum_supported_families",
        "minimum_supported_per_family",
        "minimum_supported_total",
    ):
        require(
            type(policy.get(field)) is int and policy[field] >= 1,
            "Invalid positive integer readiness threshold: " + field,
        )
    for field in (
        "require_complete_sequence_bindings",
        "require_no_known_provenance_overlap",
    ):
        require(policy.get(field) is True, "Required readiness gate differs: " + field)
    require(
        policy.get("annotation_source_policy") == ANNOTATION_POLICY
        and policy.get("selection_policy") == SELECTION_POLICY,
        "Readiness annotation/selection policy differs",
    )


def annotation_lineage(annotations):
    """Classify claims in retained SS text, never upgrade a citation to evidence."""
    sources = annotations.get("SS", [])
    require(
        isinstance(sources, list) and all(isinstance(s, str) for s in sources),
        "Malformed structure-source annotation",
    )
    text = "; ".join(sources)
    normalized = text.casefold()
    tools = [
        name
        for name, pattern in (
            ("RNAfold", r"\brnafold\b"),
            ("RNAalifold", r"\brnaalifold\b"),
            ("MFOLD", r"\bmfold\b"),
            ("PFOLD", r"\bpfold\b"),
            ("R-scape", r"\br[- ]?scape\b"),
            ("CaCoFold", r"\bcacofold\b"),
        )
        if re.search(pattern, normalized)
    ]
    predicted = bool(tools or re.search(r"\bpredict(?:ed|ion|ions)?\b", normalized))
    published = bool(re.search(r"\bpublished\b|\bpmid\s*:", normalized))
    experimental = bool(
        re.search(
            r"\bexperimental(?:ly)?\b|\bnmr\b|\bcrystallograph\w*\b|\bcryo[- ]?em\b|\bprobing\b",
            normalized,
        )
    )
    if predicted and (published or experimental):
        category = "mixed_prediction_and_source_claim"
    elif predicted:
        category = "prediction_declared"
    elif experimental:
        category = "experimental_claim_unverified"
    elif published:
        category = "published_source_unverified"
    else:
        category = "unknown"
    return {
        "structure_source_lines": sources,
        "source_category": category,
        "declared_prediction_tools": tools,
        "structure_source_pmids": sorted(
            set(re.findall(r"\bPMID\s*:\s*(\d+)", text, re.I))
        ),
        "family_bibliography_pmids": annotations.get("RM", []),
        "per_sequence_experiment_verified": False,
        "native_control_reference_independence_certified": False,
    }


def assess(binding, lineages, policy, exposed_families):
    validate_policy(policy)
    records, families = binding["records"], binding["families"]
    require(
        isinstance(records, list) and isinstance(families, list), "Binding rows missing"
    )
    require(
        len({r["id"] for r in records}) == len(records), "Duplicate reference identity"
    )
    names = [f["family_id"] for f in families]
    require(
        len(set(names)) == len(names) and set(names) == set(lineages),
        "Family lineage inventory differs",
    )
    require(
        all(
            r["family_id"] in names and r["reference_status"] in STATUSES
            for r in records
        ),
        "Unexpected reference family/status",
    )
    require(
        binding["planned_records"] == len(records)
        and binding["supported_references"]
        == sum(r["reference_status"] == "ok" for r in records),
        "Binding reference denominators differ",
    )
    rows = []
    for family in families:
        name = family["family_id"]
        selected = [r for r in records if r["family_id"] == name]
        counts = Counter(r["reference_status"] for r in selected)
        require(
            family["planned_records"] == len(selected)
            and family["supported_references"] == counts["ok"],
            "Family reference denominators differ",
        )
        rows.append(
            {
                "family_id": name,
                "planned_records": len(selected),
                "supported_references": counts["ok"],
                "unsupported_references": len(selected) - counts["ok"],
                "status_counts": dict(sorted(counts.items())),
                "minimum_family_coverage_met": counts["ok"]
                >= policy["minimum_supported_per_family"],
                "prior_family_exposure": name in exposed_families,
                **lineages[name],
            }
        )
    total = sum(r["supported_references"] for r in rows)
    qualified = sum(r["minimum_family_coverage_met"] for r in rows)
    reasons = []
    if qualified < policy["minimum_supported_families"]:
        reasons.append("insufficient_supported_families")
    if total < policy["minimum_supported_total"]:
        reasons.append("insufficient_supported_references")
    if not binding["sequence_bindings_complete"]:
        reasons.append("incomplete_sequence_bindings")
    if binding["known_provenance_overlap"]:
        reasons.append("known_provenance_overlap")
    if any(r["prior_family_exposure"] for r in rows):
        reasons.append("families_already_consumed")
    return {
        "planned_records": len(records),
        "supported_references": total,
        "unsupported_references": len(records) - total,
        "families_meeting_coverage": qualified,
        "coverage_thresholds_met": (
            qualified >= policy["minimum_supported_families"]
            and total >= policy["minimum_supported_total"]
        ),
        "fresh_comparative_panel_ready": not reasons,
        "readiness_failures": reasons,
        "independent_experimental_panel_ready": False,
        "training_tool_independence_certified": False,
        "families": rows,
    }


def analyze(sources, policy, exposures):
    exposed = {r["family_id"] for r in exposures if r.get("family_id")}
    output = []
    for path in sources:
        summary = audit_binding(Path(path))
        run = Path(summary["run_dir"])
        manifest = json.loads((run / "manifest.json").read_text())
        evidence = Path(manifest["evidence_run"])
        binding = summary["binding"]
        lineages = {
            family["family_id"]: annotation_lineage(
                parse_stockholm(
                    (evidence / (family["family_id"] + ".sto")).read_bytes(),
                    family["family_id"],
                )["annotations"]
            )
            for family in binding["families"]
        }
        output.append(
            {
                "binding_summary": str(Path(path).resolve()),
                **assess(binding, lineages, policy, exposed),
            }
        )
    return output


def render(summary):
    lines = [
        "# Fixed-panel reference readiness",
        "",
        "Coverage and declared annotation lineage only. No predictions, native folds, model selection, or new exposure.",
        "",
        "Published/cited consensus annotations are not automatically experimental per-sequence truth. Thresholds are design minima, not a statistical-power claim.",
        "",
        "| Panel | Family | Planned | Supported | Source category | Prior family exposure |",
        "|---|---|---:|---:|---|---|",
    ]
    for panel in summary["panels"]:
        for family in panel["families"]:
            lines.append(
                f"| {Path(panel['binding_summary']).parent.name} | {family['family_id']} | {family['planned_records']} | {family['supported_references']} | {family['source_category']} | {family['prior_family_exposure']} |"
            )
    for panel in summary["panels"]:
        lines += [
            "",
            f"Panel {Path(panel['binding_summary']).parent.name} readiness failures: "
            + ", ".join(panel["readiness_failures"]),
            "",
        ]
    lines += [
        "Training/tool independence and per-sequence experimental truth remain uncertified.",
        "",
    ]
    return "\n".join(lines)


def build(root, binding_paths, policy_path):
    sources = sorted({str(Path(p).resolve()) for p in binding_paths})
    require(sources, "At least one fixed binding summary is required")
    policy_raw = Path(policy_path).read_bytes()
    policy = json.loads(policy_raw)
    validate_policy(policy)
    exposures = collect_known_exposures(root)
    panels = analyze(sources, policy, exposures)
    # Freeze the full dependency graph, rather than relying on mutable latest pointers.
    inputs = {str(Path(policy_path).resolve()): digest(policy_raw)}
    for path in sources:
        summary = json.loads(Path(path).read_text())
        manifest_path = Path(summary["run_dir"]) / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        inputs[path] = digest(Path(path).read_bytes())
        inputs[str(manifest_path)] = digest(manifest_path.read_bytes())
        inputs.update(manifest["source_sha256"])
    run = root / "results" / (NAME + "_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    (run / "policy.json").write_bytes(policy_raw)
    atomic_json(run / "exposure.json", exposures)
    atomic_json(run / "sources.json", sources)
    code = [
        Path(__file__),
        *sorted((root / "src/rnastable").glob("*.py")),
        *[
            root / "scripts" / name
            for name in (
                "evaluate_prospective_panel.py",
                "download_prospective_evidence.py",
                "prepare_prospective_family_panel.py",
            )
        ],
    ]
    manifest = {
        "run_dir": str(run),
        "inputs_sha256": inputs,
        "code_sha256": {str(p.resolve()): digest(p.read_bytes()) for p in code},
        "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
    }
    atomic_json(run / "manifest.json", manifest)
    summary = {
        "complete": True,
        "run_dir": str(run),
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "policy": policy,
        "exposure_records_checked": len(exposures),
        "exposures_without_family_id": sum(not r.get("family_id") for r in exposures),
        "panels": panels,
        "inference_performed": False,
        "new_exposure_recorded": False,
        "experimental_independence_certified": False,
    }
    atomic_json(run / "summary.json", summary)
    audit(run / "summary.json")
    rows = [{"panel": p["binding_summary"], **f} for p in panels for f in p["families"]]
    publish(
        root,
        NAME,
        summary,
        rows,
        [
            "panel",
            "family_id",
            "planned_records",
            "supported_references",
            "unsupported_references",
            "source_category",
            "prior_family_exposure",
        ],
        render(summary),
    )
    return summary


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(
        summary == json.loads((run / "summary.json").read_text()),
        "Retained readiness summary differs",
    )
    raw = (run / "manifest.json").read_bytes()
    require(digest(raw) == summary["manifest_sha256"], "Readiness manifest changed")
    manifest = json.loads(raw)
    require(manifest["run_dir"] == str(run), "Readiness run identity differs")
    require(
        set(manifest["snapshot_sha256"])
        == {"policy.json", "exposure.json", "sources.json"},
        "Readiness snapshot inventory differs",
    )
    for field in ("inputs_sha256", "code_sha256"):
        for name, sha in manifest[field].items():
            require(
                digest(Path(name).read_bytes()) == sha,
                "Readiness input/code changed: " + name,
            )
    for name, sha in manifest["snapshot_sha256"].items():
        require(digest((run / name).read_bytes()) == sha, "Readiness snapshot changed")
    policy = json.loads((run / "policy.json").read_text())
    exposures = json.loads((run / "exposure.json").read_text())
    panels = analyze(json.loads((run / "sources.json").read_text()), policy, exposures)
    expected = {
        "complete": True,
        "run_dir": str(run),
        "manifest_sha256": digest(raw),
        "policy": policy,
        "exposure_records_checked": len(exposures),
        "exposures_without_family_id": sum(not r.get("family_id") for r in exposures),
        "panels": panels,
        "inference_performed": False,
        "new_exposure_recorded": False,
        "experimental_independence_certified": False,
    }
    require(summary == expected, "Readiness outcomes differ from replay")
    print(
        f"Reference readiness replay passed: {len(panels)} panels; no predictions or exposure."
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding", action="append", type=Path)
    parser.add_argument(
        "--policy", type=Path, default=ROOT / "configs/reference_readiness.json"
    )
    parser.add_argument("--verify", type=Path, metavar="SUMMARY")
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()
    if args.verify:
        require(not args.binding, "Cannot replace binding inputs during replay")
        result = audit(args.verify)
    else:
        require(args.binding, "Specify at least one --binding summary")
        result = build(ROOT, args.binding, args.policy)
    if args.require_ready and not all(
        p["fresh_comparative_panel_ready"] for p in result["panels"]
    ):
        print(
            "Reference readiness gate not met; no inference authorized.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
