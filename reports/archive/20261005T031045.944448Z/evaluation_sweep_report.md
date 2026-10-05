# CPU evaluation sweep

Run: `/home/zyliu/Documents/rna-stable-ai/results/sweep_runs/20261005T022904.959274Z`

36/36 runs completed; statuses: {'validated': 36}.

Lengths: [1000, 2000]; sequence seeds: [1729, 1730, 1731]; search seeds: [2718, 2719, 2720]; beam sizes: [200, 400]; proposal budget: 8.

| Kind | Length | Beam | Validated / planned | Improved | Unchanged | Worsened | Median input pair F1 | Median LF seconds | Mean Vienna delta / nt |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| mixed | 1000 | 200 | 9/9 | 8 | 1 | 0 | 0.89202 | 0.61643 | -0.00663 |
| mixed | 1000 | 400 | 9/9 | 8 | 1 | 0 | 0.98529 | 0.86674 | -0.00700 |
| mixed | 2000 | 200 | 9/9 | 9 | 0 | 0 | 0.78959 | 1.41842 | -0.00311 |
| mixed | 2000 | 400 | 9/9 | 9 | 0 | 0 | 0.98361 | 2.36904 | -0.00363 |

![CPU sweep tradeoffs](../results/sweep_runs/20261005T022904.959274Z/sweep_tradeoffs.png)


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
./scripts/rnastable evaluate --config /home/zyliu/Documents/rna-stable-ai/configs/evaluation_robustness.json --resume /home/zyliu/Documents/rna-stable-ai/results/sweep_runs/20261005T022904.959274Z
```
