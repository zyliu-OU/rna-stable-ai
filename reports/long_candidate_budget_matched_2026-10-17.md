# RNA-StableAI Step 2: matched long candidate-budget study

Date: 2026-10-17 (America/Los_Angeles)  
Workspace: `/home/zyliu/Documents/rna-stable-ai`

This extends the seed-1729 pilot to all six fixed-final checkpoints from the matched 88-record control versus 105-record extended sampled-pair training run. Each arm and seed used the same 11-reference, four-family, label-informed development cohort. For each checkpoint and RNA, pair scores were computed once with a top-64 tile scan; the same bounded exact decoder then evaluated nested top-16, top-32, and top-64 candidate sets. Budgets and interpretation were frozen before execution. All six top-16 prediction sets exactly matched their prior saved predictions.

| Arm | Mean pair F1, top 16 | Mean pair F1, top 32 | Mean pair F1, top 64 | Mean legal gold candidate recall, top 16 / 32 / 64 |
| --- | ---: | ---: | ---: | ---: |
| Control, 88 records | 0.2605 | 0.2823 | 0.2889 | 51.65% / 62.70% / 71.05% |
| Extended, 105 records | 0.2960 | 0.3096 | 0.3123 | 64.71% / 74.15% / 79.86% |

The top-64 minus top-16 F1 gain was positive for all three seeds in each arm: control +0.0226, +0.0320, +0.0306; extended +0.0207, +0.0145, +0.0137. The extended-minus-control mean paired F1 advantage was +0.0355 at top 16, +0.0273 at top 32, and +0.0234 at top 64. The extended arm remained ahead in every seed at every budget, but the lead narrowed as the control arm recovered more from additional candidates. More candidates did not help every RNA: at top 64 versus top 16, the extended arm improved 9, 7, and 6 of the 11 records across the three seeds.

Across all three seeds, the top-64 control candidates contained 14,207 legal gold pairs, of which 6,282 appeared in decoded structures (44.22%). The extended candidates contained 15,968 legal gold pairs, of which 7,050 appeared in decoded structures (44.15%). This ratio is descriptive: the exact decoder maximizes the learned logit objective subject to noncrossing and one-partner constraints, and it does not use the gold labels. Candidate availability alone cannot explain the remaining error; the learned scores and competing candidate pairs also matter.

The sequential six-checkpoint process reached 738,124 KiB peak RSS. Aggregate decoder time across all three seeds was 9.35, 15.61, and 25.62 s for the control arm and 9.63, 15.21, and 23.53 s for the extended arm at top 16, 32, and 64. These times exclude shared candidate scoring and do not represent full inference latency. Candidate counts and per-record measurements are retained in the run summaries.

This supports the development diagnosis that sparse candidate retention limits pair recovery. Even the best mean learned-model score here, 0.3123, remains below the frozen native-control results on this panel (0.4742 LinearFold, 0.4499 ViennaRNA). The panel was selected using reference completeness and contains related sequences. The 17 bpRNA training additions have CRW or RFAM source-group labels, but the local DBN headers contain no family IDs; family separation from validation remains unproved. This is not independent validation, a production-default decision, or evidence of improved biological stability or expression.

Canonical artifacts:

- Frozen protocol: `results/long_candidate_budget_matched_protocol_runs/20261017T183354.499840Z/manifest.json`
- Run summary: `results/long_candidate_budget_matched_runs/20261017T183356.669629Z/summary.json`
- Driver and replay: `scripts/study_long_candidate_budget_matched.py`

Verification: the run replay passed source and code hashes, all six saved top-16 prediction comparisons, per-record F1, aggregate candidate recall and counts, and paired differences. The sampled-pair and long-exact-decoder focused suite passed (6 tests). The driver compiled.

Next, investigate whether score calibration or a different bounded decoder can recover more gold pairs without treating this panel as an independent test. In parallel, obtain source-level family provenance for the bpRNA additions and freeze a genuinely independent long-reference validation panel before any checkpoint promotion.
