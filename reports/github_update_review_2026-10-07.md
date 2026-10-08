# RNA-StableAI GitHub update review — 2026-10-07

Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Target: https://github.com/zyliu-OU/rna-stable-ai (`main`, existing public repository).
Previous published commit: `9169b03895074637b320db3090c4495cbab22120`.

## Reviewed development

- Sequence-only local helix head; matched baseline/stack/helix study across three model seeds and frozen 89-training/47-validation records. Reused helix validation F1: 0.5244, 0.4951, 0.4911.
- Explicit sparse-decoder pair penalties, with frozen inference identity and replay.
- Rank-based population sampling with inverse-inclusion-weighted BCE; three fixed training draws and synthetic 1,000/5,000/10,000-nt resource demonstrations.
- Native request journaling, immutable resume bindings, orphan-output rejection, interruption accounting, and Linux parent-death cleanup.
- Completed first helix native replication and separate extended validation of frozen stack finalists.
- Per-record/source/length diagnostics, bound PNG/SVG figures, exposure tracking, and an empty longer-training availability result.

## Verification

Audits passed for the completed first helix replication, all nine matched head fits, decoder penalties, population training, sampled resource steps, development slices, figures, extended native validation, and longer-training availability.
Full suite passed: **481 passed in 219.21 seconds** (`reports/github_update_tests_2026-10-07.log`).
Export file hashes verified; credential-pattern scan passed; no exported file exceeds GitHub's 100 MiB limit. Source/config/test/document whitespace checks passed. Generated SVG and historical logs retain original whitespace and bytes.

## Publication scope and pending work

Existing GitHub history is preserved in an isolated checkout. Source, scripts, tests, configs, synthetic inputs, reports, and result evidence are updated. External dependencies, local credentials, the virtual environment, and top-level trained checkpoints remain excluded. Historical evidence retains absolute paths, so rerun studies on a new machine.

The second helix study (`results/helix_prior_replication_runs/20261007T023827.967339Z`) has ten saved component pointers but no aggregate `summary.json`. It remains incomplete; it was not resumed during this publication task. Independent family evaluation, longer biological annotations, and generalization remain pending. Development metrics and native energy changes do not establish biological stability.

Older `current_work_status.*` files describe their original checkpoint and are retained as historical evidence. The dated handoff created for this update is the continuation reference.
