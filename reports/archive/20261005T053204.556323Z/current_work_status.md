# RNA-StableAI saved work status

UTC: 20261005T053116.439564Z
Workspace: `/home/zyliu/Documents/rna-stable-ai`

All source changes and measured research artifacts are saved locally. No neural training or system-driver changes were performed.

## Verification and latest completed study

- 173 automated tests passed: reports/tests-development-checkpoint.xml.
- Long equal-budget study: four paired inputs, 20 validated searches, 256 successful proposal folds, zero recorded search failures.
- Long search selected the lower ViennaRNA energy on all four inputs. Only two synthetic inputs per length: descriptive results, not a general-performance or biological claim.
- Full child and combined audits passed, including native concurrency peak of two owned CPU jobs.
- The driver has finished; no benchmark processes remain active.

| Length | Seed | Long change | Restart change | Winner |
|---:|---:|---:|---:|---|
| 5000 | 1735 | -27.00 | -8.20 | long |
| 5000 | 1736 | -9.70 | -2.30 | long |
| 10000 | 1735 | -14.00 | -8.20 | long |
| 10000 | 1736 | -9.10 | -7.90 | long |

Energy changes are kcal/mol. Concurrent CPU costs include contention and are not isolated benchmark timings.

## Saved artifacts

- Run: `/home/zyliu/Documents/rna-stable-ai/results/equal_budget_batch_runs/20261005T045331.190725Z`
- results/equal_budget_long.csv and results/equal_budget_long_summary.json
- reports/equal_budget_long_report.md
- results/equal_budget_long_cost_summary.json and reports/equal_budget_long_cost_report.md
- Full source sweeps, selected FASTAs, raw fold outputs, native driver events and standalone figure remain under the run directory.
- Exact execution commands and versions are saved in reports/commands.jsonl, study manifests and this checkpoint JSON.

## Known issue and pending work

Historical heartbeat counters included archived checkpoints and displayed inflated search counts. This affected progress display; actual source rows and audited results contain exactly 20 searches. The archive-safe helper budget_progress.py and two regression tests passed, but the running/frozen driver was deliberately left unchanged. Connecting that helper with historical resume compatibility is the next implementation task.

New portfolio, budget studies and batch-development changes remain local and have not been pushed to the public GitHub repository.

## Recheck saved results

```bash
.venv/bin/python scripts/verify_equal_budget.py --summary results/equal_budget_long_summary.json
.venv/bin/python scripts/summarize_equal_budget.py --summary results/equal_budget_long_summary.json --name equal_budget_long
.venv/bin/python -m pytest -q
```

## Optional resume of the completed study

Use the unchanged frozen driver/config/environment; this reuses saved trajectories.

```bash
./scripts/rnastable compare-search-budgets --config configs/evaluation_equal_budget_long.json --workers 2 --resume results/equal_budget_batch_runs/20261005T045331.190725Z
```

## Checkpoint

Machine-readable snapshot: `/home/zyliu/Documents/rna-stable-ai/checkpoints/development_20261005T053116.439564Z/status.json`
Readable snapshot: `/home/zyliu/Documents/rna-stable-ai/checkpoints/development_20261005T053116.439564Z/status.md`
