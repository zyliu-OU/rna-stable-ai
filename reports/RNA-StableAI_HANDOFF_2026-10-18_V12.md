# RNA-StableAI handoff — 2026-10-18 V12

Project: **RNA-StableAI**  
Date: **2026-10-18, America/Los_Angeles**  
Version: **V12**  
Workspace: **`/home/zyliu/Documents/rna-stable-ai`**  
Selected architecture: **RNAfold + STRAND + RiboNN + BoTorch**  
Previous STRAND milestone: [V11](RNA-StableAI_HANDOFF_2026-10-18_V11.md). Integration mechanics: [V10](RNA-StableAI_HANDOFF_2026-10-18_V10.md). Architecture plan: [V9](RNA-StableAI_HANDOFF_2026-10-18_V9.md). Historical scientific/publication records: [V7](RNA-StableAI_HANDOFF_2026-10-18_V7.md), [V8](RNA-StableAI_HANDOFF_2026-10-18_V8.md).

## User priorities and completed milestone

The user said **“ok continue next”** after the STRAND reference milestone. The authorized next task was isolated **RiboNN pretrained inference**: acquire/verify the released archive, inventory named checkpoints and folds, execute fixed annotated inputs and verify replay, identity and exclusions. **This inference milestone is complete.** The full biological pipeline remains incomplete: RNAfold-to-STRAND compatibility/calibration and independent validation remain unresolved, and cell-free expression candidate design is still disabled.

RiboNN human inference now uses the original pinned model/data/predict code, released Python/PyTorch versions on CPU, verified tensor-only checkpoints, and the original top-five-per-fold ensemble. Two independent processes give identical raw arrays across **70 rows × 78 tasks**. A named HEK293T output is a software probe, not an application-specific cell-free translation objective. No tissue mean or guessed physical-unit conversion is used.

Current boundaries: **1–2,999 nt**, no truncation or hidden omission of supplied tail regions; explicit CDS/UTR annotations for coding workflows. Historical 3,000+ nt studies and all frozen artifacts remain preserved. [Scope](../configs/project_scope_2026-10-18.json) and [Stage 2 gate](../configs/stage2_to_stage3_gate_2026-10-18.json) are unchanged. Stage 2 stays open; Stage 3 targets cell-free expression and remains queued. Independent sequence/family/clan-separated validation, accuracy/failure reporting by length/family against native controls, sparse 2,000–2,999 nt evidence, constraints/resource/replay review and explicit limitations are still required. No numerical biological acceptance thresholds, translation floor or assay budget have been selected.

The RNAfold + STRAND + RiboNN + BoTorch direction still supersedes making another custom pair-loss sweep the default next task. Preserve old studies as controls. A future stability objective subject to a prespecified translation floor remains proposed, not frozen for candidate screening. Do not treat deterministic proxy optimization or successful checkpoint execution as biological evidence.

## New paths and changes

- [`scripts/acquire_ribonn_weights.py`](../scripts/acquire_ribonn_weights.py): bounded archive download, pinned length/MD5/SHA-256 checks, safe ZIP extraction and full file inventory. Preserves original weight license; does not deserialize weights.
- [`scripts/ribonn_inference_worker.py`](../scripts/ribonn_inference_worker.py): isolated upstream CPU inference, exact checkpoint order/architecture/weight checks, independent encoding comparison, raw per-fold outputs, runtime/config/resources and full task inventory. Wraps only torch.load for audited CPU tensor-only loading.
- [`scripts/run_ribonn_fixed_inference.py`](../scripts/run_ribonn_fixed_inference.py): source/weight checks, frozen input and checkpoint inventories, isolated source workspace, two fresh inference processes, exact all-task replay, named-task identity/fold join, explicit exclusions, artifact manifest and `--verify-run` cached verification.
- [`src/rnastable/ribonn_integration.py`](../src/rnastable/ribonn_integration.py): top-k per-fold checkpoint selection guards, weight integrity checks, exact keyed prediction replay.
- [`configs/ribonn_fixed_inference_v1_2026-10-18.json`](../configs/ribonn_fixed_inference_v1_2026-10-18.json): pinned source/weight/runtime, named task, ten folds/five checkpoints, batch/thread limits and fixed input/control protocol. No design/calibration/Stage 3 permission is enabled.
- [`tests/test_ribonn_integration.py`](../tests/test_ribonn_integration.py): per-fold selection, ambiguous/incomplete/unsafe inventory rejection, replay identity/score/dropout guards, weight path/length/hash corruption checks.
- [`ribonn_checkpoint_inventory_2026-10-18.json`](ribonn_checkpoint_inventory_2026-10-18.json): concise selected model IDs, exact paths, hashes, validation R², archive/license identity and replay result.
- [`ribonn_fixed_inference_review_2026-10-18.md`](ribonn_fixed_inference_review_2026-10-18.md): runtime/protocol, output and resource tables, exact limitations and safe commands.
- [`ribonn-fixed-inference-focused-tests-2026-10-18.log`](ribonn-fixed-inference-focused-tests-2026-10-18.log), [`ribonn-fixed-inference-replay-checks-2026-10-18.log`](ribonn-fixed-inference-replay-checks-2026-10-18.log): actual test, artifact and corruption-check evidence. Test log explicitly records the terminal output of executed session94084 rather than claiming a new invocation.
- [`docs/four_component_integration_2026-10-18.md`](../docs/four_component_integration_2026-10-18.md): appended current RiboNN milestone and commands, preserving earlier milestones.

No historical scientific module, original integration contract, source snapshot, model checkpoint, scope/gate or README was edited. No original .venv packages were replaced. All changes are local and unpublished; no original-index staging, commit or push occurred.

## Pinned source and verified archive

Author source **Sanofi-Public/RiboNN**, commit **dc896e1d1f78bf6b4e9bb7525c7852fcf25532e8**; snapshot `results/four_component_source_runs/20261019T040820.389955Z/ribonn/`. Original manifest `results/four_component_source_runs/20261019T040820.389955Z/manifest.json`, SHA-256 **5cb505276eeb7dd738cb804eddeae873e7bee9b537e00d6e343ca336f84e3cc3**. All 18 combined inventory source files were rehashed. Model/data/predict/helper files copied into the inference workspace are byte-identical. Empty Python package marker files were created locally to make source imports unambiguous; their bytes are recorded in the run manifest. No upstream main/training program was invoked.

Pinned weight metadata came from **Zenodo record17258709**. Actual download URL: `https://zenodo.org/api/records/17258709/files/weights.zip/content`.

- Archive: **`results/ribonn_weight_acquisition_runs/20261019T044334.430330Z/weights.zip`**.
- Size: **207,395,960 bytes**, matched to original metadata.
- MD5: **dd088ee2feffcda6ce26124a471a140f**, matched to original metadata.
- Locally measured SHA-256: **2ce3bc1adb38ec6752c79147241a4fb2664e9804e806b3eab1287489a15d8b64**.
- Acquisition manifest: **`results/ribonn_weight_acquisition_runs/20261019T044334.430330Z/manifest.json`**, SHA-256 **d86d5b98beb39feffe90d8eebc41f0f5114bb8a417f4e07605bfc61335eea1a9**.
- Extraction: adjacent **`extracted/`**, with **90 human checkpoints, 90 mouse checkpoints and two runs.csv tables =182 files**. Every extracted file length and SHA-256 was verified. Mouse inference was not executed.
- Weight license: **`results/ribonn_weight_acquisition_runs/20261019T044334.430330Z/MODEL WEIGHTS LICENSE.txt`**, SHA-256 **ce6b253151d10e66606a52a1c99ac08854051d912f01ad1d01331941310cc49b**. Original text is also preserved in the pinned source and inference workspace. It restricts use to academic research and noncommercial purposes, separately from source-code license. Weights remain ignored local research artifacts; none was published.

No source archive code from Zenodo's separate RiboNN-1.0.0.zip was downloaded; the exact inference code is the pinned GitHub snapshot. Strict state-dictionary loading and the successful actual output replay demonstrate compatibility with that source/runtime, not parity with an unavailable external published golden prediction array.

## Isolated environment and compatibility fix

Environment: **`external/ribonn-inference/`**. Exact **75-package** URL/build lock in canonical run **`conda_explicit.txt`**, full installed metadata including package archive hashes in **`conda_package_metadata.json`**. Actual versions:

- Python **3.10.13**.
- PyTorch **1.13.1**, CPU build `py3.10_cpu_0`; no CUDA available.
- NumPy **1.22.4**, pandas **2.2.3**, SciPy **1.13.1**, scikit-learn **1.0.2**.
- pytorch-lightning **1.8.5**, torchmetrics **1.3.1**, lightning-utilities **0.10.1**.
- setuptools **81.0.0**, PyYAML installed by recorded environment.
- **MKL2023.2.0**, TBB2021.13.0 and compatible BLAS3.9 builds, as frozen in the exact lock.

The released environment's CUDA11.3/cuDNN stack is intentionally replaced with CPU PyTorch for this inference-only protocol. MLflow training logging was not required/imported via main, and was not installed. GPU inference/parity and original training were not tested. The original project Python3.12/torch2.14.1 environment, isolated R environment and BoTorch target packages remain separate.

Commands actually run to create/fix the environment:

```bash
/home/zyliu/anaconda3/bin/conda create --prefix /home/zyliu/Documents/rna-stable-ai/external/ribonn-inference --override-channels -c conda-forge -c pytorch python=3.10.13 'pytorch::pytorch=1.13.1=py3.10_cpu_0' cpuonly numpy=1.22.4 pandas=2.2.3 scipy scikit-learn=1.0.2 pytorch-lightning=1.8.5 torchmetrics=1.3.1 lightning-utilities=0.10.1 pyyaml 'setuptools<82' --yes --quiet
/home/zyliu/anaconda3/bin/conda install --prefix /home/zyliu/Documents/rna-stable-ai/external/ribonn-inference --override-channels -c conda-forge -c pytorch 'mkl<2024' 'pytorch::pytorch=1.13.1=py3.10_cpu_0' --yes --quiet
```

Initial MKL2026.1.0 resolution caused actual torch import error **undefined symbol: iJIT_NotifyEvent**. The second command resolved it; subsequent exact-version imports and full inference passed. A pkg_resources deprecation warning remains logged; it did not prevent inference. Do not infer original-environment breakage from this isolated setup issue.

## Frozen inference protocol, weights and inputs

Canonical successful run: **`results/ribonn_fixed_inference_runs/20261019T045101.117038Z/`**. Summary SHA-256 **`deca964a5d5ba53d85a989067ef484d2775cb55502c2d62b540b22699ca6306c`**. Exact protocol `protocol.json`, source hashes in `identity.json`, implementation copies in `source/`, all artifact hashes in `manifest.json`. Retained exact source/weight manifests are `source_manifest.json`, `weight_manifest.json`.

Checkpoint policy: **human**, folds **0–9**, **top five per fold by released metrics.val_r2 descending**, applied to the 90-row human `runs.csv`. All selected and boundary ties are rejected. The independent inventory agrees exactly with original pandas selection and actual checkpoint load order. No current input prediction/outcome was used for selection. Full selected 50 identities, per-model validation scores, byte sizes, exact checkpoint paths and SHA-256 are in **`checkpoint_inventory.json`** and the linked tracked inventory. Actual loaded state dictionaries are recorded under each inference summary; original files remain unmodified.

Checkpoint shape/config verification: ReLU, ten middle convolution blocks, filters64, kernel5, stride1, padding0, dilation1, ln_epsilon0.007, dropout0.3, no residual, len_after_conv9, **78 output targets**, five input channels (four nucleotides plus CDS markers), pad_5_prime true, label_codons true, other region/splice/probability labels false, label_3rd_nt false, with_NAs true (historical loss setting), max_shift **0**. A selected model has49 state tensors and250,511 parameter/buffer elements. Architecture-relevant config matches for all50 models; model.load_state_dict remains strict.

CPU inference adjustment: wrapper requires a pinned path/hash and calls the original torch.load with **map_location=cpu, weights_only=True**. Only tensor dictionaries with string keys are accepted. Model classes, weights, forward passes, original data preprocessing and checkpoint mean operations are unchanged. No precision/autocast alteration, fine-tuning, learning rate or loss optimization was applied. Workers use **two CPU threads, one interop thread, batch2, zero DataLoader workers, deterministic algorithms, eval mode and no gradients**. No random seed is needed for zero-shift/eval fixed-state inference; actual fresh-process replay was verified. Do not confuse the historical training hyperparameters in metadata with training done this turn.

Input inventory: **`input_inventory.json`**, complete sequence, CDS start/end, context, provenance, sequence SHA-256 and annotation/context SHA-256. Reuse the V10 fixed synthetic panel from `results/four_component_build_runs/20261019T041458.024816Z/fixed_inputs.json` after verifying its manifest hash. Those five sequences were generated at seed1729 at lengths64/400/1000/2000/2999, before any RiboNN score. Add only fixed software controls: empty UTRs, exactly1381-nt 5′ UTR and over-limit1382-nt 5′ UTR. No observed target values or designed biological candidate panel is present.

`validated_input.tsv` explicitly omits the excluded control; **`upstream_input.tsv`** includes all8 in-scope inputs so native filtering is actually tested. Upstream filters the 1382-nt control and retains seven. Complete sequence length cap applies before adapter-specific UTR limits. Full-transcript input avoids missing-value interpretation of empty UTR columns. Each accepted input is independently encoded as **5 × 13,318** with nucleotide channel order **A,T,C,G**, CDS first-base markers (including the stop codon), start aligned to offset1381. Independent encoded tensors equal upstream exactly, with hashes/counts in **`inference_*/encoding_audit.json`**. No CDS boundary, cap, tail or modified base is silently invented or omitted.

Named task: **predicted_TE_HEK293T**, explicitly frozen as a software-replay output, not selected as a cell-free experimental objective. The released routine averages five checkpoints within each fold and returns raw per-fold rows for all78 outputs. We then join by ID and sequence and average the ten verified values for this named task. No row-position join and no cross-tissue average. Raw output must carry all expected folds exactly once per accepted input; unexpected/duplicate/missing/nonfinite/wrong-sequence rows fail. Reversing raw row order preserves folds/means within numerical summation tolerance.

## Actual outputs and measured resources

| Input | Full nt | CDS start | CDS end | Status | Mean released-task score / reason |
| --- | ---: | ---: | ---: | --- | --- |
| fixed_synthetic_64 | 64 | 12 | 57 | ok | 1.691883635520935 |
| fixed_synthetic_400 | 400 | 12 | 393 | ok | 1.0533050537109374 |
| fixed_synthetic_1000 | 1000 | 12 | 993 | ok | 0.34637500792741777 |
| fixed_synthetic_2000 | 2000 | 12 | 1992 | ok | 0.02124803075566888 |
| fixed_synthetic_2999 | 2999 | 12 | 2991 | ok | -0.14130756631493568 |
| ribonn_empty_UTRs | 9 | 0 | 9 | ok | 1.692789363861084 |
| ribonn_utr5_1381 | 1390 | 1381 | 1390 | ok | 1.4407749772071838 |
| ribonn_utr5_1382 | 1391 | 1382 | 1391 | excluded | utr5_exceeds_1381_nt |

These **are not physical protein yields or validated cell-free translation efficiencies**. No inverse transform was inferred; scores stay on the released model target scale. Negative values are retained as valid model-scale numbers, not clipped or reinterpreted. Synthetic tiny/empty-UTR inputs establish execution/annotation handling only, not biological domain validity. Training overlap, biological accuracy and calibration were not evaluated.

Each process produces **70 rows** (7 accepted transcripts ×10 folds) and78 output columns =**5,460 score values**. All78 tasks match exactly across processes, and the entire raw TSV files are **byte-identical**. Selected task maximum replay difference **0.0**. Joined output has seven accepted records and one explicit excluded record.

| Process | Upstream inference s | Full subprocess wall s | Peak worker VmHWM KiB |
| ---: | ---: | ---: | ---: |
| 0 | 12.992448 | 16.263913 | 382704 |
| 1 | 12.641503 | 14.945671 | 377160 |

Measurement is CPU worker post-exec Linux VmHWM; no GPU measurement or worst-case claim. Worker timeout is1800s, with no OS memory cap enforced. This workload is fixed and small. Actual prediction arrays are **`inference_0/raw_fold_predictions.tsv`**, **`inference_1/raw_fold_predictions.tsv`**. Joined task output **`joined_predictions.json`**; exclusions **`expected_exclusions.json`**; worker logs **`worker_0.log`**, **`worker_1.log`**; effective metadata and loaded model order under each **`inference_*/summary.json`** and **`effective_config.json`**. Unused nonfinite legacy metadata is tagged explicitly for JSON audit without changing inference config values.

The source workspace **`upstream_workspace/`** contains unchanged snapshot files and licenses; its **`models` symlink** points to the retained archive extraction. The49-artifact manifest does not traverse/duplicate the raw external model tree. Fresh replay requires that retained weight/source environment state; cached artifact verification needs the saved raw outputs and inventory. Do not claim the run alone is a complete portable weight distribution.

## Verification, failures and what was not done

- **50 focused tests passed in3.38s** across new checkpoint/replay tests and prior component, STRAND, BO, project-scope and Stage2 tests. Exact command and terminal result are recorded in the linked log. No full repository suite was run.
- Two fresh worker processes each loaded all50 selected checkpoints and generated predictions, so this is actual **pretrained neural inference replay**, not merely cache loading. No retraining or transfer learning occurred.
- All182 weight extraction files were verified against their acquisition inventory; actual download length/MD5 matched pinned upstream metadata, SHA-256 measured locally. Every selected checkpoint was rehashed at actual torch.load.
- **49 run artifacts** and8 transcript sequence/annotation identities verified; cached output replay and named join reproduced. A modified joined-output file in a temporary copied run was correctly rejected; canonical results/weights stayed untouched.
- Empty UTR and exact1381-nt boundary were actually accepted; native1382-nt control actually excluded. Independent encoded channels match all accepted upstream tensors. Duplicate/lost/wrong-sequence/nonfinite row and ambiguous-checkpoint guards pass unit tests.
- Initial acquisition attempt **`results/ribonn_weight_acquisition_runs/20261019T044229.160581Z/`** failed under sandbox DNS restriction and retains its license file only; approved retry at044334 completed. No partial archive is treated as verified.
- Initial inference run **`results/ribonn_fixed_inference_runs/20261019T045042.418182Z/`** failed **before model loading**: the independent check initially assumed A,C,G,T channels. The pinned code actually uses A,T,C,G. Corrected only the independent check, preserved upstream bytes, then started the new successful canonical run. Failed run/source/log remain in place; do not resume it or claim predictions for it.
- The publisher paper route on nature.com could not be retrieved by the browser tool. The pinned author README/code, release metadata and actual checkpoint execution support this software work. Task output physical units/cell-free applicability remain deliberately unasserted.
- Not run: mouse inference, GPU parity, external golden-array comparison, labeled accuracy/calibration, new training/optimizer experiment, RNA candidate selection, stability/translation combined objective, assay, independent Stage2 validation or publication.
- All task-owned acquisition, environment, inference, tests and replay sessions finished. Other system processes were not exhaustively audited.

## Carry-forward milestones and scientific limits

**STRAND:** canonical source reproduction **`results/strand_reference_reproduction_runs/20261019T042427.196161Z/`**, summary hash **45c676301131bd5c66d88b0a81e8df879068ecc14214115e4e6bdf3ab9935669**, selected reference model hash **660d07587f0c906fa3eb3663ee9ca8ccb4affaac541d67b85bd434da5018d354**. Under isolated R4.5.3/pls2.8.5/jsonlite2.0.0, 69nLuc training references selected2components withALO and1without, solely by nLuc LOO PRESS. Selected eGFP exposed-reference RMSE0.1893218848801146h vs0.2174279666658343h control; selected nLuc LOO slightly regressed0.2974973285188195 vs0.29292010214781455h. Nine exploratory MEV rows transferred poorly. These are exposed reference reproduction numbers, not new independent validation. R/Python predictions agree within6e-15; two fits' predictions were byte-identical.

The paper's original structural features are **LinearPartition**, not RNAfold; version/beam/parameters remain unpinned. Archived methods **`results/strand_methods_source_runs/20261019T042128.056915Z/article.xml`**. Six fixed diagnostics supported ensemble energy over MFE as the closer released energy mapping, but still showed AUP/ALO differences. Unrestricted new-sequence stability scoring remains disabled. Original released GC uses percent; derived ViennaRNA feature GC is a fraction and needs explicit conversion. Existing reference-only scoring rejects substituted extraction provenance. Do not label a new RNAfold-derived calibrated model unchanged published STRAND.

**First integration mechanics:** **`results/four_component_build_runs/20261019T041458.024816Z/`**, summary hash **d898cfbc288bab7bd386e7dfe79f681280fb171941ff7ac763941e64ab2a01e2**. Fixed synthetic MFE/PF through2999nt passed (64.644s and721,996KiB for its longest case), with three deterministic toy BO seed runs7/1729/20261015 at eight unique evaluations and copied cached resume. These are software mechanics, not optimization benefit or full-domain accuracy.

**Historical custom structure science:** baseline long/short pairF1 **0.3173511819/0.1560640870**, assignment **0.3261881307/0.1606458705**, LinearFold **0.4381334451/0.3301074317**, ViennaRNA **0.4214700331/0.3346291106**. Retained cohorts six longer and13shorter; only one reference is2000–2999nt. All are exposed development evidence with lineage/label limits, not stability/expression scores. Assignment short seed20261015 regressed, hard-negative study regressed, recovery oracles are label-informed bounds. These were not remeasured here.

Exact historical anchors remain baseline protocol/run **`results/under3000_development_protocol_runs/20261018T223802.654756Z/manifest.json`**, **`results/under3000_development_runs/20261018T223810.974436Z/`**; assignment protocol/run **`results/under3000_endpoint_assignment_protocol_runs/20261018T234607.509040Z/manifest.json`**, **`results/under3000_endpoint_assignment_runs/20261018T234628.064395Z/`**. Per-seed **`assignment_seed{s}/final_model.pt`**, **`predictions.json`**, **`summary.json`** remain local. Historical training was103references/ten epochs/Adam0.001 with exactsparse top32 decoder; unrelated to inference performed here.

**Publication/workspace:** no push or publication now. V8 still records last published commit **e1758333075e1c7eaaeea3d22c55d79d1d462c59** via **`/tmp/rna-stable-ai-publish-20261018-stage2`**; remote state was not rechecked. Original workspace has extensive pre-existing staged/modified/untracked state; do not bulk-stage it. V9–current implementation work remains local. Preserve every earlier handoff and manifest. Before any future publication fetch latest GitHub README and merge upstream edits/picture/assets. Last V8-verified picture HTML was `<img width="1774" height="887" alt="image" src="https://github.com/user-attachments/assets/4da2605a-3a6d-4130-9014-950dc75bd34d" />`; that historical tag is not a fresh verification of live upstream. README was not written this task.

## Next priorities and exact safe continuation

1. **Resolve RNAfold→STRAND feature compatibility or a separately named calibration.** Use the six fixed differences as diagnostic evidence only. Obtain original LinearPartition extraction settings if available; prespecify an agreement/calibration criterion and independent lineage-separated evaluation. Do not tune on exposed eGFP and call it independent. Preserve RNAfold as selected structural engine unless an explicit decision changes it.
2. **Connect versioned adapter score records** with explicit sequence/annotation/settings/weight identity, units/scale, status/exclusion and raw artifact paths. Reference-only STRAND remains gated; RiboNN named-task proxy is uncalibrated. Freeze an appropriate task and translation-floor policy only when there is evidence for the intended assay.
3. **Complete Stage2 gate evidence**, especially independent2000–2999nt coverage, native baseline comparisons and application-specific criteria. Only after explicit gate closure freeze actual parents/allowed edits, controls, evaluation budgets and cell-free assay protocol for candidate selection. BO/random/greedy must share feasibility and budget rules.

Read or verify existing state without checkpoint inference:

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-18_V12.md
cat reports/ribonn_fixed_inference_review_2026-10-18.md
cat configs/ribonn_fixed_inference_v1_2026-10-18.json
cat configs/stage2_to_stage3_gate_2026-10-18.json
PYTHONPATH=src .venv/bin/python scripts/run_ribonn_fixed_inference.py --verify-run results/ribonn_fixed_inference_runs/20261019T045101.117038Z
PYTHONPATH=src .venv/bin/python scripts/reproduce_strand_reference.py --verify-run results/strand_reference_reproduction_runs/20261019T042427.196161Z
PYTHONPATH=src .venv/bin/python scripts/verify_four_component_build.py results/four_component_build_runs/20261019T041458.024816Z
PYTHONPATH=external/four_component_deps:src .venv/bin/python -m pytest -q tests/test_ribonn_integration.py tests/test_component_integration.py tests/test_strand_reference.py tests/test_discrete_bo.py tests/test_project_scope.py tests/test_stage2_scope_audit.py
```

Fresh two-process pretrained replay, no training or candidate design:

```bash
cd /home/zyliu/Documents/rna-stable-ai
PYTHONPATH=src .venv/bin/python scripts/run_ribonn_fixed_inference.py
```

Recreate exact environment in a **new** target if needed (network required; do not overwrite the retained working environment):

```bash
/home/zyliu/anaconda3/bin/conda create --prefix /home/zyliu/Documents/rna-stable-ai/external/ribonn-inference-recreated --file /home/zyliu/Documents/rna-stable-ai/results/ribonn_fixed_inference_runs/20261019T045101.117038Z/conda_explicit.txt --yes
```

The driver pins `external/ribonn-inference/bin/python` and original source/weight manifests; using a different runtime path or task needs a new versioned protocol. A fresh inference run creates a new unique directory and requires the retained extraction and environment. Cached `--verify-run` does not load model weights or do new inference. Do not use failed run045042 as a resume target. Do not overwrite the completed canonical run or silently switch checkpoint ensembles.

No combined RNAfold+STRAND+RiboNN expression candidate-scoring command is approved/validated yet. Keep those gates explicit when wiring the score table, preserve old histories, and use an isolated publication checkout only when publication is requested.
