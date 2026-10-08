# RNA-StableAI handoff

- Project: RNA-StableAI
- Date: 2026-10-06 (America/Los_Angeles)
- Version: V2
- Workspace: `/home/zyliu/Documents/rna-stable-ai`
- Saved: 2026-10-06 19:57 America/Los_Angeles
- State: active development; the seed20261006 helix-prior replication completed and audited, while the separately named seed20261007 checkpoint replication remains in progress.

## Completed work

- Hardened native journals and resume behavior: immutable directory bindings, request/config/source/runtime binding, orphan-output refusal, interruption accounting, read-only completed-run audit after later code changes, and Linux parent-death process-group cleanup.
- Added the separate 300-second native reference extension for the frozen 10,000-nt stack finalists. All 12 requests succeeded; original 30-second results remain unchanged. The extended selected deltas were seed20261006: random 0, compatibility −6.1, checkpoint prior −2.4 kcal/mol; seed20261007: random 0, compatibility −5.3, checkpoint prior −6.6.
- Added and audited the sequence-only local-helix pair head: eight contiguous helix/pair-type features, zero-initialized feature weights, same base initialization, full BCE, exact sparse decoding, and matched baseline/stack/helix study across three model seeds. Reused validation F1 for helix was 0.5244, 0.4951 and 0.4911 for seeds20261006/07/08.
- Added explicit sparse decoder pair penalty (0..8), frozen in inference manifests. The posthoc grid selected zero for eight of nine checkpoints; the seed20261006 baseline selected0.5 and rose from0.3885 to0.3979 on the reused validation cohort.
- Added rank-based population sampling with all representable positives, uniform negative sampling without dense labels, inverse-inclusion-weighted BCE, full-population positive weighting, and strict supervision validation. Three fixed draws retained136,538 of1,180,545 negatives and produced reused F1 0.5251/0.5196/0.5245 versus0.5244 for full supervision.
- Added synthetic sampled-training resource steps at1,000/5,000/10,000 nt. At10,000 nt, sampled label tensors use3,298,680 bytes versus374,711,560 bytes for the theoretical full index/label layout; this is a constructed resource demonstration, not biological accuracy.
- Added conservative longer-training availability audit. The local archive has503 CRW training members, maximum674 nt; the fixed1025–4096-nt training-only import therefore remains empty. No holdout/test labels were read or projected.
- Added nested exposure discovery, callback/config/supervision immutability checks, complete per-record development slice diagnostics, source-bound PNG/SVG figures, a helix model card, and native-study denominator accounting that retains unstarted, interrupted, and orphan raw-output work.

## Verification

- Full suite after the latest fixes: **480 passed in 225.20s** (`reports/development-until-21-full-suite-stage5.log`).
- Focused native/training regression: 49 passed (`reports/formatted-native-training-focused.log`).
- Focused population/slice/exposure checks passed; figure audit passed; source linter and compileall passed.
- Helix scalability audit passed for synthetic1000/5000/10000 inputs with no labels or accuracy evaluation.
- Development slice audit passed for423 stored checkpoint predictions (9 checkpoints ×47 records); no new inference or fitting.

## Native study state at handoff

- Frozen helix-prior replication run: `results/helix_prior_replication_runs/20261007T015942.325358Z`.
- All six components of `results/helix_prior_replication_runs/20261007T015942.325358Z` completed and passed audit: 18 trajectories and 198 native requests.
- The separate seed20261007-checkpoint run is `results/helix_prior_replication_runs/20261007T023827.967339Z`; it had eight completed component pointers when this handoff was saved. Resume it only from its frozen snapshot. Interrupted native outcomes remain unknown and unretried.
- Do not claim the second aggregate is complete until its `summary.json` reports `complete:true` and `--verify` passes. Partial denominators remain inspectable.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/run_helix_prior_replication.py --verify
.venv/bin/python scripts/run_helix_prior_replication.py --resume results/helix_prior_replication_runs/20261007T023827.967339Z --publish-name helix_prior_seed7_replication
.venv/bin/python scripts/run_helix_prior_replication.py --verify --publish-name helix_prior_seed7_replication
.venv/bin/python scripts/audit_native_study_accounting.py --study results/helix_prior_replication_runs/20261007T023827.967339Z
.venv/bin/python scripts/audit_native_study_accounting.py --verify
.venv/bin/python scripts/run_helix_prior_replication.py --verify --publish-name helix_prior_seed7_replication
.venv/bin/python scripts/compare_checkpoint_priors.py --verify
.venv/bin/python scripts/run_population_development.py --verify
.venv/bin/python scripts/run_population_resource.py --verify
.venv/bin/python scripts/analyze_development_slices.py --verify
.venv/bin/python scripts/prepare_long_population_training.py --verify
.venv/bin/python scripts/plot_development_review.py --verify
.venv/bin/python -m pytest -q
```

## Key evidence and limitations

- Review: `reports/development_2026-10-06_review.md`.
- Model card: `reports/helix_checkpoint_model_card.md`.
- Figures: `reports/figures/development_2026-10-06.png` and `.svg`.
- Native final validation is an energy-based selection gate, not structure accuracy, biological stability, or retained function. All proposal priors use previously exposed synthetic inputs; repeated seeds share sequences and are not independent biological samples.
- Default exact sparse inference remains bounded to1024 nt. Explicit greedy/refined inference supports up to10000 nt with approximate decoding. No fresh test-set or generalization claim was made.
- For the next handoff, preserve this V2 file and create V3 on the same local date; never overwrite earlier handoffs.
