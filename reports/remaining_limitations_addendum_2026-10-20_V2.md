# Remaining limitations — addendum 2, 2026-10-20

- **Project:** RNA-StableAI
- **Workspace:** `/home/zyliu/Documents/rna-stable-ai`
- **Purpose:** Stage 2 gate requirement 6,
  `Document_remaining_limitations_before_expression_candidate_design`.
- **Relationship to earlier documents:** this **extends** and does not replace
  `reports/remaining_limitations_before_candidate_design_2026-10-19.md` or
  `reports/remaining_limitations_addendum_2026-10-20.md`, both unedited and both still
  standing in full.
- **Why a second addendum on the same date:** the first external validation and the
  modification-constancy check both produced results that change what may be claimed. One
  of them **weakens a standing claim**, which the earlier documents do not cover.

---

## N9. The modification-constancy argument is not supported on the expression readout

This is the most consequential limitation added today, because it weakens an argument the
project has been relying on rather than adding a new gap.

### N9.1 What the argument was

Every uridine in the collaborator's molecules is **N1-methylpseudouridine**. No component in
the stack represents it: ViennaRNA, `strand_rnafold_calibration_v1` and RiboNN all fold and
score the sequence as canonical U. Section A1 of the 2026-10-19 document therefore argued:

> The modification is **constant across the panel**, so it does not by itself confound a
> *ranking* of constructs that differ in sequence. That ranking argument assumes the
> modification's effect is **sequence-independent**, which is **unverified**.

That assumption is what licenses using unmodified-sequence predictions to order modified
molecules. It was carried as unverified because there was no evidence either way.

### N9.2 What was measured

Leppek et al. 2022 measured six constructs both unmodified and pseudouridine-modified, by two
independent readouts. Protocol and criteria:
`configs/pseudouridine_effect_check_v1_2026-10-20.json`. Run:
`results/pseudouridine_effect_runs/20261020T212132.473715Z/`.

| readout | fold-change range | same direction | dispersion ratio | verdict |
|---|---|---|---|---|
| in-solution half-life | 1.230 – 2.683× | **yes** | 1.76 | **ambiguous** |
| protein output, 6 h | 0.234 – 1.250× | **no** | 23.14 | **construct-dependent** |
| protein output, 24 h | 0.256 – 3.309× | **no** | 19.84 | **construct-dependent** |

Protein output at 24 h, per construct:

| 5′UTR | CDS | PSU / Unmodified |
|---|---|---|
| CoV-2-TTG-dSL1-3 | LinearDesign-1 | 0.256× |
| C3 | LinearDesign-1 | 0.464× |
| hHBB | LinearDesign-1 | 0.569× |
| CoV-2-TTG-dSL1-3 | Nluc_start | 0.623× |
| hHBB | Nluc_start | 1.228× |
| C3 | Nluc_start | **3.309×** |

The effect spans **13-fold** and **changes sign**. The factorial points at the CDS: every
`LinearDesign-1` construct loses output, while `Nluc_start` ranges from 0.62× to 3.31×.

### N9.3 The limitation

**A modification that inverts the ordering cannot be treated as a constant shift.** For the
expression readout, the sequence-independence assumption is **contradicted** by this evidence.
On the stability readout it is **not contradicted but not supported either**: every construct
moved the same way, and the magnitude still varied about 2.2-fold, more than the reported
errors comfortably explain.

**Binding consequence.** Every ranking claim this project makes about a modified panel —
including the Pareto fronts and the selected panels in
`results/design_workflow_runs/` — inherits this limitation and must carry it. Specifically,
a predicted *ordering* of modified constructs may not be presented as the expected measured
ordering.

### N9.4 Three caveats that cut the other way, and must travel with the finding

1. **This is Ψ, not m1Ψ.** They are different nucleosides, and m1Ψ is used in therapeutic
   mRNA partly because it behaves better than Ψ. The result shows that a uridine
   modification's effect **can** be strongly sequence-dependent; it is **not** a measurement
   of m1Ψ, and a constant Ψ effect would not have proven m1Ψ constant either. **This cannot
   be resolved with this dataset.**
2. **The dispersion ratio of 23 is flattered by its denominator.** Luciferase replicates are
   technically precise, with a standard error near 0.044 in log2, so the ratio compares
   biological differences against *technical* noise rather than independent-preparation
   reproducibility. The robust part of the finding is the 13-fold span and the sign change,
   not the number 23.
3. **Protein output is translation × stability.** A construct-dependent effect there could
   enter through either side; this design cannot separate them.

**No significance claim is made.** Six constructs cannot support one.

### N9.5 What would resolve it

A paired m1Ψ-versus-unmodified comparison across constructs that differ in sequence, on the
project's own readout. The collaborator's panel could answer it directly at the cost of
doubling the panel, which is a trade for them to weigh, not an assumption to keep carrying.

---

## N10. The stability calibration transfers, and matches a free baseline

Recorded here because it bounds what the stability side may claim. Full detail in handoff
[2026-10-20 V7](RNA-StableAI_HANDOFF_2026-10-20_V7.md) §5; protocol
`configs/external_validation_leppek_v1_2026-10-20.json`.

- On **123 held-out** measured in-solution half-lives: **Spearman +0.3268**, Pearson on log
  +0.5871, MAE 0.413 h. Not falsified; weak transfer.
- A **per-nucleotide EternaFold score reaches −0.3248** on the same records, so the refit
  **adds nothing** over a free published predictor.
- Training subset, an **upper bound and not a result**: +0.5290.
- **Pearson on log well above Spearman** means the model separates fast- from slow-degrading
  RNA better than it orders similar ones — the wrong way round for synonymous design, where
  predicted differences span a few percent.

**Limitation:** the calibration's demonstrated ability is **coarse discrimination**, not fine
ordering. The design workflow asks it for fine ordering. That gap is now measured rather than
suspected.

Also recorded: **all 69 of the calibration's training records are rows of the Leppek
supplementary sheet**, so the calibration's training provenance is now known and any future
evaluation must exclude them. The join is inferred from exact matches on GC and half-life, not
documented upstream.

---

## N11. The published artifacts of requirements 2, 3 and 4 can no longer be regenerated

From the purge recorded in `configs/stage2_to_stage3_gate_v7_2026-10-20.json`: the three
generators imported the retired model's shared constants and were removed. Their artifacts
remain unchanged and every path the gate chain cites still resolves, but regenerating them
would require rewriting the generators against the native path.

---

## What must not be claimed, as of this addendum

- That a predicted ordering of **modified** constructs is the expected measured ordering.
- That m1Ψ's effect is known to be sequence-independent. It is unverified, and the nearest
  available evidence points the other way for Ψ on expression.
- That the stability calibration orders similar sequences usefully. It discriminates coarsely.
- That the calibration improves on published predictors. It matches one that is free.
- That any molecule in this project has been measured. None has.
