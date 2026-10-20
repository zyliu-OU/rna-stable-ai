# Remaining limitations before expression candidate design — 2026-10-19

- **Project:** RNA-StableAI
- **Workspace:** `/home/zyliu/Documents/rna-stable-ai`
- **Purpose:** Satisfy Stage 2 gate requirement 6,
  `Document_remaining_limitations_before_expression_candidate_design`
  (`configs/stage2_to_stage3_gate_v2_2026-10-19.json`).
- **Status of this document:** a complete statement of known limitations as of
  2026-10-19. **It does not itself mark the requirement satisfied** — that is a
  gate-review judgement, recorded separately.

This document exists so that nobody begins designing expression candidates
without knowing what the stack cannot currently support. Each limitation names
the artifact that establishes it. Where a limitation is unresolved, it says so
rather than offering a workaround.

---

## A. Limitations that bound what any score can mean

### A1. No component represents N1-methylpseudouridine

Every uridine in the molecules to be assayed is **m1Ψ**, confirmed by the
collaborator (cap 1 analogue, Hongene ON-134, with m1Ψ). RNAfold, STRAND,
`strand_rnafold_calibration_v1` and RiboNN all treat the sequence as canonical U.

- Computed structures and free energies are **not those of the assayed
  molecule**. This bears directly on the stability arm.
- The modification is **constant across the panel**, so it does not by itself
  confound a *ranking* of constructs that differ in sequence.
- That ranking argument assumes the modification's effect is
  **sequence-independent**, which is **unverified** and may not hold.

*Evidence:* `configs/transcript_inputs_v1_2026-10-19.json`
(`modelling_consequences.m1_pseudouridine_is_now_a_live_limitation`).

### A2. The two score sides are incommensurable; no composite is permitted

Stability is in **hours** on the released STRAND in-solution scale. Translation
is on a **released RiboNN task scale** with no inverse transform or physical
unit. No weighting is justified and no floor is selected.

The first record carrying both sides exists
(`results/reference_score_record/FLUC-REF-V1_score_record.json`,
`records_with_both_sides: 1`) and **emits no composite score**. Having both sides
available is precisely when combining them becomes tempting; the prohibition in
`score_record_schema_v1` stands.

### A3. Nothing in the stack predicts the assay's own units

No component predicts relative light units, or in-cell mRNA decay. The
quantity mismatches are recorded in `assay_definition_v3`:

| Component | Predicts | Assay measures |
|---|---|---|
| `strand_rnafold_calibration_v1` | in-solution half-life of purified RNA in buffer (hours) | in-cell mRNA decay by RT-qPCR |
| RiboNN `predicted_TE_A549` | translational efficiency of endogenous human transcripts | luminescence from a designed reporter |
| none | — | expression in the assay's own units |

Permitted claims are **correlation or ranking, explicitly labelled**. Calibrated
prediction is not available from any component.

---

## B. Limitations of the stability arm

### B1. The published STRAND model is not applicable

`configs/strand_rnafold_agreement_criterion_v1_2026-10-19.json` returned
`feature_level_compatible: false`, `output_level_equivalent: false`,
`outcome: rejected`. The unchanged published coefficients **may not** be applied
to RNAfold-derived features. Every stability score therefore comes from a
separately named refit.

### B2. That refit is unvalidated

`strand_rnafold_calibration_v1` has **no independent evaluation** against
held-out measurements. It is recorded as not published and not validated, and
every score entry carries `independent_validation: false`.

### B3. The engine incompatibility is unresolved, and localised to `alo`

`energy_per_length` agrees with the released LinearPartition features to
**1.4 × 10⁻⁵** and `aup` agrees 5/6, while `alo` agrees 2/6. Two hypotheses were
excluded (the clipping convention; the CONTRAfold model — STRAND used Vienna
parameters). A small-pair cutoff near 1e-6 improves `alo` to 3/6 but was **not
adopted**, being tuned on six burned records.

**Closed without resolution by decision on 2026-10-19.** The blinded 85-record
evaluation set remains **unspent**.

*Evidence:* `reports/alo_convention_investigation_2026-10-19.md`.

### B4. Folding features depend on an unbounded base-pair span

`max_bp_span: -1` is now an explicit decision, because every bounded alternative
moved features further from the reference engine. **The caveat stands:** features
on 1–2 kb transcripts are partly determined by base pairs spanning more than a
kilobase, in exactly the regime where an equilibrium MFE model is least
trustworthy for mRNA that folds co-transcriptionally and is traversed by
ribosomes.

The released STRAND features **share** this property, so it is inherent to the
feature definition on long mRNA rather than introduced here. **It is carried as a
known limitation, not resolved.**

*Evidence:* `reports/bp_span_policy_diagnostic_2026-10-20.md`.

### B5. The current construct is outside the calibration's training domain

The reference construct's **GC is 64.44%**; the calibration trained on
**39.44–60.24%**. Its stability score is an **extrapolation** on one of three
features. Any candidate with similar GC inherits this.

*Evidence:* `results/reference_score_record/FLUC-REF-V1_score_record.json`
(`features_outside_training_domain: ["GC"]`).

### B6. A withdrawn finding, retained as a caution

A reported UTR–ORF coupling result was published and then **withdrawn**: the
observation reproduced, but it was an artifact of unbounded span, not a sequence
property. Bounding the span to ≤200 nt makes the two ORF contexts agree to four
decimal places.

**Nothing in this project currently establishes that a UTR's folding depends on
its ORF context** — nor that it does not.

*Evidence:* `reports/utr_orf_coupling_is_a_span_artifact_2026-10-20.md`.

---

## C. Limitations of the translation arm

### C1. The T-cell arm is model-blind

The lab's cells are **activated CD3+ T cells containing CD4+ and CD8+
populations**. A scan of all 78 released RiboNN tasks found no CD3, no CD8 and no
activated-state task. The only primary T-cell task is CD4-only and differs in
subset composition and unknown activation state; better-scoring lymphoid tasks
are transformed lines and are worse biological matches.

**No translation-side score exists for the T-cell arm, and none may be inferred
from the A549 arm.** PARADE's Jurkat MPRA data does not fill this gap: Jurkat is
a transformed line, and PARADE scores UTR segments in a fixed reporter rather
than TE of an arbitrary transcript.

### C2. RiboNN is out of distribution for a designed reporter

The task predicts TE of **endogenous human transcripts**. The constructs are
designed reporters. The A549 selection carries this documented caveat.

### C3. An unconfirmed assumption underlies the per-task accuracy

The RiboNN A549 per-task accuracy (Pearson 0.709, n = 9,776) rests on the
**unconfirmed assumption** that the released prediction table holds out-of-fold
predictions. If it does not, that accuracy is optimistic.

### C4. RiboNN cannot represent protein-level effects

Fluc-PEST scored 5.08% below Fluc, systematically across all ten folds. That
difference is **confounded with CDS length**, which RiboNN consumes as an input,
and RiboNN is **structurally blind** to what a PEST tag does, since protein
turnover is downstream of translation efficiency. **Fluc-PEST is not shown to
translate less well.**

---

## D. Limitations of the structure-prediction side (the Stage 2 gate itself)

### D1. Zero of six gate requirements are satisfied

| # | Requirement | Status |
|---|---|---|
| 1 | Frozen independent sequence- and family/clan-separated validation | **not satisfied** |
| 2 | Accuracy and failures by length band and family vs native controls | **partially satisfied** |
| 3 | Resolve sparse 2,000–2,999 nt coverage | **blocked on acquisition** |
| 4 | Credible structure accuracy with review of native baseline gaps | **not satisfied** |
| 5 | Constraint decoder resource and replay checks | **partially satisfied** |
| 6 | Document remaining limitations | **partially satisfied** — *this document addresses it* |

Statuses as recorded in
`results/stage2_band_coverage_census_runs/20261019T180243.655199Z/summary.json`.
"Partially satisfied" is not satisfied: `requirements_satisfied` is **0**.

### D2. No experimental reference structures

Every available reference in the frozen in-scope selection is a **computational
Rfam-consensus reference**, not an experimental structure. Independent
complete-reference validation is recorded as unestablished.

### D3. The learned model is below both native controls

Accuracy is reported by band, family and seed against LinearFold and ViennaRNA;
**the learned model remains below both** on development references.

### D4. The 2,000–2,999 nt band rests on a single record

The in-scope frozen selection holds **6 records across 3 families and 2 clans**;
the 2,000–2,999 nt band contributes **1**. Its per-band figure therefore carries
**no dispersion and no family contrast**.

Precisely: **family-level expansion is available** (56 eligible records locally,
RF02540 31 and RF02541 25, with RF02540 a new family), while **clan-level
expansion is not** — the only out-of-baseline clan, CL00004 via RF02462, is
blocked by prior-exposure overlap on both its records.

*Evidence:* `results/stage2_band_coverage_census_runs/20261019T180243.655199Z/summary.json`,
`results/band_clan_availability_runs/20261019T185713.116447Z/summary.json`.

---

## E. Limitations of the planned experiment

### E1. The design is underpowered for its own target

At the stated CV bound of 20%, n = 3 gives **54.2%** power for the 1.5-fold
target, and the minimum detectable effect is **1.75-fold**, exceeding the target.
Under the exact log-normal convention these become **47.9%** and **1.84-fold**.
The replicate count needed for 80% power is **5** under either convention.

**The CV is a planning bound supplied by the user, not a measurement.** No CV has
been measured, so no statement about the actual sensitivity of the planned
experiment is supported.

*Evidence:* `src/rnastable/assay_power.py`, `tests/test_assay_power.py`.

### E2. No floor can be frozen

Floor selection is blocked on three missing inputs: a **measured** CV, a stated
**decision cost** of a false accept versus a false reject, and the recognition
that 1.5-fold is a target *experimental effect*, not an acceptance threshold on a
model score. A floor frozen on an assumed bound would be provisional and must be
labelled as such. **None is frozen.**

### E3. Construct provenance is partly unconfirmed

- The **CDS history is unclear** by the collaborator's own statement. The
  identification of the parent as the GenScript F-Luc plus alpha-globin
  composition used as a baseline in the mRNAutilus preprint is **indicated, not
  established**.
- The **5′UTR is a shortened mRNA-1273 derivative**, omitting the leading `GGG`
  and an internal 10 nt `CCCCGGCGCC`. Whether that shortening is deliberate is
  **unconfirmed**.
- Consequently **no external fold-change figure** (mRNAutilus 400× vs wild-type;
  GEMORNA 41× vs an optimized benchmark) **may be compared** to the 1.5-fold
  target.

### E4. Two constructs cannot be pooled

Fluc and Fluc-PEST are different sequences of different lengths with different
protein turnover. Comparisons must be **within** a construct. No decision has
been taken on whether Fluc-PEST enters the panel.

---

## F. What follows from all of this

Before expression candidate design begins, a reader should understand:

1. **No model in the stack can currently predict the assay's outcome.** Only
   labelled ranking or correlation is supported, and only for the A549 arm.
2. **The stability arm rests on an unvalidated refit**, applied outside its
   training domain for the current construct, on features that do not represent
   the assayed nucleoside and depend on an unbounded pair span.
3. **The T-cell arm has no translation-side model at all.**
4. **The experiment as specified is underpowered for its own target**, and no
   floor can be frozen until a CV is measured and a decision cost is stated.
5. **The structure-prediction gate is not met**, and the learned model is below
   both native controls.

None of this prohibits candidate design as a future activity. It does mean that
any candidate ranking produced today would be a **model-score ordering carrying
every limitation above**, and must not be presented as a predicted improvement in
stability, translation or expression.

---

## What must not be claimed

- This document **does not** satisfy any requirement by itself; marking
  requirement 6 satisfied is a gate-review judgement recorded separately.
- Listing a limitation is **not** resolving it. B3, B4 and D1–D4 remain open.
- **0 of 6** gate requirements are satisfied at the time of writing.
- No floor is selected or frozen, `new_sequence_scoring_enabled` is false, and
  `expression_candidate_design_enabled` is false.
