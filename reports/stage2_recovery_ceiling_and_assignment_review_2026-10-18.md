# Stage 2 recovery ceiling and endpoint assignment review — 2026-10-18

Workspace: `/home/zyliu/Documents/rna-stable-ai`. Active scope: **1–2,999 nt**. Stage 3 target: cell-free expression, queued behind Stage 2.

## Decision

A gold-label diagnostic identified large remaining pair-selection and candidate-recovery gaps. One subsequently frozen endpoint partner/null auxiliary-loss experiment produced a modest three-seed improvement on the longer exposed development cohort and a smaller, inconsistent short-cohort gain. Retain it as a development variant; **keep the original 103-record BCE comparison baseline and all inference defaults unchanged**. Stage 2 remains open. No independent-validation or Stage 3 gate passed.

| Cohort | BCE baseline F1 | Assignment F1 | Difference | LinearFold | ViennaRNA |
| --- | --- | --- | --- | --- | --- |
| Long, 6 references | 0.3173511819 | 0.3261881307 | +0.0088369487 | 0.4381334451 | 0.4214700331 |
| Short, 13 references | 0.1560640870 | 0.1606458705 | +0.0045817835 | 0.3301074317 | 0.3346291106 |

Metric: mean record pair F1 per cohort within seed, then mean across seeds. Native controls are previously saved results on the same cohorts; no new native folds were requested. Both cohorts have been reused for development and are not independent tests.

## Gold-label ceiling diagnostic

Let G be all original reference pairs, L the legal subset (AU/UA/CG/GC/GU/UG with index separation at least four), K_full the maximum cardinality noncrossing subset of L, and K_candidate the maximum cardinality noncrossing gold subset available in the baseline's retained candidate pool. The unchanged exact sparse decoder computes each oracle using only allowed gold edges with unit weights. These outputs explicitly use gold labels and are **not model predictions**. All original gold pairs, including unsupported and crossing pairs, remain in the scoring denominator. Since false-positive edges cannot improve pair F1, the optimistic oracle F1 is 2K/(G+K); it bounds any feasible prediction in its allowed edge set.

Candidate pools are baseline **strictly positive** logits retained at top 32 per right endpoint, with block size 64. Missing candidates can arise from either the threshold or top-k pruning. These effects are not separately identified here. Baseline actual structures must exactly reproduce the frozen saved predictions before decomposition. Cached full oracles bind the exact sequence and reference-pair hashes.

| Cohort | Actual F1 | Full legal gold oracle F1 | Retained gold oracle F1 | Retained legal-gold recall (micro) | Actual TP / retained-oracle TP (micro) |
| --- | --- | --- | --- | --- | --- |
| long | 0.3173511819 | 0.9606455787 | 0.8256698667 | 0.7617835938 | 0.4595196437 |
| short | 0.1560640870 | 0.9027071479 | 0.7059245554 | 0.6612121212 | 0.3668666359 |

The missed-gold count partition is `(G-L) + (L-K_full) + (K_full-K_candidate) + (K_candidate-actual_TP) = G-actual_TP`:

| Missing-gold component | Long count (18 record-seed rows) | Long fraction | Short count (39 rows) | Short fraction |
| --- | --- | --- | --- | --- |
| unsupported_gold | 639 | 10.6447% | 564 | 18.3773% |
| legal_noncrossing_limit | 0 | 0.0000% | 51 | 1.6618% |
| retained_candidate_limit | 1966 | 32.7503% | 1082 | 35.2558% |
| score_selection_gap | 3398 | 56.6050% | 1372 | 44.7051% |

These fractions partition **missed gold counts**, not F1 loss or causal attribution. Long/short actual false-positive counts are 6,374/4,753 across record-seed rows and are separate from the partition. The score-selection gap reflects the model scores/objective relative to label-informed recovery; it is not evidence of an exact-decoder implementation bug. Counts repeat references across three optimizer seeds, not independent biological samples.

Unique-reference totals: long G=2,964, L=2,751, K_full=2,751; short G=1,288, L=1,100, K_full=1,083. Therefore legal noncrossing restrictions alone do not explain the large observed model gap, although unsupported labels create a real ceiling. `bpRNA_RFAM_5479` (417 nt) has 75 noncanonical reference pairs and a full legal gold oracle F1 of 0.4347826087. This is a source/chemistry annotation audit flag, not proof of a sequence/reference mismatch. Do not remove this record or filter its original labels after seeing the result. The existing subset loader was inspected read-only; no label correction was made.

## Endpoint partner/null experiment

Same 103 training records (88 base plus 15 in-scope longer additions), lengths 61–2,941 nt, seeds 7/1729/20261015, ten epochs, fixed final checkpoint. Same original uniform samples: 12,511 legal positives plus 50,044 negatives per seed (`max_negatives=8192`, four negatives per positive). Initial state tensors match the baseline seed-by-seed; shuffle/optimizer/model/decoder settings remain matched. Adam lr=0.001, weighted BCE positive weight=4.0, embedding16/channels32/pairdim16, dilations [1,2,4,8], local_helix_context_v1, two CPU threads, exact sparse top32/block64.

New objective: **weighted BCE + 0.25 × endpoint assignment loss**. Each known nucleotide chooses among incident sampled pair logits and an explicit null class with logit zero. The target is its gold partner or null if truly unpaired. Unsupported gold endpoints are unknown for this auxiliary loss rather than relabeled unpaired; BCE behavior remains inherited unchanged. Each epoch includes 53,020 known nodes (25,022 paired, 27,998 null) and 2,154 unknown nodes. Stable scatter log-sum-exp uses O(n+m) auxiliary storage. This is sampled local categorical supervision, not a globally normalized noncrossing structure likelihood. No teacher mining, ranking term, validation-based epoch selection or decoder retuning was used.

| Seed | Long baseline | Long assignment | Long difference | Short baseline | Short assignment | Short difference |
| --- | --- | --- | --- | --- | --- | --- |
| 7 | 0.2994837245 | 0.3144590134 | 0.0149752890 | 0.1552876958 | 0.1795793890 | 0.0242916932 |
| 1729 | 0.3149238665 | 0.3206222634 | 0.0056983969 | 0.1479018661 | 0.1553106038 | 0.0074087377 |
| 20261015 | 0.3376459548 | 0.3434831152 | 0.0058371604 | 0.1650026990 | 0.1470476186 | -0.0179550804 |

The longer mean improves in all three seeds; the short cohort regresses for seed 20261015. Mean precision and recall both rise slightly, without resolving the native gap:

| Arm | Cohort | Rows | Mean precision | Mean recall | Mean predicted pairs |
| --- | --- | --- | --- | --- | --- |
| baseline | long | 18 | 0.3107277878 | 0.3248961817 | 514.6111111111 |
| baseline | short | 39 | 0.1379064654 | 0.1932544216 | 142.2564102564 |
| assignment | long | 18 | 0.3220692468 | 0.3313669272 | 508.5555555556 |
| assignment | short | 39 | 0.1409991377 | 0.2030950659 | 139.8717948718 |

These are descriptive means from saved per-record score rows. No confidence intervals or significance claims were made. The reused cohort informed selection of this experiment; absence of validation use inside the training loop does not make it independent. Sample/target hashes, initial-state equality, saved checkpoints, exposures, predictions and scores are verified by replay. No checkpoint is promoted.

## Artifacts and verification

- Oracle protocol: `results/under3000_recovery_ceiling_protocol_runs/20261018T234336.469918Z/manifest.json`.
- Oracle run: `results/under3000_recovery_ceiling_runs/20261018T234344.201186Z/` (full_gold_oracles.json, summary.json, manifest.json, and three seed folders with rows.json plus 19 candidate NPZ archives each).
- Assignment protocol: `results/under3000_endpoint_assignment_protocol_runs/20261018T234607.509040Z/manifest.json` (pinned train.json, validation.json, config.json, sources/code/runtime).
- Assignment run: `results/under3000_endpoint_assignment_runs/20261018T234628.064395Z/` (protocol.json, summary.json and three assignment_seed folders, each with initial/final checkpoints, predictions.json, summary.json and exposure events).
- Original baseline: `results/under3000_development_runs/20261018T223810.974436Z/`; protocol `results/under3000_development_protocol_runs/20261018T223802.654756Z/manifest.json`.
- New modules: `src/rnastable/recovery_ceiling.py`, `src/rnastable/endpoint_assignment.py`.
- New runners: `scripts/diagnose_under3000_recovery_ceiling.py`, `scripts/study_under3000_endpoint_assignment.py`.
- New tests: `tests/test_recovery_ceiling.py`, `tests/test_endpoint_assignment.py`.

Combined targeted tests: **18 passed in 1.16 s** (new modules, sampled supervision and exact sparse decoder). Oracle full/candidate replay passed, including all 19 full gold oracles, 57 saved-baseline candidate pools/structures and decompositions. Assignment sample/target, initial/checkpoint/exposure, inference and score replay passed for all three fits and 57 predictions. Freeze also verified the original scoped baseline artifacts/scores. These are artifact/inference replays, not deterministic optimizer retraining. Full repository tests and independent biological validation were not run.

Python 3.12.14, PyTorch 2.14.1+cu130; all new work ran on CPU with two Torch threads. Original process peak RSS: oracle 834,344 KiB; assignment 857,312 KiB. Assignment training-only times: seed7 3.7566 s, seed1729 3.5889 s, seed20261015 3.5668 s. Times exclude startup/source checks/validation and are not controlled speed comparisons with old runs. Per-record oracle scoring/decoding observations are saved in rows.json; replay preserves original observations.

## Next work

Audit the flagged short-reference sequence/structure binding and annotation provenance without posthoc relabeling the frozen benchmark. Preserve the present scoring. Then use one matched, frozen follow-up to address the residual pair-selection gap, reporting both cohorts and the short-seed regression. Avoid selecting from a broad sweep and treating reused scores as independent validation. In parallel, define quantitative use-specific acceptance criteria and obtain genuinely independent sequence/family/clan-separated evidence within scope, especially 2,000–2,999 nt (currently only one longer reference). Cell-free expression design stays queued until the Stage 2 gate is reviewed and met.
