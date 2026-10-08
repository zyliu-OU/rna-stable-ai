# RNA-StableAI development review — 2026-10-06

Workspace: `/home/zyliu/Documents/rna-stable-ai`. Development continues until 21:00 America/Los_Angeles. This review records completed evidence as it becomes available; the end-of-session versioned handoff will identify the final state.

## Native execution reliability

Native requests now have a directory-wide immutable binding as well as individual request identities. Changes to input, checkpoint, code, runtime or configuration reject unfinished resumption. Completed historical pilots can be audited after later code development. Orphan raw output cannot silently trigger a duplicate fold. Interrupted requests retain unknown outcomes/cost and are never automatically retried.

Linux native jobs run under a parent-death supervisor. If their driver dies, the supervisor kills the native process group, including descendants. Timeout cleanup handles a simultaneous process exit, and unexpected wait failures clean up the group before propagating. GNUtime peak RSS describes tool descendants, excluding the supervisor; the memory limit remains a per-process address-space cap. The benchmark CSV explicitly includes the supervisor metadata.

## Helix feature comparison

The sequence-only head adds eight indicators: contiguous canonical outer/inner support at offsets one through three, GC pair and GU pair. Its weights start at zero, with the same base initialization as the controls. The frozen cohort remains 89 training and 47 reused validation records. Each of three model seeds uses ten epochs, the same full BCE objective, and exact sparse checkpoint selection over top16 positive candidate pairs.

All nine fits completed and audited. Reused validation F1:

| Model seed | Baseline | Adjacent stack | Local helix |
|---:|---:|---:|---:|
| 20261006 | 0.3885 | 0.4234 | 0.5244 |
| 20261007 | 0.3763 | 0.4010 | 0.4951 |
| 20261008 | 0.3933 | 0.4055 | 0.4911 |

These are descriptive development results after repeated exposure and selection. They do not establish family independence, generalization, experimental stability or long-RNA biological accuracy. Evidence: `pair_head_development_study_report.md` and `../results/pair_head_development_study_summary.json`.

## Explicit decoder penalty

The inference API accepts an explicit pair-logit penalty in 0..8; zero preserves existing decoding. Penalty identity is frozen in manifests and replayed by the inference auditor. A posthoc grid of 0,0.5,1,2,4 on the nine frozen checkpoints selected zero for eight checkpoints. The seed20261006 baseline selected0.5, increasing reused F1 from0.3885 to0.3979. The helix checkpoints all selected zero. This was a penalty comparison at each already selected epoch, not joint epoch/penalty optimization. Evidence: `pair_penalty_development_report.md`.

## Population sampling

A rank-based canonical-pair population index counts and samples negatives without enumerating a dense label matrix. Every representable positive is retained. A uniform negative sample without replacement has inclusion probability m/N; negative BCE terms receive N/m weight and the loss divides by the full per-record population size. Positive weighting uses the full training population. Averaged over random draws, loss and gradient equal the full-population objective; a fixed draw reused during training need not produce the same optimization trajectory.

Three draws use the same model seed20261006, same cohort, optimizer and full validation labels. All retain136,538 negatives from1,180,545, and2,820,000 bytes of index/label tensors. Reused F1 is0.5251,0.5196,0.5245 versus0.5244 for full supervision. No sampling seed is selected as an independent biological replicate. All sampled tensors, population counts, checkpoint predictions and validation losses replayed. These byte figures describe primary exported sample arrays; API private copies and other allocations are outside this count. Training callbacks receive private supervision/configuration copies, and retained population labels are checked against reference contacts before checkpoint output. Sampled population training requires an explicit importance-weighted loss callback. Evidence: `population_development_report.md`.

Synthetic nested reverse-complement toys demonstrate one sampled Adam step at1000,5000,10000nt. All three completed within bounds and replayed exact losses, gradients and model tensor digests. At10000nt,159,936 sampled negatives plus4,998 positives retain3,298,680 label bytes; the avoided full index/label layout would require374,711,560 bytes. These byte figures exclude Python/model/optimizer allocations. The measured whole-worker peak RSS was813.93MiB, including Python/Torch. This is resource feasibility, with constructed labels and no biological accuracy evaluation. Evidence: `population_resource_report.md`.

## Longer annotations

The requested training-only CRW import range remains1025–4096nt. The local archive contains503 CRW training members, with maximum raw length674nt. Across all5430 upstream training members, the maximum is also674nt. The empty import is preserved as a completed availability result; no labels are projected, fabricated, or drawn from holdout/test sources to fill the range. Evidence: `long_population_training_data_report.md`.

## Extended native validation

The original stack replication's30-second10000nt Vienna timeouts remain intact. A separate extension froze those six finalists and made12 reference requests at300seconds each, without new proposal search or fitting. All12 succeeded. For search seed20261006, selected deltas were0 (random),−6.1 (compatibility),−2.4 (checkpoint prior); for20261007,0,−5.3,−6.6kcal/mol. The neural prior did not beat compatibility in both seeds. Evidence: `checkpoint_prior_reference_extension_report.md`.

The helix checkpoint is undergoing the same six exposed synthetic input/search-seed components, with a fixed code snapshot and300-second final validation for every arm. Results will be recorded after complete artifact replay. Final inference still requires native reference improvement before selecting a mutated sequence; pair logits rank proposals and are not physical energies.

## Verification status

The first expanded full suite passed426 tests. A later run passed452 tests and caught one CLI CSV failure from supervisor metadata; the schema fix passed the41-test CLI/process-guard regression. A subsequent full suite passed461 tests; later exposure-discovery and callback-hardening checks are in progress. Focused sampler/resource tests include exact expectation loss/gradient checks, randomized rank inventories, state replay and corruption rejection. Earlier experimental evidence remains retained and independently auditable.

## Complete development error diagnostics

All423 stored predictions (nine selected checkpoints ×47 reused records) are retained in the fixed-slice report. Mean F1 across the three model seeds is0.6676/0.6631/0.7174 for baseline/stack/helix on12 PDB-derived records;0.4109/0.4268/0.4811 on23 Rfam-derived records; and0.0568/0.1245/0.3326 on12 CRW-derived records. Absolute CRW performance remains poor. Helix improves34 records, regresses on5 and ties8 versus baseline, averaging each record across seeds. Empty fixed length/source slices retain zero denominators and unknown means. No new checkpoint selection or inference is performed. Evidence: `development_slices_report.md`.

Exposure discovery now includes nested model-study components and frozen native runner directories, while avoiding external directory symlinks. A corrupt nested event fails inspection rather than being silently skipped. This preserves conservative exposure accounting for future planning.

Static, source-bound scientific figures: [PNG](figures/development_2026-10-06.png) and [SVG](figures/development_2026-10-06.svg). Whiskers show observed model-seed ranges, not confidence intervals. Full-layout storage is theoretical; primary sample tensor storage is directly counted.
