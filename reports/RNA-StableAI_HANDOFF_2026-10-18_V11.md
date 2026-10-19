# RNA-StableAI handoff — 2026-10-18 V11

Project: **RNA-StableAI**  
Date: **2026-10-18, America/Los_Angeles**  
Version: **V11**  
Workspace: **`/home/zyliu/Documents/rna-stable-ai`**  
Plan: **RNAfold + STRAND + RiboNN + BoTorch**  
Previous integration record: [V10](RNA-StableAI_HANDOFF_2026-10-18_V10.md). Architecture plan: [V9](RNA-StableAI_HANDOFF_2026-10-18_V9.md). Historical science/publication: [V7](RNA-StableAI_HANDOFF_2026-10-18_V7.md), [V8](RNA-StableAI_HANDOFF_2026-10-18_V8.md).

## Current intent, completed milestone and decisions

The user approved the stated next task: reproduce STRAND's reference fit in an isolated R environment, resolve component selection, export verified coefficients/predictions, and check compatibility with RNAfold features. **That reference-reproduction milestone is complete.** A full combined pipeline is still pending: RiboNN pretrained inference is not installed or run, and new-sequence stability scoring is disabled pending extraction compatibility/calibration review.

Key new decision: the archived article methods identify **LinearPartition** as the feature engine; RNAfold was used for visualization. Therefore RNAfold outputs cannot silently inherit the unchanged STRAND model identity. Keep RNAfold as the selected structure engine, retain both energy hypotheses, and use a reference-only STRAND scoring contract for now. Six fixed-input diagnostics support ensemble energy as the closer match to the released energy column; they do not establish unrestricted feature substitution validity. Original LinearPartition version, beam and parameterization remain unknown.

Active length scope is **1–2,999 nt**, no truncation and no implicit exclusion of supplied transcript tails. Valid annotated coding-transcript workflows are a narrower subset. Preserve all historical 3,000+ nt artifacts and frozen studies. [Scope](../configs/project_scope_2026-10-18.json) and [Stage 2 transition gate](../configs/stage2_to_stage3_gate_2026-10-18.json) are unchanged. Stage 2 remains open; cell-free expression Stage 3 remains queued. No expression candidates, assay, biological intervention, architecture default promotion, or publication occurred.

The gate still needs independent sequence/family/clan-separated validation, accuracy/failures by length and family against native controls, review of native gaps, resolution of sparse 2,000–2,999 nt evidence, constraints/decoder/resource/replay checks and documented limitations. No quantitative acceptance threshold or translation floor has been invented. Existing exposed studies do not become independent validation. Future objective remains predicted stability subject to a prespecified translation floor and hard annotated-transcript constraints; those application-specific settings remain pending.

## New files and purpose

- [`scripts/reproduce_strand_reference.R`](../scripts/reproduce_strand_reference.R): numerical reference extraction and scaled kernel PLS fit without plotting dependencies; all component models, training/LOO/validation outputs, PRESS and selection policies retained. Executes the exact whitelisted upstream fit/selection expressions as a separate parity check. Saves RDS models and raw-unit coefficient exports.
- [`scripts/replay_strand_reference.R`](../scripts/replay_strand_reference.R): saved-model inference replay without refitting; checks cached LOO outputs separately.
- [`scripts/reproduce_strand_reference.py`](../scripts/reproduce_strand_reference.py): pinned-source validation, run freezing, full R environment export, two fits, cross-language checks, reference whitelist model export, six-input native folding diagnostic, artifact manifest, `--verify-run` replay.
- [`scripts/acquire_strand_methods.py`](../scripts/acquire_strand_methods.py): bounds and archives open-access Europe PMC article XML with source URL and SHA-256; does not alter earlier upstream snapshots.
- [`src/rnastable/strand_reference.py`](../src/rnastable/strand_reference.py): exact released reference features and hashes, named raw-unit linear prediction arithmetic, reference-only replay rejecting wrong extraction engine or any unlisted identity/value changes. No new-sequence score API is enabled.
- [`configs/strand_reference_reproduction_v1_2026-10-18.json`](../configs/strand_reference_reproduction_v1_2026-10-18.json): immutable run protocol for source/runtime, cohorts, training-only selection, numerical tolerances, fit repeats and fixed diagnostic panel; explicit disabled expression/new-sequence scoring flags.
- [`tests/test_strand_reference.py`](../tests/test_strand_reference.py): R-derived cross-language prediction fixture, units, row/sequence/context/provenance guards and malformed-length rejection.
- [`tests/fixtures/strand_reference_r_export_2026-10-18.json`](../tests/fixtures/strand_reference_r_export_2026-10-18.json), [provenance](../tests/fixtures/strand_reference_r_export_2026-10-18_PROVENANCE.md): portable selected R coefficients and three feature/prediction examples, without depending on ignored run sources for ordinary unit tests. Three already released target values are carried only as context; scoring does not use them.
- [`strand_reference_reproduction_review_2026-10-18.md`](strand_reference_reproduction_review_2026-10-18.md): scientific interpretation, full selected-model metric table, exact coefficient equation, extraction findings and continuation.
- [`strand-reference-focused-tests-2026-10-18.log`](strand-reference-focused-tests-2026-10-18.log) and [`strand-reference-replay-checks-2026-10-18.log`](strand-reference-replay-checks-2026-10-18.log): actual test/replay outcomes. The test log explicitly records the terminal result from session 52550 rather than pretending it is a fresh test invocation.
- [`docs/four_component_integration_2026-10-18.md`](../docs/four_component_integration_2026-10-18.md): appended current STRAND milestone and replay commands; earlier build description remains historical.

Original integration modules, the earlier build driver/config, scope/gate, old scientific sources and frozen results remain unchanged. README was not edited. New files are local/unpublished; no index staging, commit or push was performed.

## Pinned sources and isolated runtime

STRAND author repository **S00NYI/BITS_STRAND**, commit **ea9e7de635e7cf4053c676c495b8e65717369206**. Pinned source manifest `results/four_component_source_runs/20261019T040820.389955Z/manifest.json`, SHA-256 **5cb505276eeb7dd738cb804eddeae873e7bee9b537e00d6e343ca336f84e3cc3**. All 18 inventory files were rechecked. Inputs for this task are its `strand/Data/nluc_cleaned_new_final.csv`, `strand/Data/validate_cleaned_new_final.csv` and `strand/Figure_Scripts_1.R`. Raw upstream files remain unchanged and local; the MIT repository license remains alongside them.

Article methods source: [Europe PMC full text XML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13264031/fullTextXML), DOI [10.1016/j.omtn.2026.102960](https://doi.org/10.1016/j.omtn.2026.102960). Archive **`results/strand_methods_source_runs/20261019T042128.056915Z/article.xml`**, SHA-256 **`66c049a31894926d94bba29998582898fc7ec7617f95bbfbda93775a163df82f`**, manifest **`results/strand_methods_source_runs/20261019T042128.056915Z/manifest.json`**, SHA-256 **`ec3804d3ef34dbff130e78f01de060566dafba0ef4750f9b53d84aa0a96978f2`**. The inspected methods identify LinearPartition, summed positional pairing probabilities, scaled R PLS and training LOOCV; they report R 4.4.0. Exact historical package/engine settings are not supplied. This is a numerical source-code reproduction under recorded versions, not a claim of the identical author environment.

New isolated environment **`external/strand-r/`**: **R 4.5.3, pls 2.8.5, jsonlite 2.0.0**, conda-forge. Created with:

```bash
/home/zyliu/anaconda3/bin/conda create --prefix /home/zyliu/Documents/rna-stable-ai/external/strand-r --override-channels -c conda-forge r-base=4.5 r-pls=2.8 r-jsonlite --yes
```

The resolved **91-package** explicit URL/build lock is in canonical run `conda_explicit.txt`; full installed package metadata with original package archive hashes is in `conda_package_metadata.json`. Conda cache downloads were approved; no original `.venv` dependency was replaced. The R environment occupies a separate ignored project path. Core Python/ViennaRNA runtime remains Python 3.12.14 / ViennaRNA 2.7.2 / NumPy 2.5.3; earlier BoTorch dependencies remain separately enabled via `PYTHONPATH=external/four_component_deps:src`.

## Frozen reproduction protocol, inventories and exposure

Canonical run: **`results/strand_reference_reproduction_runs/20261019T042427.196161Z/`**. Frozen protocol `protocol.json`; code and hashes `source/` and `identity.json`; source manifest copies `source_manifest.json` and `methods_manifest.json`; archived `article.xml`; run-wide checksums `manifest.json`.

Training: all **69** released nLuc records in their supplied order, 928–984 nt, with no outcome-based exclusions. Validation: all **13** `CDS (eGFP) variants` rows from the released validation CSV, 1,155–1,215 nt. Exploratory: **nine** MEV rows, 504–507 nt, from that same validation CSV. They are not the distinct separate MEV table used in a later upstream figure, which was not acquired/refit here. Exact ordered feature/sequence hashes and target values are in **`reference_inventory.json`**; R feature tables are `fit/r_train_features.csv`, `fit/r_egfp_features.csv` and `fit/r_mev_features.csv`. These are already released/exposed records. The eGFP set is held out from this nLuc fit but is not a new independent project test. Training/source overlap with earlier degradation studies or eventual RiboNN inputs remains to be audited.

Feature order: **energy_per_length, GC, aup, alo**. Energy is the released energy column divided by actual supplied length; GC is supplied **percent**, AUP is supplied fraction. ALO reproduces R natural log odds after replacing all values <=0 by 1e-10 and >=1 by 1-1e-10; positive values <1e-10 remain unchanged. Original out-of-range positional values remain in source data, never silently deleted. The prior inventory found 334 such positions in 43 nLuc rows. Python and R independently reconstruct features for cross-language comparison.

Models: **kernelpls**, centered/scaled predictors, target in **hours**, full component paths (three without ALO and four with ALO), deterministic **leave-one-out** CV. No stochastic split/seed, optimizer learning rate, neural loss or GPU is applicable. Freeze selection **before evaluation** as `which.min(apply(fit$validation$PRESS,2,mean))`, first minimum on ties, nLuc training outcomes only. No eGFP/MEV tuning. Two full fit invocations, `fit/` and `fit_repeat1/`, ran in UTC with `OPENBLAS_NUM_THREADS=1`; measured runtimes **0.861589 s** and **0.870855 s**. R process peak RSS was not measured.

The exact source expressions executed for parity are baseline lines **610–613, 631–635**, four-feature lines **678–681, 699–703**. Their coefficient and selected eGFP prediction differences versus the reproduction are **zero** under this environment. The source displays one-component training predictions with ALO and three without; later validation uses two components. Preserve those distinct policies; do not claim one uniform upstream component count. Training-only selection chooses **without ALO: one component; with ALO: two**.

PRESS (nLuc LOO SSE by increasing components):

- Without ALO: **[5.9203508507177425, 6.086208236165378, 6.342453482288674]**.
- With ALO: **[6.151910675176461, 6.106821572832575, 6.189928639859227, 6.4167881222284]**.

Selected raw-unit coefficient export `reference_model.json`, SHA-256 **`660d07587f0c906fa3eb3663ee9ca8ccb4affaac541d67b85bd434da5018d354`**:

```text
half_life_hours = -0.16879280662927765
  - 0.7979700541988914 * energy_per_length
  + 0.02653795111985797 * GC_percent
  - 1.0239404489087613 * AUP
  - 0.016562821266091512 * ALO
```

R `coef.mvr` slopes operate on X divided by the stored scale; divide each exported slope by `fit$scale` exactly once for raw features. The exported intercept already accounts for centering. Raw X means/scales, scaled means, Y mean, all component coefficients and method are in **`fit/r_models.json`**. Binary fitted objects: **`fit/with_alo_model.rds`** and **`fit/without_alo_model.rds`**. All native predictions, including cached held-out LOO arrays: **`fit/r_predictions.csv`**. Selected-model Python replay: **`python_reference_predictions.json`**. No clipping of predictions or target transforms were introduced.

## Measured reference results

| Cohort | Arm | Components | N | RMSE h | MAE h | R² |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| train | without_alo | 1 | 69 | 0.282382920658 | 0.236402186113 | 0.311919153021 |
| train | with_alo | 2 | 69 | 0.280334208892 | 0.230370896534 | 0.321867103508 |
| train_loo | without_alo | 1 | 69 | 0.292920102148 | 0.244732121149 | 0.259609271796 |
| train_loo | with_alo | 2 | 69 | 0.297497328519 | 0.242988036927 | 0.236289506259 |
| egfp | without_alo | 1 | 13 | 0.217427966666 | 0.177115445251 | 0.349878486921 |
| egfp | with_alo | 2 | 13 | 0.189321884880 | 0.165062753523 | 0.507092566456 |
| mev_exploratory | without_alo | 1 | 9 | 2.207148606268 | 2.175971894355 | -30.687470534894 |
| mev_exploratory | with_alo | 2 | 9 | 2.187611339397 | 2.155888926935 | -30.128970262385 |

The selected four-feature model improves eGFP RMSE relative to the selected three-feature model, but has slightly worse selected nLuc LOO RMSE. Exploratory MEV transfer is poor for both. Report these regressions rather than inferring universal ALO benefit. These are source-data reproduction numbers, not a new independent biological validation result. LOO also selects the component count; its reported error is not a nested evaluation of the whole selection procedure. No expression/stability candidate improvement is established.

## RNAfold feature compatibility diagnostic

Panel frozen before folding: **X320004D1, X310336T3, X310003T1** (first/middle/last nLuc rows), **X130010D1, X130002D1, X130006D1** (first/middle/last eGFP rows). No sequence edits, design search or CDS annotations were invented. These are fixed unannotated inputs for a structure-feature comparison, not RiboNN inputs. Raw fold arrays/settings/hashes are in **`rnafold_{name}.json`**; comparison inventory and all deltas are in **`rnafold_compatibility.json`**.

ViennaRNA 2.7.2, 37 °C, explicitly loaded/hashes Turner2004 parameters, dangles2, min loop3, unrestricted pair span, MFE rescaling then PF, no structure constraints. Same immutable ensemble worker as V10. Each subprocess has a 120-second timeout; no OS memory cap, GPU run or worst-case runtime claim. Worker folding time excludes import/startup; wall time includes it. Linux post-exec VmHWM is the worker memory measure.

| Reference | nt | Worker fold s | Subprocess wall s | VmHWM KiB |
| --- | ---: | ---: | ---: | ---: |
| X320004D1 | 928 | 2.597502 | 2.672207 | 100616 |
| X310336T3 | 928 | 2.565362 | 2.641931 | 100636 |
| X310003T1 | 928 | 2.597816 | 2.672967 | 100616 |
| X130010D1 | 1215 | 4.937995 | 5.023455 | 147672 |
| X130002D1 | 1215 | 4.830053 | 4.913667 | 147712 |
| X130006D1 | 1215 | 4.922896 | 5.007943 | 147684 |

Across these six fixed cases, MFE energy-per-nt absolute gaps from released data reach **0.020549575543**, versus **0.000051666385** with ensemble energy. Maximum AUP gap **0.003090857493**; ALO gap **0.277052461624**. Small GC differences include supplied eGFP rounding. Largest absolute ensemble-substitution equation output shift **0.006669322054 h**. This is diagnostic arithmetic only, not an accepted stability prediction or calibrated uncertainty. Small shifts on six examples are not proof of model equivalence across the active length domain.

New-sequence scoring is therefore **disabled**. `replay_reference` checks sequence/name/cohort/source/feature hashes against the frozen reference inventory and rejects changed values or RNAfold feature provenance. The lower-level linear arithmetic helper exists for verification and explicitly labeled diagnostics; it must not be presented as a validated candidate scorer. A future RNAfold-derived model must have an explicit compatibility criterion or independently evaluated calibration and a distinct version/name if feature extraction changes.

## Verification performed, and what was not performed

- **36 focused tests passed in 1.69 s** across `test_strand_reference.py`, earlier integration/discrete BO, project scope and Stage 2 scope audit tests. Portable fixture was generated from actual R native predictions, not Python prediction code.
- Cross-language feature max absolute residual **4.6629367034256575e-15**; exported raw-unit prediction residual **5.329070518200751e-15**.
- Two fresh R fits: all component/selection exports equal and prediction/feature CSVs **byte-identical**. This is deterministic statistical refitting, not neural retraining.
- RDS replay plus cached LOO array check (no refit) max residual **5.551115123125783e-15**. Frozen replay source is used for RDS checks.
- **42 run artifacts** and **91 reference identities** verify. Canonical summary SHA-256 **`45c676301131bd5c66d88b0a81e8df879068ecc14214115e4e6bdf3ab9935669`**. A deliberately corrupted reference model in a temporary copied run was correctly rejected; canonical artifacts were untouched.
- Six actual new native MFE/PF inferences completed. No RiboNN checkpoint inference, new model weights, assay, candidate search, independent structure-validation campaign or full repository test suite was run.
- Final AST, R parse, Markdown links, JSON and prior integration-source preservation checks are performed after this file is written; completion response states any outstanding issue.

## Attempts, failures and historical preservation

- Browser access to PMC article routes hit a browser challenge. The approved Europe PMC XML acquisition succeeded and is archived. Initial sandbox DNS failure was retried with approved escalation. No source claim relies on an unreceived page.
- Environment resolution/install completed at `external/strand-r/`; the public latest pls manual reports a newer version, but this fit explicitly pins installed **2.8.5**. Do not claim either is the author's exact unknown package version. The paper's R 4.4.0 is also different from the recorded runtime.
- Initial exploratory fit at **`results/strand_reference_probe_runs/20261019T042136.727742Z/`** correctly fit/predicted but its coefficient metadata incorrectly labeled scaled slopes as raw. Do not use that probe export. The canonical run explicitly converts slopes and checks native prediction parity. A harmless timedatectl/system-bus warning in the first probe was avoided in later runs by setting TZ=UTC.
- A transient extra parenthesis in an intermediate R script revision was caught by R parsing and corrected before the canonical run. No canonical artifact uses that revision.
- Corrected exploratory fit **`results/strand_reference_probe_runs/coefficients_corrected/`** remains as a probe; the timestamped canonical run and hashes above supersede it.
- Earlier V10 source/build/weight metadata inventories, old partial attempts and all historical model studies remain in place. No old manifest-pinned module was edited. Existing original integration source files still must match their V10 run hashes.
- No task-owned compute process remains intentionally running. Environment install, source acquisition, fits, folds, test sessions and replay checks all completed. Other system processes were not exhaustively audited.

## Historical project state to carry forward

V10's working first-integration build remains **`results/four_component_build_runs/20261019T041458.024816Z/`**, summary hash **d898cfbc288bab7bd386e7dfe79f681280fb171941ff7ac763941e64ab2a01e2**. It verified fixed synthetic folds through 2,999 nt, with 64.644 s worker time and 721,996 KiB VmHWM for its longest example; toy BoTorch8-evaluation runs at seeds7/1729/20261015 and copied cached resume succeeded. This is mechanics evidence only, not independent biological performance.

Historical custom-structure baseline/assignment means (long/short) remain **0.3173511819/0.1560640870** and **0.3261881307/0.1606458705**. Native LinearFold **0.4381334451/0.3301074317**, ViennaRNA **0.4214700331/0.3346291106**. These are exposed development structure F1, not stability/translation scores, and were not remeasured here. Longer cohort has six references, only one in 2,000–2,999 nt; shorter cohort has13. Assignment short seed20261015 regresses; hard negatives regressed. Historical 103-record training/family/clan lineage and label-informed recovery oracles remain documented in V7/V10.

Retained exact custom-study anchors: baseline `results/under3000_development_protocol_runs/20261018T223802.654756Z/manifest.json`, run `results/under3000_development_runs/20261018T223810.974436Z/`; assignment protocol `results/under3000_endpoint_assignment_protocol_runs/20261018T234607.509040Z/manifest.json`, run `results/under3000_endpoint_assignment_runs/20261018T234628.064395Z/`. Assignment summary previously verified SHA-256 `d7ddf63c2adf0bfd02943c1f433868a104d97b6a3a21c00fbf9c65ce73a01609`; not rehashed this turn. Retained per-seed checkpoints and predictions remain in `assignment_seed{s}/final_model.pt`, `predictions.json`, `summary.json`. Historical seeds7/1729/20261015, ten epochs, Adam0.001 and exact sparse top32 decoder are unrelated to this deterministic PLS fit.

RiboNN source remains pinned to **dc896e1d1f78bf6b4e9bb7525c7852fcf25532e8** in Sanofi-Public/RiboNN. Its historical environment Python3.10.13/PyTorch1.13.1/lightning1.8.5 has not been set up. Weight archive metadata remains `results/ribonn_weight_inventory_runs/20261019T041243.650769Z/summary.json`: weights.zip207,395,960 bytes, upstream md5:dd088ee2feffcda6ce26124a471a140f. Actual bytes/checkpoint SHA-256 remain unacquired/unverified. Separate weight license restricts academic research/noncommercial use. Preserve correct CDS/UTRs, expected task/folds, ID/hash joins, exclusions and calibration limits before inference.

Last publication is still only **recorded** by V8 at commit **e1758333075e1c7eaaeea3d22c55d79d1d462c59**, isolated checkout `/tmp/rna-stable-ai-publish-20261018-stage2`; not remotely rechecked here. V9–current work remains local. The original workspace has extensive pre-existing staged/modified/untracked files and prior records state local main has no commits; do not bulk-stage or publish it. Before any future publication fetch the latest GitHub README, merge upstream edits and preserve the user's picture HTML and referenced assets. No live README fetch was required for this nonpublication task, and README was not written.

## Prioritized next work and exact continuation commands

1. **RiboNN isolated pretrained inference:** inspect pinned code/weight license, define an applicable named task/checkpoint/fold inventory, acquire/archive/checksum weights when proceeding, set up its isolated dependency environment, and replay fixed annotated inputs with explicit exclusions and ID/sequence matching. Use raw per-fold outputs before the default final aggregation, as described in V10. Never use the repository's fake training targets as measured data.
2. **RNAfold-to-STRAND compatibility:** retain ensemble energy as a supported hypothesis, not an approved replacement. Pin original LinearPartition extraction details if available; define a quantitative feature/score agreement criterion or separately named RNAfold-based calibration, fit on training data and evaluate on genuinely independent lineage-separated data. Do not tune on exposed eGFP references and relabel them independent.
3. **Stage 2 review:** resolve independent 2,000–2,999 nt evidence, accuracy/native/resource/constraints/replay criteria and limitations before actual expression candidate design. After gate closure, freeze parent/CDS/allowed edits, translation floor, assay target, budgets and controls for BO/random/greedy comparisons.

Read/replay existing artifacts without fitting:

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-18_V11.md
cat reports/strand_reference_reproduction_review_2026-10-18.md
cat configs/strand_reference_reproduction_v1_2026-10-18.json
cat configs/stage2_to_stage3_gate_2026-10-18.json
cat results/strand_reference_reproduction_runs/20261019T042427.196161Z/summary.json
PYTHONPATH=src .venv/bin/python scripts/reproduce_strand_reference.py --verify-run results/strand_reference_reproduction_runs/20261019T042427.196161Z
PYTHONPATH=external/four_component_deps:src .venv/bin/python -m pytest -q tests/test_strand_reference.py tests/test_component_integration.py tests/test_discrete_bo.py tests/test_project_scope.py tests/test_stage2_scope_audit.py
```

Fresh statistical refit and six native diagnostic folds (new unique run, no candidates):

```bash
cd /home/zyliu/Documents/rna-stable-ai
PYTHONPATH=src .venv/bin/python scripts/reproduce_strand_reference.py
```

Recreate the exact R environment into a **new** target if needed (network required; do not overwrite the working environment):

```bash
/home/zyliu/anaconda3/bin/conda create --prefix /home/zyliu/Documents/rna-stable-ai/external/strand-r-recreated --file /home/zyliu/Documents/rna-stable-ai/results/strand_reference_reproduction_runs/20261019T042427.196161Z/conda_explicit.txt --yes
```

The driver currently pins `external/strand-r/bin/Rscript`; a different environment path needs a separately versioned protocol, not mutation of a completed run. Refitting also needs the retained pinned upstream CSVs; artifact verification/RDS replay uses the saved feature tables and fitted objects.

Inspect RiboNN source and metadata before the next protocol:

```bash
cat results/four_component_source_runs/20261019T040820.389955Z/ribonn/environment.yml
cat 'results/four_component_source_runs/20261019T040820.389955Z/ribonn/MODEL WEIGHTS LICENSE.txt'
cat results/ribonn_weight_inventory_runs/20261019T041243.650769Z/summary.json
sed -n '163,198p' results/four_component_source_runs/20261019T040820.389955Z/ribonn/src/main.py
cat src/rnastable/component_integration.py
```

No combined RNAfold+STRAND+RiboNN candidate-scoring command is yet valid. Preserve canonical runs and earlier handoffs; use new output paths for new protocols and separate publication checkout when publishing is requested.
