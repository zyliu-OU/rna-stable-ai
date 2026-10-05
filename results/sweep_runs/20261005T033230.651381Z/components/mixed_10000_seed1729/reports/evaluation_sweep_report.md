# CPU evaluation sweep

Run: `/home/zyliu/Documents/rna-stable-ai/results/sweep_runs/20261005T033230.651381Z/components/mixed_10000_seed1729/results/sweep_runs/20261005T033803.907327Z`

4/4 runs completed; statuses: {'validated': 4}.

Lengths: [10000]; sequence seeds: [1729]; search seeds: [2718, 2719]; beam sizes: [200, 400]; proposal budget: 8.

| Kind | Length | Beam | Validated / planned | Improved | Unchanged | Worsened | Median input pair F1 | Median LF seconds | Mean Vienna delta / nt |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| mixed | 10000 | 200 | 2/2 | 1 | 0 | 1 | 0.45156 | 8.47802 | -0.00025 |
| mixed | 10000 | 400 | 2/2 | 1 | 0 | 1 | 0.54377 | 17.01685 | 0.00001 |

![CPU sweep tradeoffs](../results/sweep_runs/20261005T033803.907327Z/sweep_tradeoffs.png)


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
./scripts/rnastable evaluate --config /home/zyliu/Documents/rna-stable-ai/results/sweep_runs/20261005T033230.651381Z/components/mixed_10000_seed1729/config.json --resume /home/zyliu/Documents/rna-stable-ai/results/sweep_runs/20261005T033230.651381Z/components/mixed_10000_seed1729/results/sweep_runs/20261005T033803.907327Z
```
