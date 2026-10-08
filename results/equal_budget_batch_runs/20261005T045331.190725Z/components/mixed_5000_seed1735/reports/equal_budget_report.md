# Prospective equal-proposal-budget CPU pilot

Run: `/home/zyliu/Documents/rna-stable-ai/results/equal_budget_batch_runs/20261005T045331.190725Z/components/mixed_5000_seed1735/results/equal_budget_runs/20261005T045331.288566Z`

One 32-proposal search versus 4 restarts of 8 proposals; beam 200.

| Length | Input seed | Long change | Restart change | Restart minus long | Winner |
|---:|---:|---:|---:|---:|---|
| 5000 | 1735 | -27.0 | -8.2 | 18.8 | long |

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
