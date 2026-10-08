# Prospective equal-proposal-budget CPU pilot

Run: `/home/zyliu/Documents/rna-stable-ai/results/equal_budget_runs/20261005T042508.068755Z`

One 32-proposal search versus 4 restarts of 8 proposals; beam 200.

| Length | Input seed | Long change | Restart change | Restart minus long | Winner |
|---:|---:|---:|---:|---:|---|
| 1000 | 1732 | -16.9 | -9.7 | 7.2 | long |
| 1000 | 1733 | -11.4 | -5.6 | 5.8 | long |
| 1000 | 1734 | -20.1 | -16.4 | 3.7 | long |
| 2000 | 1732 | -12.2 | -13.5 | -1.3 | restarts |
| 2000 | 1733 | -32.3 | -10.4 | 21.9 | long |
| 2000 | 1734 | -15.4 | -7.3 | 8.1 | long |

Energy changes are kcal/mol; negative restart minus long favors restarts. Repeated searches are selected within each input before paired comparison.

Per-input search/reference/validation seconds are separate columns in equal_budget.csv. Full proposal and folding-call budgets are independently audited.

Equal proposal caps do not imply equal CPU time or total folding calls.
Search wall time includes LinearFold baseline; do not add it twice.
Restarts require additional baselines and candidate validations; both arms include one input reference per input.
Duplicate and no-legal-proposal events need not invoke a fold; actual fold counts are audited separately.
Serial fixed arm order and single timing observations preclude a speedup claim.
Unknown or failed candidate validations exclude a paired outcome, even when input fallback is available.
Synthetic 1,000/2,000-nt pilot only; no generalization to long RNA or biological stability.
No neural training or GPU folding.
