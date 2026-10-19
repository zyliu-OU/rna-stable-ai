"""Versioned score records binding each component score to its provenance.

A record is a provenance binding, not evidence of accuracy. Composite scoring
is refused on purpose: the stability side is in hours on the released STRAND
half-life scale and the translation side is on a released RiboNN task scale
with no inverse transform, so no aggregate is justified.
"""
import hashlib
import math
from pathlib import Path

SCORE_FIELDS = ("component", "score_name", "value", "units", "target_scale",
                "model_identity", "tool_identity", "settings", "raw_artifact_paths",
                "run", "interpretation", "independent_validation")
EXCLUSION_FIELDS = ("component", "reason", "run")
FORBIDDEN_UNITS = ("", "unknown", "none", "n/a", "arbitrary")
# Any of these in a record would assert a cross-component trade-off the
# project has not established.
FORBIDDEN_RECORD_FIELDS = ("composite", "combined_score", "total_score", "rank",
                           "weighted_score", "overall_score", "priority")


def sequence_identity(sequence):
    """Canonical RNA sequence identity, matching the component workers."""
    if not sequence or set(sequence)-set("ACGU"):
        raise ValueError("Canonical ACGU RNA sequence required")
    return {"sha256": hashlib.sha256(sequence.encode()).hexdigest(),
            "length": len(sequence), "alphabet": "ACGU"}


def coding_annotation(length, cds_start=None, cds_end=None, absent_reason=None):
    """Numeric coding boundaries, or an explicit null with a stated reason.

    Descriptive annotation does not satisfy a numeric-boundary requirement, so
    a component needing boundaries must exclude a record carrying null here.
    """
    if cds_start is None or cds_end is None:
        if not absent_reason:
            raise ValueError("Absent numeric annotation requires an explicit reason")
        return {"cds_start": None, "cds_end": None, "annotation_absent_reason": absent_reason,
                "numeric_boundaries_available": False}
    for name, value in (("cds_start", cds_start), ("cds_end", cds_end)):
        if type(value) is not int:
            raise ValueError(f"{name} must be an integer")
    if not 0 <= cds_start < cds_end <= length:
        raise ValueError("Coding boundaries must satisfy 0 <= start < end <= length")
    return {"cds_start": cds_start, "cds_end": cds_end,
            "utr5_size": cds_start, "cds_size": cds_end-cds_start,
            "utr3_size": length-cds_end, "numeric_boundaries_available": True}


def _check_identity(value, label):
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{label} must be a non-empty mapping")
    evidence = [v for k, v in value.items()
                if isinstance(v, str) and v
                and ("sha256" in k or "commit" in k or "version" in k or "hash" in k)]
    if not evidence:
        raise ValueError(f"{label} must carry a hash, commit or version string")


def score_entry(root, **fields):
    """Validate one fully bound score entry."""
    missing = [name for name in SCORE_FIELDS if name not in fields]
    if missing:
        raise ValueError(f"Score entry missing bound fields: {sorted(missing)}")
    extra = set(fields)-set(SCORE_FIELDS)
    if extra:
        raise ValueError(f"Unbound score entry fields: {sorted(extra)}")
    value = fields["value"]
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("Score value must be a finite number")
    if not isinstance(fields["units"], str) or fields["units"].strip().lower() in FORBIDDEN_UNITS:
        raise ValueError("Score entry requires explicit units or a named target scale")
    if not isinstance(fields["target_scale"], str) or not fields["target_scale"].strip():
        raise ValueError("Score entry requires an explicit target scale")
    _check_identity(fields["model_identity"], "model_identity")
    _check_identity(fields["tool_identity"], "tool_identity")
    if not isinstance(fields["settings"], dict):
        raise ValueError("settings must be a mapping")
    paths = fields["raw_artifact_paths"]
    if not isinstance(paths, list) or not paths:
        raise ValueError("At least one raw artifact path is required")
    root = Path(root)
    for relative in paths:
        if not isinstance(relative, str) or Path(relative).is_absolute():
            raise ValueError(f"Raw artifact path must be workspace-relative: {relative!r}")
        if not (root/relative).exists():
            raise ValueError(f"Raw artifact path does not exist: {relative}")
    if fields["independent_validation"] is not False:
        raise ValueError("No component carries independent validation; the field must be False")
    return {name: fields[name] for name in SCORE_FIELDS}


def exclusion_entry(**fields):
    """Validate one explicit exclusion; silence about a component is not allowed."""
    if set(fields) != set(EXCLUSION_FIELDS):
        raise ValueError(f"Exclusion entry requires exactly {sorted(EXCLUSION_FIELDS)}")
    if not isinstance(fields["reason"], str) or not fields["reason"].strip():
        raise ValueError("Exclusion requires an explicit reason")
    return {name: fields[name] for name in EXCLUSION_FIELDS}


def build_record(identity, annotation, scores, exclusions, components):
    """Assemble one record, requiring every component to be scored or excluded."""
    covered = [entry["component"] for entry in scores]+[entry["component"] for entry in exclusions]
    if len(covered) != len(set(covered)):
        raise ValueError("A component may appear once per record")
    if set(covered) != set(components):
        missing = sorted(set(components)-set(covered))
        raise ValueError(f"Every component must be scored or excluded; missing {missing}")
    record = {"schema_version": 1, "record_id": identity["sha256"],
              "sequence": identity, "annotation": annotation,
              "scores": scores, "exclusions": exclusions,
              "composite_score": None,
              "composite_blocked_reason":
                  "Incommensurable units across components and no selected floor; "
                  "no weighting is justified.",
              "independent_validation": False}
    forbidden = [name for name in record if any(bad in name for bad in FORBIDDEN_RECORD_FIELDS)
                 and name not in ("composite_score", "composite_blocked_reason")]
    if forbidden:
        raise ValueError(f"Record must not assert cross-component aggregates: {forbidden}")
    return record


def coverage(records, components):
    """Per-component and joint coverage over the built records."""
    scored = {component: set() for component in components}
    excluded = {component: set() for component in components}
    for record in records:
        for entry in record["scores"]:
            scored[entry["component"]].add(record["record_id"])
        for entry in record["exclusions"]:
            excluded[entry["component"]].add(record["record_id"])
    stability = {c for c in components if c.startswith("strand")}
    translation = {c for c in components if c.startswith("ribonn")}
    with_stability = set().union(*[scored[c] for c in stability]) if stability else set()
    with_translation = set().union(*[scored[c] for c in translation]) if translation else set()
    return {"records": len(records),
            "scored_per_component": {c: len(scored[c]) for c in components},
            "excluded_per_component": {c: len(excluded[c]) for c in components},
            "records_with_stability_score": len(with_stability),
            "records_with_translation_score": len(with_translation),
            "records_with_both_sides": len(with_stability & with_translation),
            "joint_scoring_available": bool(with_stability & with_translation)}
