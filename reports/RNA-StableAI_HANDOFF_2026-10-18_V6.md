# RNA-StableAI handoff — 2026-10-18 V6

Project: RNA-StableAI
Date: 2026-10-18 (America/Los_Angeles)
Version: V6
Workspace: `/home/zyliu/Documents/rna-stable-ai`
Previous canonical handoff: `reports/RNA-StableAI_HANDOFF_2026-10-18_V5.md`.

## 1. User priorities and current stage

- Continue **Stage 2**, with active RNA lengths **1–2,999 nt**. The user's latest scope wording was "smaller than 3000nt"; 3,000 nt is excluded. Preserve all 3,000+ nt historical work without truncation/deletion.
- The user wants to reach Stage 3 faster, but explicitly requires credible Stage 2 quality first. Stage 3 is queued for **cell-free expression**, not started.
- Keep the independent-validation, accuracy, coverage, constraints/resource and replay gates. Current development studies do not establish that Stage 2 is good across the full active range.
- The user requests detailed, self-contained handoffs. This preference is already recorded in root `AGENTS.md`; retain it. Chat responses can remain concise.
- Preserve the user-added GitHub README picture and upstream text/assets before any publication. README was untouched this turn; there was no publication.

Current policies remain `configs/project_scope_2026-10-18.json` and `configs/stage2_to_stage3_gate_2026-10-18.json`. No policy, inference default, checkpoint promotion or stage-transition decision changed.

## 2. Main result and decision

Completed a fixed, matched **training-only teacher-pool hard-negative experiment**. The hard mixture lost to its random-from-pool control on **both cohorts in every seed**. Reject this configuration as a replacement for the 103-record BCE baseline.

| Development cohort | Historical uniform BCE | Random shared-pool control | Hard mixture | Hard minus random |
| --- | ---: | ---: | ---: | ---: |
| Six longer references, 1,399–2,973 nt | 0.3173511819 | 0.3142691996 | 0.2502521035 | −0.0640170961 |
| Thirteen shorter references, 400–535 nt | 0.1560640870 | 0.1681708333 | 0.1288094286 | −0.0393614047 |

Metric: mean record pair F1 within each seed, then mean across the three seeds. All methods use the same reference IDs for each cohort. Do not pool these differently sourced cohorts into one generalization statistic.

Native controls remain higher: longer LinearFold/ViennaRNA **0.4381334451 / 0.4214700331**; shorter **0.3301074317 / 0.3346291106**. No independent validation or biological expression evidence was added. Stage 2 remains active; Stage 3 remains queued.

Scientific report: `reports/stage2_hard_negative_review_2026-10-18.md`.

## 3. Work completed and files

New implementation files:

| File | Purpose |
| --- | --- |
| `src/rnastable/hard_negative_supervision.py` | Deterministic, bounded selection of matched random/hard negative samples, retaining all legal gold positives and exact original negative counts. |
| `tests/test_hard_negative_supervision.py` | Positive/budget preservation, deterministic selection, tied-score inputs, uniform fallback, missing-pool/nonfinite/illegal-input/scope rejection. |
| `scripts/study_under3000_hard_negatives.py` | Freeze, mine, train six students, and replay teacher pools/sample selections/checkpoint inference/scores. |
| `scripts/summarize_under3000_hard_negatives.py` | Independently recompute descriptive F1, precision, recall and predicted-pair counts from saved predictions. |

Documentation:

- Added `reports/stage2_hard_negative_review_2026-10-18.md` with method/results/limits/resources.
- Updated `reports/PROJECT_ROADMAP_2026-10-18.md` to record the endpoint-ranking and hard-negative outcomes, retain the baseline and recommend a ceiling diagnostic before more loss/sampling sweeps.
- Added this V6 handoff. V1–V5 remain intact.

Old model, labeler, decoder, optimizer and frozen study modules were **not edited**. The V4 BCE baseline and V5 endpoint-ranking experiment remain replayable. No new source acquisition, external messaging, Git staging/commit/push, publication or README/image edit occurred. Pre-existing staged/unstaged/untracked workspace changes were preserved.

## 4. Exact protocols, sources and artifacts

New frozen protocol:

`results/under3000_hard_negative_protocol_runs/20261018T231044.103020Z/manifest.json`

Protocol folder contains `train.json`, `validation.json`, `config.json`, `manifest.json`. The manifest pins the new driver/module and imported old implementation sources, input inventories, baseline checkpoints/predictions/summaries, local snapshots and PyTorch version. A copied manifest is stored as the run's `protocol.json`.

New completed run:

`results/under3000_hard_negative_runs/20261018T231058.189040Z/`

Layout:

```text
protocol.json
summary.json
progress.json
descriptive_diagnostics.json
mining_seed7/
mining_seed1729/
mining_seed20261015/
pool_random_seed7/
hard_mixture_seed7/
pool_random_seed1729/
hard_mixture_seed1729/
pool_random_seed20261015/
hard_mixture_seed20261015/
```

Each mining folder contains:

- `000.npz` through `102.npz` in frozen training-record order: original `base_pairs`, `base_labels`, negative `pool_pairs` and float teacher `pool_scores`.
- `manifest.json`: teacher seed, mining/serialization seconds, exposure event and SHA-256 for every archive.
- A training exposure event saved before teacher mining. There are **309** retained pool archives across the three seeds.

Each student folder contains:

- `initial_model.pt`, `final_model.pt`.
- `predictions.json` with 19 records: the six longer references first, then the thirteen shorter references.
- `summary.json`: epoch loss history, training seconds, positive/negative counts, sample digest, all per-record sampling details and cohort scores, checkpoint/prediction hashes, exposure events.
- Training/validation exposure events written before fitting/inference. Across six students there are **114** predictions and **618** per-record sample selections.

The baseline/teacher source is unchanged:

- Baseline protocol: `results/under3000_development_protocol_runs/20261018T223802.654756Z/manifest.json`.
- Baseline run: `results/under3000_development_runs/20261018T223810.974436Z/`.
- Teacher for seed `s`: `extended_103_seed{s}/final_model.pt` in that baseline run. These are fixed-final-epoch BCE checkpoints; no validation outcome selected them.
- Student initial state for seed `s` is compared tensor-by-tensor against `extended_103_seed{s}/initial_model.pt` before fitting and during replay.
- The prior 88-record control remains retained but was not retrained this turn.

## 5. Data inventories and exposure limits

Training: exactly 103 previously used records, length **61–2,941 nt**, consisting of the 88-record base plus the 15 in-scope longer additions. Full IDs/sequences/reference pairs are in the pinned `train.json`. Historical additions at 3,946/3,995 nt remain excluded; no sequence is truncated.

Every arm/seed retains **12,511 legal positive pairs** and **50,044 sampled negatives**. The original labeler reports **1,077 unsupported training gold pairs**; these were not turned into legal positives or hidden by altering old references. Legal-pair support and full-reference evaluation remain distinct. Unsupported handling is inherited unchanged from the original sampled labeler.

Longer development cohort: three RF00177, one RF02541 and two RF02542 references. Five are 1,000–1,999 nt; only one is 2,000–2,999 nt. Exact IDs/lengths:

| ID | Length |
| --- | ---: |
| RF00177:CP000159.1/3330048-3328509 | 1,540 |
| RF00177:CP001998.1/1562911-1561358 | 1,554 |
| RF00177:CP002683.1/865959-864386 | 1,574 |
| RF02541:ADVG01000004.1/1322171-1319199 | 2,973 |
| RF02542:AF024658.1/1-1399 | 1,399 |
| RF02542:FJ843105.1/1-1437 | 1,437 |

Shorter cohort: RF00010 (3), RF01502 (3), RF01052 (3), RF01267 (1), RF01469 (3), lengths 400–535 nt. Exact bpRNA IDs by family:

- RF00010: 5453, 5479, 5361.
- RF01502: 53507, 53569, 53561.
- RF01052: 45541, 45543, 45563.
- RF01267: 49603.
- RF01469: 53067, 53069, 53071.

Each suffix has prefix `bpRNA_RFAM_`; exact lengths and full sequences are in protocol `validation.json` and V5's handoff. Both cohorts are already exposed development sets. The longer cohort is label-informed and has training-family/clan/segment relationships; the shorter cohort uses computational bpRNA labels. No new independent references were added and no family/clan gate was closed.

## 6. Frozen mining and selection algorithm

For each seed, mining occurs **once before either student is trained**, using only the 103 training records and their complete saved reference pairs. No validation sequence, label, score or prediction chooses training negatives.

For training record index `i`:

1. Reproduce the old uniform pair sample with seed `fit_seed + i`, `max_negatives=8192`, `negatives_per_positive=4`.
2. Call the unchanged tiled `sparse_candidates` teacher scorer with `top_k=8`, `block_size=64`. It retains only positive-logit legal pairs, per right endpoint.
3. Union those teacher pairs with original uniform negatives; remove legal gold pairs; sort by coordinates. Score all resulting pool pairs with the same frozen teacher. No teacher prediction becomes a positive label.
4. Reserve the **same half of the original uniform negatives** in both arms using a separate per-record RNG seeded `fit_seed + i`.
5. Fill the remaining half from the same available pool: `pool_random` uniformly without replacement, `hard_mixture` by descending teacher logit with left/right coordinate tie breaks. Exclude reserved pairs and avoid duplicates.
6. Restore all legal positives and exact original negative budget; sort final pair rows by coordinates. Sampling RNG does not affect the fixed training-record shuffle RNG.

The pool's declared storage cap is `8 * sequence_length + 8192`, with no dense pair-label tensor. If the teacher adds no eligible negatives, the original uniform pool is retained; the fallback was unit-tested. In this actual run, every training record had additional pool negatives.

| Seed | Sum of pool negatives across records | Min / max per-record pool | Original-only pools | Reserved uniform negatives | Additional selected negatives |
| --- | ---: | ---: | ---: | ---: | ---: |
| 7 | 398,089 | 99 / 23,721 | 0 | 25,022 | 25,022 |
| 1729 | 407,258 | 95 / 24,632 | 0 | 25,022 | 25,022 |
| 20261015 | 396,533 | 95 / 24,570 | 0 | 25,022 | 25,022 |

Mean selected additional-negative teacher logit, averaged over training records:

| Seed | Random pool | Hard mixture |
| --- | ---: | ---: |
| 7 | 0.8050086494 | 3.2879372860 |
| 1729 | 1.0296335495 | 4.0358941164 |
| 20261015 | 0.8210953512 | 3.5181396323 |

The run checked each record's hard-selected mean is at least the matched random-selected mean. Thus a lack of harder examples does not explain the null/negative result; the intervention genuinely changed selection difficulty. It does not prove which learning or label issue causes the regression.

## 7. Model, optimizer and fair-comparison details

- Same local-helix/context model: embedding 16, channels 32, pair dimension 16, dilations `[1,2,4,8]`, `pair_features=local_helix_context_v1`.
- Training length cap 2,999; all actual train/evaluation records are within scope.
- Seeds `7`, `1729`, `20261015`; two new arms per seed, six fits total.
- Adam learning rate 0.001; ten epochs; identical seeded initial states and record-shuffle policy. No warm start from the final teacher.
- Loss is **weighted BCE only**, `pos_weight=50044/12511=4.0`. The V5 endpoint-ranking term is **not used** in this experiment.
- Fixed final checkpoint, no validation-based epoch selection, early stopping or mining refresh.
- Same exact sparse top-32 decoder and 64-column scoring blocks.
- Both new arms share the teacher pass/pool, positive labels and per-record negative count, so mining exposure and optimizer workload match between them.
- Their total compute is **not equal** to the historical single-stage uniform BCE model: this study adds a teacher pass and reuses already-trained teachers. Do not claim total-compute parity with the old baseline.

## 8. Full per-seed results and descriptive diagnosis

| Seed | Longer random | Longer hard | Hard minus random | Shorter random | Shorter hard | Hard minus random |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 7 | 0.3215789414 | 0.2894664019 | −0.0321125395 | 0.1551008646 | 0.1168110418 | −0.0382898228 |
| 1729 | 0.3075544145 | 0.2484734101 | −0.0590810044 | 0.1603898374 | 0.1298577530 | −0.0305320843 |
| 20261015 | 0.3136742429 | 0.2128164985 | −0.1008577444 | 0.1890217980 | 0.1397594909 | −0.0492623071 |

Both precision and recall deteriorate under hard selection:

| Cohort / arm | Record-seed rows | Pair precision | Pair recall | Mean predicted pairs |
| --- | ---: | ---: | ---: | ---: |
| Longer random | 18 | 0.3269922879 | 0.3031337900 | 456.3889 |
| Longer hard | 18 | 0.2710975727 | 0.2329113688 | 419.2222 |
| Shorter random | 39 | 0.1550671459 | 0.2051877092 | 122.9231 |
| Shorter hard | 39 | 0.1241064087 | 0.1468201190 | 114.4103 |

Fewer predicted pairs accompany lower precision and lower recall. Do not describe this as a beneficial precision/recall tradeoff. The data do not isolate whether pool severity, teacher bias, reference-label noise, optimization duration, calibration or model representation is responsible. Do not conclude that all hard-negative methods are ineffective from this one configuration.

No confidence intervals, hypothesis tests or independent biological replication were performed. Seed replication is optimization replication, not three independent biological panels.

## 9. Runtime, resource observations and verification

Runtime: Python **3.12.14**, PyTorch **2.14.1+cu130**; all scoring/training was CPU with two Torch threads. No GPU execution or new native folds were requested.

| Seed | Teacher mining + pool serialization (s) | Random student training only (s) | Hard student training only (s) |
| --- | ---: | ---: | ---: |
| 7 | 17.1740 | 6.3305 | 5.8941 |
| 1729 | 15.1982 | 6.5643 | 5.9520 |
| 20261015 | 16.0168 | 7.1544 | 6.4239 |

Times exclude prior teacher training, source audits/startup and student validation inference. Original study process peak RSS: **877,820 KiB**, approximately **857.25 MiB**, measured by Linux `resource.getrusage(...).ru_maxrss`. This is not whole-machine memory, GPU memory or a timing guarantee; replay preserves the original resource observation.

Checks actually run:

1. `.venv/bin/python -m pytest -q tests/test_hard_negative_supervision.py tests/test_sampled_pair_supervision.py tests/test_endpoint_ranking.py tests/test_long_exact_sparse_pairs.py` → **17 passed in 2.04 s**.
2. New protocol `--freeze` first verified the old scoped baseline artifacts/scores → passed, without retraining.
3. New `--run <manifest>` → all three mining passes and six ten-epoch student fits completed; no partial/failed runs remain.
4. New `--verify-run <summary>` → **teacher mining, sample selection, checkpoint inference and score replay passed**. It re-mined all **309** pool archives from pinned teachers, checked exact pool-array equality, regenerated both sampling arms and sample digests/details, checked initial states and checkpoint bytes, verified exposure identities, reconstructed all final students, and reproduced all **114** predictions and cohort scores/aggregates.
5. Descriptive postprocessor `--run` wrote a new artifact with exclusive creation; `--verify-run` independently recomputed its statistics from saved predictions → passed.

Limits: this was teacher/student **inference replay and artifact verification, not deterministic optimizer retraining**. No full repository suite or independent experimental validation was run. Epoch losses and observed times are retained observations, not re-derived by retraining. Final documentation/whitespace checks are reported after this file is written.

## 10. Hashes and reproducibility anchors

Run-level SHA-256:

- `protocol.json`: `f2df73ceca623d3639b1a8efc1e387ac3b213d5d09865ca6536d6357d2125111`.
- `summary.json`: `96c45e0bdb04d111e896b8f2eb7ba5e7a759df0471f3652aad4e8f087948e502`.
- `descriptive_diagnostics.json`: `cc334804d33afdad0834bc32a3153c8369d19d1192e731a073b3747c93a8be99`.

Final checkpoints:

| Arm / seed | `final_model.pt` SHA-256 |
| --- | --- |
| pool_random / 7 | `143934d1d513c29fedba0a8ed86a601c959f2abaa3ed156e4d568a89696ea199` |
| hard_mixture / 7 | `3c8a3ad91cd7f91eba9132f87172bbe4bee646593865d23343a5ba90a3a75665` |
| pool_random / 1729 | `8ce332a60de24c56f2212059a81566a00ffe894bcba1fac6b0097817635c3acb` |
| hard_mixture / 1729 | `275b233189e7840a2d400c942e5abf73480950cb091c5f6f2d3bc52977782652` |
| pool_random / 20261015 | `39dccd495d01e62888a04a1a0005a48cfd4f32fdeca45865e8a90acffb5fc1dd` |
| hard_mixture / 20261015 | `e873f5409d3fbfbb50e1b866257010bde33c010d65d3644008260de3f0873c8e` |

Sample selection digests (concatenated final edge/label arrays in frozen record order):

| Arm / seed | Sample SHA-256 |
| --- | --- |
| pool_random / 7 | `0062bcbd4b9bc65aa6970386d0c81e69a8f5d630ee374953b2ba84a182b5d084` |
| hard_mixture / 7 | `9408c428a483f31649c9bcad6eff53c4ea31036305f67ba7ea6494937bffa409` |
| pool_random / 1729 | `12832f0306dc7d2b4c23f1e4602e5389c806b6b6df1756eff3ffa9f0ede839f4` |
| hard_mixture / 1729 | `4c607e7ab3d54baf85a236970661051f84335a31717f79470bd1055cbe74f5c8` |
| pool_random / 20261015 | `9b19ede5dd1487d6387328bf93cae526977895e8f512a5449e8e357dd540f6e1` |
| hard_mixture / 20261015 | `0d9a2d05a425a0608c0710fcc5d633d12f7bd8e67aed2314426d01d196cded7c` |

Source SHA-256:

- `src/rnastable/hard_negative_supervision.py`: `f0d4c4cb582fedf97b81f583d53d222239264cde9660d057e0c0c0dc0e7ea971`.
- `scripts/study_under3000_hard_negatives.py`: `84b1330769edc1846f1271331670970eef8cba26c492f19bbaafa84ed3dd7435`.
- `scripts/summarize_under3000_hard_negatives.py`: `0a50ea556d14677504cdc770284d4b8484f7223c3678689ed3501795f4490d1b`.
- `tests/test_hard_negative_supervision.py`: `a3672d8eb8a4981926c38fe430b3210fd23d0ea81fa3f815d8597be7e058d29d`.

Full prediction hashes, initial checkpoint hashes and per-record pool archive hashes are retained in the component/mining manifests and checked by replay. Use those manifest paths rather than inferring which checkpoint/version was used.

## 11. Interpretation and what must not be claimed

- The hard-mixture intervention genuinely raised selected-negative teacher scores, but consistently worsened both cohorts under the fixed ten-epoch configuration. Reject **this configuration**, preserve its failures and do not promote its checkpoints.
- The random-from-pool arm is roughly flat on longer mean F1 and higher on shorter mean F1 versus historical BCE; that compound comparison includes a changed candidate pool and extra teacher compute. It is not proof of an independent generalization gain.
- V5 endpoint ranking also did not improve longer mean F1. Do not keep sweeping loss weights/hard fractions and then label the chosen result an independent test.
- Original 103-record uniform BCE remains the comparison baseline. No production defaults changed.
- The six-reference longer cohort has only one 2,000–2,999 nt example; training family/clan/segment exposure and label-informed selection remain. The short cohort is computational and reused. No independent-validation or full-length-coverage gate passed.
- A successful replay establishes reproducibility of saved mining/inference outputs, not biological truth, measured stability or protein-expression benefit.
- No training, mining or replay processes remain running from this continuation; the run and full verifier exited successfully.

## 12. Prioritized next work

1. **Before more fitting, freeze a label-informed recovery-ceiling diagnostic** on the exposed cohorts. Compare (a) best legal/noncrossing recovery from all legal gold pairs, (b) best recovery from legal gold pairs present in the frozen baseline's positive top-32 candidate set, and (c) actual baseline decoded recovery. This can separate unsupported/crossing-reference limits, candidate coverage and score-selection errors.
2. Label the oracle outputs explicitly as optimistic diagnostics using gold labels, never model predictions or independent accuracy. Do not use them as a Stage 3 pass metric. Preserve all full-reference gold pairs in scoring and record unsupported/crossing portions rather than deleting them.
3. Reuse existing exact sparse decoder and baseline checkpoint files in a new driver/protocol. Test tiny crossing/illegal-pair cases so the diagnostic's ceiling interpretation is correct. Do not edit frozen model/decoder files in place.
4. Use that diagnosis to select a single subsequent architecture/structured-objective experiment. If optimization duration, compute or sample budgets change, preserve a matched comparator and disclose the difference.
5. Separately, preregister quantitative application-specific accuracy acceptance criteria and obtain genuinely independent family/clan/sequence-separated evidence within scope, especially 2,000–2,999 nt. The current studies do not replace that requirement.
6. Keep Qβ/AP205 and other 3,000+ nt work deferred. Keep cell-free Stage 3 candidate design and assays queued behind Stage 2 review.

## 13. Exact safe continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-18_V6.md
cat reports/stage2_hard_negative_review_2026-10-18.md

# Unit/decoder checks only; no fitting:
.venv/bin/python -m pytest -q tests/test_hard_negative_supervision.py tests/test_sampled_pair_supervision.py tests/test_endpoint_ranking.py tests/test_long_exact_sparse_pairs.py

# Full training-only teacher mining, sampling, saved-student inference and score replay;
# no optimizer retraining or native-tool requests:
.venv/bin/python scripts/study_under3000_hard_negatives.py --verify-run results/under3000_hard_negative_runs/20261018T231058.189040Z/summary.json

# Recompute descriptive precision/recall/count statistics without model inference:
.venv/bin/python scripts/summarize_under3000_hard_negatives.py --verify-run results/under3000_hard_negative_runs/20261018T231058.189040Z

# Inspect frozen settings and representative negative result:
.venv/bin/python -m json.tool results/under3000_hard_negative_protocol_runs/20261018T231044.103020Z/manifest.json
.venv/bin/python -m json.tool results/under3000_hard_negative_runs/20261018T231058.189040Z/summary.json
.venv/bin/python -m json.tool results/under3000_hard_negative_runs/20261018T231058.189040Z/hard_mixture_seed20261015/summary.json

# Read ceiling-diagnostic building blocks and current gate before writing a new protocol:
cat src/rnastable/long_exact_sparse_pairs.py
cat tests/test_long_exact_sparse_pairs.py
sed -n '1,140p' src/rnastable/global_sparse_pairs.py
sed -n '1,100p' src/rnastable/pair_reference.py
cat configs/stage2_to_stage3_gate_2026-10-18.json
```

Do not rerun `--run` just to inspect this study; it starts a new timestamped training run. Do not overwrite any frozen protocol, checkpoint, pool archive or older handoff. No user confirmation is needed for ordinary authorized continuation. Before any future publication, inspect the live GitHub README and preserve its picture and upstream changes. This detailed V6 file is local and is the canonical resume note.
