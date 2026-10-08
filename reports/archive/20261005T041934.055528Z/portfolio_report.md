# Portfolio selection from saved CPU searches

Source: `/home/zyliu/Documents/rna-stable-ai/results/evaluation_robustness_long_summary.json`

4 inputs; 16 searches; 128 attempted proposals. No new folds or training.

| Input | Searches | Proposals | Eligible | Selected beam | Selected seed | Energy change (kcal/mol) |
|---|---:|---:|---:|---:|---:|---:|
| mixed_5000_seed1729 | 4 | 32 | 4 | 400 | 2719 | -5.7 |
| mixed_5000_seed1730 | 4 | 32 | 3 | 400 | 2719 | -4.2 |
| mixed_10000_seed1729 | 4 | 32 | 2 | 200 | 2718 | -5.2 |
| mixed_10000_seed1730 | 4 | 32 | 3 | 200 | 2718 | -4.23 |

Selection reuses saved CPU ViennaRNA validation; no new folds or training.
Best-of-several search selection uses the full recorded search budget.
Selected energy is descriptive on these inputs, not a held-out performance estimate.
Computed minimum energy does not establish biological stability.
Unknown reference energy remains null; input fallback does not invent a zero measurement.
