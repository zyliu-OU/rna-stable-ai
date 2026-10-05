# CPU evaluation sweep

Run: `/home/zyliu/Documents/rna-stable-ai/results/sweep_runs/20261004T205442.491896Z`

36/36 runs completed; statuses: {'validated': 36}.

Lengths: [1000]; sequence seeds: [1729, 1730, 1731]; search seeds: [2718, 2719]; beam sizes: [50, 100, 200]; proposal budget: 24.

| Kind | Length | Beam | Validated / planned | Improved | Unchanged | Worsened | Median input pair F1 | Median LF seconds | Mean Vienna delta / nt |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| mixed | 1000 | 50 | 6/6 | 6 | 0 | 0 | 0.39291 | 0.26578 | -0.01200 |
| mixed | 1000 | 100 | 6/6 | 6 | 0 | 0 | 0.55116 | 0.36610 | -0.01682 |
| mixed | 1000 | 200 | 6/6 | 6 | 0 | 0 | 0.89202 | 0.61639 | -0.01743 |
| structured | 1000 | 50 | 6/6 | 2 | 4 | 0 | 0.99764 | 0.26592 | -0.00028 |
| structured | 1000 | 100 | 6/6 | 3 | 3 | 0 | 0.99764 | 0.41617 | -0.00062 |
| structured | 1000 | 200 | 6/6 | 3 | 3 | 0 | 0.99764 | 0.61679 | -0.00062 |

![CPU sweep tradeoffs](../results/sweep_runs/20261004T205442.491896Z/sweep_tradeoffs.png)


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
./scripts/rnastable evaluate --config /home/zyliu/Documents/rna-stable-ai/configs/evaluation_sweep.json --resume /home/zyliu/Documents/rna-stable-ai/results/sweep_runs/20261004T205442.491896Z
```
