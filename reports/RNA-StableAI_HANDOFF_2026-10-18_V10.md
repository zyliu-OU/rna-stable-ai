# RNA-StableAI handoff — 2026-10-18 V10

Project: **RNA-StableAI**  
Date: **2026-10-18, America/Los_Angeles**  
Version: **V10**  
Workspace: **`/home/zyliu/Documents/rna-stable-ai`**  
Selected architecture: **RNAfold + STRAND + RiboNN + BoTorch**  
Previous canonical architecture plan: [V9](RNA-StableAI_HANDOFF_2026-10-18_V9.md). Publication record: [V8](RNA-StableAI_HANDOFF_2026-10-18_V8.md). Historical scientific detail: [V7](RNA-StableAI_HANDOFF_2026-10-18_V7.md).

## User intent, decisions and scope

The user first requested a handoff check, then explicitly said **“ok start the build for the plan.”** This authorizes implementation of the selected four-component architecture. This turn completes its first executable integration milestone: pinned source audit, fixed-input folding and contracts, and optimizer mechanics. **The complete combined scoring pipeline is not yet implemented.** No fitted STRAND stability predictions or RiboNN checkpoint predictions have been produced.

STRAND means the author project **S00NYI/BITS_STRAND**, Stability Regression Analysis using Nucleotide-Derived features, as recorded in V9. V9's architecture supersedes the older default proposal to run another custom pair-loss experiment. Preserve those studies as historical controls. RNAfold is the selected structural engine; STRAND supplies a future stability score, RiboNN a future translation proxy, and BoTorch a finite feasible-pool selection mechanism. The future proposed objective remains maximizing stability subject to a translation floor and hard constraints; no numerical floor, assay protocol or confirmatory acceptance threshold has been selected.

Active scope remains **1–2,999 nt**. All supplied transcript nucleotides count, including an explicitly supplied tail; no truncation or hidden omitted regions. Coding-transcript adapters support a narrower valid-CDS subset. Historical 3,000+ nt sources/results remain intact. [Scope policy](../configs/project_scope_2026-10-18.json) and [Stage 2 gate](../configs/stage2_to_stage3_gate_2026-10-18.json) are unchanged. Stage 2 remains open; cell-free expression Stage 3 is queued. Fixed-input software checks and mathematical toy optimization are permitted; actual expression candidate design stays behind the existing gate.

Stage transition still requires frozen independent sequence/family/clan-separated validation, accuracy/failures by length and family against native controls, credible review of native baseline gaps, resolution of sparse 2,000–2,999 nt coverage, constraint/decoder/resource/replay checks and documented limitations. This build does not satisfy those biological/scientific gates. No numerical gate has been invented. Preserve source/exposure lineage and never relabel exposed development references independent.

## Handoff audit completed before the build

V9 was the latest existing version. Its eight local Markdown links and eleven literal code/config/result anchors checked all existed. The retained assignment summary at `results/under3000_endpoint_assignment_runs/20261018T234628.064395Z/summary.json` still has SHA-256 `d7ddf63c2adf0bfd02943c1f433868a104d97b6a3a21c00fbf9c65ce73a01609`, matching V9/V7. Its recorded long/short baseline and assignment means match the historical handoff. This was a file/hash/summary audit, not inference replay or retraining. No external scientific literature audit was performed for V9's prior claims.

## New code, configuration and documentation

- [`src/rnastable/component_integration.py`](../src/rnastable/component_integration.py): immutable annotated transcript contract, explicit RNA and standard genetic code complete-CDS validation, sequence and annotation/context hashes, validation of supplied synonymous edits, frozen UTR/start/stop/protected positions and mutation budgets, duplicate-ID rejection, RiboNN domain exclusions, full-transcript TSV export, raw per-fold identity/sequence matching, released STRAND ALO arithmetic, and bounded subprocess folding wrapper.
- [`src/rnastable/ensemble_worker.py`](../src/rnastable/ensemble_worker.py): independent ViennaRNA MFE + partition-function worker; positional paired probabilities sum both endpoints of the 1-based upper-triangle matrix. Records per-position unpaired probabilities, AUP, ALO, GC fraction, both energy definitions, model details and saved parameter-file hash, wall time and memory. Invalid/nonfinite new probabilities fail. No unreviewed mapping to STRAND's energy column.
- [`src/rnastable/discrete_bo.py`](../src/rnastable/discrete_bo.py): double-precision CPU GP and finite-pool LogExpectedImprovement; excludes infeasible/observed choices, rejects ambiguous representations, preserves caller torch RNG, saves evaluation history and supports cached toy resume. Supplied-edit checks do not generate RNA candidates.
- [`scripts/inventory_four_component_sources.py`](../scripts/inventory_four_component_sources.py): pinned GitHub source/data/license acquisition with per-file SHA-256, upstream blob identity and source URL. Handles Git contents API large-file encoding using the blob API. No downloaded code is executed.
- [`scripts/inventory_ribonn_weights.py`](../scripts/inventory_ribonn_weights.py): records Zenodo release metadata, archive sizes and upstream checksums without acquiring weights.
- [`scripts/build_four_component_integration.py`](../scripts/build_four_component_integration.py): versioned build driver with frozen protocol/implementation copies and identities, source checks, fixed synthetic transcript input generation, RiboNN preflight export, length-panel folding, toy selection histories and artifact manifest. Unique directories for fresh runs; resume requires matching code/config/core runtime identities.
- [`scripts/verify_four_component_build.py`](../scripts/verify_four_component_build.py): validates artifact hashes, frozen code, transcript sequence/annotation identities and summary references without folding or fitting.
- [`configs/four_component_build_v1_2026-10-18.json`](../configs/four_component_build_v1_2026-10-18.json): fixed source snapshot, synthetic lengths and seed, folding timeout/settings, toy seeds/budget, optimizer versions, explicit disabled biological-scoring/design flags.
- [`configs/four_component_optimizer_requirements_2026-10-18.txt`](../configs/four_component_optimizer_requirements_2026-10-18.txt): exact added optimizer dependency versions.
- [`tests/test_component_integration.py`](../tests/test_component_integration.py) and [`tests/test_discrete_bo.py`](../tests/test_discrete_bo.py): contract, biological constraint, probability, identity, corrupt-output, feasibility, budget and cached-replay checks.
- [`docs/four_component_integration_2026-10-18.md`](../docs/four_component_integration_2026-10-18.md): usage, environments, resume behavior, adapter contracts and limitations.
- [`four_component_source_inventory_2026-10-18.json`](four_component_source_inventory_2026-10-18.json): concise local source/weight metadata inventory with original manifest entries and hashes. Raw upstream snapshots remain ignored local results.

Historical `folding.py`, `vienna_worker.py`, `optimization.py`, protocols and old model studies were not modified. No project .venv scientific dependencies were replaced. All additions are local and unpublished.

## Pinned sources, features and compatibility findings

Source manifest: `results/four_component_source_runs/20261019T040820.389955Z/manifest.json`. SHA-256: `5cb505276eeb7dd738cb804eddeae873e7bee9b537e00d6e343ca336f84e3cc3`. All **18** listed files were rehashed successfully.

- STRAND commit **ea9e7de635e7cf4053c676c495b8e65717369206** in [author repository](https://github.com/S00NYI/BITS_STRAND/tree/ea9e7de635e7cf4053c676c495b8e65717369206). Snapshot includes README, MIT source license, both R scripts, half-life overview CSV, nLuc cleaned reference and validation cleaned reference.
- RiboNN commit **dc896e1d1f78bf6b4e9bb7525c7852fcf25532e8** in [author repository](https://github.com/Sanofi-Public/RiboNN/tree/dc896e1d1f78bf6b4e9bb7525c7852fcf25532e8). Snapshot includes README, source license, separate model weight license, environment/config, inference/data/model/main/helper code and example prediction input. Its original environment uses Python 3.10.13, PyTorch 1.13.1 and pytorch-lightning 1.8.5; these were not installed or executed here.
- BoTorch release **v0.18.1**, release API target commit **cd0249c60b2a81af0d91b5e7d462ef6f574fceec**. Installed wheel version is pinned; a full upstream source checkout/wheel hash archive was not made.
- Consulted primary [ViennaRNA Python API](https://viennarna.readthedocs.io/en/latest/api_python.html) and [BoTorch acquisition API](https://botorch.readthedocs.io/en/stable/acquisition.html); installed versions and frozen worker settings govern this run.

STRAND source audit artifact: `results/four_component_build_runs/20261019T041458.024816Z/source_audit.json`.

The **69 nLuc reference rows** are 928–984 nt, and are released/exposed reference data, not new independent validation. Recomputed AUP from their positional values agrees to maximum absolute residual **4.99999985859e-10**. Recomputed GC **percent** agrees to **4.82758366616e-09**. The worker reports GC fraction; a future STRAND adapter must explicitly convert units.

The source data have **334 positional values outside [0,1] in 43 rows**, with a largest observed value of 1.0005738. Preserve original values. The R scripts replace values <=0 with 1e-10 and >=1 with 1-1e-10, then average natural log odds. Positive values smaller than 1e-10 are not clipped. The arithmetic helper reproduces that exact bounding rule; the new folding worker separately validates probabilities and only corrects <=1e-8 numerical sum overflow. This distinction was found during the first failed build and is covered by tests.

The released regression is **`pls::plsr`**, scaled features, leave-one-out validation, feature order `energy_per_length, GC, aup, alo`. Script 1 uses one component for its illustrated training predictions, a minimum-PRESS selection for an eGFP analysis and two components for some later validation analyses. No general exported coefficient artifact was identified in the pinned tree. **Rscript is absent**. Original probability extraction conditions and the precise `energy` column meaning remain unaudited; both MFE and ensemble energy are retained separately. No R reproduction, new PLS fit, saved coefficient set or stability prediction was run.

RiboNN's raw inference function emits per-fold rows; the default main routine then averages folds and tissue scores. The new join contract uses raw `predict_using_nested_cross_validation_models` output with an explicit complete fold inventory and named task, before that aggregation. The default final `prediction_output.txt` lacks the raw fold contract. Inputs are exported as full sequence plus UTR/CDS sizes to avoid empty-UTR missing-value parsing; no row order join is allowed. Upstream 5′ UTR >1,381 nt and CDS+3′ UTR >11,937 nt limits are explicit exclusions. Only standard-code complete CDS is currently supported.

Weight metadata inventory: `results/ribonn_weight_inventory_runs/20261019T041243.650769Z/summary.json`; raw metadata adjacent `zenodo_record.json`, metadata SHA-256 **5bbe572687e13d49add3805383683cfbe0e2a349a876b6e217a9dca9659f5e44**. Zenodo record 17258709 contains `weights.zip`, **207,395,960 bytes**, upstream **md5:dd088ee2feffcda6ce26124a471a140f**; and `RiboNN-1.0.0.zip`, 1,799,121 bytes, upstream md5:6f8c12f7ba678db202fa1019668c0a29. These are metadata-declared checksums, not locally verified weight hashes. **No weights were downloaded.** The weight license restricts use to academic research and noncommercial purposes, separately from source license. Task units, applicable assay context, isolated inference compatibility, actual checkpoint checksums and cell-free calibration remain pending. The build summary's broader pending weight-inventory phrase predates this separately completed release-metadata inventory; actual downloaded-weight/checkpoint inventory is still pending.

## Final measured protocol and artifacts

Canonical corrected build run: **`results/four_component_build_runs/20261019T041458.024816Z/`**. Summary SHA-256: **`d898cfbc288bab7bd386e7dfe79f681280fb171941ff7ac763941e64ab2a01e2`**. Exact fixed protocol is adjacent `protocol.json`; source copies under `source/`; code/config/version hashes in `identity.json`; input inventory in `fixed_inputs.json`; complete per-file checksums in `artifacts.json`. Every folding JSON includes sequence identity, annotation/context identity, settings, parameter-file hash, positional arrays and features. No training checkpoint exists for this integration milestone.

Runtime: Python 3.12.14; torch 2.14.1+cu130; ViennaRNA 2.7.2; NumPy 2.5.3; SciPy 1.18.1; BoTorch 0.18.1; GPyTorch 1.15.2; linear_operator 0.6.1. Linux 7.0.0-38-generic x86_64, glibc 2.43. Optimizer uses CPU, double precision and one torch thread. No GPU computation or GPU resource measurement was performed.

Optimizer additions are in **`external/four_component_deps/`**, enabled explicitly with `PYTHONPATH`. The exact 13 added versions are in the requirements lock: BoTorch 0.18.1, cloudpickle 3.1.2, gpytorch 1.15.2, joblib 1.6.0, linear_operator 0.6.1, multipledispatch 1.0.0, mypy_extensions 1.1.0, narwhals 2.27.1, ninja 1.13.2, pyre-extensions 0.0.32, scikit-learn 1.9.1, threadpoolctl 3.7.0 and typing-inspect 0.9.0. Their declared runtime requirements were checked against installed metadata with no missing or mismatched requirements after completion. This is an added-package version lock using the existing environment, not a full independently portable environment or wheel hash lock.

Fixed synthetic inputs use seed **1729**, 12-nt 5′ UTR, AUG + uniformly selected sense codons + UAA, and remaining random 3′ UTR to exact lengths 64/400/1,000/2,000/2,999. No sequence is optimized, biologically measured, protein-selected, or claimed independent structure validation. Complete sequence/CDS/context provenance and hashes are in `fixed_inputs.json`.

RNAfold: Turner2004 parameter file explicitly loaded and hashed, temperature **37 °C**, dangles **2**, minimum loop 3, unlimited pair span, no noLP restriction, no structure constraints; MFE rescaling followed by partition function and positional probability extraction. Binding/default details, including salt and numerical settings, are serialized in each result. Per-input wall timeout **120 s**. No OS memory cap was enforced. Timing is for this fixed input/hardware/environment and is not a worst-case guarantee.

| Length nt | Worker folding seconds | Total subprocess wall seconds | Worker VmHWM KiB |
| ---: | ---: | ---: | ---: |
| 64 | 0.010966 | 0.079272 | 35020 |
| 400 | 0.345547 | 0.415743 | 46776 |
| 1000 | 3.170711 | 3.252157 | 111176 |
| 2000 | 18.886571 | 18.997267 | 340416 |
| 2999 | 64.644153 | 64.811403 | 721996 |

The final 2,999-nt peak is approximately 705.1 MiB. `peak_worker_rss_kib` comes from Linux `/proc/self/status` VmHWM after exec; a separate `resource_highwater_including_preexec_kib` retains `ru_maxrss` for transparency. The earlier successful build inherited a large parent high-water mark in ru_maxrss, so its memory values are superseded. Worker runtime excludes startup/imports; subprocess wall time includes them. These are worker memory measurements, not full application/GPU memory totals.

BoTorch toy protocol: 31 one-dimensional points x=i/30, exclude 0.40<=x<=0.60; fixed initial indices **0,10,30**; objective **1-(x-0.73)^2+0.04*sin(19*x)**. **Eight total unique evaluations including the initial three**. SingleTaskGP, Standardize(m=1), observed noise variance 1e-6, ExactMarginalLogLikelihood, SciPy fitting with maxiter 50; analytic **LogExpectedImprovement**, q=1 discrete acquisition over feasible unevaluated points. Same initial design and total evaluation budget for constrained random comparison. Histories contain each index/value/log-acquisition; no RNA scores are involved.

| Seed | Unique evaluations | BO best toy value | Random best toy value | BO invocation seconds |
| ---: | ---: | ---: | ---: | ---: |
| 7 | 8 | 1.039160799193573 | 1.025882790487864 | 0.609871 |
| 1729 | 8 | 1.039160799193573 | 1.039160799193573 | 0.097082 |
| 20261015 | 8 | 1.039160799193573 | 1.035022522985463 | 0.099042 |

The BO trajectories are identical under the fixed initial design and deterministic acquisition fit; the three seeds are software checks, not independent biological replicates or evidence of optimizer variability. One random run ties BO. No broad superiority claim is justified.

## Verification actually completed

- Final focused tests: **27 passed in 1.83 s**, covering both new test files plus existing `test_project_scope.py` and `test_stage2_scope_audit.py`. Exact command/output: [test log](four-component-build-focused-tests-2026-10-18.log). Earlier passes (17, then 27) occurred during development; the final result supersedes them for current source.
- Parsed all seven new Python implementation/driver/inventory/verification files with `ast.parse`. No complete repository suite was run.
- Verified final run's **19 inventoried artifacts** plus **five transcript identities**, frozen implementation copies and summary checksum references using `scripts/verify_four_component_build.py`.
- Copied the completed run to **`results/four_component_resume_checks/20261019T041647.844691Z/`** and executed driver `--resume` there. All three toy history JSONs are byte-identical to the original. Cached folds were reused, not recomputed. The original summary hash stayed unchanged.
- The verifier deliberately rejected an altered copied folding artifact; restored the exact original bytes afterward. This was a corruption detection check on the copy. [Artifact/resume log](four-component-build-artifact-and-resume-checks-2026-10-18.log).
- Toy unit replay resumed a partially completed history and reproduced the uninterrupted result, with explicit corrupt-cache and protocol-mismatch rejection. This is not deterministic neural retraining.
- Actual new native inference consists of fixed-input MFE/PF folding in the development and corrected runs. No historical neural checkpoint inference, original assignment-study replay, RiboNN checkpoint inference, STRAND R fit, neural retraining, confirmatory validation or assay was performed.
- Handoff/doc local links, JSON and trailing whitespace are checked after writing this record; the completion response reports any remaining issue.

## Preserved failed/earlier attempts and limitations

- `results/four_component_source_runs/20261019T040717.642795Z/`: empty initial acquisition attempt failed under sandbox network restrictions. Retained, not used.
- `results/four_component_source_runs/20261019T040723.912045Z/manifest.json`: initial successful smaller snapshot, before adding nLuc and validation reference tables. Preserved; canonical source protocol uses the later manifest.
- `results/four_component_build_runs/20261019T041141.206144Z/`: partial initial build aborted because strict probability validation rejected the released reference values above one. No performance summary is claimed for it. Its frozen source and initial identity remain in place.
- `results/four_component_build_runs/20261019T041209.633772Z/`: successful first build, all folds/toy fits completed. Scientific outputs are retained, but its resource high-water marks could include parent torch memory. It is superseded by the corrected run for resource reporting. Old summary hash is `e6f31f6f4e6c9b7eee90ef8b196b63a2a231bfd6200977d4eee8c831a4d43030`.
- GitHub and Zenodo sandbox network failures were retried with approved escalation and completed. A web-tool Zenodo metadata request also failed; direct approved acquisition succeeded. No failed acquisition is represented as a verified downloaded weight.
- First dependency inventory found missing scikit-learn; the current scikit-learn release added joblib/cloudpickle/narwhals requirements. Added those into the isolated target and rechecked all declared requirements successfully.
- BoTorch import emits an upstream torch.jit.script deprecation warning; fitting and tests pass. No warning suppression or historical environment replacement was performed.
- Driver resume checks config/code/core versions and folding identity, but does not independently validate every partial cached output before a final artifact manifest exists. Verify a completed run before reuse; inspect incomplete caches or create a fresh run. Summaries update on resume, so copy completed historical runs before testing resume. The demonstrated copy is under the workspace results tree because output references are workspace-relative.
- No universal transcript support, cell-free validity, stability gain, translation gain, calibrated uncertainty, complete environment portability or independent structure-validation success is established. STRAND/RiboNN training-source overlap remains unaudited; unknown stays unknown.

## Historical scientific and publication state

Historical development cohorts remain exposed: six longer references 1,399–2,973 nt, thirteen shorter 400–535 nt. Only one longer record covers 2,000–2,999 nt; reference/training family/clan/segment relationships and computational bpRNA labels prevent independent test claims. Original 103-record BCE mean structure pair F1 is **0.3173511819 long / 0.1560640870 short**, assignment variant **0.3261881307 / 0.1606458705**, native LinearFold **0.4381334451 / 0.3301074317**, ViennaRNA **0.4214700331 / 0.3346291106**. These are carried from validated existing summaries, not newly recomputed structure scores. Assignment short seed20261015 regresses. Hard-negative study regressed against its matched control. Gold recovery oracles are label-informed bounds, not predictions. None of these metrics measures stability or expression.

Historical training: 103 references, 61–2,941 nt, 12,511 supported positives and 50,044 negatives; 1,077 unsupported gold pairs retained in original denominators. Seeds 7/1729/20261015; embedding16/channels32/pair dimension16/dilations1,2,4,8; Adam lr0.001, ten epochs, fixed final checkpoint; sparse exact top32 decoder block64. These settings apply only to retained custom structure studies.

Exact retained anchors:

- Baseline protocol `results/under3000_development_protocol_runs/20261018T223802.654756Z/manifest.json`; run `results/under3000_development_runs/20261018T223810.974436Z/`, `extended_103_seed{s}/final_model.pt`.
- Hard negatives protocol/run `results/under3000_hard_negative_protocol_runs/20261018T231044.103020Z/manifest.json` and `results/under3000_hard_negative_runs/20261018T231058.189040Z/`.
- Recovery protocol/run `results/under3000_recovery_ceiling_protocol_runs/20261018T234336.469918Z/manifest.json` and `results/under3000_recovery_ceiling_runs/20261018T234344.201186Z/`.
- Assignment protocol `results/under3000_endpoint_assignment_protocol_runs/20261018T234607.509040Z/manifest.json`; adjacent `train.json`/`validation.json`; run `results/under3000_endpoint_assignment_runs/20261018T234628.064395Z/`; `assignment_seed{s}/final_model.pt`, `predictions.json`, `summary.json`. Root summary hash was reverified above.
- The `bpRNA_RFAM_5479` noncanonical-label diagnostic remains subordinate pending historical work; do not delete its labels or amend frozen studies while implementing this architecture.

V8 records the last GitHub publication at **e1758333075e1c7eaaeea3d22c55d79d1d462c59**, in `/tmp/rna-stable-ai-publish-20261018-stage2`; not remotely rechecked this turn. The published README linked V7 then. V9 and this build are local. No commit/push, original index staging, README edit, roadmap edit or gate amendment was performed. Current pre-existing Git status plus additions: **{'??': 574, 'A ': 982, 'AM': 11}**; staged A/AM category counts remain the same as at task entry (982 and 11). Do not bulk-commit the original workspace. Earlier records state this local main has no commits; that local-history fact was not rechecked now. Publication uses an isolated checkout when requested.

Preserve the live GitHub README picture and all upstream edits/assets before future publication. V8's last verified tag was `<img width="1774" height="887" alt="image" src="https://github.com/user-attachments/assets/4da2605a-3a6d-4130-9014-950dc75bd34d" />`. A future publisher must fetch the latest README again; this historical tag is not proof that live upstream has stayed unchanged.

All sessions launched for this build have completed, including source/metadata downloads, dependency installation, folding, optimizer checks and tests. No task-owned experiment is intentionally left running. Other system processes were not exhaustively audited.

## Prioritized continuation and exact safe commands

1. Reproduce STRAND reference regression in an isolated R environment with a pinned `pls` package; resolve figure-specific component policy and save coefficients/transforms plus reference predictions. Audit original feature-generation provenance before accepting new ViennaRNA features. If any feature extraction differs, name it a new calibrated model rather than unchanged published STRAND. R installation, coefficients, regression metrics and biological acceptance thresholds are still pending.
2. Build an isolated RiboNN inference environment from the pinned source, inspect weight license applicability, acquire/archive/checksum the named weight artifact when proceeding, freeze a named task and fold/checkpoint inventory, reproduce fixed-input inference, and exercise row/exclusion matching on real outputs. Avoid broad pretrained tissue means as an unreviewed cell-free objective. Never treat the fake training example as measured translation data.
3. Add scored-table adapters with explicit units, transformation/weight/settings hashes, input identity, status/reason and raw artifact path. Keep separate stability and translation scores; do not silently invent a weighted objective or translation floor.
4. Complete independent Stage 2 validation/resource/constraints/replay review and version any gate policy change explicitly. Resolve sparse 2,000–2,999 nt independent evidence. Only then freeze parent/CDS/allowed edits, translation floor, budgets and cell-free assay plan for actual candidate screening.
5. Future real optimizer evaluation should compare unchanged parent, constrained random, simple greedy and BO with the same feasible pool/evaluation budget and lineage-safe splits. The mathematical toy is not that evaluation.

Read and verify without new fitting:

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-18_V10.md
cat docs/four_component_integration_2026-10-18.md
cat configs/four_component_build_v1_2026-10-18.json
cat configs/stage2_to_stage3_gate_2026-10-18.json
cat results/four_component_build_runs/20261019T041458.024816Z/source_audit.json
cat results/four_component_build_runs/20261019T041458.024816Z/summary.json
PYTHONPATH=src .venv/bin/python scripts/verify_four_component_build.py results/four_component_build_runs/20261019T041458.024816Z
PYTHONPATH=external/four_component_deps:src .venv/bin/python -m pytest -q tests/test_component_integration.py tests/test_discrete_bo.py tests/test_project_scope.py tests/test_stage2_scope_audit.py
```

A fresh fixed-input milestone run (CPU MFE/PF and toy GP fitting; not expression candidate design):

```bash
cd /home/zyliu/Documents/rna-stable-ai
PYTHONPATH=external/four_component_deps:src .venv/bin/python scripts/build_four_component_integration.py
```

Inspect actual pinned source before creating the next protocol:

```bash
sed -n '79,110p' results/four_component_source_runs/20261019T040820.389955Z/strand/Figure_Scripts_1.R
sed -n '675,710p' results/four_component_source_runs/20261019T040820.389955Z/strand/Figure_Scripts_1.R
cat results/four_component_source_runs/20261019T040820.389955Z/ribonn/environment.yml
cat 'results/four_component_source_runs/20261019T040820.389955Z/ribonn/MODEL WEIGHTS LICENSE.txt'
cat results/ribonn_weight_inventory_runs/20261019T041243.650769Z/summary.json
sed -n '163,198p' results/four_component_source_runs/20261019T040820.389955Z/ribonn/src/main.py
```

Dependency rebuild and copied-run resume instructions are in the usage document. Do not resume the canonical completed run merely to inspect it. New source acquisition runs require network access and create new snapshots; do not replace the source manifest inside this frozen run. Do not invent a combined stability/translation pipeline command before the remaining adapters are implemented and verified.
