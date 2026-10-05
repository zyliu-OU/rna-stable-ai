# CPU evaluation sweep

Run: `/home/zyliu/Documents/rna-stable-ai/results/sweep_runs/20261004T223012.118701Z`

18/18 runs completed; statuses: {'validated': 18}.

Lengths: [2000, 5000, 10000]; sequence seeds: [1729, 1730, 1731]; search seeds: [2718]; beam sizes: [200, 400]; proposal budget: 8.

| Kind | Length | Beam | Validated / planned | Improved | Unchanged | Worsened | Median input pair F1 | Median LF seconds | Mean Vienna delta / nt |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| mixed | 2000 | 200 | 3/3 | 3 | 0 | 0 | 0.78959 | 1.46923 | -0.00540 |
| mixed | 2000 | 400 | 3/3 | 3 | 0 | 0 | 0.98361 | 2.57088 | -0.00535 |
| mixed | 5000 | 200 | 3/3 | 1 | 0 | 2 | 0.63466 | 4.47443 | 0.00055 |
| mixed | 5000 | 400 | 3/3 | 3 | 0 | 0 | 0.56473 | 8.48163 | -0.00048 |
| mixed | 10000 | 200 | 3/3 | 2 | 0 | 1 | 0.47621 | 8.98144 | -0.00031 |
| mixed | 10000 | 400 | 3/3 | 2 | 1 | 0 | 0.61905 | 18.29801 | -0.00005 |

![CPU sweep tradeoffs](../results/sweep_runs/20261004T223012.118701Z/sweep_tradeoffs.png)


Negative ViennaRNA deltas mean lower computed MFE. Independent validation can contradict the LinearFold surrogate. Aggregation is separated by sequence kind, length and beam; unknown results stay missing.

## Limitations

- CPU folding/search only; no neural training.
- Synthetic pilot, not experimental stability validation.
- Beam comparisons share input sequences and search seeds; observations are paired.
- Search seeds repeat the same input, so runs are not independent biological samples.
- Single timed fold per input/beam; startup is included. Reference times are reused, not independent timing replicates.
- Missing validation is excluded from energy averages and exposed in failure counts. No statistical significance claim.

## Resume this run

```bash
./scripts/rnastable evaluate --config /home/zyliu/Documents/rna-stable-ai/configs/evaluation_replication.json --resume /home/zyliu/Documents/rna-stable-ai/results/sweep_runs/20261004T223012.118701Z
```
