# The UTR–ORF coupling is an artifact of unbounded base-pair span — 2026-10-20

- **Project:** RNA-StableAI
- **Workspace:** `/home/zyliu/Documents/rna-stable-ai`
- **Artifacts:** `results/utr_orf_coupling/bp_span_sensitivity.json`,
  `results/utr_orf_coupling/coupling_seed1729_n24.json`
- **Corrects:** `reports/construct_comparison_fluc_vs_fluc_pest_2026-10-19.md`

## What was claimed, and why it was wrong

The Fluc vs Fluc-PEST comparison observed that the **identical** 44 nt 5′UTR had
mean unpaired probability 0.8389 in the Fluc transcript and 0.5700 in the
Fluc-PEST transcript. That observation is correct and reproducible.

The **interpretation** was not. It was reported as empirical confirmation of the
recorded `coupling_warning`, with the design conclusion that a 5′UTR cannot be
optimised outside the transcript it will be used in. That conclusion was drawn
without establishing the mechanism, and the mechanism turns out to invalidate it.

## The two ORF contexts are nearly identical

Fluc-PEST is not a different ORF. It is Fluc with a 123 nt insert:

```
shared 5' prefix   1650 nt  (99.8% of Fluc)
insert              123 nt  at position 1650
shared 3' suffix      3 nt  (the stop codon)
```

The two contexts are **byte-identical for the first 1650 nt**. The only
difference sits roughly **1.65 kb downstream of the 5′UTR**, at the far end of
the molecule. For that difference to reach the 5′UTR at all, the folding model
must be forming base pairs across more than a kilobase.

## Bounding the span removes the effect entirely

Same sequences, same settings (Turner 2004, 37 °C, dangles 2), varying only
ViennaRNA's `max_bp_span`. Metric is mean unpaired probability over the 44 nt
5′UTR.

| `max_bp_span` | Fluc | Fluc-PEST | &#124;Δ&#124; |
|---|---:|---:|---:|
| unlimited (the worker default) | 0.8389 | 0.5700 | **0.2689** |
| 600 | 0.8398 | 0.8813 | 0.0415 |
| **200** | 0.9047 | 0.9048 | **0.0001** |
| 100 | 0.8944 | 0.8944 | 0.0000 |
| 50 | 0.9352 | 0.9352 | 0.0000 |

At a span of 200 nt or less the 5′UTR folds **identically in both ORF contexts to
four decimal places**. The entire 0.269 effect requires base pairs spanning more
than 600 nt.

**The coupling is a property of unbounded global folding, not of the sequences.**

## Why this matters beyond the one observation

1. **The design conclusion is withdrawn.** There is no evidence here that a 5′UTR
   reorders across ORF contexts for any physically grounded reason. Under local
   folding it does not move at all.
2. **It bears on the stability arm generally.** Every folding feature this
   project computes on these ~1.8 kb transcripts is produced with unlimited
   span. If a 1.65 kb-range pair can swing a region's accessibility by 32%, then
   `strand_alo`, positional accessibility and the ensemble free energy on
   full-length mRNA are all partly determined by very long-range pairs.
3. **Those pairs are of doubtful physical reality.** mRNA folds
   co-transcriptionally, is traversed by ribosomes, and is bound by proteins.
   Kilobase-range pairing in a global equilibrium MFE model is exactly the regime
   where that model is least trustworthy. This is the stated reason tools such as
   LinearFold/LinearPartition and local-folding modes exist.

**No claim is made here about which span is correct.** That is an empirical
question this project has not answered, and the right span may differ between the
stability arm's purposes. What is established is narrower and sufficient: *the
result depends on that choice, and the choice is currently an unexamined
default.*

## The broader shuffle experiment, read in this light

A separate run folded 24 dinucleotide-preserving shuffles of the reference 5′UTR
in both ORF contexts (`coupling_seed1729_n24.json`, seed 1729, unlimited span).
Between-context Spearman correlation was 0.43 for 5′UTR accessibility, 0.59 for
`strand_alo` and 0.85 for MFE.

Those numbers should **not** be read as "UTR rankings are unreliable". The
distribution is extremely skewed:

- median |Δ| across variants: **0.0083**
- mean |Δ|: 0.0461
- max |Δ|: **0.2689**, which is the reference UTR itself, **45× the median shuffle**

So most variants barely move between contexts, a small minority move a great
deal, and the modest rank correlation comes from a few large movers plus rank
swaps among many near-ties. Given the span result, those few large movers are
most likely the variants that happen to form a long-range pair, which is the same
artifact rather than a separate finding.

## What must not be claimed

- **Not** that UTR and ORF are independent. That has not been shown either; only
  that this particular evidence does not demonstrate dependence.
- **Not** that unlimited span is wrong, or that 200 nt is right. No physical
  determination was made.
- **Not** that any variant in the shuffle set is a candidate. The shuffle
  destroys the Kozak context; they are instruments, not designs.
- Every uridine in the real molecules is **N1-methylpseudouridine**, which
  ViennaRNA does not represent. These are model-behaviour results on canonical-U
  sequences.
- No Stage 2 gate requirement is satisfied; still **0 of 6**. No floor is
  selected or frozen, and sequence scoring remains disabled.

## Recommended next step

Decide the base-pair span policy for the stability arm deliberately, and record
it, rather than inheriting `max_bp_span: -1` by default. Until that is decided,
any folding-derived feature on full-length transcripts carries this sensitivity
as an open caveat.
