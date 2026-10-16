# RNA-StableAI sequence-length scope

Effective 2026-10-16, active development focuses on RNA sequences **shorter
than 5,000 nucleotides**. The boundary is exclusive:

- 1–4,999 nt: active development scope.
- 5,000 nt and longer: preserved, deferred scope.

This is a prioritization boundary, not a claim that every sequence below it is
already supported or validated. Individual methods retain their stricter
limits; for example, some current learned-model and reference protocols are
bounded to 512 or 1,024 nt.

All existing longer-sequence work remains part of the project record. Code,
synthetic 5,000/10,000-nt inputs, configurations, checkpoints, raw outputs,
reports, timing/resource observations and provenance are kept in place. Prior
protocols remain immutable and replayable. Records are not truncated to enter
the active scope, and deferred evidence is not counted as evidence for active
claims.

New work should default to the active range and declare a stricter bound when
the method requires one. Work at 5,000 nt or above is not scheduled by default,
but can be resumed later through a new, explicitly versioned protocol without
discarding the evidence already developed.

The machine-readable policy is
[`configs/project_scope_2026-10-16.json`](../configs/project_scope_2026-10-16.json).
The helper in [`src/rnastable/project_scope.py`](../src/rnastable/project_scope.py)
classifies records without deleting or truncating deferred data.
