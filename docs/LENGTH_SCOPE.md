# RNA-StableAI sequence-length scope

Effective 2026-10-18, active development focuses on RNA sequences **shorter
than 3,000 nucleotides**:

- 1–2,999 nt: active development scope.
- 3,000 nt and longer: **REMOVED on 2026-10-20.** Formerly preserved as deferred
  scope; see the reversal notice below.

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
the method requires one. Work at 3,000 nt or above is not scheduled by default,
but can be resumed later through a new, explicitly versioned protocol without
discarding the evidence already developed.

The machine-readable policy is
[`configs/project_scope_2026-10-18.json`](../configs/project_scope_2026-10-18.json).
The October 16 policy remains available for explicit historical replay.
The helper in [`src/rnastable/project_scope.py`](../src/rnastable/project_scope.py)
classifies records without deleting or truncating deferred data.


## Reversal notice, 2026-10-20

This document previously recorded that material at 3,000 nt and longer was **preserved**
as deferred scope, and that the classification deleted and truncated nothing. **That policy
is reversed.** On 2026-10-20 the user instructed that all data for RNA at or above 3,000 nt
be removed, and it was:

- 4 synthetic inputs and 33 run directories deleted, about 555 MB;
- 20 retained artifacts stripped of their out-of-scope records rather than deleted, because
  they carried in-scope evidence in the same files, with every pre-removal hash recorded;
- a content scan now finds **zero** files under `results/` carrying a sequence of 3,000 nt
  or more.

The audit trail is `results/model_purge_runs/`, and the decision is recorded in
[`configs/stage2_to_stage3_gate_v7_2026-10-20.json`](../configs/stage2_to_stage3_gate_v7_2026-10-20.json).

Requirement 5's evidence covered 11 records, 5 of them out of scope, so it was **re-issued**
on the 6 in-scope records: 12 folds, replay 12/12 exact, constraint decoder 12/12 honoured.

**What must not be claimed:** that work above 3,000 nt was never done. It was, and the
handoffs record it. What no longer exists is the data.
