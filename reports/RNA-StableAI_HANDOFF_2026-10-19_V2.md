# RNA-StableAI handoff — 2026-10-19 V2

Project: RNA-StableAI
Date: 2026-10-19, America/Los_Angeles
Version: V2
Workspace: `/home/zyliu/Documents/rna-stable-ai`
Selected architecture: **RNAfold + STRAND + RiboNN + BoTorch**
Immediately previous handoff, this session's starting point: [V1](RNA-StableAI_HANDOFF_2026-10-19_V1.md).
Publication, scope and component records: [V13](RNA-StableAI_HANDOFF_2026-10-18_V13.md). Full scientific/inference record: [V12](RNA-StableAI_HANDOFF_2026-10-18_V12.md). STRAND record: [V11](RNA-StableAI_HANDOFF_2026-10-18_V11.md). Architecture decision: [V9](RNA-StableAI_HANDOFF_2026-10-18_V9.md).

## Scope of this session

The user said "sure continue next step" after V1. The next step recorded in V1 was its **pending item 1**: define the separately named RNAfold calibration as a new versioned model refit on RNAfold ensemble features, with the feature set prespecified in a v2 criterion rather than inferred from V1's numbers.

That is now built, frozen, fitted and verified. **`strand_rnafold_calibration_v1` exists, its prespecified minimum-competence bar passed, and the outcome is `not_rejected` — which unlocks nothing.** V13 items 2 and 3 remain unstarted. No GitHub publication was performed. No network access occurred.

## Decisions that supersede earlier handoffs

- V1 listed the separately named calibration as pending. It is now **built and recorded as a named candidate**: `strand_rnafold_calibration_v1`, primary arm **without_alo**, 1 component.
- V1 flagged two leads — the identity null and the without-ALO arm — as explicitly not acted on. They are now **tested under a separate frozen criterion** rather than adopted. The without-ALO feature set was prespecified in criterion v2 before fitting, and both arms were fitted and reported so that the choice was not made by the author.
- V11–V13 recorded the published with-ALO arm as the better held-out model (eGFP RMSE 0.1893 vs 0.2174). On RNAfold features that ordering **reverses**: without_alo is better on every held-out metric, and the published with-ALO eGFP advantage does not transfer. This is a new result and it is consistent with V1's finding that ALO is engine-artifact-driven.
- The reference-only gate in `src/rnastable/strand_reference.py` **remains closed and unchanged**. The new calibration is a separate model with its own artifact; it was not wired into `replay_reference`, and no scoring path was opened.
- The V1 agreement criterion, the V1 run, `configs/strand_reference_reproduction_v1_2026-10-18.json` and the canonical STRAND reference run were **not modified**. Both criterion files were re-hashed after the fit and are byte-unchanged.

## Constraints and scope, unchanged

Active scope stays **1–2,999 nt**, with historical 3,000+ nt evidence preserved, no truncation and valid annotated-CDS limits. Stage 2 remains **open**; cell-free expression Stage 3 is queued. [Scope](../configs/project_scope_2026-10-18.json) and [gate](../configs/stage2_to_stage3_gate_2026-10-18.json) remain authoritative. No numerical acceptance threshold, translation floor, assay platform/replicates or candidate budget is newly frozen. `new_sequence_scoring_enabled`, `expression_candidate_design_enabled` and `stage3_ready` are **false** in every artifact written this session, including the new model file.

## Completed work

### Frozen criterion v2

**`configs/strand_rnafold_calibration_criterion_v2_2026-10-19.json`** — SHA-256 **`4b63898b2080c39a6d723b832688f7c955d57902b0e3f42f41aad8976c635316`**, 7,439 bytes. Written and hashed **before** any refit existed. It fixes in advance:

- **Model name and naming rule.** `strand_rnafold_calibration_v1`, which must never be presented as published STRAND, as a reproduction of STRAND, or as STRAND with a different folding engine. Its coefficients are not the published coefficients.
- **Why a refit rather than a substitution**, carrying the v1 criterion hash, the v1 run path, the `rejected` outcome, and the four label-free findings that justify the feature choices.
- **Feature source.** Reuse the hash-verified folds of the v1 run (folding is deterministic, so nothing is refolded), `ensemble_energy_per_nt`, `identity` ALO transform, GC in percent. The energy choice is justified as established label-free on 85 held-out records, **not** on any half-life outcome; the identity transform is justified by v1 having ruled out the transform family.
- **Both arms prespecified**, with feature sets mirroring the published arms exactly so the only changed variable is the folding engine.
- **A written leakage disclosure.** Published half-life accuracy for both arms was already known from V11–V13. To stop that knowledge from selecting the reported model, the criterion forbids the author from choosing the primary arm and forbids choosing it on the held-out cohort.
- **Primary-arm rule.** Lower nLuc **training-only** LOO RMSE, with_alo on a tie below 1e-12. Reads no held-out record.
- **Fitting procedure.** Mirror `scripts/reproduce_strand_reference.R` unchanged: R `pls::plsr`, `scale=TRUE`, kernelpls, LOO validation, components by `which.min` of mean training PRESS, 2 repetitions required identical. The upstream `Figure_Scripts_1.R` block checks are declared **not applicable and deliberately omitted**, because they reproduce the released-feature fit and are not a check on a refit.
- **Evaluation.** 13 eGFP records, single readout, both arms reported; 9 MEV exploratory reported and never used for fitting, selection or the primary-arm rule. An exposure disclosure states the eGFP cohort is held out from every fit but project-exposed, so it is a held-out readout and **not independent validation**.
- **Acceptance bar.** Primary arm eGFP RMSE ≤ the training-mean null RMSE on those same 13 records. Minimum competence only. Published RMSEs are recorded as **reference points, explicitly not bars**, since they come from a different feature source.
- **Five no-claim statements**, covering that passing is not validation, released target scale only, no Stage 2 requirement satisfied, 68-of-91 redundancy at 928 nt so no scope coverage, and no licence to score new sequences or design candidates.

### Implementation

- **`scripts/fit_strand_rnafold_calibration.R`** (new, 101 lines). Mirrors the published fit method exactly; the only change is that features arrive as prepared CSVs instead of being recomputed from `bpp_per_pos`. Adds the prespecified training-mean null. Asserts cohort sizes 69/13/9, exact column order and finite values. Exports both arms' components at every component count, per-cohort metrics, per-record predictions, both `.rds` fits and `sessionInfo`.
- **`scripts/fit_strand_rnafold_calibration.py`** (new, 300 lines). Verifies pinned upstream sources and the STRAND commit; resolves the pinned source manifest **through the v1 run's own protocol and identity** and checks its hash against what v1 recorded, so the sequences here are provably the ones the stored folds came from; re-verifies every stored fold against the v1 run manifest and its parameter-file hash; builds the feature CSVs; runs R twice and requires identical exported models; replays every exported component in Python against the R predictions; applies the primary-arm rule and the acceptance bar; writes the model and run. `--verify-run` re-checks artifact hashes and replays the acceptance decision without refitting.
- **`tests/test_strand_rnafold_calibration.py`** (new, 12 tests). Criterion gates, model name, energy/transform choices, repetition count; the exposure and leakage disclosures and the "not validation" claim; published reference points matching the V11–V13 record; the primary-arm rule including the near-tie branch and the both-arms requirement; cohort splitting and label carriage; exact float round-trip through the feature CSVs and refusal to overwrite them; metric lookup; and the Python/R replay check both accepting a match and rejecting 1e-6 drift.

`src/rnastable/strand_agreement.py` gained no new logic; `substituted_features` is reused unchanged. No existing module, config, protocol or canonical run was edited.

### Canonical run

**`results/strand_rnafold_calibration_runs/20261019T174049.053308Z/`** — 25 files, 304,208 bytes, `manifest.json` lists **24** artifacts.

| Artifact | SHA-256 |
| --- | --- |
| `summary.json` | `bd3a1d60c837d9088e0ae8c19a9d1fecfb38cb8a1512170874833eaa9c28f1aa` |
| `calibration_model.json` | `9daa59f2e75537d961eaf215b207a7e96c9c4bf9af65e45c26bc6ca4a636d52c` |
| `identity.json` | `077d4da58e4a4aedbadf352614e53f7699e3a35734c57c1ea38b7e9743dba017` |
| `protocol.json` | `da02447979a2be9ed038fc8c09341ae39759f9cb8338ae1b7417dfaf3224561f` |
| `manifest.json` | `9d8456b067b48c0b9e52d13dc076d03d79c4e58d6930b810dcd040c112a61581` |
| `fit/r_models.json` | `ab550bc8fc0bef17fc8653f438b40b73dc6bcbe6ef9a1c9efa386b6cf3862427` |
| `fit/r_predictions.csv` | `4b96340408f17a14067f31a3503fd16d10d1b7ceb31166f7b17cd056b7c7902b` |
| `fit/without_alo_model.rds` | `abcf2d408245fcb3ad59887beb4f978d8275dd9269f03f889c7e8b042412b736` |
| `fit/with_alo_model.rds` | `4afba15526a6580e104a146af359a53833a051064861102c200ff2a1af1db53b` |
| `features/train_features.csv` | `6c83453a54880d0863a2d14401c3f37b1d70ad285fb9187f268d5a089f7e6652` |
| `features/egfp_features.csv` | `0f9c363f344594a62b121933f2a5808631bc85b645e7ff84c0ed0bb4fb7a3cd5` |
| `features/mev_features.csv` | `75802dbe58bb0aa11a7ada97f98dfa880cdd2f666966a67aa8986ca84fcecd09` |

`protocol.json` is criterion v2 re-serialized at indent 2, so its hash differs from the config file's; `identity.json` records `criterion_sha256` = `4b63898b…`. Also present: `fit_repeat1/` with the same seven fit outputs, `fit/R_sessionInfo.txt`, both `command.log` files, and `source/` copies of the five implementation files with their hashes.

Provenance recorded in `identity.json`: feature source run `results/strand_rnafold_agreement_runs/20261019T172402.804593Z`, its manifest `d8343c39…`, its `agreement.json` `70e037d5…`. Implementation hashes: driver `95f44538…`, R script `5bac2ac3…`, `strand_agreement.py` `d59bffd1…`, `strand_reference.py` `472488c2…`, `component_integration.py` `1a592ac3…`.

### Protocol actually executed

- Inputs: the 91 released STRAND records, cohorts 69 train / 13 eGFP / 9 MEV, rebuilt from the pinned `Data/nluc_cleaned_new_final.csv` and `Data/validate_cleaned_new_final.csv`; all pinned STRAND source hashes re-verified at load.
- Features: read from the 91 stored v1 folds, each re-hashed against the v1 run manifest and each checked to carry parameter-file SHA-256 `9521527a251d5e68e6149595f8aa72aa72c63e00dc5af41d7164e6ecaa664777`. **No sequence was refolded.** ViennaRNA 2.7.2, `RNA_Turner2004`, 37 °C, dangles 2. Features written to CSV at full float round-trip precision.
- Fit: R 4.5.3, pls 2.8.5, jsonlite 2.0.0 from the isolated `external/strand-r/`, `TZ=UTC`, `OPENBLAS_NUM_THREADS=1`. Runtime asserted against the criterion. Two repetitions, 0.241 s and 0.229 s; exported model structures **identical**. No seed is involved; PLS with LOO validation is deterministic.
- Numerical guard: all exported components of both arms replayed in Python against the R predictions for the train, eGFP and MEV cohorts — **637 comparisons per repetition, max absolute difference 5.10702591327572e-15**, tolerance 1e-10. LOO rows are excluded from replay because they come from per-fold refits.

## Results

Training-mean null: mean nLuc training half-life **1.1336412079710145 h**; eGFP RMSE **0.27798382968950514 h**; MEV RMSE 2.332549 h.

Training-only LOO RMSE, which decides the primary arm: with_alo **0.2969350653178015**, without_alo **0.29273883845871723**. Primary arm = **without_alo**, selected components **1**.

LOO PRESS by component count — with_alo 6.08376 / 6.09521 / 6.28972 / 6.57805 (minimum at 1, where the published fit on LinearPartition features selected 2); without_alo 5.91303 / 6.07906 / 6.33095 (minimum at 1, matching the published selection).

### with_alo arm, 1 component

| Cohort | n | RMSE | MAE | R² | Pearson | Spearman | published (LinearPartition) | Δ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| train | 69 | 0.286752 | 0.238820 | +0.2905 | +0.5389 | +0.5310 | | |
| train_loo | 69 | 0.296935 | 0.246973 | +0.2392 | +0.4918 | +0.4931 | 0.297497 | −0.000562 |
| **egfp** | 13 | **0.235464** | 0.183112 | +0.2376 | +0.5545 | +0.5769 | 0.189322 | **+0.046142** |
| mev_exploratory | 9 | 2.215595 | 2.183886 | −30.9304 | +0.4282 | +0.5167 | | |

### without_alo arm, 1 component — primary

| Cohort | n | RMSE | MAE | R² | Pearson | Spearman | published (LinearPartition) | Δ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| train | 69 | 0.282196 | 0.236152 | +0.3128 | +0.5593 | +0.5290 | | |
| train_loo | 69 | 0.292739 | 0.244475 | +0.2605 | +0.5132 | +0.5003 | 0.292920 | −0.000181 |
| **egfp** | 13 | **0.219423** | 0.178478 | +0.3379 | +0.6235 | +0.7253 | 0.217428 | **+0.001995** |
| mev_exploratory | 9 | 2.207069 | 2.175458 | −30.6852 | +0.4349 | +0.2500 | | |

**Acceptance: `not_rejected`.** Primary arm eGFP RMSE 0.2194228670733408 h ≤ null 0.27798382968950514 h, i.e. 21.1 % below the training-mean null. The bar is minimum competence and nothing more.

Primary model component (`without_alo`, ncomp 1), beside the published LinearPartition-feature fit of the same arm and component count:

| Term | published (LinearPartition) | strand_rnafold_calibration_v1 |
| --- | --- | --- |
| intercept | 0.4414682466919088 | 0.4469112381319831 |
| energy_per_length | −0.9387228285189522 | −0.9395399443290398 |
| GC | 0.0160610384854724 | 0.0160671153423135 |
| aup | −1.4695140310461434 | −1.4900064074181592 |

## Scientific interpretation and limits

1. **The without-ALO relationship transfers across folding engines essentially intact.** Training LOO moves by −0.000181 h and eGFP by +0.001995 h against the published LinearPartition-feature fit, and the three coefficients agree to roughly 1 % with the largest shift in `aup`. That is the expected consequence of V1's label-free result: energy and GC transfer exactly and `aup` nearly.
2. **The published with-ALO advantage does not transfer.** On RNAfold features the with-ALO arm degrades on the held-out cohort by +0.046142 h, a 24 % worse RMSE, its training-only PRESS minimum moves from 2 components to 1, and it is beaten by without_alo on every held-out metric (RMSE 0.235 vs 0.219, R² 0.238 vs 0.338, Spearman 0.577 vs 0.725). Combined with V1's mechanism — the released ALO depends on exact zeros and above-one values that LinearPartition's approximate normalization produces and an exact partition function does not — the most consistent reading is that a meaningful part of the published ALO contribution is engine-specific numerical structure rather than a transferable signal. **This is an interpretation of two convergent lines of evidence on one exposed 13-record cohort, not an established fact**, and it is not a claim about the published work's biology.
3. **MEV transfer remains poor**, as V11–V13 recorded: RMSE ≈ 2.21 h against a null of 2.33 h and R² ≈ −31. The model barely beats the mean on that cohort. Nothing about MEV is improved here and it was excluded from every selection decision.

What must **not** be claimed: any validated stability, half-life, translation or expression capability; any Stage 2 progress; any independent validation. The acceptance bar was minimum competence against a training-mean null, passed on **13 project-exposed records from one construct family**. The 91 released records are highly redundant, 68 of 91 at 928 nt, so no coverage of the 1–2,999 nt scope is implied. The eGFP cohort is held out from every fit here and from the published fit, but it was used in the V11–V13 reproduction, 3 of its 13 records were in the burned v1 panel, and its RNAfold features were computed in the v1 run; it is a held-out readout, not independent evidence. `strand_rnafold_calibration_v1` must not be called STRAND.

Rejected and not done: wiring the new model into `replay_reference` or any scoring path; adopting V1's identity null or without-ALO lead without a separate frozen criterion; using the eGFP or MEV cohort to pick the arm or the component count; relaxing the acceptance bar; treating the published RMSEs as bars the refit had to beat.

## Verification performed

- **`--verify-run`** on the calibration run: **24 artifacts** re-hashed and matched, stored metrics reconciled against the stored summary, acceptance decision replayed from `fit/r_models.json`. Mode: artifact and stored-fit audit, no new fit.
- **Determinism:** two independent R fits produced identical exported model structures.
- **Cross-language:** 637 Python-versus-R prediction comparisons per repetition, max absolute difference 5.10702591327572e-15 against a 1e-10 tolerance.
- **130 focused tests passed in 1.88 s** — 12 new, plus V1's 27 and the fifteen V13 suites, confirming no regression.
- Both criterion files re-hashed after the fit and confirmed byte-unchanged (`a003eaa2…`, `4b63898b…`).
- New model file gates confirmed: `is_published_strand` false, `independent_validation` false, `new_sequence_scoring_enabled` false, `stage3_ready` false.
- Pinned source hashes, stored-fold hashes against the v1 manifest, the v1 source-manifest hash, folding parameter-file hash, cohort sizes and the R/pls/jsonlite runtime were all re-verified inside the run.

**Not run and therefore unverified:** no refolding, no RiboNN inference, no BoTorch run, no custom-model training or study replay, no full repository test suite, no GitHub publication, no network access. No previously measured result was re-measured. The new calibration has had **no** independent biological evaluation of any kind.

## Pending work, prioritized

1. **Independent lineage-safe evaluation of `strand_rnafold_calibration_v1` is the gating requirement before it is used for anything.** Needed: sequence/family-separated records with measured in-solution half-life that are not from the released STRAND tables, plus accuracy by length and by construct family against native controls. Until that exists the model stays a named candidate and scoring stays disabled. No such dataset is currently in the workspace; acquiring one is the real blocker, not more fitting.
2. **Do not open a scoring path opportunistically.** `replay_reference` must keep rejecting non-released feature sources. If a scoring path is ever added for this model it needs its own adapter, its own versioned contract and item 1 completed first.
3. **V13 item 2** (unstarted): versioned score records binding sequence/annotation/tool/settings/weight identities, units or target scale, exclusion reason and raw artifact paths; select the RiboNN named task and the stability/translation floor for the intended assay with supporting evidence. This is now the most useful next build, because it is the piece that would let a STRAND-side and a RiboNN-side score be recorded comparably.
4. **V13 item 3** (unstarted): Stage 2 independent/native/resource/constraint/replay requirements, especially sparse 2,000–2,999 nt coverage. Only after explicit gate review should parents/allowed edits, biological objective, budgets and the cell-free assay protocol be frozen. Keep BO/random/greedy feasibility and evaluation budgets matched.
5. **Optional**: publish V1 and V2 criteria, modules, scripts, tests and concise run evidence to GitHub. Not done. If done, fetch latest upstream first and preserve the repository README diagram `diagram_10182026.png` and its Markdown, per the standing rule. Note the v1 run's `per_record_features.json` is 2.08 MB and its `folds/` hold full probability arrays; publish concise summaries, not the arrays.

Do not infer expression benefit from software execution, and do not optimize actual expression candidates while the Stage 2 gate stays open. No combined biologically validated candidate-scoring command exists yet.

## Outstanding processes

None. Both R fits exited; total R time under 0.5 s. No background job, partial run or pending approval remains from this session. Other system processes were not exhaustively audited.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-19_V2.md
cat reports/RNA-StableAI_HANDOFF_2026-10-19_V1.md
cat reports/RNA-StableAI_HANDOFF_2026-10-18_V13.md
cat configs/strand_rnafold_calibration_criterion_v2_2026-10-19.json
cat configs/strand_rnafold_agreement_criterion_v1_2026-10-19.json
cat configs/stage2_to_stage3_gate_2026-10-18.json

# This session's result, cheapest first:
cat results/strand_rnafold_calibration_runs/20261019T174049.053308Z/summary.json
cat results/strand_rnafold_calibration_runs/20261019T174049.053308Z/calibration_model.json
PYTHONPATH=src:scripts .venv/bin/python scripts/fit_strand_rnafold_calibration.py \
  --verify-run results/strand_rnafold_calibration_runs/20261019T174049.053308Z

# V1 engine-agreement result:
PYTHONPATH=src:scripts .venv/bin/python scripts/audit_strand_rnafold_agreement.py \
  --verify-run results/strand_rnafold_agreement_runs/20261019T172402.804593Z

# Earlier canonical local artifact/cached checks, unchanged from V13:
PYTHONPATH=src .venv/bin/python scripts/verify_four_component_build.py results/four_component_build_runs/20261019T041458.024816Z
PYTHONPATH=src .venv/bin/python scripts/reproduce_strand_reference.py --verify-run results/strand_reference_reproduction_runs/20261019T042427.196161Z
PYTHONPATH=src .venv/bin/python scripts/run_ribonn_fixed_inference.py --verify-run results/ribonn_fixed_inference_runs/20261019T045101.117038Z
```

Focused suite, 130 tests, no new fit:

```bash
cd /home/zyliu/Documents/rna-stable-ai
PYTHONPATH=external/four_component_deps:src:scripts .venv/bin/python -m pytest -q \
  tests/test_strand_agreement.py tests/test_strand_rnafold_calibration.py \
  tests/test_component_integration.py tests/test_discrete_bo.py \
  tests/test_strand_reference.py tests/test_ribonn_integration.py tests/test_crw_panel_exposure.py \
  tests/test_crw_original_provenance.py tests/test_rcsb_long_source_survey.py tests/test_project_scope.py \
  tests/test_stage2_scope_audit.py tests/test_endpoint_ranking.py tests/test_hard_negative_supervision.py \
  tests/test_recovery_ceiling.py tests/test_endpoint_assignment.py tests/test_sampled_pair_supervision.py \
  tests/test_long_exact_sparse_pairs.py
```

Refitting from scratch creates a **new** timestamped run directory, reuses the stored v1 folds without refolding, and needs the isolated `external/strand-r/`:

```bash
cd /home/zyliu/Documents/rna-stable-ai
PYTHONPATH=src:scripts .venv/bin/python scripts/fit_strand_rnafold_calibration.py
```

Re-running the v1 agreement audit instead refolds all 91 records, about 245 s, and needs `external/four_component_deps` on `PYTHONPATH` for ViennaRNA:

```bash
cd /home/zyliu/Documents/rna-stable-ai
PYTHONPATH=external/four_component_deps:src:scripts .venv/bin/python scripts/audit_strand_rnafold_agreement.py
```

Both criterion files are frozen; do not edit either to change an outcome. A different feature set, arm rule or acceptance bar requires a new versioned criterion file and a new run. Fresh STRAND reference refit and RiboNN inference commands remain in V12/V11 and the integration guide and need the retained local sources, weights and environments. Do not pass concise published summaries as full local runs. Preserve all previous versioned handoffs.
