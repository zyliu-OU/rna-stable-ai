# RNA-StableAI development review — 2026-10-11

Workspace: `/home/zyliu/Documents/rna-stable-ai`.

## Development

The helix replication runner used a hard-coded deadline of2026-10-07T04:00:00Z,
so the previous handoff's resume command could not continue after that date.
New studies now default to a two-hour execution window. Resumes retain their
manifest deadline unless an explicit timezone-aware `--deadline-utc` is supplied.
Every execution records the original/effective deadline, manifest hash and driver
hash separately under `execution_attempts/`. The frozen source hashes and parent
plan/directory are checked before child execution. Existing bounded child limits,
locking and unknown-request no-retry behavior remain in force.

## Completed retained study

The seed20261007 model study at
`results/helix_prior_replication_runs/20261007T023827.967339Z` now has all six
component pointers and a `summary.json` with `complete:true`. Its original
manifest SHA-256 remains
`ac958c9c3156257401b9796d40ebda812ad117f660bbac9cf4d7dbfee28bc3d2`.
The execution extension was recorded without changing frozen code/configuration.

All198 planned native requests started:197 completed and one remains interrupted
with unknown outcome and cost. No native request was retried. No request remains
unstarted; no orphan output was found. The ledger retains768 completed proxy
calls and one incomplete proxy attempt. Known native wall time summed over this
study's historical and resumed work is2008.94seconds; unknown time is excluded.
Tests overlapped resumed work, so timing is not an isolated performance result.

Checkpoint-prior selected ViennaRNA energy deltas for model seed20261007:

| Synthetic length | Search seed20261006 | Search seed20261007 |
|---:|---:|---:|
| 1000 | −21.9 | −15.0 |
| 5000 | −2.2 | −11.6 |
| 10000 | −5.9 | −17.9 |

Values are kcal/mol relative to input. The10000-nt compatibility arm with search
seed20261007 retains an unknown selected delta because its earlier input
validation was interrupted. That arm must not be treated as an energy of zero.

## Combined comparison

`reports/checkpoint_prior_comparison_report.md` retains54 trajectories across
the stack checkpoint and two helix checkpoints,12 paired prior comparisons and24
checks of reproduced model-independent control search trajectories. The original
stack10000-nt final references use their separately budgeted300-second extension.

Helix selected lower energy than stack in nine paired comparisons and higher
energy in three. Versus compatibility, eight paired comparisons have lower
energy, three higher energy and one is unknown. No checkpoint is selected or
deployed. Model and search seeds share previously exposed synthetic sequences;
they are not independent biological samples. Native energy does not establish
labelled structure accuracy, biological stability, retained function or
generalization. No new fitting or fresh test-set evaluation was performed.

## Verification

- Full suite:488 passed in222.51seconds (`development-tests-2026-10-11.log`).
- Focused deadline/frozen-source/accounting regressions:10 passed.
- Original helix study and resumed seed20261007 study audits passed.
- Full native request accounting replay passed without native callbacks.
- Combined comparison generated from audited sources; its dedicated replay log
  is `checkpoint-prior-comparison-audit-2026-10-11.log`.
- Changed Python files pass Ruff with the repository's script bootstrap E402
  exception; compilation and whitespace checks pass.

## Pending work

Plan independent family evaluation with explicit exposure exclusions and a frozen
model/decoder configuration. RF00008/RF00017 and reused development records are
already exposed. Longer biological training annotations remain unavailable in
the current audited local archive; synthetic scalability is not long-sequence
biological validation. The saved development changes and evidence are local;
the publication checkout has not been updated in this session.
