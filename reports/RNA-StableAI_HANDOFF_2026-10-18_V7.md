# RNA-StableAI handoff — 2026-10-18 V7

Project: RNA-StableAI
Date: 2026-10-18 (America/Los_Angeles)
Version: V7
Workspace: `/home/zyliu/Documents/rna-stable-ai`
Previous canonical handoff: `reports/RNA-StableAI_HANDOFF_2026-10-18_V6.md`.

## 1. User priorities, scope and current decision

The active instruction is to continue **Stage 2 for RNA smaller than 3,000 nt (1–2,999)**, making it good before advancing to Stage 3. Stage 3's selected expression system is **cell-free expression**. It remains queued. No 3,000+ nt work was added, no sequences were truncated and historical longer work remains intact. The user wants faster progress and detailed self-contained handoffs, not relaxed quality or validation gates.

Scope/gate files remain `configs/project_scope_2026-10-18.json` and `configs/stage2_to_stage3_gate_2026-10-18.json`. No gate, model default, production inference behavior or promoted checkpoint changed. Keep the original uniform 103-record BCE model as the comparison baseline. The new assignment models are a promising but modest development variant, not a demonstrated independent improvement.

Preserve the user-added README image and upstream README changes/assets before future publication. README was untouched this continuation. There was no source download, network request, publication, external message, Git staging/commit/push or workspace cleanup. The large existing staged/unstaged/untracked workspace was preserved. Do not infer this turn's changes from the full dirty Git status.

## 2. Main outcome

Completed the V6-recommended recovery-ceiling diagnostic before any new fitting. It showed substantial candidate and score-selection headroom, with much smaller legal-reference limits on the longer cohort. Then froze and ran one matched endpoint partner/null auxiliary-loss study, all three seeds, ten epochs, fixed final checkpoints.

| Cohort | BCE baseline F1 | Assignment F1 | Difference | LinearFold | ViennaRNA |
| --- | --- | --- | --- | --- | --- |
| Long, 6 references | 0.3173511819 | 0.3261881307 | +0.0088369487 | 0.4381334451 | 0.4214700331 |
| Short, 13 references | 0.1560640870 | 0.1606458705 | +0.0045817835 | 0.3301074317 | 0.3346291106 |

Longer mean F1 improves in all three seeds but stays below native controls. Shorter mean improves slightly, with seed 20261015 regressing. Both cohorts are exposed development sets. No independent evidence, calibrated acceptance thresholds, full-range coverage or expression evidence was added. Stage 2 remains open.

Scientific report: `reports/stage2_recovery_ceiling_and_assignment_review_2026-10-18.md`. Roadmap updated: `reports/PROJECT_ROADMAP_2026-10-18.md`.

## 3. New files and preservation of frozen work

| New file | Purpose | SHA-256 |
| --- | --- | --- |
| src/rnastable/recovery_ceiling.py | Legal/full/retained gold oracles and exact missed-gold partition | 12b4368b0007aaffbf007e63f6c1e306c39b45d006e6dbe98d47e025b2f7966b |
| src/rnastable/endpoint_assignment.py | Sampled endpoint targets and stable partner/null auxiliary loss | 12c977b689a8b7591b5bfc0f9764d484b9bb2359d0202cdea000e3aa674c1b66 |
| scripts/diagnose_under3000_recovery_ceiling.py | Frozen oracle diagnostic and baseline/candidate replay | a638b197dc5bb45a7e78771e627d7b51ab60c1de0affbf306cd2b0b0357adfad |
| scripts/study_under3000_endpoint_assignment.py | Frozen assignment fit and checkpoint/score replay | d39b9bf2f90a4f9a75f55b91093abbf33037e905bba31a3e99770fa49b5f12a7 |
| tests/test_recovery_ceiling.py | 7 oracle tests incl crossing/exhaustive/cache binding | cf096a4e33e7a087275ff84b556127142f2b6fdd5107143a0cba8e1ea1edee40 |
| tests/test_endpoint_assignment.py | 5 assignment tests incl softmax/gradient/unknown/null/extremes | 0a6844876adfabd745fb4df59606b5fcd5313da2e731460ee9f8505eb7642092 |

Only the six listed implementation/test files are new this continuation. Added the scientific review and this handoff; updated the roadmap. Existing old model, supervision, scorer, decoder and previous frozen study sources were not edited. Preserve these new sources too: their manifests pin exact bytes. For future experiments add a new driver/module or version; do not invalidate past replay hashes.

Prior outcomes still matter: endpoint-ranking auxiliary loss left longer F1 flat while improving shorter means; the training-only hard-negative mixture regressed versus its matched random-pool control on both cohorts in every seed. See V5/V6 and their scientific reports. Do not discard negative studies or silently replace the original baseline.

## 4. Exact frozen protocols and run layout

Original scoped BCE baseline:

- Protocol `results/under3000_development_protocol_runs/20261018T223802.654756Z/manifest.json`.
- Run `results/under3000_development_runs/20261018T223810.974436Z/`.
- For seed s, fixed final teacher/baseline `results/under3000_development_runs/20261018T223810.974436Z/extended_103_seed{s}/final_model.pt`.
- New fits begin from the corresponding seed's original `initial_model.pt`, not its final checkpoint. Tensor equality checked before fitting and during replay.

Oracle protocol `results/under3000_recovery_ceiling_protocol_runs/20261018T234336.469918Z/manifest.json`; run `results/under3000_recovery_ceiling_runs/20261018T234344.201186Z/`:

```text
protocol.json
manifest.json
summary.json
full_gold_oracles.json
exposures/<timestamp>.json
seed7/rows.json, 000.npz ... 018.npz
seed1729/rows.json, 000.npz ... 018.npz
seed 20261015/rows.json, 000.npz ... 018.npz
```

There are 19 unique full oracles, 57 candidate archives, and 57 record-seed decompositions. NPZs retain candidate coordinate/score arrays from the baseline, not gold-generated model predictions. Row JSON includes actual structures, label-informed oracles, all counts, candidate counts and observed per-record timings. Root manifest hashes all saved artifacts and the exposure event written before diagnostic access. Oracle outputs carry `uses_reference_labels=True` and `not_a_model_prediction=True` and must never be reported as actual model F1.

Assignment protocol `results/under3000_endpoint_assignment_protocol_runs/20261018T234607.509040Z/manifest.json`; snapshots `train.json`, `validation.json`, `config.json`; run `results/under3000_endpoint_assignment_runs/20261018T234628.064395Z/`:

```text
protocol.json
summary.json
assignment_seed7/
assignment_seed1729/
assignment_seed20261015/
```

Each seed folder contains `initial_model.pt`, `final_model.pt`, `predictions.json` (19 predictions, six long then thirteen short), `summary.json` (ten epoch rows, training seconds, pair/node counts, sample/target digest, cohort score rows, checkpoint/prediction hashes), and two `exposures/*.json` events. Both training and validation exposures are saved before the seed's fit call; validation labels are not used inside the optimizer loop. All 57 predictions have source-bound replay. Protocols pin old/new source code, source artifacts, baseline checkpoints/summaries/predictions, local snapshots and runtime versions. No final model is chosen by validation score.

## 5. Data inventory and exposure/lineage limits

Training: exactly **103** previously used records, lengths **61–2,941 nt**, comprising 88 base records plus 15 longer in-scope additions. Full ordered IDs, sequences and original pairs are in `results/under3000_endpoint_assignment_protocol_runs/20261018T234607.509040Z/train.json`. Historical 3,946/3,995 nt additions stay excluded. Every seed reproduces the original uniform samples: **12,511 legal positives and 50,044 negatives**, four negatives per positive and per-record maximum 8192. The inherited original labeler reports **1,077 unsupported training gold pairs**. These were not converted into legal positives or removed from saved references. BCE behavior remains inherited unchanged.

Exact development inventory:

| Cohort | ID | Family | Length |
| --- | --- | --- | --- |
| long | RF00177:CP000159.1/3330048-3328509 | RF00177 | 1540 |
| long | RF00177:CP001998.1/1562911-1561358 | RF00177 | 1554 |
| long | RF00177:CP002683.1/865959-864386 | RF00177 | 1574 |
| long | RF02541:ADVG01000004.1/1322171-1319199 | RF02541 | 2973 |
| long | RF02542:AF024658.1/1-1399 | RF02542 | 1399 |
| long | RF02542:FJ843105.1/1-1437 | RF02542 | 1437 |
| short | bpRNA_RFAM_5453 | RF00010 | 400 |
| short | bpRNA_RFAM_5479 | RF00010 | 417 |
| short | bpRNA_RFAM_5361 | RF00010 | 520 |
| short | bpRNA_RFAM_53507 | RF01502 | 402 |
| short | bpRNA_RFAM_53569 | RF01502 | 521 |
| short | bpRNA_RFAM_53561 | RF01502 | 533 |
| short | bpRNA_RFAM_45541 | RF01052 | 445 |
| short | bpRNA_RFAM_45543 | RF01052 | 449 |
| short | bpRNA_RFAM_45563 | RF01052 | 493 |
| short | bpRNA_RFAM_49603 | RF01267 | 416 |
| short | bpRNA_RFAM_53067 | RF01469 | 532 |
| short | bpRNA_RFAM_53069 | RF01469 | 533 |
| short | bpRNA_RFAM_53071 | RF01469 | 535 |

Longer coverage: five references in 1,000–1,999 nt, only one in 2,000–2,999 nt. Longer selection is label-informed with training family/clan/segment relationships. Shorter references use computational bpRNA annotations; five families/clans do not make repeated use independent. These reused cohorts do not establish generalization across all 1–2,999 nt RNAs. Do not pool them into one generalization statistic. Seeds are optimizer replication, not biological replication.

Underlying sources pinned by the protocols include:

- `results/bprna_length_pilot_protocol_runs/20261016T174446.305367Z/train.json`.
- `results/bprna_long_training_smoke_runs/20261017T033749.792816Z/selection.json`.
- `results/long_validation_coverage_runs/20261017T033935.363253Z/selection.json`.
- `results/family_pair_set_training_runs/20261016T012741.486402Z/helix_seed1729/summary.json`.
- `results/bprna_five_clan_reference_screen_runs/20261017T191404.643416Z/references.json`.

Complete source/input hashes remain in both protocol manifests; use them rather than selecting similarly named artifacts by timestamp.

## 6. Oracle definition, proof and exact findings

G denotes the count of **all original** reference pairs, L legal pairs with canonical chemistry and index gap>=4, K_full maximum noncrossing legal gold cardinality, K_candidate maximum noncrossing gold cardinality retained by the frozen baseline candidate pool, and TP actual shared pairs. Validate `TP <= K_candidate <= K_full <= L <= G`. All full-reference pairs remain in the denominator. Unsupported and crossing labels are not silently filtered from scoring.

Compute oracles by giving legal gold edges score1 in the unchanged exact sparse noncrossing decoder. The unit-weight optimum maximizes correct cardinality. Any false positive worsens F1, so `2K/(G+K)` is an optimistic F1 bound over feasible predictions in that allowed set. These bounds use labels, not learned performance. A tiny exhaustive crossing example is unit-tested. Cached full oracles are bound to exact sequence and full-pair hashes, preventing reuse across a different same-length record.

Candidate pools are strictly positive baseline logits, top32 per right endpoint, block64. The candidate limit includes both score-threshold exclusion and top-k pruning; this diagnostic does not disentangle them. Actual decoded structures must equal the frozen baseline byte-for-byte before computing gaps.

| Cohort | Actual F1 | Full legal gold oracle F1 | Retained gold oracle F1 | Retained legal-gold recall (micro) | Actual TP / retained-oracle TP (micro) |
| --- | --- | --- | --- | --- | --- |
| long | 0.3173511819 | 0.9606455787 | 0.8256698667 | 0.7617835938 | 0.4595196437 |
| short | 0.1560640870 | 0.9027071479 | 0.7059245554 | 0.6612121212 | 0.3668666359 |

| Seed | Long retained-oracle F1 | Short retained-oracle F1 |
| --- | --- | --- |
| 7 | 0.8381697979 | 0.7281908412 |
| 1729 | 0.8174066174 | 0.6934806566 |
| 20261015 | 0.8214331848 | 0.6961021684 |

Missing-gold partition:

`(G-L) + (L-K_full) + (K_full-K_candidate) + (K_candidate-TP) = G-TP`.

| Missing-gold component | Long count (18 record-seed rows) | Long fraction | Short count (39 rows) | Short fraction |
| --- | --- | --- | --- | --- |
| unsupported_gold | 639 | 10.6447% | 564 | 18.3773% |
| legal_noncrossing_limit | 0 | 0.0000% | 51 | 1.6618% |
| retained_candidate_limit | 1966 | 32.7503% | 1082 | 35.2558% |
| score_selection_gap | 3398 | 56.6050% | 1372 | 44.7051% |

Long missing total 6,003, actual FP 6,374; short missing total 3,069, actual FP 4,753. Counts aggregate 18/39 record-seed rows. Fractions above partition **missed gold counts**, not F1 percentages or causal contributions. The candidate and score-selection components depend on the chosen nested diagnostic order. The latter is a scoring/objective gap, not proof of a decoder bug. Across unique records, long G=2,964/L=2,751/K_full=2,751; short G=1,288/L=1,100/K_full=1,083.

Full unique-reference oracle audit:

| Cohort | ID | Full gold G | Legal gold L | Oracle TP K_full | Full gold oracle F1 | Unsupported reasons |
| --- | --- | --- | --- | --- | --- | --- |
| long | RF00177:CP000159.1/3330048-3328509 | 462 | 433 | 433 | 0.9675977654 | {"noncanonical_only": 29, "short_and_noncanonical": 0, "short_only": 0} |
| long | RF00177:CP001998.1/1562911-1561358 | 462 | 432 | 432 | 0.9664429530 | {"noncanonical_only": 29, "short_and_noncanonical": 0, "short_only": 1} |
| long | RF00177:CP002683.1/865959-864386 | 462 | 438 | 438 | 0.9733333333 | {"noncanonical_only": 24, "short_and_noncanonical": 0, "short_only": 0} |
| long | RF02541:ADVG01000004.1/1322171-1319199 | 846 | 793 | 793 | 0.9676632093 | {"noncanonical_only": 51, "short_and_noncanonical": 0, "short_only": 2} |
| long | RF02542:AF024658.1/1-1399 | 366 | 333 | 333 | 0.9527896996 | {"noncanonical_only": 33, "short_and_noncanonical": 0, "short_only": 0} |
| long | RF02542:FJ843105.1/1-1437 | 366 | 322 | 322 | 0.9360465116 | {"noncanonical_only": 44, "short_and_noncanonical": 0, "short_only": 0} |
| short | bpRNA_RFAM_5453 | 108 | 96 | 89 | 0.9035532995 | {"noncanonical_only": 12, "short_and_noncanonical": 0, "short_only": 0} |
| short | bpRNA_RFAM_5479 | 108 | 33 | 30 | 0.4347826087 | {"noncanonical_only": 75, "short_and_noncanonical": 0, "short_only": 0} |
| short | bpRNA_RFAM_5361 | 109 | 97 | 90 | 0.9045226131 | {"noncanonical_only": 10, "short_and_noncanonical": 0, "short_only": 2} |
| short | bpRNA_RFAM_53507 | 91 | 61 | 61 | 0.8026315789 | {"noncanonical_only": 29, "short_and_noncanonical": 0, "short_only": 1} |
| short | bpRNA_RFAM_53569 | 104 | 85 | 85 | 0.8994708995 | {"noncanonical_only": 18, "short_and_noncanonical": 0, "short_only": 1} |
| short | bpRNA_RFAM_53561 | 99 | 72 | 72 | 0.8421052632 | {"noncanonical_only": 27, "short_and_noncanonical": 0, "short_only": 0} |
| short | bpRNA_RFAM_45541 | 38 | 38 | 38 | 1.0000000000 | {"noncanonical_only": 0, "short_and_noncanonical": 0, "short_only": 0} |
| short | bpRNA_RFAM_45543 | 38 | 38 | 38 | 1.0000000000 | {"noncanonical_only": 0, "short_and_noncanonical": 0, "short_only": 0} |
| short | bpRNA_RFAM_45563 | 38 | 38 | 38 | 1.0000000000 | {"noncanonical_only": 0, "short_and_noncanonical": 0, "short_only": 0} |
| short | bpRNA_RFAM_49603 | 126 | 116 | 116 | 0.9586776860 | {"noncanonical_only": 10, "short_and_noncanonical": 0, "short_only": 0} |
| short | bpRNA_RFAM_53067 | 143 | 142 | 142 | 0.9964912281 | {"noncanonical_only": 1, "short_and_noncanonical": 0, "short_only": 0} |
| short | bpRNA_RFAM_53069 | 143 | 143 | 143 | 1.0000000000 | {"noncanonical_only": 0, "short_and_noncanonical": 0, "short_only": 0} |
| short | bpRNA_RFAM_53071 | 143 | 141 | 141 | 0.9929577465 | {"noncanonical_only": 2, "short_and_noncanonical": 0, "short_only": 0} |

`bpRNA_RFAM_5479` is a notable chemistry/annotation outlier:417 nt,108 reference pairs,75 noncanonical and full oracle F1 .4347826087. The existing source loader in `scripts/prepare_bprna_training_subset.py` was inspected read-only; it binds DBN name/sequence/length and retains full pairs while counting legal support. That does not settle source annotation correctness. Do not infer mismatch, correct labels, exclude the record or claim a cleaner benchmark on this basis. Audit original sequence/DBN/provenance as a separate documented task while keeping current frozen scoring intact.

## 7. Matched assignment objective and training settings

For each known endpoint i, classify among its incident **sampled** edges and a null class with fixed logit0. If its full-reference partner is legal, target that sampled edge (must exist); if truly unpaired, target null. Endpoints of unsupported full-reference pairs are masked unknown. Both endpoints of each legal pair are supervised. Stable scatter-reduce maximum/scatter-add logsumexp uses O(n+m) auxiliary storage and differentiates through logits. The loss is a local sampled categorical objective; it is not a normalized noncrossing structure likelihood.

Loss: weighted BCE (`pos_weight=4.0`) **+0.25×assignment loss**, averaged over known endpoints within record, then one update per record. All 103 records per epoch sum to 53,020 known nodes: 25,022 paired and 27,998 null; 2,154 unknown nodes correspond to twice 1,077 unsupported pairs. Unknown auxiliary targets do not alter inherited BCE handling.

- Seeds 7, 1729, 20261015; ten epochs; Adam lr0.001, unchanged seeded record shuffle and baseline initial tensors.
- Model embedding16/channels32/pairdim16/dilations[1,2,4,8], pair_features local_helix_context_v1.
- Original uniform samples regenerated deterministically with seed+record-index; no teacher hard-negative pool or endpoint-ranking term.
- CPU, 2 threads, fixed final checkpoint; no validation-based early stopping or epoch choice.
- Unchanged inference exact sparse top32/block64; no weight sweep, threshold/offset tuning or candidate-budget sweep this turn.
- Sampling/optimizer step count is matched, but the new objective adds computation. No total-runtime parity or speedup claim.

Final epoch training observations (retained, not recomputed by replay):

| Seed | Total loss | BCE | Assignment |
| --- | --- | --- | --- |
| 7 | 0.4870976325 | 0.4042774535 | 0.3312807084 |
| 1729 | 0.5045461744 | 0.4172659917 | 0.3491207309 |
| 20261015 | 0.5119943567 | 0.4234330411 | 0.3542452637 |

## 8. Per-seed and descriptive results

| Seed | Long baseline | Long assignment | Long difference | Short baseline | Short assignment | Short difference |
| --- | --- | --- | --- | --- | --- | --- |
| 7 | 0.2994837245 | 0.3144590134 | 0.0149752890 | 0.1552876958 | 0.1795793890 | 0.0242916932 |
| 1729 | 0.3149238665 | 0.3206222634 | 0.0056983969 | 0.1479018661 | 0.1553106038 | 0.0074087377 |
| 20261015 | 0.3376459548 | 0.3434831152 | 0.0058371604 | 0.1650026990 | 0.1470476186 | -0.0179550804 |

| Arm | Cohort | Rows | Mean precision | Mean recall | Mean predicted pairs |
| --- | --- | --- | --- | --- | --- |
| baseline | long | 18 | 0.3107277878 | 0.3248961817 | 514.6111111111 |
| baseline | short | 39 | 0.1379064654 | 0.1932544216 | 142.2564102564 |
| assignment | long | 18 | 0.3220692468 | 0.3313669272 | 508.5555555556 |
| assignment | short | 39 | 0.1409991377 | 0.2030950659 | 139.8717948718 |

Precision/recall/count means were read and averaged from saved baseline `validation_scores` rows (first 6 long, next 13 short) and assignment `cohorts[cohort].rows`, not a new predictive run. Slight mean precision/recall improvements do not eliminate the short seed regression or native-control gap. No significance test/confidence interval was performed. Do not claim a statistically established or independently validated improvement.

## 9. Runtime and verification actually completed

Python 3.12.14, PyTorch 2.14.1+cu130, NumPy 2.5.3; CPU with two Torch threads. No GPU execution or new native folds. Original process peak RSS: oracle 834,344 KiB (~814.79 MiB), assignment 857,312 KiB (~837.22 MiB). RSS is Linux process ru_maxrss, not GPU/whole-machine use. Training-only seconds are in the checkpoint table below; exclude startup/source audits/validation. Historical timing differences are not controlled performance comparisons. Oracle per-record model-scoring, actual-decode and candidate-oracle seconds are retained in rows.json; full-oracle timing is not a separately reported resource measurement.

Commands/checks actually run:

1. Oracle targeted tests after cache binding:12 passed in 0.17 s (oracle, exact decoder, scope aggregation).
2. Final combined `.venv/bin/python -m pytest -q tests/test_endpoint_assignment.py tests/test_recovery_ceiling.py tests/test_sampled_pair_supervision.py tests/test_long_exact_sparse_pairs.py` → **18 passed in 1.16 s**. Coverage: softmax value/gradients, unsupported unknown targets, explicit null, extreme finite logits, empty/unknown cases, missing gold/scope errors; exhaustive tiny oracle bound, crossing/unsupported denominators, partition+FP, invalid candidates/cache binding; original sampled/exact decoder checks.
3. Oracle freeze verified the original scoped baseline artifacts/scores before writing the new protocol. Oracle run completed all 57 rows. `--verify-run` → **Full/candidate oracle, baseline inference, candidate-score and decomposition replay passed (no training)**. Recomputed 19 full oracles, all 57 model candidate arrays/actual decodes/candidate oracles and nested count/score checks, checked saved source/artifact/exposure hashes. Candidate arrays reproduced exactly. Original timing/RSS observations preserved rather than remeasured.
4. Assignment freeze completed and three ten-epoch fits finished. `--verify-run` → **Endpoint assignment checkpoint inference and score replay passed (no retraining)**. Regenerated all 309 training samples/targets and their digests, checked saved initial/final bytes, matched initial tensors against original baseline, checked exposure identities, reproduced 57 predictions and full cohort/aggregate scores.
5. Read-only descriptive aggregation recomputed precision/recall/predicted-pair means. Its first attempt assumed the baseline had cohort row arrays, raised KeyError('rows'), then was corrected to the baseline's `validation_scores` layout. No artifact or frozen code was changed by that inspection error.

No optimizer retraining replay, full repository suite, independent reference validation, biological assay, native-control rerun or external source acquisition was performed. Saved epoch losses and observed resource values remain observations. All actual runs and verifiers finished successfully; no mining/training/replay sessions remain active from this continuation. Documentation checks are recorded after creation below.

## 10. Hash anchors and checkpoint paths

| Artifact | SHA-256 |
| --- | --- |
| results/under3000_recovery_ceiling_protocol_runs/20261018T234336.469918Z/manifest.json | ba4d88370d6ff2671100dfd0e25f298e2ca058f63da20fb1e490e2e679d9c271 |
| results/under3000_recovery_ceiling_runs/20261018T234344.201186Z/protocol.json | ba4d88370d6ff2671100dfd0e25f298e2ca058f63da20fb1e490e2e679d9c271 |
| results/under3000_recovery_ceiling_runs/20261018T234344.201186Z/summary.json | 5844c2010de771da24b973218c6dd2871840c06c0c09692f9f94f4930bb3c6b1 |
| results/under3000_recovery_ceiling_runs/20261018T234344.201186Z/manifest.json | 242c219971001d861db99bb998678ea3a57723d05b81b8925a04283124efbfb7 |
| results/under3000_recovery_ceiling_runs/20261018T234344.201186Z/full_gold_oracles.json | b67c4ba5edbe67a68ebe9910a342d9cef194b7153faa0858691031b0bfe45173 |
| results/under3000_endpoint_assignment_protocol_runs/20261018T234607.509040Z/manifest.json | 524118977515c6d3e8e0f67ebb78e6cdd04b12aea6082aeee8ac17f8f33cb26b |
| results/under3000_endpoint_assignment_runs/20261018T234628.064395Z/protocol.json | 524118977515c6d3e8e0f67ebb78e6cdd04b12aea6082aeee8ac17f8f33cb26b |
| results/under3000_endpoint_assignment_runs/20261018T234628.064395Z/summary.json | d7ddf63c2adf0bfd02943c1f433868a104d97b6a3a21c00fbf9c65ce73a01609 |
| results/under3000_endpoint_assignment_protocol_runs/20261018T234607.509040Z/train.json | be9101b2d2dd86c0fed2aa4b3dcc32a10d71e5a958c7939e0d389347f6c57cba |
| results/under3000_endpoint_assignment_protocol_runs/20261018T234607.509040Z/validation.json | 6da80cbe45051a24f6d779345daaacb8c287f325f2331ed6134152d865754dee |
| results/under3000_endpoint_assignment_protocol_runs/20261018T234607.509040Z/config.json | 7405ade9b38eb64b642961ccf67d9a5d7031d82db76e150cbb814d584f46c3e3 |

Assignment final checkpoint for seed s: `results/under3000_endpoint_assignment_runs/20261018T234628.064395Z/assignment_seed{s}/final_model.pt`.

| Seed | Final checkpoint SHA-256 | Sample and assignment-target SHA-256 | Training-only seconds |
| --- | --- | --- | --- |
| 7 | 298c25df47e0889c31e1b2b8d6cba561078ac65c90e7bbac1c448a89a443d8ef | 776b3e34dcf10e59390884c571b4ddda2d33435eefa6173120cb19621a309aba | 3.7565966990 |
| 1729 | dfe41a30a498a0225bfd7af0666f7dee34c3a18753bd7cd3b805289739180c1c | 3966ab493c2d7fcde689cbde99146aa42e53f196f88ddf7cf3d98c64a3063dce | 3.5889065280 |
| 20261015 | 8e27a0730a687abfbc2dfe5d65417343ec67dcefd2bf68e1efa93f988b53b05a | d0fda434c9acb8e961e0ee6f825bbad5056302e509cff4d08e995038107e2730 | 3.5668140680 |

Initial checkpoint/prediction/exposure hashes are retained in each seed summary. Full candidate-archive hashes and oracle row hashes are retained in `results/under3000_recovery_ceiling_runs/20261018T234344.201186Z/manifest.json`. Full imported code hashes are in the protocol manifests. These are the reproducibility anchors; this handoff does not replace them.

## 11. Pending work and prioritized continuation

1. Audit `bpRNA_RFAM_5479` and the broader unsupported-label pattern using the original acquisition inventory/DBN bytes and exact sequence binding, without changing the frozen benchmark or silently relabeling any pair. Distinguish annotation chemistry from genuine provenance mismatches. A corrected dataset, if justified, needs a new version/protocol with original comparisons preserved.
2. Use this diagnostic to choose one fixed matched follow-up addressing score/partner selection or structure-aware supervision. Preserve the same samples/initial states or add a matched control if training duration, budget or architecture changes. Report all seeds, both cohorts and per-length/family behavior; preserve regressions. Do not keep widening sweeps to choose an exposed-cohort winner.
3. If desired, diagnose the assignment model's candidate ceiling in a **new** protocol; present diagnostic above is specifically the original BCE model. Do not attribute its oracle ceilings to the new assignment checkpoints without measurement.
4. Define quantitative application-specific accuracy acceptance criteria before independent testing. Assemble genuinely independent sequence/family/clan-separated evidence under 3,000 nt, particularly 2,000–2,999 nt. This evidence is still sparse and the gate is not closed.
5. Continue to compare native controls on the identical full-reference denominators. Unsupported-label ceilings do not excuse remaining learned-model gaps.
6. Keep Stage 3 cell-free design/assays queued behind Stage 2. When ready, define platform/CDS/UTRs/genetic code/protected features/synonymous edits/assay conditions, measuring protein and time-matched RNA separately. No expression benefit follows from structure F1 alone. Keep 3,000+ nt Qβ/AP205 work deferred.

No routine continuation approval is needed. Before publishing, inspect latest live GitHub README, merge upstream changes and preserve the user's image markup and image assets. No publication snapshot was prepared this turn.

## 12. Exact safe continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-18_V7.md
cat reports/stage2_recovery_ceiling_and_assignment_review_2026-10-18.md
cat configs/stage2_to_stage3_gate_2026-10-18.json

# Targeted unit and decoder checks; no fitting:
.venv/bin/python -m pytest -q tests/test_endpoint_assignment.py tests/test_recovery_ceiling.py tests/test_sampled_pair_supervision.py tests/test_long_exact_sparse_pairs.py

# Recompute baseline candidate pools, all gold oracles and diagnostic decompositions:
.venv/bin/python scripts/diagnose_under3000_recovery_ceiling.py --verify-run results/under3000_recovery_ceiling_runs/20261018T234344.201186Z/summary.json

# Recompute samples/targets and saved assignment checkpoint inference/scores:
.venv/bin/python scripts/study_under3000_endpoint_assignment.py --verify-run results/under3000_endpoint_assignment_runs/20261018T234628.064395Z/summary.json

# Inspect frozen policies, scores, original labels and outlier (no data mutation):
.venv/bin/python -m json.tool results/under3000_recovery_ceiling_protocol_runs/20261018T234336.469918Z/manifest.json
.venv/bin/python -m json.tool results/under3000_recovery_ceiling_runs/20261018T234344.201186Z/summary.json
.venv/bin/python -m json.tool results/under3000_recovery_ceiling_runs/20261018T234344.201186Z/full_gold_oracles.json
.venv/bin/python -m json.tool results/under3000_endpoint_assignment_protocol_runs/20261018T234607.509040Z/manifest.json
.venv/bin/python -m json.tool results/under3000_endpoint_assignment_runs/20261018T234628.064395Z/summary.json
.venv/bin/python -m json.tool results/under3000_endpoint_assignment_runs/20261018T234628.064395Z/assignment_seed20261015/summary.json
rg -n 'bpRNA_RFAM_5479' results/under3000_endpoint_assignment_protocol_runs/20261018T234607.509040Z/validation.json
sed -n '100,180p' scripts/prepare_bprna_training_subset.py
cat src/rnastable/endpoint_assignment.py
cat src/rnastable/recovery_ceiling.py
```

`--verify-run` performs source/artifact/inference checks without optimizer training or native requests. Do not run `--run` to inspect existing artifacts: it creates a new timestamped study. Do not overwrite frozen artifacts, prior handoffs or manifest-pinned sources. This versioned file is the canonical local resume note.

## 13. Final documentation checks

Whitespace/final-newline checks passed for all nine new or updated code/test/documentation files. Relative Markdown report links resolve. Both frozen protocol code-manifest inventories still match the source bytes after documentation work. The oracle and assignment verifier sessions exited successfully; no study subprocess remains active. Earlier handoffs V1–V6 were preserved; V7 was created with exclusive creation.
