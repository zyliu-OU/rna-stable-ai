# Long search robustness and bounded CPU execution

Completed a 16-search study at 5,000/10,000 nt with mixed inputs, input seeds
1729/1730, search seeds 2718/2719 and beams 200/400. Each search had eight
proposals, a 40-position mutation cap, 120-second LinearFold timeout,
600-second ViennaRNA timeout and 8 GiB per-process address-space cap.

Run: `/home/zyliu/Documents/rna-stable-ai/results/sweep_runs/20261005T024600.985769Z`.

All 16 computations validated; 128 proposal folds and eight paired beam
comparisons passed audit. Twelve finalists had confirmed lower ViennaRNA energy;
four worsened and were rejected by selection. Use selected.fasta, while retained
finalist.fasta remains research evidence. No tool failures occurred.

| Length | Beam | Selected / searches | Mean input-mean selected change (kcal/mol) |
|---:|---:|---:|---:|
| 5000 | 200 | 3/4 | -1.7500 |
| 5000 | 400 | 4/4 | -3.7750 |
| 10000 | 200 | 2/4 | -2.3575 |
| 10000 | 400 | 3/4 | -0.4250 |

Only two synthetic inputs and two search seeds per length/beam were studied.
The means average search repeats within each input before averaging inputs.
These are descriptive results, not population or biological-stability claims.
At 10,000 nt, beam 200 gave a larger mean selected improvement in this study.

111 tests passed, including bounded concurrency, child-launch failure continuation
and interruption cleanup. The actual driver/component audit verified four
components, identical merged rows and peak two concurrent CPU batches. A real
resume reused all 16 cells; 164 raw-fold file mtimes/sizes remained unchanged.
The short-study artifacts also passed the generalized reporter/auditor.

Concurrent CPU wall times include contention and are not isolated benchmark
measurements. Original CPU/GPU benchmark files and all earlier studies remain
preserved. No dependencies were installed, no system files changed and no
training occurred. Commands, component logs, installed versions, source hashes
and concurrency are recorded in reports and run manifests.

See [search_robustness_long_report.md](search_robustness_long_report.md),
[long_batch_verification.txt](long_batch_verification.txt) and
[long_batch_resume_integrity.txt](long_batch_resume_integrity.txt).

```bash
.venv/bin/python scripts/run_robustness_batches.py --config configs/evaluation_robustness_long.json --workers 2
.venv/bin/python scripts/summarize_robustness.py --config configs/evaluation_robustness_long.json --name robustness_long
.venv/bin/python scripts/verify_robustness.py --summary results/evaluation_robustness_long_summary.json
.venv/bin/python scripts/verify_batch_study.py
```

Next build step: add a multi-start optimization command that compares selected
outputs across seeds using the same reference-energy policy and retains every
source run. This would expose search variability in routine optimization without
starting neural training.
