# CPU evaluation sweep

Run: `/home/zyliu/Documents/rna-stable-ai/results/equal_budget_runs/20261005T042508.068755Z/restarts/results/sweep_runs/20261005T042847.716988Z`

24/24 runs completed; statuses: {'validated': 24}.

Lengths: [1000, 2000]; sequence seeds: [1732, 1733, 1734]; search seeds: [2740, 2741, 2742, 2743]; beam sizes: [200]; proposal budget: 8.

| Kind | Length | Beam | Validated / planned | Improved | Unchanged | Worsened | Median input pair F1 | Median LF seconds | Mean Vienna delta / nt |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| mixed | 1000 | 200 | 12/12 | 12 | 0 | 0 | 0.98792 | 0.57052 | -0.00614 |
| mixed | 2000 | 200 | 12/12 | 11 | 1 | 0 | 0.88462 | 1.37200 | -0.00346 |

![CPU sweep tradeoffs](../results/sweep_runs/20261005T042847.716988Z/sweep_tradeoffs.png)


Negative ViennaRNA deltas mean lower computed MFE. Independent validation can contradict the LinearFold surrogate. Aggregation is separated by sequence kind, length and beam; unknown results stay missing.

Use each job's selected.fasta as the output: only a confirmed ViennaRNA improvement selects the finalist. Otherwise it contains the original input. Retained finalist scores, failure statuses and aggregate improvement/worsening counts above describe search candidates before selection.

## Limitations

- CPU folding/search only; no neural training.
- Synthetic pilot, not experimental stability validation.
- Beam comparisons share input sequences and search seeds; observations are paired.
- Search seeds repeat the same input, so runs are not independent biological samples.
- Single timed fold per input/beam; startup is included. Reference times are reused, not independent timing replicates.
- Missing validation is excluded from energy averages and exposed in failure counts. No statistical significance claim.

## Resume this run

```bash
./scripts/rnastable evaluate --config /home/zyliu/Documents/rna-stable-ai/results/equal_budget_runs/20261005T042508.068755Z/restarts/config.json --resume /home/zyliu/Documents/rna-stable-ai/results/equal_budget_runs/20261005T042508.068755Z/restarts/results/sweep_runs/20261005T042847.716988Z
```
