# CPU evaluation sweep

Run: `/home/zyliu/Documents/rna-stable-ai/results/sweep_runs/20261004T212439.359013Z`

6/6 runs completed; statuses: {'validated': 6}.

Lengths: [2000, 5000, 10000]; sequence seeds: [1729]; search seeds: [2718]; beam sizes: [200]; proposal budget: 8.

| Kind | Length | Beam | Validated / planned | Improved | Unchanged | Worsened | Median input pair F1 | Median LF seconds | Mean Vienna delta / nt |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| mixed | 2000 | 200 | 1/1 | 1 | 0 | 0 | 0.54575 | 1.41834 | -0.00505 |
| mixed | 5000 | 200 | 1/1 | 1 | 0 | 0 | 0.63466 | 4.17229 | -0.00048 |
| mixed | 10000 | 200 | 1/1 | 1 | 0 | 0 | 0.45156 | 8.32898 | -0.00052 |
| structured | 2000 | 200 | 1/1 | 1 | 0 | 0 | 0.99882 | 1.46824 | -0.00015 |
| structured | 5000 | 200 | 1/1 | 0 | 1 | 0 | 0.99813 | 4.52482 | 0.00000 |
| structured | 10000 | 200 | 1/1 | 1 | 0 | 0 | 0.94096 | 12.64294 | -0.00008 |

![CPU sweep tradeoffs](../results/sweep_runs/20261004T212439.359013Z/sweep_tradeoffs.png)


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
./scripts/rnastable evaluate --config /home/zyliu/Documents/rna-stable-ai/configs/evaluation_long.json --resume /home/zyliu/Documents/rna-stable-ai/results/sweep_runs/20261004T212439.359013Z
```
