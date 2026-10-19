# RNA-StableAI handoff — 2026-10-18 V9

Project: **RNA-StableAI**  
Date: **2026-10-18 (America/Los_Angeles)**  
Version: **V9**  
Workspace: **`/home/zyliu/Documents/rna-stable-ai`**  
Canonical plan: **RNAfold + STRAND + RiboNN + BoTorch**  
Previous publication record: [V8](RNA-StableAI_HANDOFF_2026-10-18_V8.md). Previous detailed scientific record: [V7](RNA-StableAI_HANDOFF_2026-10-18_V7.md).

## 1. Latest user decision and scope

The user explicitly selected this four-component combination and requested a handoff for it. This document records the new architecture and continuation plan. It supersedes the earlier recommendation to make another custom pair-scoring/loss experiment the default next development task. Prior model studies remain historical controls and replayable evidence; preserve them in place.

The selected architecture is a development direction, not an implemented or validated pipeline. This turn creates this handoff only. It does not install software, train models, select candidates, change inference defaults, amend frozen protocols, start expression work, or publish to GitHub.

Carry forward the existing constraints:

- Active RNA length: **1–2,999 nt**, excluding 3,000 nt. This is project scope, not a claim that every component supports or is validated across every length. Coding-transcript workflows require valid CDS annotations and form a narrower subset.
- Preserve historical 3,000+ nt code/data/results; do not truncate sequences to fit models.
- **Stage 2 remains open. Stage 3 targets cell-free expression and remains queued.** The new combination does not itself satisfy the transition gate.
- Existing policies remain authoritative: [`configs/project_scope_2026-10-18.json`](../configs/project_scope_2026-10-18.json) and [`configs/stage2_to_stage3_gate_2026-10-18.json`](../configs/stage2_to_stage3_gate_2026-10-18.json).
- Preserve source/exposure lineage, genuinely independent validation, explicit coverage gaps, constraints, resource bounds and replay. Define quantitative acceptance criteria before confirmatory evaluation; existing gates have no newly established numerical thresholds.
- Preserve the GitHub README picture and upstream edits before any future publication. This documentation turn leaves README unchanged.

## 2. Component identities, roles and primary sources

**Interpretation of STRAND:** use *Stability Regression Analysis using Nucleotide-Derived features*, associated with **S00NYI/BITS_STRAND**. This is a contextual assumption about the user's intended STRAND, explicitly recorded here. The similarly named RNA–protein diffusion refinement project and RNA STRAND structure database are different resources. Resolve any different intended identity before implementing that adapter.

| Component | Planned responsibility | Boundary |
| --- | --- | --- |
| RNAfold / ViennaRNA | Thermodynamic secondary structure and ensemble feature computation | Folding output supplies structural evidence; folding energy alone does not establish stability or expression benefit. |
| STRAND | Predict in-solution stability from its specified structural/sequence features | Preserve the released feature definitions, fitted transformations, units and assay context. |
| RiboNN | Score translation efficiency for correctly annotated mRNA inputs | Treat pretrained scores as a proxy until calibrated to the intended cell-free system. |
| BoTorch | Select feasible candidates using a fitted surrogate and acquisition function | Requires an explicit candidate representation, observations, objective, constraints and budget. It is not a pretrained RNA generator. |

Sources consulted on 2026-10-18:

1. [RNAfold official manual](https://viennarna.readthedocs.io/en/latest/man/RNAfold.html): MFE and partition-function calculations, including ensemble probabilities. Use the installed version's settings explicitly.
2. [Author STRAND repository](https://github.com/S00NYI/BITS_STRAND): the README identifies STRAND as a four-feature regression approach and exposes R figure scripts and associated data. Its publication is linked there at [DOI 10.1016/j.omtn.2026.102960](https://doi.org/10.1016/j.omtn.2026.102960). The [author manuscript search record](https://pmc.ncbi.nlm.nih.gov/articles/PMC13264031/) identifies ALO, FE, AUP and GC content. Full PMC retrieval encountered a browser challenge this turn. Exact feature formulas, coefficients and extraction compatibility have **not** been audited.
3. [Author RiboNN repository](https://github.com/Sanofi-Public/RiboNN): mRNA translation-efficiency prediction with annotated UTR/CDS inputs, human/mouse prediction entrypoints and pretrained model downloads. It lists separate source-code and model-weight license files. Its README excludes inputs with 5′ UTR >1,381 nt or CDS plus 3′ UTR >11,937 nt. These restrictions must be checked even within this project's length cap.
4. [BoTorch acquisition API](https://botorch.readthedocs.io/en/stable/acquisition.html) and [optimization API](https://botorch.readthedocs.io/en/stable/optim.html): candidate acquisition and discrete optimization building blocks. Freeze actual installed API versions before implementation.

These are mutable source links, not frozen source snapshots. No upstream commit SHA, STRAND parameter artifact or RiboNN weight checksum was pinned this turn. That inventory is the first implementation task.

## 3. Proposed data flow and interfaces

```text
Annotated parent mRNA + allowed-edit specification + assay context
                         |
              Feasible candidate construction
                         |
              +----------+------------------+
              |                             |
       RNAfold ensemble                  RiboNN
              |                             |
       STRAND features                 Translation proxy
              |
       Stability prediction
              +--------------+--------------+
                             |
         Versioned score table + feasibility + provenance
                             |
             BoTorch surrogate / acquisition ranking
                             |
         Selected next evaluation batch + full audit log
                             |
         New observations -> surrogate update -> repeat
```

This is a planning diagram, not a running service. Before the Stage 2 gate closes, integration work is limited to source audit, adapter checks, fixed-input evaluation and optimizer verification on synthetic/toy objectives. Actual expression candidate design remains behind the existing stage gate. After it closes, computational candidate screening precedes any cell-free assay campaign.

Define an immutable record per transcript/candidate containing: unique ID; sequence and SHA-256; parent ID and edit history; explicit 5′ UTR/CDS/3′ UTR boundaries; translation table; protected positions; cap/poly(A)/modified-base handling; length; assay conditions; data provenance and exposure split. Include sequence regions counted in the length cap explicitly; do not silently omit a tail or protected segment.

Each adapter should return the input hash, tool/version/settings/weight hashes, status or exclusion reason, output units and direction, raw output artifact path, runtime and measured resource use. Join results by identity/hash, never output row position. A dropped RiboNN row must produce an explicit exclusion, not a misaligned score.

**RNAfold adapter:** retain MFE structure/energy and ensemble quantities needed by STRAND. Pin temperature, energy parameter set, dangles, constraints, numerical precision and probability extraction. An MFE structure alone cannot supply ensemble features. Existing native worker uses `.mfe()`; partition-function extraction needs separate audited implementation. Measure partition-function runtime/memory at representative in-scope lengths before large batches.

**STRAND adapter:** first reproduce the released R analysis on its available reference inputs. Audit ALO, FE, AUP and GC definitions, aggregation, log-odds clipping, fitted coefficients, scaling, target transformation and output interpretation. Establish whether the original features were generated compatibly with the chosen ViennaRNA settings. If not, label a newly fitted/calibrated version separately; do not call it the unchanged published STRAND. The repository is analysis code/data, so a general sequence-to-score API must not be assumed to exist.

**RiboNN adapter:** annotate regions explicitly, preserve start/stop codons, identify checkpoint/task/output scale, and record exclusion behavior. Published human/mouse prediction entrypoints do not establish cell-free validity. Freeze inference initially; consider adaptation only with appropriate independent cell-free data. Isolate dependencies if the upstream environment conflicts with the project environment. Use unique run directories because the upstream README says default prediction output files can be overwritten.

**BoTorch adapter:** begin with a finite, validated candidate pool and a modest fixed representation; optimize acquisition over feasible choices. Do not optimize unconstrained continuous nucleotide coordinates and assume rounding preserves biological feasibility. A low-dimensional edit/codon descriptor is a proposed starting point, subject to surrogate validation. Choose surrogate/kernel only after representation and initial observations are defined. Recheck constraints after selection.

## 4. Objective, constraints and feedback policy

Proposed first objective after the stage gate: **maximize predicted stability subject to a prespecified translation floor relative to the unchanged parent and hard sequence constraints**. The floor, score transformation, assay context and candidate budget remain to be selected and frozen; no arbitrary numerical value is established here. Retain separate stability and translation scores. A Pareto study is a later option; avoid an unexplained weighted sum of quantities on incompatible scales.

Preserve the encoded protein using explicit CDS boundaries and the chosen genetic code. Freeze UTRs initially unless a later protocol explicitly permits edits. Protect start/stop, designated motifs and positions; define mutation and GC/composition budgets, forbidden motifs and feasibility checks in the protocol. Existing `src/rnastable/optimization.py` contains useful constraint examples but assumes a whole frame-0 coding sequence for protein preservation and exact GC-count preservation. It cannot be applied unchanged to a full UTR-bearing transcript. Keep its historical behavior intact and add an annotated adapter rather than changing old study semantics.

For deterministic computational screening, observations are cached STRAND/RiboNN outputs. Such a loop optimizes **model predictions**. It creates neither new independent biological observations nor evidence that candidate RNA survives longer or produces more protein. Check whether BO adds value over simply ranking a small fully scored pool; do not fit a surrogate to already scored features merely to rediscover a known deterministic score.

For later experimental feedback, retain assay replicate IDs, batch effects, conditions, detection limits and estimated noise. Fit to measured outcomes separately from computational proxies. Use a noise-aware acquisition when warranted; `qLogNoisyExpectedImprovement` is a candidate to evaluate, not a frozen choice. Surrogate posterior uncertainty does not quantify all STRAND/RiboNN domain error. Do not present it as calibrated biological confidence without validation.

## 5. Work sequence and acceptance gates

1. **Source and compatibility inventory.** Pin upstream commits/releases, source/data/weight hashes, license terms, R/Python dependencies, released target definitions and supported input domains. Check STRAND feature extraction against RNAfold; check RiboNN input/task/output semantics. Deliver a manifest and integration-risk report before choosing a scoring formula.
2. **Structure baseline evaluation within Stage 2.** Treat RNAfold as the selected structural engine. Freeze independent sequence/family/clan-separated validation, report accuracy and failures by length band/family against existing native controls, resolve sparse 2,000–2,999 nt coverage, and review constraints/resources/replay. Compare to native performance rather than requiring the old custom network to win before considering this architecture. Any gate-policy amendment must be explicit and versioned.
3. **Reproduce component behavior on fixed inputs.** Reproduce STRAND reference calculations and RiboNN saved-checkpoint inference; audit row matching, malformed CDS, exclusions, nonfinite probabilities/scores and run isolation. These checks are not expression candidate design or independent biological validation.
4. **Verify optimizer mechanics.** Use toy objectives to check discrete feasibility, duplicate prevention, caching, fixed seeds, evaluation accounting, resume and logged acquisition choices. Freeze an initial-design and acquisition budget before real screening.
5. **After Stage 2 review closes the gate**, freeze the annotated parent, allowed edits, assay target, stability objective/translation floor and experimental protocol. Run matched-budget computational comparisons, then choose a bounded candidate panel with controls for cell-free validation.

Planned optimizer comparisons: unchanged parent, constrained random search, a simple greedy strategy and the four-component BO loop, using the same candidate rules and unique expensive-evaluation budget. Report best feasible objective versus evaluations, constraint violations, failures, score disagreement, runtime and memory. Use seeds **7, 1729, 20261015** as a proposed continuity choice; they are not yet frozen for a new run. Do not tune on confirmatory test outcomes.

For stability/translation validation, split by parent transcript/ORF and appropriate lineage so close synonymous variants do not cross train/test boundaries. Audit overlaps with STRAND/RiboNN training sources; unknown overlap must remain unknown. Existing exposed structure-development references cannot be relabeled independent expression/stability test data. Cell-free system, reporter, reagents, temperature, timepoints, replicate count and measured acceptance thresholds remain pending.

## 6. Historical evidence to preserve

These values are carried from V7/V8, **not recomputed this turn**:

| Development cohort | Original 103-record BCE mean pair F1 | Endpoint assignment variant | LinearFold | ViennaRNA |
| --- | ---: | ---: | ---: | ---: |
| Longer, 6 references, 1,399–2,973 nt | 0.3173511819 | 0.3261881307 | 0.4381334451 | 0.4214700331 |
| Shorter, 13 references, 400–535 nt | 0.1560640870 | 0.1606458705 | 0.3301074317 | 0.3346291106 |

These are structure F1 values, not degradation or expression metrics. Both cohorts are already exposed development sets. Only one longer record is 2,000–2,999 nt; shorter references include computational bpRNA labels. Longer references have training-family/clan/segment relationships. Prior hard-negative sampling regressed in every seed against its matched random-pool control; the assignment variant improved longer F1 in all seeds but regressed on one short seed. Gold recovery oracles are label-informed bounds, never model predictions. The `bpRNA_RFAM_5479` noncanonical-label audit remains pending historical diagnostic work, subordinate to the newly selected integration direction unless needed for validation.

Historical training: 103 records, 61–2,941 nt; 12,511 supported positives, 50,044 sampled negatives, 1,077 unsupported gold pairs retained in original references. Seeds 7/1729/20261015; local helix/context model embedding 16/channels 32/pair dimension 16/dilations 1,2,4,8; Adam lr 0.001, ten epochs, fixed final checkpoint; exact sparse top-32 decoder with block size 64. These settings describe old structure studies only. STRAND/RiboNN training losses, optimizer settings and new BoTorch hyperparameters have not been selected or verified.

Exact retained anchors:

- Baseline protocol: `results/under3000_development_protocol_runs/20261018T223802.654756Z/manifest.json`.
- Baseline run: `results/under3000_development_runs/20261018T223810.974436Z/`; per-seed checkpoint `extended_103_seed{s}/final_model.pt`.
- Hard-negative protocol/run: `results/under3000_hard_negative_protocol_runs/20261018T231044.103020Z/manifest.json` and `results/under3000_hard_negative_runs/20261018T231058.189040Z/`.
- Recovery protocol/run: `results/under3000_recovery_ceiling_protocol_runs/20261018T234336.469918Z/manifest.json` and `results/under3000_recovery_ceiling_runs/20261018T234344.201186Z/`.
- Assignment protocol: `results/under3000_endpoint_assignment_protocol_runs/20261018T234607.509040Z/manifest.json`; full ordered training/validation inventories are adjacent `train.json` and `validation.json`.
- Assignment run: `results/under3000_endpoint_assignment_runs/20261018T234628.064395Z/`; `assignment_seed{s}/final_model.pt`, `predictions.json`, `summary.json` retain checkpoint, 19-record predictions and per-seed metrics.
- V7 recorded assignment root summary SHA-256: `d7ddf63c2adf0bfd02943c1f433868a104d97b6a3a21c00fbf9c65ce73a01609`. Not rehashed this turn.
- Scientific reviews: [recovery/assignment](stage2_recovery_ceiling_and_assignment_review_2026-10-18.md), [hard negatives](stage2_hard_negative_review_2026-10-18.md), and historical [degradation pilot](degradation_pilot_review_2026-10-13.md). Inspect the degradation pilot's sources/exposures before claiming any data are new to STRAND validation.
- Published concise summaries: [publication manifest](stage2_publication_2026-10-18/MANIFEST.json). These are not a full portable replay bundle; raw reference inventories, checkpoints and prediction arrays remain local.

Historical detailed per-seed results, runtime measurements and hashes remain in V7/V6; this plan creates no new run, checkpoint, prediction file or performance claim for the combination.

## 7. Workspace, publication and verification status

V8 records the previous publication to `zyliu-OU/rna-stable-ai` at commit `e1758333075e1c7eaaeea3d22c55d79d1d462c59`, prepared in `/tmp/rna-stable-ai-publish-20261018-stage2`. This was **not rechecked remotely this turn**. V8 remains local; the published README linked V7 at that time. The new V9 plan has not been published and README/roadmap/configs still describe the prior implementation state. This handoff is the authoritative new planning record until those documents are deliberately updated.

The original workspace has extensive pre-existing staged/modified/untracked files. `git log -1 --oneline` failed because this local `main` has no commits. Do not infer that the published GitHub repository lacks history or try to commit the entire workspace. Preserve the existing index and use a separately prepared publication checkout when publishing.

Checks actually performed this turn:

- Read root `AGENTS.md`, latest V8 publication record, V7 scientific details, V6/V5 context, current policies and `pyproject.toml`; inspected relevant optimization/native-worker code.
- Determined local date using `TZ=America/Los_Angeles date`; existing versions V1–V8 were present, so selected V9 without overwriting them.
- Inspected Git status and local history. Status confirms existing mixed work; the no-commit local-history failure is recorded above.
- Queried installed runtime: **Python 3.12.14; torch 2.14.1+cu130; ViennaRNA 2.7.2; numpy 2.5.3**. `importlib.util.find_spec` found **neither botorch nor gpytorch** in `.venv`. STRAND/RiboNN installation and available R runtime were not checked.
- Browsed the primary sources linked above. Some BoTorch website routes failed; the ReadTheDocs API pages loaded. No weights or source repositories were downloaded.
- Final document checks verify the next-version file, required content, local Markdown link targets and absence of trailing whitespace. See the completion response for outcome.

No unit tests, native folding, partition-function runs, model inference replay, deterministic retraining, new data acquisition or combined-pipeline experiment was run. No new compute time, peak memory, GPU use, calibration accuracy or combined result was measured. Prior V8's 51-test publication pass and V7's replay evidence are historical, not tests run for V9. No experiment process was started or left running by this task; other system processes were not audited.

## 8. Exact safe continuation commands

The following commands inspect existing state; they do not start new training or candidate design:

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-18_V9.md
cat configs/project_scope_2026-10-18.json
cat configs/stage2_to_stage3_gate_2026-10-18.json
cat reports/RNA-StableAI_HANDOFF_2026-10-18_V8.md
cat reports/RNA-StableAI_HANDOFF_2026-10-18_V7.md
cat reports/degradation_pilot_review_2026-10-13.md
cat src/rnastable/folding.py
cat src/rnastable/vienna_worker.py
sed -n '1,165p' src/rnastable/optimization.py
cat pyproject.toml
.venv/bin/python -c 'import sys, importlib.util, importlib.metadata as m; print(sys.version); print({p:m.version(p) for p in ("torch","ViennaRNA","numpy")}); print({p:importlib.util.find_spec(p) is not None for p in ("botorch","gpytorch")})'

# Optional historical artifact/inference replay; no optimizer retraining:
.venv/bin/python scripts/study_under3000_endpoint_assignment.py --verify-run results/under3000_endpoint_assignment_runs/20261018T234628.064395Z/summary.json

# Read-only upstream inventory, requires network access:
gh api repos/S00NYI/BITS_STRAND/commits/main --jq .sha
gh api repos/Sanofi-Public/RiboNN/commits/main --jq .sha
gh api repos/zyliu-OU/rna-stable-ai/commits/main --jq .sha
```

Those optional replay/network commands were **not executed for this handoff**. There is no runnable four-component driver yet, so no fictitious pipeline command is supplied. Next implementation should add a versioned source manifest and adapter protocol in new paths, then a separately named driver after compatibility checks. Do not edit manifest-pinned historical modules to implement the new plan. Before publication, fetch the latest GitHub README and preserve the exact user image and all upstream edits/assets again.
