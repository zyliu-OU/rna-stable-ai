# RNA-StableAI handoff — 2026-10-19 V8

Project: RNA-StableAI
Date: 2026-10-19, America/Los_Angeles
Version: V8
Workspace: `/home/zyliu/Documents/rna-stable-ai`
Selected architecture: **RNAfold + STRAND + RiboNN + BoTorch**
Immediately previous handoff: [V7](RNA-StableAI_HANDOFF_2026-10-19_V7.md), band clan availability. The six assay questions were posed in [V6](RNA-StableAI_HANDOFF_2026-10-19_V6.md#six-questions-the-user-is-preparing-answers-to).
Publication record: [V5](RNA-StableAI_HANDOFF_2026-10-19_V5.md). Score records: [V3](RNA-StableAI_HANDOFF_2026-10-19_V3.md). Named calibration: [V2](RNA-StableAI_HANDOFF_2026-10-19_V2.md). Engine agreement: [V1](RNA-StableAI_HANDOFF_2026-10-19_V1.md).

## Scope of this session

The user answered all six assay questions and supplied an example firefly luciferase CDS. Delivered: validation of that sequence, confirmation that matching RiboNN tasks exist, a power calculation for the stated design, and a frozen assay-definition config.

**One answer conflicts with a frozen config and with published material. It is flagged for the user's decision and was not absorbed silently.** No task was selected, no floor frozen, no gate amended, no inference run, no publication made.

## The answers, as given

| Question | Answer |
| --- | --- |
| 1. Cell-free or transfected cells? | **Transfected cells or in vivo.** "We all do transfected cells or in vivo assay for monitoring expression level." |
| 2. mRNA measured over time? | **Yes.** RT-PCR to monitor RNA stability, comparing before and after sequence optimization. |
| 3. Endpoint or time course? | **Time course** at this stage. |
| 4. What varies between constructs? | **Both** UTRs and codon usage. |
| 5. Replicates and dynamic range? | Aiming for **1.5-fold enhancement**, **3 replicates**, across different cell types, e.g. **A549 and T-cell**. |
| 6. Which luciferase and UTR scaffold? | **Fluc**, with an example CDS supplied. Authoritative sequence pending from a colleague referred to as Ping. **UTR scaffold not supplied.** |

## Decision required from the user: the Stage 3 target conflicts with the assay

`configs/stage2_to_stage3_gate_2026-10-18.json` records `"stage3_target": "cell_free_expression"` — verified by reading the file, not recalled. The user's assay is **transfected cells or in vivo**. These disagree.

The cell-free framing is not confined to that config. It is repeated in the **published README** ("the first planned expression system remains **cell-free**", still live at commit `1ca32bb3…`), in V13's "cell-free first target", and in the V3 score-record schema's reasoning about why no RiboNN task matched. Every one of those statements is now inconsistent with how the lab actually works.

**This requires a gate review decision, which is yours:**

1. **Amend the Stage 3 target** to the transfected-cell assay. Consequence: the cell-free statements in the gate, the README and the roadmap need correcting, and the published README is currently wrong on this point.
2. **Keep cell-free as the Stage 3 target** and treat the luciferase assay as a separate proxy track with its own objective.

I have **not** amended the gate, the scope, the README or any published claim. `gate_amended` is false in the new config. Until you decide, the project has two incompatible statements of its own target, and that is the single most consequential open item in this handoff — more than any band or calibration question, because it determines what the whole pipeline is aiming at.

## Completed work

### Frozen assay definition

**`configs/assay_definition_v1_2026-10-19.json`** — SHA-256 **`37d47273645c32c8939c246fa2edcc2ec35fb54e409aa1638cff7d416791a45a`**, 8,808 bytes. All of `gate_amended`, `task_selected`, `floors_frozen`, `new_sequence_scoring_enabled`, `expression_candidate_design_enabled` and `stage3_ready` are false.

It records the two readouts and that both are time courses, the cell types with the T-cell identity marked unspecified, the replicate count and target effect, the design space, the reference construct with its validation, the RiboNN candidates and what still blocks selection, both floors as unselected with their blockers, the gate conflict above, and four no-claim statements.

### Reference CDS validated

The supplied sequence checks out as a coding sequence and is consistent with firefly luciferase:

| Property | Value |
| --- | --- |
| Length | **1,653 nt**, 551 codons |
| Protein | **550 aa**, no internal stops |
| Start / stop | `ATG` / `TGA` |
| GC fraction | 0.6534 |
| **GC3 fraction** | **0.996** |
| SHA-256 (uppercase DNA) | `86322fc15d89f604e34e3a3fb275f059adb834f7dc904f97f20c44498ba9168d` |
| N-terminus | `MEDAKNIKKGPAPFYPLEDGTAGEQLHKAMKRYALVPGTIAFTDA` |

The N-terminal sequence and 550 aa length are consistent with firefly luciferase. **I did not align it against a reference database, so the exact variant is not asserted.**

Two observations that matter for the work:

- **GC3 is 0.996** — only 1 adenine and 1 thymine across 551 third codon positions. The construct is already at essentially maximal human codon optimization, so codon-usage variation from this starting point can realistically only *reduce* GC3. Any claim that the pipeline "optimizes codon usage" relative to this parent needs to say in which direction and why.
- Codon edits move GC content and folding free energy, which are **STRAND features**. So the stability side responds to codon changes as well as UTR changes, and the two axes of the design space are not independent in their effect on model scores.

**Blocking gap: the UTR scaffold was not supplied.** A scorable transcript needs 5′ UTR + CDS + 3′ UTR, and RiboNN additionally requires integer `utr5_size` and `cds_size`. **No component can score this construct until the UTRs arrive.** STRAND's released constructs used hHBB 5′ and 3′ UTRs; whether this assay uses the same scaffold is unknown.

### RiboNN task selection: two of four blockers cleared

V3 recorded four blockers. Checking the released task inventory against the stated cell types:

| Cell type | Matching released tasks |
| --- | --- |
| A549 | `predicted_TE_A549` |
| T cell | `predicted_TE_Primary_CD4._T.cells`, `predicted_TE_HSB2`, `predicted_TE_Molt.3` |

- **Blocker 1, intended assay undefined — resolved** by this config.
- **Blocker 2, no released task is cell-free — moot.** The assay is in transfected cells, and matching tasks exist. V3's reasoning was sound but rested on the cell-free premise, which was mine, not the lab's.
- **Blocker 3, no per-task accuracy evidence locally — still blocking.** Only per-checkpoint validation R² is held, 0.4847–0.5372 across 50 human checkpoints. Upstream per-task metrics have not been retrieved; they may be obtainable, which would be a bounded next step.
- **Blocker 4, per-task training overlap unknown — still blocking.**

Two further blockers are now visible: the T-cell type is not pinned, so that task cannot be chosen; and a designed Fluc reporter is out-of-distribution for tasks trained on endogenous human transcripts, so applicability needs its own argument. **No task was selected.** Name matching between a cell line and a task label is not evidence, and the config says so.

### Power analysis for the stated design

For a two-sample t-test at α = 0.05 two-sided with 80% power, detecting a **1.5-fold** change:

| Replicates per group | Maximum tolerable CV |
| --- | --- |
| **3** | **≈ 14.1 %** |
| 4 | ≈ 18.6 % |
| 5 | ≈ 22.2 % |
| 6 | ≈ 25.3 % |

So the stated design of 3 replicates is adequate **only if the assay CV is at or below roughly 14 %**. Transfection-based luciferase assays frequently run above that unless dual-reporter normalisation is used. **The measured CV was not supplied and is now the single remaining input needed for any floor**, per the requirement already written into `configs/score_record_schema_v1_2026-10-19.json`. If the real CV is above ~14 %, the options are more replicates or tighter normalisation, and the 1.5-fold target should be restated as a detectable effect rather than an assumed one.

### Three distinct quantities, recorded explicitly

The config records each mismatch and what may be claimed:

| Component | Predicts | Assay measures | Permitted claim |
| --- | --- | --- | --- |
| STRAND, `strand_rnafold_calibration_v1` | in-solution half-life, purified RNA in buffer, hours | **in-cell** mRNA decay by RT-qPCR | correlation only, explicitly labelled |
| RiboNN released tasks | TE of endogenous human transcripts, released scale | luminescence from a designed reporter | ranking or correlation, not calibrated prediction |
| nothing in the stack | — | relative light units | none, until a model is fitted to the lab's own data and independently evaluated |

The first row matters most and is easy to get wrong: **the RT-PCR time course does not validate either stability model against its own target.** In-cell decay runs through deadenylation, decapping, exonucleolytic and miRNA-directed pathways that a buffer degradation measurement does not contain. This is the same class of error as the ALO engine mismatch in V1 — a quantity substituted for a different quantity because both are called "stability". The assay is nonetheless the most useful stability data the project has access to, because the lab controls the sequences and defines the annotation exactly.

## Verification performed

- Gate conflict grounded by reading `configs/stage2_to_stage3_gate_2026-10-18.json` (`stage3_target = cell_free_expression`) and confirming the README still contains the cell-free framing.
- CDS validated arithmetically: length divisible by three, single reading frame, zero internal stops, terminal stop present, GC and GC3 computed, translation performed with a standard codon table, SHA-256 recorded.
- RiboNN candidate tasks confirmed present in `results/score_record_runs/20261019T175011.658062Z/ribonn_task_inventory.json`, searched across eight cell-type patterns.
- Power figures computed numerically with the non-central t distribution via `scipy.stats.nct`, bisecting on the standard deviation, not approximated by a rule of thumb.
- All six mutation flags in the new config asserted false programmatically.

**Not run and therefore unverified:** the CDS was not aligned to a reference database, so the exact luciferase variant is unasserted; no sequence was folded, scored or submitted to any component, because the UTR scaffold is missing; upstream RiboNN per-task metrics were not retrieved; no inference, refit, census or publication occurred; the focused test suite was not re-run because no module or test changed; **220 focused tests** remain the last recorded state, from V7.

## Scientific state

Unchanged by this session. The Stage 2 gate is **open with 0 of 6 requirements satisfied**; RNAfold substitution into published STRAND is **rejected**; `strand_rnafold_calibration_v1` has **no independent validation**; **no composite score exists or is permitted**; **no sequence carries both a stability and a translation score**; the 2,000–2,999 nt band is unresolvable from Rfam seed and the PDB. No stability, translation or expression benefit is established. Published snapshot remains commit `1ca32bb3ea4eaf05c4931fa1060be64c6d1cd82d`; V6, V7 and V8 are **local and unpublished**.

What did change is that the assay is now defined, which unblocks the *path* to task selection and floors without satisfying either.

## Pending work, prioritized

1. **Decide the Stage 3 target conflict** — amend the gate to the transfected-cell assay, or keep cell-free and treat this as a proxy track. Everything downstream of the objective depends on this, and the published README is currently inconsistent with the lab's practice either way.
2. **Supply the UTR scaffold**, 5′ and 3′, and the authoritative construct sequence from Ping. Until then nothing can be scored, because a bare CDS is not a transcript and RiboNN needs numeric boundaries.
3. **Supply the measured assay CV.** It is the last input needed for a floor, and it determines whether 3 replicates can detect 1.5-fold at all.
4. **Pin the T-cell type** (primary CD4+ versus a line such as HSB2 or Molt-3) so the corresponding task can be considered.
5. **Retrieve upstream RiboNN per-task accuracy and training-overlap evidence.** Bounded, needs no decision from you, and would clear the two remaining task-selection blockers. I can do this.
6. **Decide requirement 3** from V7: retrain to free the two RF02462 records, amend the requirement by gate review, or accept the band as a documented limitation.
7. **Decide the OpenVaccine acquisition** from V6 — the pinned in-solution degradation source whose bytes were never downloaded, and still the nearest route to an independent evaluation of the calibration *against its own target*, which the luciferase assay cannot provide.
8. **Publish V6–V8** if wanted. Not done. Preserve `diagram_10192026.svg`, its README Markdown and the retained `diagram_10182026.png`. Note that the README's cell-free statement should be corrected in the same publication if item 1 resolves that way; the workflow diagram would also need its cell-free box relabelled.

Do not infer expression benefit from software execution, and do not optimize actual expression candidates while the gate stays open.

## Outstanding processes

None. All validation was synchronous. No background job or pending approval remains. The example CDS is recorded by hash in the config; the raw sequence text lives only in this conversation and in session scratch, so the authoritative sequence from Ping should be committed to a proper input inventory when it arrives.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-19_V8.md
cat configs/assay_definition_v1_2026-10-19.json
cat configs/stage2_to_stage3_gate_2026-10-18.json     # stage3_target still reads cell_free_expression

# Confirm the RiboNN candidate tasks and the recorded blockers:
cat results/score_record_runs/20261019T175011.658062Z/ribonn_task_inventory.json

# Local verifications, all offline, unchanged from V7:
PYTHONPATH=src:scripts .venv/bin/python scripts/audit_band_clan_availability.py \
  --verify-run results/band_clan_availability_runs/20261019T185713.116447Z
PYTHONPATH=src:scripts .venv/bin/python scripts/audit_stage2_band_coverage.py \
  --verify-run results/stage2_band_coverage_census_runs/20261019T180243.655199Z
PYTHONPATH=src:scripts .venv/bin/python scripts/build_score_records.py \
  --verify-run results/score_record_runs/20261019T175011.658062Z
PYTHONPATH=src:scripts .venv/bin/python scripts/fit_strand_rnafold_calibration.py \
  --verify-run results/strand_rnafold_calibration_runs/20261019T174049.053308Z
PYTHONPATH=src:scripts .venv/bin/python scripts/audit_strand_rnafold_agreement.py \
  --verify-run results/strand_rnafold_agreement_runs/20261019T172402.804593Z
```

Focused suite, 220 tests, is listed in [V7](RNA-StableAI_HANDOFF_2026-10-19_V7.md#exact-continuation-commands); no code changed this session, so it was not re-run.

All six 2026-10-19 configs are frozen; do not edit any to change an outcome. The assay-definition config may be superseded by a v2 when the UTR scaffold, the authoritative sequence, the CV and the T-cell identity arrive — supersede it with a new version, do not edit it. Selecting a RiboNN task or freezing a floor each require their own versioned config with evidence. Amending the Stage 3 target requires an explicit gate review and a new versioned gate file; no config, module or script may do it. Preserve all previous versioned handoffs.
