# RNA-StableAI development roadmap — 2026-10-13

Workspace: `/home/zyliu/Documents/rna-stable-ai`.
RNA-StableAI remains a research prototype. The current gate is independent
biological validation; computational functionality and several descriptive
benchmarks are complete, while validated stability/function remain unresolved.

| Step | Stage | Current evidence and remaining work |
|---:|---|---|
| 1 | Reproducible foundations | Native resource bounds, journals, hashes, CPU folds and separate encoder benchmarks work. Verified metadata replay caching now avoids repeated identical screens. |
| 2 | Structure-model development | Nine matched BCE fits, candidate-loss diagnostics and the 16/32/64 budget study are complete. Three matched structured-loss helix fits reduced false positives but lowered F1 on all seeds; defaults remain unchanged. |
| 3 | Model-guided optimization | Existing synthetic/native energy-selection studies remain retained. Computational energy gates do not establish chemical stability or retained function. |
| **4** | **Independent biological validation — current gate** | Three prospective source panels have now been evaluated. The latest has15 planned records, four supported lysine references, and11 unsupported annotations. Broad accuracy and complete training/tool independence remain unestablished. |
| 5 | Long biological RNA validation | Synthetic resources reach10000 nt; exact sparse inference remains bounded to1024 nt. Longer inference is approximate. Complete longer biological annotations and a declared screened evaluation are still needed. |
| 6 | Measured stability and function | The pinned public OpenVaccine 64-record assay pilot is complete: 320 supported assays, 384 predictions and 2880 association rows. All 128 native calls completed; descriptive associations and figures audited. This cannot establish causal mutation effects or retained function. |
| 7 | Validated release | Remains gated on the scientific evidence above. Code, experimental checkpoints, input data and retained results are being published as research artifacts, without a validated release. |

## Current working step: source archive and GitHub publication

The frozen measured-proxy assessment is complete and audited. The source archive
retains257/267 recorded Python versions and the current source bundle; ten older
versions remain explicitly unavailable. Publish the updated code, documentation,
input data, checkpoints and measured evidence, then stop at the user's request.
No further experiment is authorized by this continuation.

If research is resumed, the main scientific gate remains step4. Design a screened
independently annotated panel with adequate supported references, documenting
training/tool provenance and excluding previously consumed families as fresh tests.
Do not select models on the completed assay pilot or claim mutation/function validation.

The dataset is an author-provided processed short-construct source, not a fresh
blind clinical/biological experiment. The pilot contains only `SN_filter=1` rows.
Its public measurements do not validate the project's proposed mutations,
long-RNA accuracy, cellular half-life or retained function. All source sequences
are conservatively marked as validation exposure when their assays are bound.

The latest Rfam comparison gives helix F1 0.533167 on four lysine references,
versus0.726724 for ViennaRNA and0.748810 for LinearFold. Unsupported RNase P,
tmRNA and lysine records remain in denominators with null metrics. All three
families, including unsupported records, are consumed for future fresh-test
planning. Do not tune on this panel or rerun it as independent evidence.

## Evidence

- `reports/candidate_budget_development_review_2026-10-13.md`
- `reports/helix_objective_development_review_2026-10-13.md`
- `reports/prospective_third_pair_evaluation_review_2026-10-13.md`
- `docs/PROSPECTIVE_REPLAY_CACHE.md`
- `docs/MEASURED_DEGRADATION_SOURCE.md`

- `reports/degradation_pilot_review_2026-10-13.md`
- `docs/MEASURED_DEGRADATION_PILOT.md`
- `docs/REPLAY_SOURCE_ARCHIVE.md`
