# Fluc vs Fluc-PEST — first comparison of two real constructs — 2026-10-19

- **Project:** RNA-StableAI
- **Workspace:** `/home/zyliu/Documents/rna-stable-ai`
- **Constructs:** both supplied by the colleague referred to as Ping in
  `Fluc and Fluc-PEST sequence.xlsx`, both hash-verified on assembly
- **Scope:** characterisation of two supplied constructs. No candidate was
  designed or scored, nothing was selected, no floor was frozen, and every scope
  flag remains false.

| | Fluc | Fluc-PEST |
|---|---|---|
| CDS | 1,653 nt / 551 codons / 550 aa | 1,776 nt / 592 codons / 591 aa |
| CDS sha256 | `86322fc1…` | `37033351…` |
| Transcript (core) | 1,811 nt | 1,934 nt |
| GC3 | 0.9964 | 0.9611 |

Both share the identical 44 nt 5′UTR and 114 nt 3′UTR, both carry the tandem
stop, and neither triggers a RiboNN exclusion. Fluc-PEST is 123 nt (41 codons)
longer, consistent with a C-terminal PEST degradation tag.

## The headline result is not the score difference

**The 5′UTR is byte-identical in both constructs, yet its folding changes
substantially.**

| Region (mean unpaired probability) | Fluc | Fluc-PEST | Δ |
|---|---:|---:|---:|
| **5′UTR (identical sequence)** | **0.838862** | **0.570002** | **−0.268860** |
| CDS | 0.362727 | 0.370452 | +0.007725 |
| 3′UTR | 0.419823 | 0.410295 | −0.009528 |
| start-codon window | 0.484376 | 0.485470 | +0.001094 |

The same 44 nucleotides go from highly accessible (0.84) to substantially paired
(0.57), a **32% relative change**, purely because the ORF downstream of them is
different. Nothing about the 5′UTR itself changed.

This is direct empirical confirmation of the `coupling_warning` recorded in
`configs/assay_definition_v3_2026-10-19.json`: *"Edits in all three regions move
GC content and folding free energy, which are STRAND features… The regions are
not independent in their effect on model scores."* That warning was an argument;
this is a measurement of it.

**Consequence for any future design work:** a 5′UTR cannot be optimised in
isolation and assumed to carry its folding properties into a different ORF
context. Any UTR candidate must be evaluated **in the full transcript it will
actually be used in**. A UTR library ranked against one ORF may re-rank against
another.

Note the start-codon window is essentially unchanged (0.4844 vs 0.4855), so the
difference sits in the 5′ portion of the UTR rather than at the initiation site.
That is an observation about where the change falls, not a claim that initiation
is therefore unaffected.

## Folding

ViennaRNA 2.7.2, Turner 2004, 37 °C, dangles 2, parameter file
`9521527a…`. Artifacts: `results/reference_fold/FLUC-REF-V1_core.json`,
`results/reference_fold/FLUC-PEST-V1_core.json`.

| Metric | Fluc | Fluc-PEST | Δ |
|---|---:|---:|---:|
| MFE (kcal/mol) | −740.400024 | −782.400024 | −42.000000 |
| Ensemble free energy | −771.977661 | −817.059509 | −45.081848 |
| MFE per nt | −0.408835 | −0.404550 | +0.004285 |
| Ensemble FE per nt | −0.426271 | −0.422471 | +0.003800 |
| STRAND average log odds | 1.143062 | 1.082453 | −0.060609 |
| Mean unpaired probability | 0.377889 | 0.377340 | −0.000549 |

The raw energies differ mainly because Fluc-PEST is longer. **Per nucleotide the
two constructs are nearly indistinguishable** (within 0.004 kcal/mol/nt), and
their overall mean unpaired probabilities agree to three decimal places. By these
whole-transcript summaries the PEST tag does not make a structurally distinct
molecule; the difference it produces is local, and lands in the 5′UTR.

## RiboNN, A549 arm

- **Run:** `results/ribonn_fixed_inference_runs/20261020T021707.178744Z`
- **Protocol:** `configs/ribonn_reference_inference_v2_2026-10-19.json`
- **Task:** `predicted_TE_A549`; 50 released human checkpoints, 10 folds × top-5
- Both constructs scored in **one run with identical checkpoints**, so the
  comparison is not confounded by checkpoint selection.

| Fold | Fluc | Fluc-PEST | Δ |
|---:|---:|---:|---:|
| 0 | 0.763999 | 0.724318 | −0.039681 |
| 1 | 0.888405 | 0.823252 | −0.065154 |
| 2 | 0.838184 | 0.798852 | −0.039332 |
| 3 | 0.824222 | 0.762308 | −0.061914 |
| 4 | 0.832333 | 0.801000 | −0.031333 |
| 5 | 0.827665 | 0.794307 | −0.033359 |
| 6 | 0.793685 | 0.755711 | −0.037974 |
| 7 | 0.821687 | 0.784199 | −0.037489 |
| 8 | 0.807745 | 0.769190 | −0.038555 |
| 9 | 0.878797 | 0.843158 | −0.035640 |
| **mean** | **0.827672** | **0.785629** | **−0.042043** |

Fluc-PEST scores **5.08% lower**. Unlike the poly(A) test, this difference is
**systematic**: all ten folds agree in sign, the per-fold deltas span −0.031 to
−0.065 without crossing zero, and the effect is **1.15× the between-fold standard
deviation** (0.0367). For contrast, the poly(A) effect was 0.019 SD with
alternating signs.

### What this does and does not mean

**It is a consistent model-score difference. It is not a biological result.**

1. **The difference is confounded with CDS length.** RiboNN consumes `cds_size`
   as an input feature, and Fluc-PEST's CDS is 7.4% longer. Part or all of the
   −5.08% may be a length response rather than a response to the PEST sequence.
   This comparison **cannot separate** the two, and no attempt was made to.
2. **RiboNN does not model what a PEST tag does.** A PEST tag is a
   protein-level degradation signal; it shortens the half-life of the translated
   protein. RiboNN predicts translational efficiency — ribosome occupancy
   relative to mRNA level — which is upstream of, and blind to, protein turnover.
   The model is structurally incapable of representing the tag's actual purpose.
3. For the assay this matters in the opposite direction from the score: because
   Fluc-PEST protein turns over quickly, its **luminescence tracks current mRNA
   level more closely**, while untagged Fluc integrates past translation. That is
   an argument about assay interpretation, not about this score.

## What must not be claimed

- **Fluc-PEST is not shown to translate less well.** A 5.08% lower released-task
  score, confounded with CDS length, is not evidence of reduced translation, and
  nothing here was measured in cells.
- Every uridine in both assayed molecules is **N1-methylpseudouridine**. Neither
  ViennaRNA nor RiboNN represents it. No absolute value here is a property of the
  molecules that will be transfected.
- RiboNN scores are on the released task's own scale and carry the documented
  out-of-distribution caveat for designed reporter constructs. They are **not**
  predictions of luminescence.
- The T-cell arm remains **model-blind**; nothing here applies to it.
- The 5′UTR coupling result is a **computed** property under one folding model at
  37 °C, not a measured structure.
- No Stage 2 gate requirement is satisfied; still **0 of 6**. No floor is selected
  or frozen, and sequence scoring remains disabled.
