# RNA-StableAI: Stage 2 review below 3,000 nt

Date: 2026-10-18 (America/Los_Angeles)
Workspace: `/home/zyliu/Documents/rna-stable-ai`

## Decision

**Stage 2 remains open; do not start Stage 3 expression design yet.** The user selected cell-free expression for Stage 3, conditional on credible Stage 2 performance for lengths smaller than 3,000 nt. The current policy uses an exclusive 3,000-nt boundary: 1–2,999 nt active, 3,000 nt and longer deferred. Method-specific lower limits remain in force.

Software checks pass, but the learned model still has a substantial accuracy gap against both native controls, and the available cohorts do not establish independent validation across the length range. A runnable model and lower training loss do not satisfy the scientific gate.

## New matched in-scope study

Frozen before fitting: three seeds (7, 1729, 20261015), ten epochs, identical initial weights within each seed, unchanged sampled-pair objective, and fixed-final checkpoints. The control has 88 training records. The extension adds the 15 prior longer training records below 3,000 nt, for 103 total. Two historical additions of 3,946/3,995 nt are deferred. No training or new model inference in this study uses a sequence of 3,000 nt or longer.

The decoder uses top-32 candidates, chosen from prior **exposed development** diagnostics. The six longer and thirteen shorter references are reused development cohorts; this is not an independent test. No validation result selected an epoch. Both cohorts were scored on the same fixed checkpoint, and results are reported separately.

| Development cohort | Control, mean over three seeds | Extension, mean over three seeds | LinearFold | ViennaRNA |
| --- | ---: | ---: | ---: | ---: |
| Six references, 1,399–2,973 nt | 0.2695 | **0.3174** | 0.4381 | 0.4215 |
| Thirteen references, 400–535 nt | 0.1357 | **0.1561** | 0.3301 | 0.3346 |

Metric: mean record pair F1 within each seed, then mean across seeds for learned methods. Native values use the same reference IDs and retained folds; no new native jobs were required. These cohorts have different annotation sources and must not be pooled into a single generalization score.

| Seed | Control: six longer refs | Extension: six longer refs | Control: thirteen shorter refs | Extension: thirteen shorter refs |
| --- | ---: | ---: | ---: | ---: |
| 7 | 0.2765 | 0.2995 | 0.1566 | 0.1553 |
| 1729 | 0.2536 | 0.3149 | 0.1206 | 0.1479 |
| 20261015 | 0.2783 | 0.3376 | 0.1298 | 0.1650 |

All three longer-reference seed differences are positive. One shorter-reference seed difference is negative. The extension remains approximately 0.121 below LinearFold and 0.104 below ViennaRNA on the longer cohort. The modest data and related families do not support uncertainty estimates or a claim of broad improvement.

## Scoped historical audit and coverage

The earlier 11-reference longer cohort has six references below the new cap and five above it. Five in-scope references lie in 1,000–1,999 nt; only one lies in 2,000–2,999 nt. The shorter feasibility cohort spans 400–535 nt. This does not establish coverage throughout 1–2,999 nt.

The historical 105-record checkpoints, when restricted to the same six longer references, average F1 0.2787/0.2965/0.2949 at top-16/32/64 respectively. Raising candidate count alone did not consistently improve this subset. Those checkpoints include now-deferred training sequences and remain historical development evidence. The fresh 103-record study establishes an in-scope baseline, not an independent comparison proving that removing longer training records improves accuracy.

Known shared training families/clans, exact shared training segments in the longer development cohort, computational structure labels and prior label-informed selection prevent reclassifying these cohorts as independent. The completed CRW provenance work helps plan future exclusions, but does not remove these exposures.

## Verification

- 21 focused checks passed across project scope, metadata planner compatibility, Stage 2 aggregation, exact decoding and sampled supervision.
- The old October 16 scope remains explicitly loadable; boundary tests cover 2,999/3,000 nt and preserve deferred sequences without truncation.
- Scoped historical audit replay passed through original candidate-budget, native-output and five-clan checks.
- All six new fits completed. Saved checkpoint hashes, predictions, exposure events, cohort scores and matched initial weights passed the artifact/score replay; this replay does **not** retrain models.
- The three control models' structures on the six longer references exactly reproduce historical top-32 controls.
- README picture markup is preserved. No publication, inference-default change or checkpoint promotion occurred.

## Artifacts and next step

- Active scope: `configs/project_scope_2026-10-18.json`.
- Stage 2 transition requirements and cell-free target: `configs/stage2_to_stage3_gate_2026-10-18.json`.
- Historical scoped audit: `results/stage2_under3000_audit_runs/20261018T223708.786045Z/summary.json`.
- Fresh study protocol: `results/under3000_development_protocol_runs/20261018T223802.654756Z/manifest.json`.
- Fresh study: `results/under3000_development_runs/20261018T223810.974436Z/summary.json`.
- Original scope source snapshot: `reports/source_snapshots/20261018T223458.718948Z/`.

Focus the next development experiment on pair ranking/training objectives with a separately frozen protocol, keeping the current baseline and native controls. Do not repeatedly tune decoder budgets on the same cohort and call it validation. Before any Stage 3 transition, preregister quantitative acceptance criteria, obtain independent family/clan-separated references within scope, and address the single-record 2,000–2,999 nt band. Existing longer-RNA source leads are deferred; avoid further above-cap acquisition.
