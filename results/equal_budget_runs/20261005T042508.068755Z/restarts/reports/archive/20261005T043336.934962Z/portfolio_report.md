# Portfolio selection from saved CPU searches

Source: `/home/zyliu/Documents/rna-stable-ai/results/equal_budget_runs/20261005T042508.068755Z/restarts/results/evaluation_sweep_summary.json`

6 inputs; 24 searches; 192 attempted proposals. No new folds or training.

| Input | Searches | Proposals | Eligible | Selected beam | Selected seed | Energy change (kcal/mol) |
|---|---:|---:|---:|---:|---:|---:|
| mixed_1000_seed1732 | 4 | 32 | 4 | 200 | 2743 | -9.7 |
| mixed_1000_seed1733 | 4 | 32 | 4 | 200 | 2743 | -5.6 |
| mixed_1000_seed1734 | 4 | 32 | 4 | 200 | 2741 | -16.4 |
| mixed_2000_seed1732 | 4 | 32 | 4 | 200 | 2743 | -13.5 |
| mixed_2000_seed1733 | 4 | 32 | 3 | 200 | 2740 | -10.4 |
| mixed_2000_seed1734 | 4 | 32 | 4 | 200 | 2740 | -7.3 |

Selection reuses saved CPU ViennaRNA validation; no new folds or training.
Best-of-several search selection uses the full recorded search budget.
Selected energy is descriptive on these inputs, not a held-out performance estimate.
Computed minimum energy does not establish biological stability.
Unknown reference energy remains null; input fallback does not invent a zero measurement.
