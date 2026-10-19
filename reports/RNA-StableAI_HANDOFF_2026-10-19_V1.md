# RNA-StableAI handoff — 2026-10-19 V1

Project: RNA-StableAI
Date: 2026-10-19, America/Los_Angeles
Version: V1
Workspace: `/home/zyliu/Documents/rna-stable-ai`
Selected architecture: **RNAfold + STRAND + RiboNN + BoTorch**
Previous handoff (publication, scope and component records): [V13](RNA-StableAI_HANDOFF_2026-10-18_V13.md).
Full scientific/inference record: [V12](RNA-StableAI_HANDOFF_2026-10-18_V12.md). STRAND record: [V11](RNA-StableAI_HANDOFF_2026-10-18_V11.md). Architecture decision: [V9](RNA-StableAI_HANDOFF_2026-10-18_V9.md).

## Scope of this session

The user asked to check the latest handoff and then start **prioritized next work item 1** from V13: "Resolve RNAfold→STRAND original-feature compatibility or a separately named calibration using a prespecified agreement criterion and independent lineage-safe evidence. Six exposed diagnostics cannot close the gate."

This session built and ran that prespecified criterion. **The outcome is negative: RNAfold-derived features are rejected as a substitute for the released LinearPartition features of the published STRAND model.** Nothing was unlocked, no gate advanced, no frozen default changed, and no publication to GitHub was performed. Items 2 and 3 of the V13 priority list were not started.

## Decisions that supersede earlier handoffs

- V13 described the RNAfold/STRAND compatibility question as open with only six exposed diagnostics. It is now **decided for the feature-substitution route under a frozen criterion**, on 85 held-out records: substitution into the unchanged published model is rejected. The route forward is a separately named refit, not a substitution.
- The V13 statement "Six fixed diagnostics support ensemble energy as a closer released-energy match than MFE" is now **confirmed on held-out data and strengthened**: the original `energy` feature is the ViennaRNA **ensemble free energy**, reproduced to within released rounding on 85 unseen records (median excess 0).
- The V13 statement that "AUP and ALO still differ" is now **quantified and mechanistically explained**, and ALO is reclassified from "differs" to **not reproducible across engines in principle** (see Mechanism below).
- The reference-only gate in `src/rnastable/strand_reference.py` (`replay_reference` rejects any feature source other than `released_LinearPartition_features`) **stays as it is**. This study is the positive justification for keeping it, not a reason to relax it.
- `configs/strand_reference_reproduction_v1_2026-10-18.json` and the canonical STRAND run were **not modified or rerun**. No STRAND refit was performed.

## Constraints and scope, unchanged

Active scope stays **1–2,999 nt**, with historical 3,000+ nt evidence preserved, no truncation and valid annotated-CDS limits. Stage 2 remains **open**; cell-free expression Stage 3 is queued. [Scope](../configs/project_scope_2026-10-18.json) and [gate](../configs/stage2_to_stage3_gate_2026-10-18.json) remain authoritative. No numerical acceptance threshold, translation floor, assay platform/replicates or candidate budget is newly frozen. `new_sequence_scoring_enabled`, `expression_candidate_design_enabled` and `stage3_ready` remain **false** in every artifact written here.

## Completed work

### Frozen agreement criterion

**`configs/strand_rnafold_agreement_criterion_v1_2026-10-19.json`** — SHA-256 **`a003eaa22b3e4391e1de1911cdb50c3a9228d62216b402ccfa4ff31ffab2d058`**, 6,987 bytes. Written and hashed **before** any RNAfold feature for the held-out records existed. It fixes, in advance:

- **Purpose and limits.** The question is label-free engine agreement. The criterion states explicitly that it cannot close the Stage 2 gate and that passing would imply nothing about stability, translation or expression.
- **Cohort split.** Selection set = the six names already prespecified in the V1 reproduction config (`X320004D1`, `X310336T3`, `X310003T1`, `X130010D1`, `X130002D1`, `X130006D1`), declared **burned** because their RNAfold differences were already visible in V13 and therefore carrying no confirmatory weight. Evaluation set = the remaining **85** records (66 train, 10 eGFP, 9 exploratory MEV), never folded with RNAfold before this run. The decision rests on the evaluation set.
- **Tolerances as formulas, not numbers.** Per-feature tolerance = 0.05 × interquartile range of that feature across all 91 released records, computed by the script so the values were not inspected before freezing. Output tolerance = 0.10 × 0.1893218848801146 h, the published held-out eGFP RMSE of the selected with-ALO model, i.e. substitution-induced error must be at most one tenth of the model's own held-out error.
- **Released-rounding handling.** Per record and column, half-width = 0.5 × 10^(−decimals) from the released string, divided by length for `energy_per_length`. The released validation table carries GC/aup to about two decimals while the nLuc training table carries 7–9, so the validation cohort cannot evidence agreement finer than its own rounding. ALO is recomputed from the full released `bpp_per_pos` array and carries half-width 0.
- **Closed hypothesis grid.** 2 energy hypotheses × 11 ALO transforms = 22 cells, declared closed and non-extensible after any evaluation number is computed.
- **Selection then single evaluation.** One cell chosen on the burned six only; that cell plus the prespecified `identity` null scored **once** on the 85. An instability rule states that if the selected transform is worse than identity on held-out ALO, it confers no support.
- **Decision rules.** `feature_level_compatible` (all four features pass) is the only state that licenses applying unchanged published STRAND to RNAfold features. `output_level_equivalent` alone licenses only a separately named and versioned calibration, which would still need its own independent lineage-safe biological evaluation.

### Implementation

- **`src/rnastable/strand_agreement.py`** (new, 160 lines). Pure, dependency-free agreement logic: `alo_transform`, `released_decimals`, `rounding_half_widths`, `quantile`, `feature_tolerances`, `substituted_features`, `feature_deltas`, `select_cell`, `summarize`, `output_differences`, `decide`. Raises on unknown transforms, degenerate spreads, nonfinite features and incomplete feature sets.
- **`scripts/audit_strand_rnafold_agreement.py`** (new, 268 lines). Driver: verifies pinned upstream source hashes and the STRAND commit, rebuilds the 91-record inventory, checks the frozen reference-model hash, folds every record in a fresh isolated worker, asserts the folding engine identity is constant across the run, scores the grid, applies selection then single evaluation, and writes the run. `--verify-run` re-checks stored artifact hashes and replays the stored decision without folding.
- **`tests/test_strand_agreement.py`** (new, 27 tests). Covers transform semantics and rejection of unknown transforms, decimal counting, rounding half-widths including the length division, quantile interpolation, IQR tolerances and degenerate-spread rejection, GC fraction→percent conversion, the fact that the transform moves ALO but not AUP, delta/rounding-excess arithmetic, the selection rule including identity tie-breaking, pass/fail summarization, frozen-replay drift detection, every branch of `decide`, and a direct check that one zeroed position shifts ALO by log-odds(1e-10)/n.

No existing module, config, protocol or canonical run was edited.

### Canonical run

**`results/strand_rnafold_agreement_runs/20261019T172402.804593Z/`**

| Artifact | SHA-256 | Bytes |
| --- | --- | --- |
| `summary.json` | `d7a8ab3eb97b00edf6e6655505697c3acf7fa52e53f6be2b3526efba4abb8755` | 1,238 |
| `agreement.json` | `70e037d54804a967f5c8267fcdbb176abdc7bdc7387be4fc2b5bd9953efca2ef` | 106,501 |
| `per_record_features.json` | `68482ce3bae08fe3eab438c4dd64a0264e51049b19df17e6325e61072a4843b3` | 2,084,600 |
| `feature_tolerances.json` | `ae8182c5fa6f77386f9cb6a4d93bd446b37f6f8fc4401f6ef09efa8c36868da6` | 421 |
| `identity.json` | `f9bcc782e581e7c395a7480238697a501d5af5c731b9a0f7b9d2ab0a70203be2` | 868 |
| `protocol.json` | `a1b1a90d33370e786ed71d8853b818cbd197626f5ac3c9191454677fbc567f54` | 7,140 |
| `manifest.json` | `d8343c39c2ecb791825e3df1a5aa1ec0653769bcb914e18a451d43fa19fa4fc6` | 9,944 |

`protocol.json` is the criterion re-serialized at indent 2, so its hash differs from the config file's; `identity.json` records `criterion_sha256` = `a003eaa2…`, the config's own hash. Also present: `folds/<name>.json` for all 91 records (full positional paired/unpaired probability arrays, MFE and ensemble structures and energies, parameter-file hash, per-worker runtime and VmHWM) and `source/` copies of the five implementation files with their hashes. Total run size 6,736,225 bytes; `manifest.json` lists **102** artifacts.

### Protocol actually executed

- Inputs: all **91** released STRAND reference records, lengths 504–1,215 nt (68 of 91 at 928 nt), rebuilt from pinned `Data/nluc_cleaned_new_final.csv` and `Data/validate_cleaned_new_final.csv` at STRAND commit **`ea9e7de635e7cf4053c676c495b8e65717369206`**; all seven pinned STRAND source hashes re-verified at load. Per-record sequence SHA-256 checked against the frozen inventory.
- Frozen model: `reference_model.json` from `results/strand_reference_reproduction_runs/20261019T042427.196161Z`, hash **`660d07587f0c906fa3eb3663ee9ca8ccb4affaac541d67b85bd434da5018d354`** re-verified; `new_sequence_scoring_enabled` asserted false. With-ALO arm = 2 components; without-ALO arm (1 component, feature order energy/GC/aup) read from `fit/r_models.json`.
- Folding: one fresh `rnastable.ensemble_worker` subprocess per record. ViennaRNA **2.7.2**, `RNA_Turner2004`, parameter-file SHA-256 `9521527a251d5e68e6149595f8aa72aa72c63e00dc5af41d7164e6ecaa664777`, 37 °C, dangles 2, `noLP` 0, `max_bp_span` −1, `min_loop_size` 3, MFE then partition function with `exp_params_rescale`. Engine identity asserted constant across all 91 workers. Python 3.12.14.
- Resources: per-worker folding 0.607–4.940 s, **245.3 s** summed; worker VmHWM 54,392–148,004 KiB. No GPU, no network, no randomness, no seed (the computation is deterministic).
- Arithmetic guard: for every record the with-ALO prediction recomputed from the released reference features matched the frozen `python_reference_predictions.json` replay to ≤1e-10, so the comparison baseline is the frozen one.

## Results

Computed tolerances (0.05 × IQR over all 91 released records):

| Feature | Tolerance |
| --- | --- |
| `energy_per_length` | 0.005548940468588457 |
| `GC` | 0.25862068975000024 |
| `aup` | 0.002807531325000001 |
| `alo` | 0.05132036110543378 |

Selected cell: **`ensemble_energy_per_nt`** + **`two_sided_1e-05`**. Evaluation set n = 85 (66 train, 10 eGFP, 9 MEV). Rounding-excess statistics on the 85:

| Feature | median | p95 | max | tolerance | pass |
| --- | --- | --- | --- | --- | --- |
| `energy_per_length` | 0 | 0.000134807 | 0.000584968 | 0.005549 | **yes** |
| `GC` | 0 | 0 | 0 | 0.258621 | **yes** |
| `aup` | 0.000334939 | 0.00117866 | 0.00749761 | 0.002808 | **no** |
| `alo` | 0.163454 | 0.671746 | 1.15835 | 0.051320 | **no** |

Identity null on the same 85: energy and GC identical to the above; `aup` identical (the transform does not touch AUP, by design); `alo` median 0.1841, p95 0.702445, max 0.999037.

Predicted half-life differences from substitution, hours, on the 85:

| Cell | Arm | max | median |
| --- | --- | --- | --- |
| selected | with_alo | **0.01922181764201425** | 0.00250108 |
| selected | without_alo | 0.011572 | 0.000907895 |
| identity | with_alo | 0.0165832 | 0.00272575 |
| identity | without_alo | 0.011572 | 0.000907895 |

Output tolerance **0.018932188488011464 h** (the config literal `0.018932188488011462` is the same IEEE double).

**Decision: `rejected`.** `feature_level_compatible` = false and `output_level_equivalent` = false. The with-ALO output difference exceeds tolerance by 0.00028963 h, i.e. by 1.53 % — a narrow miss, equal to 10.15 % of the model's own published eGFP RMSE against the 10 % bar.

**`selection_unstable` = true.** The transform chosen on the burned six is *worse* than identity on held-out ALO at the maximum (1.15835 vs 0.999037) while slightly better at the median (0.163454 vs 0.184100). Per the frozen instability rule the selected transform **confers no support**: probability flooring and two-sided saturation of RNAfold probabilities do **not** explain the ALO gap. This was the session's main mechanistic hypothesis and it is **not supported**.

ALO rounding-excess by length group (selected cell): 928 nt n=65 max 1.1583; 1215 nt n=5 max 0.5631; 1155 nt n=5 max 0.4632; 504 nt n=6 max 0.6036; 507 nt n=3 max 0.4696; 984 nt n=1 max 0.2455. Every group fails by an order of magnitude or more; the failure is not confined to one length.

## Mechanism: why ALO cannot transfer

Across the 85 held-out records, the released LinearPartition arrays contain **1,642 exactly-zero positions** (median 16 per record, max 70) and **1,522 positions at or above 1.0** (median 2, max 110). The RNAfold arrays contain **zero of each** — no position is exactly 0 and none reaches 1.0 in any of the 91 records.

`strand_alo` is the released R rule: bound to [1e-10, 1−1e-10], then mean natural log odds. Each released zero therefore contributes −23.03 and each value ≥1 contributes +23.03, and those saturated terms dominate the mean. Worst held-out record `X310007T1` (train, 928 nt) has 41 released zeros and 102 released values ≥1 against 0 and 0 from RNAfold; reference ALO 2.8924286701344086, RNAfold ALO 1.734083500037002, difference −1.1583451700974066.

Values above 1.0 are arithmetic artifacts of LinearPartition's approximately normalized per-position probability sums (released maxima 1.000127 and 1.0003739 were observed). An exact partition function does not produce them, and `ensemble_worker` additionally clamps paired sums into [0, 1]. A floor or two-sided transform can only *create* saturation at a threshold; it cannot recreate which positions LinearPartition's beam pruning zeroed, and it cannot manufacture the above-one artifacts at all, so it pushed ALO further down for exactly the records that needed it pushed up. **The released ALO feature depends on numerical artifacts of the original engine's approximate normalization, so it is not reproducible by a correctly normalized engine in principle, not merely in practice.** Reproducing it would require the original LinearPartition version, beam width and parameterization, all of which V11–V13 record as unknown.

AUP fails differently and much more mildly: median excess 3.3e-4 and p95 1.2e-3 are inside the 2.8e-3 tolerance, and only a tail of 928-nt records reaches 7.5e-3. That is consistent with beam-pruning loss of pairing mass rather than with a definitional difference. It is a genuine disagreement — the training cohort carries 7–9 released decimals, so rounding cannot explain 7.5e-3.

## Verification performed

- **`--verify-run`** on the canonical run: **102 artifacts** re-hashed and matched, stored decision replayed from stored summaries, `criterion_sha256` confirmed as `a003eaa2…`. Mode: artifact and stored-fold audit, no new folding.
- **27 new unit tests passed**; **118 focused tests passed in 1.90 s** across the new module plus the fifteen V13 suites, confirming no regression. Command and composition are in the continuation section.
- Both new Python files parse under `ast.parse`; the new config parses as JSON.
- Pinned STRAND source hashes, STRAND commit, frozen reference-model hash, per-record sequence hashes and folding-engine identity all re-verified inside the run.
- Per-record reference-feature arithmetic matched the frozen V13 replay to ≤1e-10 for all 91 records.

**Not run and therefore unverified:** no STRAND refit, no R execution, no RiboNN inference, no BoTorch run, no custom-model training or study replay, no full repository test suite, no GitHub publication and no network access of any kind this session. No previously measured result was re-measured.

## Scientific interpretation and limits

What this session establishes, on 85 records never previously folded:

1. The original `energy` feature is the **ensemble free energy**, not the MFE. Median rounding-excess 0 and max 5.85e-4 against a 5.55e-3 tolerance is a clean held-out confirmation of V13's six-sequence hint.
2. `GC` transfers exactly — max excess 0 across all 85.
3. `aup` transfers to within tolerance for about 95 % of records but not in the tail.
4. `alo` does not transfer, by a factor of 3–23, and the reason is structural rather than a tuning gap.
5. Therefore **unchanged published STRAND must not be applied to RNAfold-derived features.** The reference-only adapter stays closed.

What must **not** be claimed from this work: any stability, half-life, translation or expression result; any Stage 2 progress; any validation of STRAND on new sequences; any coverage of the 1–2,999 nt scope. The 91 records are highly redundant (68 of 91 at 928 nt, all nLuc/eGFP/MEV constructs from one study), so this is engine agreement on a narrow construct family, not scope coverage. The held-out 85 are lineage-safe with respect to *hypothesis selection* only — 66 of them were used to fit the reference model, so they are legitimate unseen inputs for a label-free engine comparison but carry no weight as independent biological evidence.

Two observations that are **reported, prespecified, and deliberately not acted on**:

- The **without-ALO arm is output-equivalent** under ensemble-energy substitution: max 0.011572 h, inside the 0.018932 h tolerance, and 5.32 % of that arm's own published eGFP RMSE of 0.2174279666658343 h. Its feature set (energy, GC, aup) excludes precisely the one feature that cannot transfer. The criterion specifies the without-ALO arm as reported-only; the decision is defined on the with-ALO arm, which is the published selection. This is a lead for a separately frozen criterion, not a result that licenses anything.
- The **identity null's** with-ALO output difference, 0.0165832 h, would have fallen inside the tolerance. Switching the decision to identity now would be exactly the post-hoc selection the frozen protocol exists to prevent, so it was not done. A v2 criterion prespecifying identity as the single hypothesis is a legitimate next step and would need its own fresh evaluation evidence.

Rejected approaches: probability flooring and two-sided saturation as a route to ALO compatibility (held-out-unstable and mechanistically ruled out); substituting RNAfold features into the unchanged published model (rejected by the criterion); relaxing the ALO tolerance or the output tolerance after seeing the 1.53 % miss (not done — the criterion was frozen first and its result stands).

## Pending work, prioritized

1. **Define the separately named RNAfold calibration.** Freeze `strand_rnafold_calibration_v1` as a new, versioned model **refit on RNAfold ensemble features** — not a substitution into published coefficients — with the feature set chosen in advance. The evidence above argues for dropping ALO, but that choice must be prespecified in a v2 criterion and evaluated on evidence not used to make it, with a prespecified agreement/accuracy criterion. The name must never be presented as published STRAND.
2. **Keep the reference-only gate closed** until item 1 completes. `replay_reference` must keep rejecting non-released feature sources; no code change is needed and none should be made opportunistically.
3. **V13 item 2** (unstarted): versioned score records binding sequence/annotation/tool/settings/weight identities, units or target scale, exclusion reason and raw artifact paths; select the RiboNN named task and the stability/translation floor for the intended assay with supporting evidence.
4. **V13 item 3** (unstarted): Stage 2 independent/native/resource/constraint/replay requirements, especially sparse 2,000–2,999 nt coverage. Only after explicit gate review should parents/allowed edits, biological objective, budgets and the cell-free assay protocol be frozen. Keep BO/random/greedy feasibility and evaluation budgets matched.
5. **Optional**: publish this session's criterion, module, script, tests and concise run evidence to GitHub. Not done this session; if done, fetch latest upstream first and preserve the repository README diagram `diagram_10182026.png` and its Markdown, per the standing rule.

Do not infer expression benefit from software execution, and do not optimize actual expression candidates while the Stage 2 gate stays open. No combined biologically validated candidate-scoring command exists yet.

## Outstanding processes

None. All folding workers exited; the 245.3 s of folding was synchronous and completed. No background job, partial run or pending approval remains from this session. Other system processes were not exhaustively audited.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-19_V1.md
cat reports/RNA-StableAI_HANDOFF_2026-10-18_V13.md
cat configs/strand_rnafold_agreement_criterion_v1_2026-10-19.json
cat configs/stage2_to_stage3_gate_2026-10-18.json

# This session's result, cheapest first:
cat results/strand_rnafold_agreement_runs/20261019T172402.804593Z/summary.json
cat results/strand_rnafold_agreement_runs/20261019T172402.804593Z/feature_tolerances.json
PYTHONPATH=src:scripts .venv/bin/python scripts/audit_strand_rnafold_agreement.py \
  --verify-run results/strand_rnafold_agreement_runs/20261019T172402.804593Z

# Earlier canonical local artifact/cached checks, unchanged from V13:
PYTHONPATH=src .venv/bin/python scripts/verify_four_component_build.py results/four_component_build_runs/20261019T041458.024816Z
PYTHONPATH=src .venv/bin/python scripts/reproduce_strand_reference.py --verify-run results/strand_reference_reproduction_runs/20261019T042427.196161Z
PYTHONPATH=src .venv/bin/python scripts/run_ribonn_fixed_inference.py --verify-run results/ribonn_fixed_inference_runs/20261019T045101.117038Z
```

Focused suite, 118 tests, no new study fit:

```bash
cd /home/zyliu/Documents/rna-stable-ai
PYTHONPATH=external/four_component_deps:src:scripts .venv/bin/python -m pytest -q \
  tests/test_strand_agreement.py tests/test_component_integration.py tests/test_discrete_bo.py \
  tests/test_strand_reference.py tests/test_ribonn_integration.py tests/test_crw_panel_exposure.py \
  tests/test_crw_original_provenance.py tests/test_rcsb_long_source_survey.py tests/test_project_scope.py \
  tests/test_stage2_scope_audit.py tests/test_endpoint_ranking.py tests/test_hard_negative_supervision.py \
  tests/test_recovery_ceiling.py tests/test_endpoint_assignment.py tests/test_sampled_pair_supervision.py \
  tests/test_long_exact_sparse_pairs.py
```

Re-running the audit from scratch creates a **new** timestamped run directory and re-folds all 91 records (about 245 s of worker time; needs `external/four_component_deps` on `PYTHONPATH` for ViennaRNA):

```bash
cd /home/zyliu/Documents/rna-stable-ai
PYTHONPATH=external/four_component_deps:src:scripts .venv/bin/python scripts/audit_strand_rnafold_agreement.py
```

The criterion config is frozen; do not edit it to change an outcome. A different hypothesis set requires a new versioned criterion file and a new run. Fresh STRAND refit and RiboNN inference commands remain in V12/V11 and the integration guide and need the retained local sources, weights and environments. Do not pass concise published summaries as full local runs. Preserve all previous versioned handoffs.
