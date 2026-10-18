# RNA-StableAI: endpoint-ranking development study

Date: 2026-10-18 (America/Los_Angeles)
Workspace: `/home/zyliu/Documents/rna-stable-ai`
Active sequence scope: 1–2,999 nt. Stage 3 target: cell-free expression, queued behind Stage 2 quality review.

## Result and decision

Adding sampled endpoint-ranking loss improved the shorter reused development cohort, but did not improve mean F1 on the longer cohort. Retain the method as an experiment; do not replace the BCE baseline, promote a checkpoint or advance the Stage 3 gate.

| Cohort | Baseline BCE F1 | BCE + ranking F1 | Mean paired difference |
| --- | ---: | ---: | ---: |
| Six references, 1,399–2,973 nt | 0.317351 | 0.316780 | −0.000571 |
| Thirteen references, 400–535 nt | 0.156064 | 0.169610 | +0.013546 |

| Seed | Longer baseline | Longer ranking | Difference | Shorter baseline | Shorter ranking | Difference |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 7 | 0.299484 | 0.312097 | +0.012613 | 0.155288 | 0.177372 | +0.022084 |
| 1729 | 0.314924 | 0.324755 | +0.009831 | 0.147902 | 0.172599 | +0.024698 |
| 20261015 | 0.337646 | 0.313489 | −0.024157 | 0.165003 | 0.158858 | −0.006144 |

The third seed regressed on both cohorts. Native controls remain higher: LinearFold/ViennaRNA F1 are 0.4381/0.4215 on the longer cohort and 0.3301/0.3346 on the shorter cohort. These are reused development references, not independent tests.

## What changed

The new module `src/rnastable/endpoint_ranking.py` compares each legal gold pair's logit with the largest sampled false-pair logit sharing either endpoint. The ranking term is `softplus(1 + competing_logit - gold_logit)`, averaged over gold pairs with a sampled competitor. Gold pairs without a competitor contribute no comparison. The complete objective is the unchanged weighted BCE plus 0.25 times this ranking term.

Competitors come only from the baseline's existing legal negative sample; this is not global hard-negative mining or a structured decoder loss. Storage is linear in sequence length plus sampled pairs, with no dense pair-label tensor. The loss validates the exclusive 3,000-nt boundary, finite scores, binary labels and legal index coordinates. It handles absent comparisons with a differentiable zero.

Frozen settings: 103 training records (61–2,941 nt), seeds 7/1729/20261015, ten epochs, Adam at 0.001, two CPU threads, unchanged local-helix model, exact sparse top-32 decoding in 64-column scoring blocks, fixed final checkpoint. Each seed starts from weights exactly equal to its earlier 103-record BCE baseline. Data, sample seeds, negative counts, record order/shuffle policy, architecture and decoder match that baseline. Validation labels never enter the training objective, and no epoch is selected by validation scores.

Every seed uses 12,511 legal gold pairs and 50,044 sampled negatives; BCE positive weight is 4.0. Approximately 96.86–97.14% of gold pairs have sampled endpoint competitors. Unsupported gold-pair handling remains inherited from the unchanged labeler. Fixed sample counts were checked against the BCE baseline.

## Descriptive diagnosis

Values below average record-level metrics over records and seeds. Mean predicted-pair count is per record, not a count of unique biological structures.

| Cohort / arm | Pair precision | Pair recall | Mean predicted pairs |
| --- | ---: | ---: | ---: |
| Longer / BCE | 0.310728 | 0.324896 | 514.61 |
| Longer / ranking | 0.305701 | 0.329254 | 532.44 |
| Shorter / BCE | 0.137906 | 0.193254 | 142.26 |
| Shorter / ranking | 0.148120 | 0.218701 | 142.82 |

On the longer cohort, more predicted pairs and slightly higher recall coincide with lower precision. On the shorter cohort, both metrics rise. This is a descriptive comparison, not a causal explanation of generalization or a calibration selected for deployment.

## Verification and resources

- Twelve tests passed across the new endpoint loss, sampled supervision and exact sparse decoding. Tests cover highest competing gradients, an unrelated high-scoring negative, competition across endpoint orientation, differentiable zero for missing classes/comparisons, invalid labels, nonfinite scores and the deferred-length boundary.
- The old scoped baseline artifact/score replay passed before freezing the new study.
- All three new fits completed. Checkpoint inference and score replay reproduced all 57 saved predictions from saved model weights, checked initial-weight matches, source/snapshot hashes and exposure identities, and recomputed all F1 comparisons. This was inference replay, not deterministic retraining.
- The precision/recall postprocessor independently recomputed its saved descriptive statistics from predictions.
- Python 3.12.14; PyTorch 2.14.1+cu130; training/inference used CPU. Training-only seconds: 7.961, 7.839 and 7.806. Whole-study process peak RSS: 857,552 KiB (about 837.45 MiB), measured with Linux `ru_maxrss`, not a system-wide or GPU-memory measurement.

## Artifacts and continuation

- Protocol: `results/under3000_endpoint_ranking_protocol_runs/20261018T230319.775906Z/manifest.json`.
- Run: `results/under3000_endpoint_ranking_runs/20261018T230346.828091Z/summary.json`.
- Each `ranking_seed{seed}/` contains initial/final checkpoints, predictions, epoch history/cohort scores in `summary.json`, and exposure events.
- Descriptive statistics: `results/under3000_endpoint_ranking_runs/20261018T230346.828091Z/descriptive_diagnostics.json`.
- Recompute/check them with `scripts/summarize_under3000_ranking.py --verify-run` and the run directory.

Next, investigate whether the uniform sampled pool misses the model's important false competitors. A separately frozen training-only hard-negative experiment is a reasonable next direction; keep the unchanged 103-record BCE baseline, three matched seeds, fixed final epoch and decoder. Do not sweep ranking weights on these cohorts and call the selected result independent validation. The single 2,000–2,999 nt reference and independent family/clan-separated validation gap remain open. Stage 2 remains active; Stage 3 remains queued.
