# RNA-StableAI current work checkpoint

UTC: 20261005T052935.692276Z
Workspace: `/home/zyliu/Documents/rna-stable-ai`

## Completed work

V1 CPU folding, separate untrained encoder benchmark, constrained optimization, sweep/robustness audits, validated portfolio selection and short equal-budget study are saved.
Short equal-budget pilot: 30 validated searches / 384 proposal folds; longer search won five of six paired synthetic inputs. 164 tests passed at that checkpoint.
New long-study runner and configuration passed 171 tests before launching the current benchmark. No training or system installations/changes.

## Current long benchmark

Run: `/home/zyliu/Documents/rna-stable-ai/results/equal_budget_batch_runs/20261005T045331.190725Z`
Actual saved searches from current checkpoints: 20/20; planned total 256 proposals.
At most two independent owned input studies run concurrently. Concurrent CPU costs include contention.

| Input study | Complete | Saved searches | Active PID |
|---|---|---:|---:|
| mixed_5000_seed1735 | True | 5 |  |
| mixed_5000_seed1736 | True | 5 |  |
| mixed_10000_seed1735 | True | 5 |  |
| mixed_10000_seed1736 | True | 5 |  |

The heartbeat counter mistakenly includes archived checkpoints; its displayed count is inflated. The live count above excludes archives. Full results use actual source rows. An archive-safe helper and regression tests have been added but are not connected to the frozen running driver yet; they still need verification.

## Continue safely

The benchmark was left running. Do not start a duplicate driver. Check component logs or the parent driver_status.json. After completion:

```bash
.venv/bin/python scripts/verify_equal_budget.py --summary results/equal_budget_long_summary.json
.venv/bin/python scripts/summarize_equal_budget.py --summary results/equal_budget_long_summary.json --name equal_budget_long
```

If the current driver terminates or is interrupted, resume with unchanged frozen source/config/environment:

```bash
./scripts/rnastable compare-search-budgets --config configs/evaluation_equal_budget_long.json --workers 2 --resume results/equal_budget_batch_runs/20261005T045331.190725Z
```

Changing the driver fingerprint before resuming will trigger its provenance guard. Finish the active run before wiring the progress fix, or retain/use the recorded historical driver.

## Pending development

- Wait for both 10000-nt input studies to finish.
- Audit combined study and render long energy/cost figure.
- Connect archive-safe progress helper after current run; preserve historical driver/provenance and test compatibility.
- Run final tests and record measured long-study results.

Original WIP repository is public. Portfolio/equal-budget and current batch-development updates remain local.

Complete machine-readable state: `/home/zyliu/Documents/rna-stable-ai/checkpoints/development_20261005T052935.692276Z/status.json`
