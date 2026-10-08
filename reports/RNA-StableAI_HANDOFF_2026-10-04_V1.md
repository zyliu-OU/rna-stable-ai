# RNA-StableAI — handoff 2026-10-04 V1

Work stopped at the user's request. All changes are saved locally; no benchmark
processes remain active. No neural training was started.

Project: **RNA-StableAI**

Date: **2026-10-04** (America/Los_Angeles)

Handoff version: **V1**

## Workspace

`/home/zyliu/Documents/rna-stable-ai`

Python 3.12 environment: `.venv`. Use its Python and `./scripts/rnastable`.
Keep the existing environment, tools, raw results and archived files. Do not modify
system Python, NVIDIA drivers, CUDA, kernel or boot files. No sudo is needed.

## Completed and verified

- Original V1 folding and separate untrained encoder benchmarks remain preserved.
- Constrained optimization, sweeps, robustness analysis and validated portfolio selection are implemented.
- Short equal-budget pilot: 30 validated searches / 384 proposal folds; one longer search won five of six paired inputs.
- Long equal-budget replication: 20 validated searches / 256 successful proposal folds, zero recorded search failures. One longer search won all four paired inputs (two synthetic inputs each at 5,000 and 10,000 nt).
- Full source/portfolio/budget/concurrency audits passed. Peak owned CPU concurrency was two.
- Latest full test suite: **173 passed**, recorded in `reports/tests-development-checkpoint.xml` and `reports/commands.jsonl`.
- These synthetic outcomes are descriptive; they do not establish population performance or biological stability. Concurrent costs include contention.

## Where to find the outputs

- `reports/equal_budget_long_report.md`: paired energy results.
- `reports/equal_budget_long_cost_report.md`: CPU costs and standalone figure.
- `results/equal_budget_long.csv` and `results/equal_budget_long_summary.json`.
- `results/equal_budget_long_cost_summary.json`.
- Full run: `results/equal_budget_batch_runs/20261005T045331.190725Z`.
- `reports/current_work_status.json`: versions, source hashes, component details, results and pending work.
- `reports/source_backups/`: preserved source versions before edits.

## Next implementation task

Connect `src/rnastable/budget_progress.py` to the batch driver in
`src/rnastable/budget_batches.py`. Its two regression tests already pass.
The historical driver counts archived checkpoints in its heartbeat display and
showed inflated numbers. Actual merged rows and all scientific audits correctly
contain 20 searches. The helper excludes archives and obsolete runs.

Do not silently change historical provenance. Preserve the recorded old driver
and handle historical resume compatibility explicitly: the current resume guard
rejects changed driver code. The completed long run does not need refolding.
Run the relevant regression tests and full suite after wiring the helper.

## Recheck existing results tomorrow

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/verify_equal_budget.py --summary results/equal_budget_long_summary.json
.venv/bin/python -m pytest -q
```

The figure/report are already saved. To regenerate them from audited evidence:

```bash
.venv/bin/python scripts/summarize_equal_budget.py --summary results/equal_budget_long_summary.json --name equal_budget_long
```

Optional completed-study resume, only with unchanged frozen driver/config/environment:

```bash
./scripts/rnastable compare-search-budgets --config configs/evaluation_equal_budget_long.json --workers 2 --resume results/equal_budget_batch_runs/20261005T045331.190725Z
```

## GitHub

Public WIP repository: https://github.com/zyliu-OU/rna-stable-ai

The original snapshot was pushed from:
`exports/20261005T040714.078931Z/rna-stable-ai`

Portfolio and subsequent equal-budget/batch-development changes are local and
have not been pushed. The workspace-root `.git` is a protected placeholder;
use the export checkout for Git operations. Preserve its existing history when
preparing the next development commit. No release or tag was created.

## Prompt to resume

> Continue RNA-StableAI from reports/RNA-StableAI_HANDOFF_2026-10-04_V1.md. First fix the archive-safe
> batch progress counter with explicit historical resume compatibility, preserve all
> measured artifacts, and rerun the tests. Do not begin neural-network training.
