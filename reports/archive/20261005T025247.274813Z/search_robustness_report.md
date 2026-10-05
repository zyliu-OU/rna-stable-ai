# CPU search-seed robustness study

Run: `/home/zyliu/Documents/rna-stable-ai/results/sweep_runs/20261005T022904.959274Z`

36/36 complete; statuses: {'validated': 36}.

Three mixed-composition input seeds, three search seeds per input, paired beams 200/400, eight proposals/search, mutation cap 40 positions. Each selected output requires independent ViennaRNA improvement. Input references are shared within the run; repeated searches are not independent input samples. CPU folds only; no training.

| Length | Beam | Inputs | Searches | Validated candidates | Selected finalists | Returned inputs | Mean input-mean selected change | SD across input means |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1000 | 200 | 3 | 9 | 9 | 8 | 1 | -6.6333 | 3.4020 |
| 1000 | 400 | 3 | 9 | 9 | 8 | 1 | -7.0000 | 3.8128 |
| 2000 | 200 | 3 | 9 | 9 | 9 | 0 | -6.2222 | 1.0189 |
| 2000 | 400 | 3 | 9 | 9 | 9 | 0 | -7.2556 | 1.2842 |

![Search variability](../results/sweep_runs/20261005T022904.959274Z/search_variability.png)

## Within-input variation

| Length | Beam | Input seed | Selected / searches | Mean selected change | SD across searches | Best | Worst | Candidate worsenings | Distinct selected sequences |
|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 1000 | 200 | 1729 | 2/3 | -2.7667 | 2.7502 | -5.5000 | 0.0000 | 0 | 3 |
| 1000 | 200 | 1730 | 3/3 | -9.1667 | 5.6412 | -15.3000 | -4.2000 | 0 | 3 |
| 1000 | 200 | 1731 | 3/3 | -7.9667 | 2.5482 | -10.9000 | -6.3000 | 0 | 3 |
| 1000 | 400 | 1729 | 2/3 | -2.6000 | 4.3313 | -7.6000 | 0.0000 | 0 | 3 |
| 1000 | 400 | 1730 | 3/3 | -9.0667 | 5.7744 | -15.3000 | -3.9000 | 0 | 3 |
| 1000 | 400 | 1731 | 3/3 | -9.3333 | 2.6274 | -10.9000 | -6.3000 | 0 | 3 |
| 2000 | 200 | 1729 | 3/3 | -5.1667 | 4.4377 | -10.1000 | -1.5000 | 0 | 3 |
| 2000 | 200 | 1730 | 3/3 | -7.2000 | 0.8888 | -8.2000 | -6.5000 | 0 | 3 |
| 2000 | 200 | 1731 | 3/3 | -6.3000 | 7.1358 | -14.1000 | -0.1000 | 0 | 3 |
| 2000 | 400 | 1729 | 3/3 | -8.5667 | 2.1962 | -11.1000 | -7.2000 | 0 | 3 |
| 2000 | 400 | 1730 | 3/3 | -7.2000 | 0.8888 | -8.2000 | -6.5000 | 0 | 3 |
| 2000 | 400 | 1731 | 3/3 | -6.0000 | 6.2522 | -12.8000 | -0.5000 | 0 | 3 |

Energy changes are kcal/mol; lower is better. Candidate worsenings remain visible even though selection returns the input. Unknown measurements stay missing; denominator fields in the CSV expose failures and known selected energies. Group means give each measured input equal weight after averaging its search repeats. Standard deviations are descriptive, not confidence intervals or significance tests.

Only three synthetic inputs at each length were studied. This study does not establish biological stability or generalize search variability to 5,000/10,000 nt. One fold per timing observation includes startup; reference reuse is not repeated timing.

```bash
./scripts/rnastable evaluate --config configs/evaluation_robustness.json
.venv/bin/python scripts/summarize_robustness.py
.venv/bin/python scripts/verify_robustness.py
```
