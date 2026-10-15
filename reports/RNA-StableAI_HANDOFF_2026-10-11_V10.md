# RNA-StableAI handoff

Project: RNA-StableAI. Date: 2026-10-11 (America/Los_Angeles). Version: V10.
Workspace: `/home/zyliu/Documents/rna-stable-ai`. Saved UTC: 2026-10-12T04:06:54.222941+00:00.
Current roadmap step: **4 — development candidate-loss diagnostics completed**.

## Completed work

Added `src/rnastable/candidate_diagnostics.py` and
`scripts/analyze_candidate_development.py` with eight focused tests and protocol
`docs/CANDIDATE_DEVELOPMENT.md`. Updated README with the audit command.
The driver verifies the existing nine-checkpoint head study and frozen47-record
validation cohort, retains input/checkpoint/code hashes in an immutable plan,
and records development exposure before model scoring. It partitions every
reference contact into illegal chemistry/minimum distance, nonpositive score,
positive-but-pruned candidate, retained-but-unselected pair or recovered pair.
Every contact remains counted; false positives are reported separately.

All423 checkpoint-record outcomes are retained. The run is `/home/zyliu/Documents/rna-stable-ai/results/candidate_development_runs/20261012T040208.111315Z`.
For seed20261006 helix:2351 reference contacts partition as7 excluded,30
nonpositive,402 positive/pruned,841 retained/missed and1071 recovered.
Predicted false positives:1502. Original mean-record F1 remains0.5244.
Across the three seeds helix prunes402–757 contacts; baseline1200–1305.
Counts sum contacts, while F1 averages records. Repeated initialization seeds
reuse the same biological labels; no independent uncertainty claim is made.
Retained misses can reflect higher-scoring incorrect competitors rather than
incorrect exact decoding. No model fitting, checkpoint selection, decoder
changes, native folds or prospective-panel input occurred.

## Verification

- Full suite: **573 passed in216.35seconds**.
- Focused new diagnostic and existing slice tests:14 passed in0.04seconds.
- Replay audit:all423 outcomes and contact partitions match; bound source,
  checkpoint/code/input hashes and original validation exposure checked.
- Ruff, compileall and whitespace checks pass.
- Logs: `reports/candidate-development-2026-10-11.log`,
  `reports/candidate-development-audit-2026-10-11.log`,
  `reports/candidate-development-focused-2026-10-11.log`,
  `reports/candidate-development-full-suite-2026-10-11.log`.
- No Git index change, commit, push or publication.

## Pending work

Next implement a declared development-only candidate-budget comparison with
16/32/64 partners per right endpoint, all nine frozen checkpoints and all47
validation records. Retain coverage, F1, runtime/storage costs and empty slices;
verify top16 exactly reproduces stored predictions. Larger pools may introduce
incorrect competing pairs; do not assume a gain from improved retention alone.
Checkpoint epochs were chosen with top16, so this is posthoc development tuning,
not joint epoch/budget selection. Keep defaults fixed until evidence supports a
reviewable change. Reserve a new source panel before subsequent testing.

All completed prospective families remain consumed and cannot be reused as
fresh tests. Full training/tool provenance, long biological annotation,
experimental stability/function and validated release remain pending.
No user terminal commands are currently required.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/analyze_candidate_development.py --verify
.venv/bin/python -m pytest -q tests/test_candidate_diagnostics.py tests/test_development_slices.py
.venv/bin/python -m pytest -q
```

Read `reports/candidate_development_review_2026-10-11.md` and
`docs/CANDIDATE_DEVELOPMENT.md` before implementing the next declared study.
Previous current status files preserved at `/home/zyliu/Documents/rna-stable-ai/reports/archive/20261012T040654.222941Z`.
