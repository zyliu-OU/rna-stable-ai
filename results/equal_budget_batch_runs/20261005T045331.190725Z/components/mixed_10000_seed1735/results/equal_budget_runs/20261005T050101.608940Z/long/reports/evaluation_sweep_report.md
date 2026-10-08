# CPU evaluation sweep

Run: `/home/zyliu/Documents/rna-stable-ai/results/equal_budget_batch_runs/20261005T045331.190725Z/components/mixed_10000_seed1735/results/equal_budget_runs/20261005T050101.608940Z/long/results/sweep_runs/20261005T050101.620894Z`

1/1 runs completed; statuses: {'validated': 1}.

Lengths: [10000]; sequence seeds: [1735]; search seeds: [2740]; beam sizes: [200]; proposal budget: 32.

| Kind | Length | Beam | Validated / planned | Improved | Unchanged | Worsened | Median input pair F1 | Median LF seconds | Mean Vienna delta / nt |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| mixed | 10000 | 200 | 1/1 | 1 | 0 | 0 | 0.53945 | 8.68323 | -0.00140 |

![CPU sweep tradeoffs](../results/sweep_runs/20261005T050101.620894Z/sweep_tradeoffs.png)


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
./scripts/rnastable evaluate --config /home/zyliu/Documents/rna-stable-ai/results/equal_budget_batch_runs/20261005T045331.190725Z/components/mixed_10000_seed1735/results/equal_budget_runs/20261005T050101.608940Z/long/config.json --resume /home/zyliu/Documents/rna-stable-ai/results/equal_budget_batch_runs/20261005T045331.190725Z/components/mixed_10000_seed1735/results/equal_budget_runs/20261005T050101.608940Z/long/results/sweep_runs/20261005T050101.620894Z
```
