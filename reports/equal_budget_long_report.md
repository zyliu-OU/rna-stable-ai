# Long-RNA equal-proposal-budget CPU study

Run: `/home/zyliu/Documents/rna-stable-ai/results/equal_budget_batch_runs/20261005T045331.190725Z`

| Length | Input seed | Long change | Restart change | Restart minus long | Winner |
|---:|---:|---:|---:|---:|---|
| 5000 | 1735 | -27.0000 | -8.2000 | 18.8000 | long |
| 5000 | 1736 | -9.7000 | -2.3000 | 7.4000 | long |
| 10000 | 1735 | -14.0000 | -8.2000 | 5.8000 | long |
| 10000 | 1736 | -9.1000 | -7.9000 | 1.2000 | long |

Changes are kcal/mol; negative restart-minus-long favors restarts.

Only two synthetic inputs per length in the default long pilot; descriptive outcomes only.
Equal proposal caps do not equalize folding requests or CPU work.
Concurrent CPU wall times include contention; not isolated benchmark timing.
Each input runs the long arm before its restarts; no speedup or biological stability claim.
Unknown paired outcomes remain missing; no neural training.
