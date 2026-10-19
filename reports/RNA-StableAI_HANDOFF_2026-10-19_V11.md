# RNA-StableAI handoff — 2026-10-19 V11

Project: RNA-StableAI
Date: 2026-10-19, America/Los_Angeles
Version: V11
Workspace: `/home/zyliu/Documents/rna-stable-ai`
Selected architecture: **RNAfold + STRAND + RiboNN + BoTorch**
Immediately previous handoff: [V10](RNA-StableAI_HANDOFF_2026-10-19_V10.md), RiboNN per-task evidence. Assay definition and the Stage 3 conflict: [V8](RNA-StableAI_HANDOFF_2026-10-19_V8.md), [V9](RNA-StableAI_HANDOFF_2026-10-19_V9.md). Band availability: [V7](RNA-StableAI_HANDOFF_2026-10-19_V7.md). Publication: [V5](RNA-StableAI_HANDOFF_2026-10-19_V5.md).

## Scope of this session

The user supplied three decisions and one planning bound. All are recorded, and two long-standing blockers close as a result.

| Input | Decision |
| --- | --- |
| Stage 3 target | **Amend the gate to transfected cells** |
| ORF edits | **Must be synonymous** |
| T-cell arm | **Declare model-blind** |
| CV | **Use below 20 % for both readouts** |
| Transcript / UTRs | still pending, waiting on colleagues |

Delivered: an amended gate as a new versioned file, assay definition v3, and the first **RiboNN task selection**. Also a finding about the repository's full test suite that I should have surfaced earlier. No inference run, no scoring, no publication.

## The gate is amended

**`configs/stage2_to_stage3_gate_v2_2026-10-19.json`** — SHA-256 **`8ca6b32e8aa9389037c299a6d1cbcb47f41dc3b0cd35f806931c17fba40bceef`**.

`stage3_target` changes from `cell_free_expression` to **`transfected_cell_expression`**, resolving the conflict raised in V8 and carried through V9 and V10.

**What did not change, verified programmatically:** all six `requirements_before_stage3` are byte-identical to the 2026-10-18 gate, the active length scope is unchanged, `requirements_satisfied` is **0**, and `stage3_ready` is false. Amending the target satisfies, relaxes and reorders nothing. The previous gate is **frozen and unedited**, confirmed still at SHA-256 `956fef4d…`, and is retained because existing frozen runs reference it.

The amendment record names the authorising instruction, where the conflict was raised, and the artifacts that now carry a stale cell-free target.

### Stale artifacts that still say cell-free

The amendment makes three live artifacts wrong, and **one of them is published**:

1. **`README.md`** — the cell-free first-target statement, currently live at commit `1ca32bb3ea4eaf05c4931fa1060be64c6d1cd82d`.
2. **`diagram_10192026.svg`** — the gated box reads "Cell-free expression / Stage 3 target". Also published.
3. **`reports/PROJECT_ROADMAP_2026-10-18.md`** if it repeats the target.

I have **not** edited any of them. Correcting the README and the diagram changes published material, which is a publication decision rather than a config change. Handoffs up to V10 are historical records and must **not** be rewritten; they correctly describe what was believed at the time.

## Three decisions recorded

**`configs/assay_definition_v3_2026-10-19.json`** — SHA-256 **`97be8d631c563e1ba36c4ebaa41d8648d9c7e8319b9e7bbaf7ede34df2e0272b`**. V1 and V2 remain frozen and unedited at `37d47273…` and `4e32c4d1…`.

**ORF edits are synonymous-only.** This resolves the question V9 flagged as consequential and left at `assumed_default: null`. Because the encoded 550 aa protein is now invariant across the panel, enzyme specific activity is constant, and luminescence differences cannot be caused by a changed protein. **That is precisely what licenses reading luminescence as an mRNA-level effect.** The config adds a validation rule: a proposed ORF variant must translate to exactly the parent protein under the standard genetic code; one changed residue makes it invalid, not merely risky.

**The T-cell arm is model-blind.** No RiboNN task is applied to it, and none may be inferred from the A549 arm.

**CV below 20 % for both readouts** — recorded as `bound_supplied_not_measured`.

### The CV bound leaves the design underpowered for its own target

This needs to be said plainly because the bound chosen is the worst case I flagged in V9. At CV 20 % with 3 replicates:

- power to detect 1.5-fold is **54.2 %** — a real effect of the target size is missed about half the time
- the minimum detectable effect at n=3 becomes **1.75-fold**, larger than the 1.5-fold target

At CV 10 % the same design gives 96.7 %. So "below 20 %" spans the range from comfortable to inadequate, and the design's validity depends on where the real number falls. The config records the rule: either the measured CV comes in nearer 10 %, or replicates rise to **5**, or the analysis is **paired across cell types** (6 paired units reach 98.9 % at CV 20 %), or the reported outcome becomes the minimum detectable effect rather than the 1.5-fold target.

**Floors remain unfrozen.** A bound is not a measurement, `configs/score_record_schema_v1_2026-10-19.json` requires measurement error, and no decision cost has been stated for a false accept versus a false reject.

## First RiboNN task selected

**`configs/ribonn_task_selection_v1_2026-10-19.json`** — SHA-256 **`12e03e87b595936fd4fd8e8bb1013edce06ec5e74ed234cd740bfc6745516056`**.

**Arm A549 → task `predicted_TE_A549`.** All four blockers that V8 and V9 recorded are now cleared: the assay is defined, it is not cell-free, per-task accuracy exists, and training overlap is known.

Evidence cited from `results/ribonn_task_evidence_runs/20261019T202103.166652Z`: Pearson **0.7092**, R² 0.5013, n = 9,776, **rank 23 of 78**, above the 0.6878 median; 97.4 % of released transcripts carry an A549 measurement; training overlap **none**.

The applicability argument does not paper over the gap it has to cross. RiboNN was trained only on endogenous human APPRIS transcripts; the assay construct is a designed, codon-optimized reporter at GC3 0.996, far outside the endogenous distribution. The config therefore permits **ranking and correlation within the A549 arm only** and prohibits calibrated TE prediction, any prediction of luminescence, transfer to the T-cell arm, and treating a score as evidence of expression benefit. It also records a falsification condition: once luminescence exists, the correlation is testable, and a null or negative result means the selection is **withdrawn rather than reinterpreted**.

For the T-cell arm the config records why no task was chosen: scanning all 78 tasks found no CD3, no CD8 and no activated-state task; the only primary T-cell task is Primary_CD4+_T-cells at Pearson 0.6688, rank 47 of 78, differing in subset composition and unknown activation state; and the better-scoring lymphoid tasks are all transformed lines — MM1.S 0.7834 myeloma, LCL 0.7559, Molt-3 0.7021 T-ALL. Choosing one of those for its higher number would trade a biological mismatch for a numerical one.

## A reporting gap I should have surfaced earlier

Every handoff today has reported a **focused suite** — most recently 235 tests. That is a curated subset, which the handoffs do say, but I had not run the **full** repository suite at any point today. I ran it now: **1,086 passed, 8 failed in 219 s.**

All 8 failures are in `tests/test_replay_source_archive.py` and share one cause: `scripts/archive_replay_sources.py` shells out to the `rg` binary, and **ripgrep is not installed as an executable in this environment**. `command -v rg` resolves only because `rg` is defined as a *shell function* in the interactive profile, which `subprocess` cannot invoke, so every call raises `FileNotFoundError: [Errno 2] No such file or directory: 'rg'`.

**These failures are pre-existing and not caused by today's work.** Both the test module and the script are dated 2026-10-13, neither references anything added today, and the failure is an environment dependency rather than a logic error. The practical consequence is that `scripts/archive_replay_sources.py` cannot run here at all; installing ripgrep as a real binary, or replacing the `rg` call with a Python file walk, would fix it. I have not changed either file.

## Verification performed

- Gate amendment scope verified programmatically: requirements list and active scope byte-identical to the previous gate, `requirements_satisfied` 0, `stage3_ready` false, previous gate hash unchanged.
- Assay v1 and v2 re-hashed and confirmed unedited; all mutation flags in v3 and in the task-selection config confirmed false except the intended `task_selected_for_a549`.
- **Focused suite: 235 passed.** **Full suite: 1,086 passed, 8 failed**, cause diagnosed and attributed above.
- Gate-dependent checks re-run after the amendment and still passing: `audit_stage2_under3000.py --verify-run` and `audit_band_clan_availability.py --verify-run`. Both read the 2026-10-18 gate, which is intentionally unchanged.

**Not run and therefore unverified:** no sequence folded or scored, because the transcript is still pending; no RiboNN inference run under the new selection; the README, diagram and roadmap were not corrected; nothing was published.

## Scientific state

Stage 2 gate **open, 0 of 6 requirements satisfied** — unchanged by the amendment. RNAfold substitution into published STRAND **rejected**. `strand_rnafold_calibration_v1` has **no independent validation**. **No composite score permitted.** **No sequence carries both a stability and a translation score.** The 2,000–2,999 nt band is unresolvable from Rfam seed and the PDB. No stability, translation or expression benefit is established. Published snapshot remains `1ca32bb3…`; V6–V11 are **local and unpublished**.

What changed: the Stage 3 target now matches the lab, ORF edits are constrained to synonymous, the A549 arm has a selected task, and the T-cell arm is explicitly model-blind.

## Pending work, prioritized

1. **The transcript.** 5′UTR and 3′UTR sequences, the parent construct, and plasmid-versus-IVT-mRNA. Nothing can be folded or scored without them. Also needed eventually: poly(A) presence and length, cap and modification chemistry, and Ping's authoritative CDS.
2. **Correct the stale cell-free artifacts** — README and `diagram_10192026.svg` are published and now wrong. I can prepare both and publish V6–V11 together on your word.
3. **Measured CVs**, to replace the bound and let a floor be frozen. Also decide replicates or pairing, given the 54.2 % power at the bound.
4. **State the decision cost** for a false accept and a false reject, the remaining input any floor needs.
5. **Decide band requirement 3** from V7: retrain to free the two RF02462 records, amend the requirement, or accept the band as a documented limitation.
6. **Decide the OpenVaccine acquisition** from V6 — still the only route to evaluating `strand_rnafold_calibration_v1` against its own target.
7. **Optional, no input needed:** pin down whether RiboNN's primary CD4+ samples were resting or activated; fix or replace the `rg` dependency in `scripts/archive_replay_sources.py`.

Do not infer expression benefit from software execution, and do not optimize actual expression candidates while the gate stays open.

## Outstanding processes

None. All work was synchronous. No background job or pending approval remains.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-19_V11.md
cat configs/stage2_to_stage3_gate_v2_2026-10-19.json     # stage3_target now transfected_cell_expression
cat configs/assay_definition_v3_2026-10-19.json
cat configs/ribonn_task_selection_v1_2026-10-19.json

# Confirm the amendment changed only the target:
.venv/bin/python -I -c "
import json
new=json.load(open('configs/stage2_to_stage3_gate_v2_2026-10-19.json'))
old=json.load(open('configs/stage2_to_stage3_gate_2026-10-18.json'))
print('requirements unchanged:', new['requirements_before_stage3']==old['requirements_before_stage3'])
print('scope unchanged:', new['active_length_nt']==old['active_length_nt'])
print('target:', old['stage3_target'], '->', new['stage3_target'])
print('satisfied:', new['requirements_satisfied'])
"

# Focused suite, 235 tests:
PYTHONPATH=external/four_component_deps:src:scripts .venv/bin/python -m pytest -q \
  tests/test_ribonn_task_evidence.py tests/test_band_availability.py tests/test_stage2_census.py \
  tests/test_score_records.py tests/test_strand_agreement.py tests/test_strand_rnafold_calibration.py \
  tests/test_component_integration.py tests/test_discrete_bo.py tests/test_strand_reference.py \
  tests/test_ribonn_integration.py tests/test_crw_panel_exposure.py tests/test_crw_original_provenance.py \
  tests/test_rcsb_long_source_survey.py tests/test_project_scope.py tests/test_stage2_scope_audit.py \
  tests/test_endpoint_ranking.py tests/test_hard_negative_supervision.py tests/test_recovery_ceiling.py \
  tests/test_endpoint_assignment.py tests/test_sampled_pair_supervision.py tests/test_long_exact_sparse_pairs.py

# Full suite: 1,086 pass, 8 fail; the 8 need a real ripgrep binary, not a shell function.
PYTHONPATH=external/four_component_deps:src:scripts .venv/bin/python -m pytest -q tests/
```

All eleven 2026-10-19 configs are frozen; do not edit any to change an outcome. Supersede with a new version instead, as the gate, assay and task-selection configs do. The 2026-10-18 gate stays in place for runs that reference it; new work should cite the v2 gate. Preserve all previous versioned handoffs, including those that describe the cell-free target, which were correct when written.
