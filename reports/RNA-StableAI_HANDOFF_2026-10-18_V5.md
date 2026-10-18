# RNA-StableAI handoff — 2026-10-18 V5

Project: RNA-StableAI
Date: 2026-10-18 (America/Los_Angeles)
Version: V5
Workspace: `/home/zyliu/Documents/rna-stable-ai`
Canonical predecessor: `reports/RNA-StableAI_HANDOFF_2026-10-18_V4.md`.

## 1. Current user direction and persistent preferences

- Continue **Stage 2**. The user requires credible structure-model performance for lengths **smaller than 3,000 nt before Stage 3**. The current policy is exclusive: active 1–2,999 nt; 3,000 nt and longer preserved/deferred. Do not truncate sequences to enter scope.
- Stage 3's eventual target is **cell-free expression**. Do not start expression candidate design or claim the transition gate has passed.
- Prioritize focused model development rather than more above-cap source inventory. Qβ/AP205 source leads are above the active cap and remain deferred.
- New user preference this turn: save as much useful detail/information as possible in future handoffs. Added a detailed-handoff section to root `AGENTS.md`, covering priorities, exact artifacts/settings/hashes, per-seed results/regressions, verification limits, failed attempts and safe continuation commands. Keep chat answers concise while the canonical file is comprehensive.
- Preserve the user-added README picture and upstream README edits before any publication. This turn did not edit README or publish.

## 2. Outcome of this continuation

Completed one frozen three-seed experiment adding a sampled endpoint-ranking term to the in-scope 103-record BCE baseline. Result is **mixed, not a replacement baseline**:

| Development cohort | Previous 103-record BCE | BCE + endpoint ranking | Mean paired difference |
| --- | ---: | ---: | ---: |
| Six longer references, 1,399–2,973 nt | 0.3173511819 | 0.3167803094 | −0.0005708725 |
| Thirteen shorter references, 400–535 nt | 0.1560640870 | 0.1696098167 | +0.0135457297 |

The final seed regresses on both cohorts. Do not promote the new loss/checkpoint. Stage 2 remains below both native baselines and lacks independent validation across the active range. Stage 3 stays queued. All old baselines, protocols, data and checkpoints remain intact.

Detailed study review: `reports/stage2_endpoint_ranking_review_2026-10-18.md`.

## 3. Files changed or added this turn

| Path | Purpose |
| --- | --- |
| `AGENTS.md` | Persist the user's request for detailed, self-contained future handoffs. |
| `src/rnastable/endpoint_ranking.py` | New differentiable auxiliary loss for sampled false pairs competing at gold endpoints; validates scope and tensor inputs. No old model/labeler/decoder was edited. |
| `tests/test_endpoint_ranking.py` | Six loss cases, including gradients, endpoint orientation, missing comparisons/classes and invalid inputs. |
| `scripts/study_under3000_endpoint_ranking.py` | Freeze/run/verify the fixed three-seed comparison, including data/code/checkpoint hashes, exposure events, and inference replay. |
| `scripts/summarize_under3000_ranking.py` | Independently recompute saved precision/recall/predicted-pair descriptive diagnostics from saved predictions. |
| `reports/stage2_endpoint_ranking_review_2026-10-18.md` | Scientific result, configuration, diagnosis, verification limits and next direction. |
| This versioned handoff | Canonical resume record; V1–V4 remain preserved. |

New run artifacts are retained under ignored `results/`. No Git staging, commit, push, PR, publication, native-tool download or network acquisition occurred. The workspace already had extensive staged/unstaged/untracked work; it was preserved. `AGENTS.md` showed `AM`, and the four new implementation/test scripts/modules showed `??` when inspected.

## 4. Frozen study and exact inputs

New protocol:

`results/under3000_endpoint_ranking_protocol_runs/20261018T230319.775906Z/manifest.json`

New run:

`results/under3000_endpoint_ranking_runs/20261018T230346.828091Z/`

The protocol folder contains `train.json`, `validation.json`, `config.json`, and `manifest.json`. The manifest pins source files, old baseline checkpoints/predictions/summaries, code dependencies, local snapshots and the PyTorch version. The run keeps an exact `protocol.json` copy.

Previous matched scoped baseline:

- Protocol: `results/under3000_development_protocol_runs/20261018T223802.654756Z/manifest.json`.
- Run: `results/under3000_development_runs/20261018T223810.974436Z/summary.json`.
- Comparison uses only its `extended_103_seed7`, `extended_103_seed1729` and `extended_103_seed20261015` components. The earlier 88-record control remains retained but was not retrained this turn.
- The prior baseline artifact/score verifier passed before the new protocol was frozen.

Training: exactly 103 existing records, length 61–2,941 nt. This is the prior 88-record base plus the 15 in-scope additions. The two deferred historical training additions (`bpRNA_CRW_55396`, 3,946 nt; `bpRNA_RFAM_43122`, 3,995 nt) were not used. Full record IDs, sequences and pair labels are in the pinned `train.json`; do not reconstruct them through numeric-ID metadata joins.

Validation: the same two exposed development cohorts as V4, kept separate in all reporting. No newly acquired references and no independent test were introduced.

Longer cohort, exact reference IDs and lengths:

| ID | Length |
| --- | ---: |
| RF00177:CP000159.1/3330048-3328509 | 1,540 |
| RF00177:CP001998.1/1562911-1561358 | 1,554 |
| RF00177:CP002683.1/865959-864386 | 1,574 |
| RF02541:ADVG01000004.1/1322171-1319199 | 2,973 |
| RF02542:AF024658.1/1-1399 | 1,399 |
| RF02542:FJ843105.1/1-1437 | 1,437 |

Thus five references are 1,000–1,999 nt and only one is 2,000–2,999 nt. They represent three family labels within the exposed SSU/LSU groups and have known development-selection/lineage/segment limitations. They are not independent family-separated validation.

Shorter cohort:

- RF00010: `bpRNA_RFAM_5453` (400), `bpRNA_RFAM_5479` (417), `bpRNA_RFAM_5361` (520).
- RF01502: `bpRNA_RFAM_53507` (402), `bpRNA_RFAM_53569` (521), `bpRNA_RFAM_53561` (533).
- RF01052: `bpRNA_RFAM_45541` (445), `bpRNA_RFAM_45543` (449), `bpRNA_RFAM_45563` (493).
- RF01267: `bpRNA_RFAM_49603` (416).
- RF01469: `bpRNA_RFAM_53067` (532), `bpRNA_RFAM_53069` (533), `bpRNA_RFAM_53071` (535).

These thirteen references come from the earlier five-clan bpRNA feasibility panel, with computational labels and prior exposure. They cannot be relabeled as independent tests now.

## 5. Model, loss and controlled comparison

Unchanged model/configuration:

```json
{
  "embedding_dim": 16,
  "channels": 32,
  "pair_dim": 16,
  "dilations": [1, 2, 4, 8],
  "pair_features": "local_helix_context_v1",
  "training_max_length": 2999,
  "epochs": 10,
  "learning_rate": 0.001,
  "cpu_threads": 2,
  "top_k": 32,
  "block_size": 64,
  "inference_decoder": "exact_sparse"
}
```

- Seeds: `7`, `1729`, `20261015`.
- Adam optimizer; fixed final epoch, no validation-based checkpoint selection or early stopping.
- Uniform sampled supervision is the unchanged `sampled_pair_supervision`: sampling seed `fit_seed + training_record_index`, maximum 8,192 negatives per record, four negatives per retained legal gold pair. All legal gold labels are retained; unsupported gold handling is inherited unchanged.
- Every seed has 12,511 retained legal positive pairs and 50,044 sampled negatives. Counts were explicitly checked against the matching old BCE baseline. BCE `pos_weight = negatives / positives = 4.0`.
- Same training data/order, random record-shuffle policy, initialization, architecture, sample generator and decoder as the previous 103-record BCE run. Each new initial state was compared tensor-by-tensor against its old baseline initial state before training and again during replay.
- New term: for a gold pair `(i,j)`, find the highest-logit sampled negative containing `i` or `j`, regardless of whether that endpoint is the negative pair's left or right coordinate. The per-pair term is `softplus(1.0 + false_logit - gold_logit)`; average only over gold pairs with an available sampled competitor.
- Total loss is **weighted BCE + 0.25 × endpoint-ranking loss**. Weight and margin were frozen before running all three seeds; no sweep or post-hoc selection occurred.
- Negatives are from the old sampled pool. This is **not global hard-negative mining**, not all-pairs BCE and not a structured decoder objective.
- Worst-negative storage is length-sized, plus sampled pair vectors; no dense all-pairs label tensor is introduced.
- Validation inputs/labels never enter the training loss. They are used only after the fixed final checkpoint is saved.

## 6. Full per-seed results

| Seed | Longer BCE | Longer ranking | Paired difference | Shorter BCE | Shorter ranking | Paired difference |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 7 | 0.2994837245 | 0.3120966271 | +0.0126129026 | 0.1552876958 | 0.1773716678 | +0.0220839720 |
| 1729 | 0.3149238665 | 0.3247550801 | +0.0098312135 | 0.1479018661 | 0.1725994227 | +0.0246975566 |
| 20261015 | 0.3376459548 | 0.3134892211 | −0.0241567337 | 0.1650026990 | 0.1588583595 | −0.0061443395 |

Native controls retained from earlier runs, same cohort IDs:

| Cohort | LinearFold F1 | ViennaRNA F1 |
| --- | ---: | ---: |
| Longer | 0.4381334451 | 0.4214700331 |
| Shorter | 0.3301074317 | 0.3346291106 |

Do not combine these two differently sourced cohorts into one generalization score or treat three seeds as independent biological replicates. No p-values or confidence intervals were computed.

Descriptive precision/recall diagnosis, averaged over record/seed rows:

| Cohort / arm | Rows | Precision | Recall | Mean predicted-pair count |
| --- | ---: | ---: | ---: | ---: |
| Longer BCE | 18 | 0.3107277878 | 0.3248961817 | 514.6111 |
| Longer ranking | 18 | 0.3057012291 | 0.3292544481 | 532.4444 |
| Shorter BCE | 39 | 0.1379064654 | 0.1932544216 | 142.2564 |
| Shorter ranking | 39 | 0.1481197077 | 0.2187009727 | 142.8205 |

Interpretation: longer recall rises slightly while precision falls, with more decoded pairs and flat F1. Shorter precision and recall both rise. This diagnosis is descriptive and does not establish a general mechanism or a deployable calibration.

Final epoch ranking coverage and losses:

| Seed | Gold pairs with competitor / total | Total loss | BCE loss | Ranking loss |
| --- | ---: | ---: | ---: | ---: |
| 7 | 12,118 / 12,511 | 0.5216563192 | 0.4104151934 | 0.4449645100 |
| 1729 | 12,153 / 12,511 | 0.5343965945 | 0.4193020518 | 0.4603781661 |
| 20261015 | 12,133 / 12,511 | 0.5513402166 | 0.4302026600 | 0.4845502246 |

Coverage is roughly 96.86–97.14%, so the ranking term was exercised on most sampled gold pairs. Do not infer that these are the model's globally hardest competitors: the pool is still uniform sampled negatives.

## 7. Checkpoints, hashes and resource observations

All component paths are under:

`/home/zyliu/Documents/rna-stable-ai/results/under3000_endpoint_ranking_runs/20261018T230346.828091Z/`

Each `ranking_seed7/`, `ranking_seed1729/`, `ranking_seed20261015/` contains:

- `initial_model.pt`, `final_model.pt`.
- `predictions.json` (19 records, longer cohort first, shorter cohort second).
- `summary.json` (epoch history, sample counts, training seconds, full per-record cohort scores, checkpoint/prediction hashes, exposure-event records).
- `exposures/*.json` created before training/validation requests.

| Seed | Final checkpoint SHA-256 |
| --- | --- |
| 7 | `76e599e5c86a66417f4c266a565f747407fb6a83b0bc75ba737f8f533c0151dc` |
| 1729 | `355845ed0e643961fc0cafe2fa64b97a43bbaacfbf52539ff9953166bbf8f2fe` |
| 20261015 | `7115bd3d8be5243d05b98670c271f566249b0a0749cc269940295676ed03e69c` |

Other useful SHA-256 values:

- Run `protocol.json`: `d0be9ba8c0aa0da1a44440d60aa722021d9c68f844b21a60df4515b3c59cd8b0`.
- Run `summary.json`: `7a85fee54a158ae456e2b64d159d3a4ad22e5e1be31e460bb9f06781a1f550ac`.
- Run `descriptive_diagnostics.json`: `824a969281fe35fa726f0ea07d96c8809824cb29c4c8a93231c7db36ee5b508a`.
- `scripts/summarize_under3000_ranking.py`: `80e7b3a0fa7cff9f293292b725e0055b818742b4d6f4b06bea389454719d4a86`.
- Individual initial-state and prediction hashes are retained in each component summary and verified by the study replay; source/code hashes are in the frozen manifest.

Runtime: Python **3.12.14**, PyTorch **2.14.1+cu130**. Computation was CPU, two Torch threads. The CUDA wheel suffix does not indicate GPU execution here.

Training-only times: seed 7 **7.9605 s**; seed 1729 **7.8386 s**; seed 20261015 **7.8057 s**. These exclude source audit, startup and final inference. Original study process peak RSS: **857,552 KiB**, approximately **837.45 MiB**, from Linux `resource.getrusage(...).ru_maxrss`. This is not full-machine memory or GPU memory; the replay retains the original observation instead of pretending to reproduce a timing/RSS measurement.

## 8. Verification actually performed

1. `.venv/bin/python -m pytest -q tests/test_endpoint_ranking.py tests/test_sampled_pair_supervision.py tests/test_long_exact_sparse_pairs.py` → **12 passed in 1.84 s**.
2. New study `--freeze` first invoked the previous scoped baseline's artifact/score verifier → passed, no retraining.
3. New study `--run <manifest>` → all three ten-epoch fits completed and saved all 57 predictions. No interrupted/failed fits remain.
4. New study `--verify-run <summary>` → **checkpoint inference and score replay passed**. Reconstructed each final model from its saved checkpoint and reproduced all predictions, compared initial states with the old baseline, verified pinned input/code/snapshot/checkpoint/prediction bytes, checked exposure events and their identities, and recomputed cohort scores/paired differences.
5. `summarize_under3000_ranking.py --verify-run <run-directory>` → descriptive precision/recall replay passed from saved predictions.
6. Explicit check confirmed positive/negative sample counts match each old BCE baseline seed.
7. New implementation/test file whitespace checks passed. Final documentation checks should be reported only if run after writing this file.

Limits: no deterministic **retraining** replay was run for the new objective; inference replay verifies saved checkpoints/predictions, not every optimizer update or epoch-loss value. No full repository suite, new native folds, new independent references or biological expression assays were run. Tests were not rerun solely for documentation changes.

## 9. Interpretation, decisions and unresolved gates

- The new term provides a short-cohort development improvement but no mean longer-cohort improvement. The negative seed must remain visible. No loss/default/checkpoint promotion.
- Keep the V4 103-record BCE checkpoints as the comparison baseline. The ranking checkpoints are retained experiments, not replacements.
- Both cohorts were already exposed; the longer cohort is label-informed and has training-family/clan/shared-segment relationships. The shorter cohort uses computational bpRNA labels. This is not independent evidence that Stage 2 is good across 1–2,999 nt.
- Only one longer reference is in 2,000–2,999 nt. No study here closes that coverage gap.
- Native controls remain substantially better on both cohorts. Passing software checks does not satisfy structure-accuracy readiness.
- `configs/stage2_to_stage3_gate_2026-10-18.json` and the cell-free Stage 3 target remain unchanged. Quantitative acceptance criteria and independent validation must precede any transition claim.
- No active training/replay processes remain from this continuation. The three-fit run and its replay completed successfully.

## 10. Prioritized next work

1. Investigate the **training negative pool**, rather than sweeping ranking coefficients on these same cohorts. The current comparison ranks against the hardest negative only within a uniform sample; it may miss the false pairs dominating actual top-32 inference.
2. A concrete next experiment is bounded **training-only hard-negative mining** with a separately frozen driver/protocol. Keep the existing 103-record BCE baseline, three seeds, fixed-final epochs and top-32 decoder. Preserve all legal positives and cap negative storage; do not let validation labels or predictions choose training negatives, epochs or hyperparameters.
3. Before fitting, specify mining schedule, tie breaking, random/hard-negative mixture, sample/compute budget and comparator. Keep a matched control if those budgets or sample counts change; do not attribute a compound change solely to hard negatives.
4. Diagnose candidate recall versus decoded recovery on exposed development data when needed, retaining precision/recall and failure denominators. Such diagnostics do not create an independent test.
5. In parallel as a project requirement, obtain independent sequence/family/clan-separated references within scope, especially 2,000–2,999 nt, and preregister application-specific accuracy acceptance criteria. Keep above-cap phage acquisition deferred.
6. Continue Stage 2 until credible quality evidence supports review. Cell-free Stage 3 design and measured protein/RNA assays remain later work.

## 11. Exact safe continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-18_V5.md
cat reports/stage2_endpoint_ranking_review_2026-10-18.md

# Focused correctness checks; no model fitting:
.venv/bin/python -m pytest -q tests/test_endpoint_ranking.py tests/test_sampled_pair_supervision.py tests/test_long_exact_sparse_pairs.py

# Reconstruct saved ranking models and reproduce all prediction/score outputs;
# no optimizer steps, no native-tool requests, no new source acquisition:
.venv/bin/python scripts/study_under3000_endpoint_ranking.py --verify-run results/under3000_endpoint_ranking_runs/20261018T230346.828091Z/summary.json

# Recompute descriptive precision/recall from existing predictions:
.venv/bin/python scripts/summarize_under3000_ranking.py --verify-run results/under3000_endpoint_ranking_runs/20261018T230346.828091Z

# Inspect the frozen settings and complete per-seed result:
.venv/bin/python -m json.tool results/under3000_endpoint_ranking_protocol_runs/20261018T230319.775906Z/manifest.json
.venv/bin/python -m json.tool results/under3000_endpoint_ranking_runs/20261018T230346.828091Z/summary.json
.venv/bin/python -m json.tool results/under3000_endpoint_ranking_runs/20261018T230346.828091Z/ranking_seed20261015/summary.json

# Read relevant implementation before designing a separately versioned next study:
cat src/rnastable/endpoint_ranking.py
cat src/rnastable/sampled_pair_supervision.py
sed -n '1,145p' src/rnastable/global_sparse_pairs.py
sed -n '120,185p' scripts/train_sampled_long_development.py
cat configs/stage2_to_stage3_gate_2026-10-18.json
```

Do not rerun `--run` merely to review these results; it creates a new training run. Do not edit frozen source/labeler/decoder files in place without preserving replay bytes and creating a new protocol. Before any future publication, inspect the live GitHub README and preserve the user's picture markup, upstream text and repository image assets. This V5 file is the canonical resume note; it was saved locally and has not been published.
