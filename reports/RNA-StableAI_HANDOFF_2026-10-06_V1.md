# RNA-StableAI handoff

- Project: RNA-StableAI
- Date: 2026-10-06 (America/Los_Angeles)
- Version: V1
- Workspace: `/home/zyliu/Documents/rna-stable-ai`
- State: native journal integration and fixed-budget synthetic replication completed and verified.
- Continued from: `reports/RNA-StableAI_HANDOFF_2026-10-05_V15.md`.

## Completed work

- Added `src/rnastable/pooled_native.py` and integrated `NativeJournal` into `scripts/run_checkpoint_prior_pilot.py`.
- Request keys bind policy, phase, and step to the manifest, sequence, stored configuration, source snapshots, checkpoint, Python source digests, and native commands/executable digests.
- Added full-driver locking and `--resume`, `--input-index`, and `--seed` options. Completed requests reuse journal results and verify raw-output digests. Interrupted requests retain unknown outcome/cost and are never retried.
- Resume replays deterministic proposal pools, reuses exposure records, and counts completed proxy calls across all attempts. Incomplete attempts may have additional unknown proxy work.
- Completed-run resume verified zero native callbacks and unchanged retained file bytes. Resume applies to new journal-backed runs; the legacy V15 pilot remains intact and audit-compatible.
- Added nine integration tests in `tests/test_pooled_native.py`, including whole-driver interruption/recovery, exposure preservation, proxy replay accounting, trajectory replay, source/config/checkpoint/runtime binding, and raw-output changes.
- Added `scripts/run_checkpoint_prior_replication.py` with a resumable six-component plan and aggregate audit.
- Replicated all three arms on previously exposed synthetic 1,000/5,000/10,000-nt resource inputs, seeds 20261006 and 20261007. Each arm retains eight planned native proposals, pool size 16, one LinearFold baseline, and two ViennaRNA validation requests.
- Results: 18 trajectories; 198 native requests (162 successful LinearFold, 24 successful ViennaRNA, 12 ViennaRNA timeouts); 768 experimental checkpoint proxy calls; zero unknown native request costs in these completed replicas.
- All 12 ViennaRNA validation requests at 10,000 nt timed out at the existing 30-second limit. Those arms retain the original input, with unknown reference-energy deltas rather than zero-improvement claims.
- Native acceptance/final selection, mutation/protected-position constraints, exposure inventories, raw folds, journal results, and budget denominators passed replay audits. No checkpoint fitting or accuracy evaluation was performed by the replication.
- Updated `README.md` with resume, audit, replication, cost, and limitation guidance.

## Artifacts

- Replication run: `/home/zyliu/Documents/rna-stable-ai/results/checkpoint_prior_replication_runs/20261007T005714.695875Z`
- Aggregate summary: `results/checkpoint_prior_replication_summary.json`
- Aggregate CSV: `results/checkpoint_prior_replication.csv`
- Report: `reports/checkpoint_prior_replication_report.md`
- Timing/verification context: `reports/checkpoint_prior_replication_execution_notes.md`
- Bound source snapshot: `reports/source_snapshots/20261007T011201.883526Z`
- Pre-integration script backups: `reports/source_backups/journal-integration-20261006`

## Verification

- Full suite: **386 passed in 193.87s**; log `reports/journal-integration-full-suite.log`.
- Focused journal/prior/pool/integration suite: **23 passed in 2.53s**; log `reports/journal-integration-focused.log`.
- Aggregate audit: **6 components, 18 exact trajectories, 198 native requests verified**; log `reports/checkpoint-prior-replication-audit.log`.
- Completed-run resume: zero native callbacks and identical retained file bytes; log `reports/pooled-native-completed-resume.log`.
- Legacy pilot audit passed; log `reports/checkpoint-prior-legacy-audit.log`.
- Source comparative-development and synthetic-resource audits passed; logs `reports/journal-stack-comparative-audit.log` and `reports/journal-stack-scalability-audit.log`.
- Source audits and the full suite overlapped portions of replication. Recorded wall times describe this execution, not isolated throughput; scorer timing excludes model setup/audit replay. See execution notes for exact accounting scope.

## Pending work and limits

- The journal integration, six-component replication, and full-suite checks from V15 are complete.
- Independent longer experimental/family-data evaluation remains pending. This stage authorizes no new test-set, generalization, or biological stability claim.
- Longer reference validation would require a separately specified budget/timeout plan; the current 10,000-nt results do not confirm ViennaRNA improvement.
- Repeated search seeds share the same exposed synthetic inputs and are not independent biological samples. Equal planned request counts do not imply equal wall time or proxy costs.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/run_checkpoint_prior_replication.py --verify
.venv/bin/python scripts/verify_checkpoint_prior_pilot.py
.venv/bin/python scripts/run_checkpoint_prior_pilot.py --resume /home/zyliu/Documents/rna-stable-ai/results/checkpoint_prior_pilot_runs/20261007T005714.846113Z
.venv/bin/python -m pytest -q tests/test_native_journal.py tests/test_checkpoint_prior.py tests/test_pooled_proposals.py tests/test_pooled_native.py
.venv/bin/python scripts/verify_stack_comparative_development.py
.venv/bin/python scripts/run_stack_scalability.py --verify
.venv/bin/python -m pytest -q
```
