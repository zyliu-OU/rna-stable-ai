# RNA-StableAI candidate-budget development review — 2026-10-13

Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Run: `/home/zyliu/Documents/rna-stable-ai/results/candidate_budget_development_runs/20261014T001919.742401Z`.
Protocol: [CANDIDATE_BUDGET_DEVELOPMENT.md](../docs/CANDIDATE_BUDGET_DEVELOPMENT.md).

Completed the declared 16/32/64 pool comparison on all nine selected checkpoints
and all 47 reused development records. All 1269 outcomes remain in the CSV and
retained JSON. All 423 top-16 structures exactly reproduce the original saved
predictions. Candidate pools are nested, exact logit objectives never decrease,
and every reference contact remains in the diagnostic denominator. Source,
checkpoint, code, cohort, exposure and outcome hashes bind the run.

## Accuracy and retention

Mean record pair F1, separately for every initialization seed:

| Seed | Head | Top-16 | Top-32 | Top-64 |
|---:|---|---:|---:|---:|
| 20261006 | baseline | 0.388499 | 0.388059 | 0.403335 |
| 20261007 | baseline | 0.376277 | 0.383412 | 0.393030 |
| 20261008 | baseline | 0.393253 | 0.363242 | 0.376919 |
| 20261006 | stack | 0.423380 | 0.428287 | 0.443834 |
| 20261007 | stack | 0.401013 | 0.403147 | 0.417943 |
| 20261008 | stack | 0.405548 | 0.389244 | 0.402716 |
| 20261006 | helix | 0.524423 | 0.518819 | 0.515626 |
| 20261007 | helix | 0.495077 | 0.498060 | 0.493577 |
| 20261008 | helix | 0.491069 | 0.478505 | 0.483749 |

Helix positive reference contacts pruned by top-16/32/64 respectively:
402/160/43 for seed 20261006, 757/250/56 for seed 20261007, and
731/284/81 for seed 20261008. Each checkpoint has 2351 reference contacts.
Although gold retention improves, helix top-64 F1 regresses on all three seeds.
Across seeds its descriptive mean record F1 is 0.503523/0.498461/0.497651.
The mean uses the same 47 records three times; it is not independent biological
uncertainty. Baseline and stack top-64 improve mean F1 on two seeds and regress
on one. No universal pool enlargement is supported.

For seed 20261006 helix, larger pools increase recovered reference contacts
1071/1105/1101, while false positives increase 1502/1727/1828. Per-record F1
regressions affect 16 records at top-32 and 17 at top-64; improvements affect
five records at each budget. Better candidate coverage alone does not establish
better predictions. Source, length and reference-kind slices, including empty
slices, and all per-record changes remain available in the retained artifacts.

## Costs and decision

For the 141 helix checkpoint-record outcomes at each budget, summed decoder
seconds are 1.863/3.229/5.276. Across all heads, maximum per-record candidate
array bytes are 132720/252416/457296. Maximum DP-array storage remains 3538188
bytes at every budget. These observations measure array costs and single CPU
wall times with two Torch threads. They exclude other allocations, include
fixed-order warmup effects and were collected while the test suite ran on the
host; they do not establish statistically significant speed differences.

Keep the default top-16 configuration unchanged. Original checkpoint epochs
were selected with that setting, so this is posthoc development tuning, not
joint epoch/budget selection. No fitting, checkpoint selection, native folding,
prospective-panel input, commit, push or publication occurred.

Next declare a development-only experiment addressing retained-contact scoring
and competing false positives, with a frozen protocol and complete matched
outcome accounting. New independent evaluation requires a newly reserved,
screened source panel before testing. All consumed prospective families remain
exposed. Full training/tool provenance, long biological annotations,
experimental stability/function and validated release remain pending.

## Verification

The prior 423-outcome candidate diagnostic replays successfully. New focused
checks cover missing/duplicate/unknown planned outcomes, empty slices, measured
cost accounting, accuracy regression from a nested pool, and failure retention
when top-16 reproduction or pool nesting fails. The budget replay recomputes
all structures, partitions, objective/storage values and aggregates. Historical
times are hash-bound and validated, rather than compared to newly measured times.
Final test counts and audit status are recorded in the versioned handoff.

Logs: `candidate-original-audit-2026-10-13.log`,
`candidate-budget-development-2026-10-13.log`,
`candidate-budget-audit-2026-10-13.log`,
`candidate-budget-focused-2026-10-13.log`,
`candidate-budget-full-suite-2026-10-13.log` under `reports/`.
