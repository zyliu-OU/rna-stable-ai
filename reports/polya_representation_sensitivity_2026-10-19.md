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

### Recommendation

**Fold the 1,811 nt core and exclude the poly(A) tail from the folding input**,
recording that choice explicitly. This is now an evidence-based decision rather
than an arbitrary default: the tail contributes no structure, and its only effect
on the feature set is to dilute a length-normalized metric.

This recommendation covers the **folding** input only. It says nothing about
whether RiboNN should see the tail, which is a separate question about a
different model's training distribution and has not been measured here.

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
