# RNA-StableAI — handoff 2026-10-05 V1

Project: **RNA-StableAI**

Date: **2026-10-05** (America/Los_Angeles)

Handoff version: **V1**

Absolute workspace: `/home/zyliu/Documents/rna-stable-ai`

## Completed work

- Continued from `reports/RNA-StableAI_HANDOFF_2026-10-04_V1.md`.
- Wired `count_saved_searches` into `src/rnastable/budget_batches.py` heartbeats. Only the newest child run and newest live checkpoint per arm count; archives and obsolete runs are excluded.
- Added the progress helper to new batch code fingerprints.
- Kept exact-provenance resume enforcement. Changed historical driver/helper/environment provenance rejects resume before creating events or launching children, with an explicit explanation and an audit command. No provenance override or migration was introduced.
- Preserved the original driver and edited source/status files under `reports/source_backups/20261006T004345.851559Z/`. The original driver hash matches the completed long study's frozen manifest.
- Documented compatibility in `README.md` and updated `reports/current_work_status.json`.
- All work is local. No neural training, refolding, push, release or tag was performed.

## Verification

- Focused regression tests: **13 passed**, `reports/tests-budget-progress-2026-10-05.xml`.
- Full suite: **177 passed**, `reports/tests-development-2026-10-05.xml`.
- Full completed long-study audit passed: four paired inputs, 20 validated searches, 256 proposal folds, peak owned CPU concurrency two; child plans, raw folds, selections, costs and denominators verified.
- Real historical resume was rejected as intended. Hashes of all **682 study files** were unchanged before/after that check; live checkpoint count is **20**.
- Commands and their output are recorded in `reports/commands.jsonl`.
- Historical synthetic outcomes remain descriptive and do not establish biological stability or population performance. Concurrent timing includes contention.

## Pending work

The requested progress fix and verification are complete. Development changes have not been pushed. Prepare/push to the existing public WIP repository only when requested, using the existing export checkout and preserving its history. The workspace-root `.git` is a protected placeholder.

Public repository: https://github.com/zyliu-OU/rna-stable-ai

Existing export checkout: `/home/zyliu/Documents/rna-stable-ai/exports/20261005T040714.078931Z/rna-stable-ai`

## Exact continuation commands

Read the current status and recheck the completed study:

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/current_work_status.json
.venv/bin/python scripts/log_command.py .venv/bin/python scripts/verify_equal_budget.py --summary results/equal_budget_long_summary.json
.venv/bin/python scripts/log_command.py .venv/bin/python -m pytest -q
```

The old completed-study execution resume command is intentionally incompatible with the updated driver. Audit the saved results instead; no refolding is needed. Do not rewrite historical manifests or replace their fingerprints. An interrupted historical run requires its exact original code, dependencies and environment.

If further budget measurements are explicitly requested, start a new run with the current driver rather than resuming the completed historical run:

```bash
cd /home/zyliu/Documents/rna-stable-ai
./scripts/rnastable compare-search-budgets --config configs/evaluation_equal_budget_long.json --workers 2
```

Keep `.venv`, installed tools, raw measurements and archives. Do not modify system Python, NVIDIA drivers, CUDA, kernel or boot files. Do not begin neural training.
