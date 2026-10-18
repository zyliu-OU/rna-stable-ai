# RNA-StableAI: matched hard-negative development study

Date: 2026-10-18 (America/Los_Angeles)
Workspace: `/home/zyliu/Documents/rna-stable-ai`
Active sequence scope: 1–2,999 nt. Stage 3 remains queued for cell-free expression after Stage 2 quality review.

## Result and decision

**Reject this fixed hard-mixture configuration as a replacement for the BCE baseline.** It regressed against a matched random-from-pool control on both development cohorts in all three seeds.

| Cohort | Historical uniform BCE | Random from shared pool | Hard mixture | Hard minus random |
| --- | ---: | ---: | ---: | ---: |
| Six longer references, 1,399–2,973 nt | 0.317351 | 0.314269 | 0.250252 | −0.064017 |
| Thirteen shorter references, 400–535 nt | 0.156064 | 0.168171 | 0.128809 | −0.039361 |

| Seed | Longer random | Longer hard | Difference | Shorter random | Shorter hard | Difference |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 7 | 0.321579 | 0.289466 | −0.032113 | 0.155101 | 0.116811 | −0.038290 |
| 1729 | 0.307554 | 0.248473 | −0.059081 | 0.160390 | 0.129858 | −0.030532 |
| 20261015 | 0.313674 | 0.212816 | −0.100858 | 0.189022 | 0.139759 | −0.049262 |

Metric: mean record pair F1, then mean over seeds. Native controls remain higher: LinearFold/ViennaRNA 0.4381/0.4215 on the longer cohort and 0.3301/0.3346 on the shorter cohort. No checkpoint, default, scope or Stage 3 gate changed.

## Controlled intervention

Training uses the same 103 records, length 61–2,941 nt. The 19 validation references are the same exposed development cohorts as prior studies; their labels never enter mining or training. The teacher for each seed is that seed's frozen 103-record BCE **final** checkpoint, selected by fixed epoch rather than validation. Teacher mining runs once on training sequences before fitting either new student.

For each training record:

1. Recreate the original uniform sample using `fit_seed + record_index`, retaining every legal gold pair and at most 8,192 sampled negatives at four negatives per positive.
2. Score the training sequence in 64-column tiles and collect the teacher's top eight **positive-logit** legal candidates per right endpoint. Union these with the original uniform negatives, remove all legal gold pairs, then score the resulting bounded negative pool.
3. Reserve the same half of the original uniform negatives in both student arms. Fill the remaining half from that same pool: uniformly without replacement for `pool_random`; descending teacher score, ties by coordinates, for `hard_mixture`.
4. Preserve the exact original per-record positive and negative counts. The teacher never supplies new positive labels.

Both students use weighted BCE **without** the prior endpoint-ranking term. Settings remain seeds 7/1729/20261015, ten epochs, Adam 0.001, two CPU threads, identical initial weights, fixed-final checkpoints, the unchanged local-helix model and exact sparse top-32 decoder. Every seed/arm has 12,511 positives, 50,044 negatives and BCE positive weight 4.0. The shared teacher pass makes the two new arms comparable in mining exposure and optimizer workload; their total compute is **not** equal to the historical single-stage BCE run.

The pool size is capped by `8 × sequence_length + 8192`, with no dense pair-label tensor. Both model scoring and canonical/spacing masks remain unchanged. Reserved negatives and sampling RNG are separate from the fixed training-record shuffle RNG.

## Descriptive diagnostics

| Cohort / arm | Pair precision | Pair recall | Mean predicted pairs |
| --- | ---: | ---: | ---: |
| Longer / random pool | 0.326992 | 0.303134 | 456.39 |
| Longer / hard mixture | 0.271098 | 0.232911 | 419.22 |
| Shorter / random pool | 0.155067 | 0.205188 | 122.92 |
| Shorter / hard mixture | 0.124106 | 0.146820 | 114.41 |

Both precision and recall fall under hard selection, with fewer decoded pairs. This is not merely a precision/recall tradeoff in the saved predictions. It does not establish whether sampling severity, label quality, optimization duration, score calibration or model representation causes the regression. One frozen configuration cannot rule out all hard-negative methods.

The selected-pool logits confirm that the intervention actually made negatives harder. Mean selected teacher logit, averaged over training records, rises from 0.805/1.030/0.821 in the random arms to 3.288/4.036/3.518 in the hard arms (seed order 7/1729/20261015). Every record was checked to have at least as high a selected-pool mean in the hard arm. Pool totals across records were 398,089, 407,258 and 396,533; all gold exclusions and original uniform negatives were retained according to policy.

## Evidence, runtime and verification scope

- Protocol: `results/under3000_hard_negative_protocol_runs/20261018T231044.103020Z/manifest.json`.
- Run: `results/under3000_hard_negative_runs/20261018T231058.189040Z/summary.json`.
- Three `mining_seed{seed}/` folders contain 103 hashed `.npz` pool archives each. These preserve original sample edges/labels plus teacher-pool edges/logits.
- Six `{pool_random,hard_mixture}_seed{seed}/` folders contain initial/final checkpoints, 19 predictions each, epoch histories, per-record sample metadata, scores, selection digests and exposure events.
- `descriptive_diagnostics.json` is independently recomputed by `scripts/summarize_under3000_hard_negatives.py`, which pins its driver and prediction inputs.
- Python 3.12.14; PyTorch 2.14.1+cu130; CPU computation with two threads. Mining plus pool serialization took 17.174/15.198/16.017 seconds. Student training-only times were 6.330/5.894, 6.564/5.952 and 7.154/6.424 seconds (random/hard per seed). These exclude baseline teacher training, startup and student validation inference.
- Original process peak RSS: 877,820 KiB, about 857.25 MiB, from Linux `ru_maxrss`; not system-wide or GPU memory.
- Seventeen focused tests passed across hard-negative selection, sampled supervision, endpoint-ranking regression tests and exact decoding. The old scoped baseline artifact/score replay passed before freeze.
- Descriptive precision/recall recomputation passed. The full study verifier passed: re-mined all 309 training pools from pinned teacher checkpoints, reproduced both sampling arms, reconstructed six final students and reproduced all 114 predictions/scores. This is inference/mining replay, not optimizer retraining.

## Scientific limits and next direction

All validation references were already exposed. The longer cohort is label-informed and related to training families/clans/segments, with only one 2,000–2,999 nt reference. The shorter cohort uses computational bpRNA labels. No independent validation, causal stability or expression evidence was added.

Keep the original 103-record BCE model as the comparison baseline. Avoid sweeping hard fractions on these cohorts and calling the best result validation. Before further loss/sampling changes, a useful next diagnostic is an explicitly label-informed **oracle ceiling**: compare full legal-gold/noncrossing recovery, gold recovery within the baseline's retained top-32 candidates, and actual model recovery. Freeze that diagnostic separately. It can distinguish structural/candidate ceilings from score-selection errors without claiming a new model or independent accuracy. The independent reference and quantitative Stage 2 acceptance gates remain unresolved.
