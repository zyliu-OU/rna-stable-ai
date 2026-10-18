"""Project-wide active/deferred sequence-length policy."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / "configs/project_scope_2026-10-18.json"


def load_policy(path=DEFAULT_POLICY):
    policy = json.loads(Path(path).read_text())
    active = policy.get("active_sequence_length_nt", {})
    deferred = policy.get("deferred_sequence_length_nt", {})
    if (policy.get("schema_version") != 1
            or type(active.get("minimum_inclusive")) is not int
            or type(active.get("maximum_exclusive")) is not int
            or active["minimum_inclusive"] != 1
            or active["maximum_exclusive"] not in (3000, 5000)
            or deferred.get("minimum_inclusive") != active["maximum_exclusive"]
            or policy.get("historical_protocols_remain_immutable") is not True
            or policy.get("automatic_truncation_allowed") is not False
            or policy.get("active_claims_may_use_deferred_evidence") is not False):
        raise ValueError("Invalid project sequence-length scope policy")
    return policy


def length_scope(length, policy=None):
    if type(length) is not int or length < 1:
        raise ValueError("Sequence length must be a positive integer")
    policy = load_policy() if policy is None else policy
    active = policy["active_sequence_length_nt"]
    if active["minimum_inclusive"] <= length < active["maximum_exclusive"]:
        return _labels(policy)[0]
    return _labels(policy)[1]


def _labels(policy):
    boundary = policy["active_sequence_length_nt"]["maximum_exclusive"]
    if boundary == 5000:
        return "active_under_5000_nt", "deferred_5000_nt_or_longer"
    return "active_under_3000_nt", "deferred_3000_nt_or_longer"


def require_active_length(length, policy=None):
    scope = length_scope(length, policy)
    policy = load_policy() if policy is None else policy
    if scope != _labels(policy)[0]:
        boundary = policy["active_sequence_length_nt"]["maximum_exclusive"]
        raise ValueError(f"Active development is limited to sequences under {boundary} nt (maximum {boundary - 1} nt)")
    return length


def partition_records(records, policy=None):
    """Partition without dropping or truncating any retained record."""
    policy = load_policy() if policy is None else policy
    output = {label: [] for label in _labels(policy)}
    for record in records:
        sequence = record["sequence"]
        output[length_scope(len(sequence), policy)].append(record)
    return output
