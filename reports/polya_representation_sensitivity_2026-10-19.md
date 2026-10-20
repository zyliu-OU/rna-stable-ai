# Poly(A) representation sensitivity of the folding features — 2026-10-19

- **Project:** RNA-StableAI
- **Workspace:** `/home/zyliu/Documents/rna-stable-ai`
- **Transcript:** `FLUC-REF-V1`, assembled from committed construct inputs
- **Artifacts:** `results/reference_fold/FLUC-REF-V1_core.json`,
  `results/reference_fold/FLUC-REF-V1_polyA.json`
- **Tool:** ViennaRNA 2.7.2, Turner 2004, 37 °C, dangles 2, parameter file
  sha256 `9521527a251d5e68e6149595f8aa72aa72c63e00dc5af41d7164e6ecaa664777`

## Question

`configs/transcript_inputs_v1_2026-10-19.json` recorded an open decision: should
the 103 nt template-encoded poly(A) tail be part of the transcript the models
see? The argument for inclusion is that `assay_definition_v3` counts a supplied
poly(A) toward scope. The argument against is that the downstream models were
derived from transcript representations that do not generally carry long
homopolymeric tails.

The decision was deliberately not defaulted. This note measures it.

## Method

The same CDS and UTRs were assembled twice, once as the 1,811 nt core
(5′UTR 44 + CDS 1,653 + 3′UTR 114) and once with the recorded 103 nt poly(A)
appended, giving 1,914 nt. Both were folded through the existing isolated
ViennaRNA worker under identical settings. Nothing else differed.

## Result

| Metric | core (1,811 nt) | +poly(A) (1,914 nt) | Δ |
|---|---:|---:|---:|
| MFE (kcal/mol) | −740.400024 | −740.400024 | **0.000000** |
| Ensemble free energy (kcal/mol) | −771.977661 | −771.994934 | −0.017273 |
| MFE per nt | −0.408835 | −0.386834 | +0.022001 |
| Ensemble FE per nt | −0.426271 | −0.403341 | +0.022930 |
| **STRAND average log odds** | **1.143062** | **0.594838** | **−0.548224** |
| Mean unpaired probability | 0.377889 | 0.411310 | +0.033421 |

Per-region mean unpaired probability is unchanged to the fourth decimal:

| Region | core | +poly(A) |
|---|---:|---:|
| 5′UTR | 0.838862 | 0.837000 |
| CDS | 0.362727 | 0.362743 |
| 3′UTR | 0.419823 | 0.419593 |
| start-codon window | 0.484376 | 0.484417 |
| poly(A) | — | **0.999720** |

Structural checks:

- The core MFE structure is an exact **prefix** of the poly(A) MFE structure.
- The poly(A) region of the MFE structure is **entirely unpaired** (all dots).
- The poly(A) region's mean unpaired probability is **0.99972**.

## Interpretation

**The poly(A) tail is thermodynamically inert in this construct.** It forms no
base pairs, leaves the MFE identical to six decimal places, shifts the ensemble
free energy by 0.017 kcal/mol out of 772, and does not perturb the folding of any
other region. This is the expected behaviour of a homopolymeric adenosine tract,
which cannot self-pair under the Turner model.

**But the STRAND average-log-odds feature falls by 48%**, from 1.143 to 0.595.
That change is **not structural**. `strand_alo` is a positional mean of log odds,
so appending 103 maximally unpaired positions drags the mean down by dilution
alone. The same molecule, folded the same way, yields a feature value that is
nearly halved purely by a representation choice.

### Consequence that matters

`strand_alo` is **not invariant to poly(A) representation**, while the energy
terms essentially are. Therefore:

1. The poly(A) convention must be **fixed and recorded** for every construct any
   comparison touches. Mixing conventions within a comparison would be a defect.
2. If candidate constructs ever differ in tail length, `strand_alo` would rank
   them partly **by tail length rather than by structure**. Any design round that
   varies the poly(A) must either hold it constant or stop using this feature.
3. Because the tail is thermodynamically inert, including it buys no structural
   information and costs feature interpretability.

## RiboNN: the same question, measured

The folding result above left open whether RiboNN should see the tail. That has
now been measured directly rather than argued.

- **Run:** `results/ribonn_fixed_inference_runs/20261020T020239.050049Z`
- **Protocol:** `configs/ribonn_reference_inference_v1_2026-10-19.json`
- **Task:** `predicted_TE_A549`, the task selected for the A549 arm in
  `configs/ribonn_task_selection_v1_2026-10-19.json`
- **Models:** 50 released human checkpoints, 10 folds × top-5, 182 weight files
  hash-verified, archive `2ce3bc1a…`
- **Replay:** two independent worker processes produced **bitwise-identical**
  predictions (`max_abs_difference` 0.0) across every released task, not only the
  designated one.

| Fold | core (1,811 nt) | +poly(A) (1,914 nt) | Δ |
|---:|---:|---:|---:|
| 0 | 0.763999 | 0.769519 | +0.005520 |
| 1 | 0.888405 | 0.883308 | −0.005098 |
| 2 | 0.838184 | 0.846833 | +0.008649 |
| 3 | 0.824222 | 0.821954 | −0.002267 |
| 4 | 0.832333 | 0.834633 | +0.002300 |
| 5 | 0.827665 | 0.824487 | −0.003178 |
| 6 | 0.793685 | 0.801914 | +0.008230 |
| 7 | 0.821687 | 0.820089 | −0.001599 |
| 8 | 0.807745 | 0.808071 | +0.000326 |
| 9 | 0.878797 | 0.872914 | −0.005884 |
| **mean** | **0.827672** | **0.828372** | **+0.000700** |

Neither variant was excluded; both pass the 1,381 nt upstream-domain limit.

**RiboNN is effectively insensitive to poly(A) representation.** The mean shift is
**+0.085%**. Against a between-fold standard deviation of **0.036650**, the effect
is **0.019 SD** — roughly fiftieth the size of the checkpoint-to-checkpoint
spread. The per-fold differences alternate in sign and the largest is 0.0087,
which is the signature of noise rather than a systematic shift.

## Combined picture

| Feature | Poly(A) sensitivity |
|---|---|
| MFE | **0.000000** — exactly none |
| Ensemble free energy | 0.002% |
| **STRAND average log odds** | **−48%** |
| RiboNN `predicted_TE_A549` | +0.085%, 0.019 SD — noise |

Of the four quantities the stack produces, **only `strand_alo` responds to the
poly(A) convention, and its response is a normalization artifact rather than
signal.** Both energy terms and the translation-side model are indifferent.

### Recommendation

**Exclude the poly(A) tail from the folding input and fold the 1,811 nt core.**
This is now evidence-based rather than an arbitrary default: the tail contributes
no structure, and its only effect anywhere in the stack is to dilute one
length-normalized metric.

For **RiboNN the choice does not matter**, so the same core transcript can be used
for both arms without loss. Using one representation throughout is preferable to
two, because it removes the risk of a comparison silently mixing conventions.

The measured reference value for the A549 arm is `predicted_TE_A549` =
**0.8277** (mean over 10 folds, core transcript). This is a released-task score on
the task's own scale. It is **not** a prediction of luminescence in this assay and
carries the documented out-of-distribution caveat for a designed reporter
construct.

## What must not be claimed

- Every uridine in the assayed molecule is **N1-methylpseudouridine**. ViennaRNA
  has no parameters for it and folded the sequence as canonical U. **None of the
  absolute values above is the thermodynamics of the molecule in the
  experiment.** The modification is constant across the panel, so relative
  comparisons remain usable; absolute values must not be reported as the assayed
  molecule's.
- This is a computation on one construct. It establishes no stability,
  translation or expression benefit, and no comparison to any other construct has
  been made.
- The 5′UTR's high mean unpaired probability (0.839) is a **computed property of
  the sequence as folded**, not evidence of efficient initiation.
- No Stage 2 gate requirement is satisfied; still 0 of 6. No floor is selected or
  frozen, and sequence scoring remains disabled.
