# CPU evaluation sweep

Run: `/home/zyliu/Documents/rna-stable-ai/results/sweep_runs/20261005T033230.651381Z`

16/16 runs completed; statuses: {'validated': 16}.

Lengths: [5000, 10000]; sequence seeds: [1729, 1730]; search seeds: [2718, 2719]; beam sizes: [200, 400]; proposal budget: 8.

| Kind | Length | Beam | Validated / planned | Improved | Unchanged | Worsened | Median input pair F1 | Median LF seconds | Mean Vienna delta / nt |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| mixed | 5000 | 200 | 4/4 | 3 | 0 | 1 | 0.73670 | 4.13181 | -0.00026 |
| mixed | 5000 | 400 | 4/4 | 4 | 0 | 0 | 0.75013 | 7.95005 | -0.00076 |
| mixed | 10000 | 200 | 4/4 | 2 | 0 | 2 | 0.53326 | 8.52104 | -0.00017 |
| mixed | 10000 | 400 | 4/4 | 3 | 0 | 1 | 0.64586 | 16.88997 | -0.00003 |

![CPU sweep tradeoffs](../results/sweep_runs/20261005T033230.651381Z/sweep_tradeoffs.png)


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
.venv/bin/python scripts/run_robustness_batches.py --config /home/zyliu/Documents/rna-stable-ai/configs/evaluation_robustness_long.json --workers 2 --resume /home/zyliu/Documents/rna-stable-ai/results/sweep_runs/20261005T033230.651381Z
```

Concurrent CPU wall times include contention; not isolated benchmark timing.
