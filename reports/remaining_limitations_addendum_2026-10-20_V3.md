# Remaining limitations — addendum 3, 2026-10-20

- **Project:** RNA-StableAI
- **Workspace:** `/home/zyliu/Documents/rna-stable-ai`
- **Purpose:** Stage 2 gate requirement 6,
  `Document_remaining_limitations_before_expression_candidate_design`.
- **Extends, does not replace:**
  `reports/remaining_limitations_before_candidate_design_2026-10-19.md`,
  `reports/remaining_limitations_addendum_2026-10-20.md` and
  `reports/remaining_limitations_addendum_2026-10-20_V2.md`, all unedited.
- **Why a third addendum:** addendum 2 recorded the modification-constancy problem using
  **pseudouridine** on six constructs. It can now be tested with
  **N1-methylpseudouridine**, the nucleoside the collaborator's molecules actually carry,
  at 40,000 sequences per arm. The result both **strengthens and narrows** what addendum 2
  said.

---

## N12. m1Ψ rescales the GC-to-ribosome-load relationship

### N12.1 What was measured

Sample et al. 2019 measured a random 50-mer 5′UTR library on eGFP in HEK293T under
unmodified and m1Ψ conditions. Because the arms are independent random libraries they share
**zero** sequences, and their ribosome-load scales differ (14 against 13 polysome
fractions), so no per-sequence or absolute comparison is possible. What is comparable is the
**shape** of the sequence-to-ribosome-load mapping within each arm.

Three features were declared in advance. Protocol:
`configs/m1pseudouridine_feature_slope_check_v1_2026-10-20.json`. Run:
`results/m1pseudouridine_slope_runs/20261020T214354.531676Z/`.

| feature | unmodified slopes | m1Ψ slope | between | within | ratio | verdict |
|---|---|---|---|---|---|---|
| out-of-frame uAUG | −1.5594 / −1.4273 | −1.3223 | 0.1711 | 0.1321 | 1.30 | ambiguous |
| **GC fraction** | **−1.0252 / −0.9748** | **−0.2769** | **0.7231** | **0.0504** | **14.34** | **sequence-dependent** |
| ViennaRNA MFE | 0.0280 / 0.0322 | 0.0347 | 0.0046 | 0.0042 | 1.09 | ambiguous |

Slopes are in within-arm standard deviations of ribosome load per unit feature. 40,000
sequences per arm, drawn from 163,000–176,000 passing a within-arm median-depth filter. The
two libraries' GC means differ by 0.0017, so they are drawn from the same sequence
distribution.

### N12.2 The finding

**GC content costs about 3.7× more ribosome load in unmodified mRNA than under m1Ψ**
(−1.00 against −0.28). The two unmodified replicates agree to 0.05, so a difference of 0.72
is not replicate noise. It is a **magnitude** change, not a sign change: both arms still lose
ribosome load as GC rises.

The uAUG and structure slopes are stable within replicate noise. So the modification's effect
is **not** uniformly sequence-dependent — it localises to composition.

### N12.3 Why this is the worst feature for this project

`GC` is one of the **three inputs** to `strand_rnafold_calibration_v1`, alongside
`energy_per_length` and `aup`. It is also the feature on which the project's own construct
**extrapolates**: 64.4% GC against a 39.4–60.2% training range, flagged on every member of
every design-workflow run.

So the modification rescales the relationship for exactly the input the pipeline leans on,
in a region where the pipeline is already outside its fitted domain. Those two problems
compound rather than cancel.

### N12.4 Limitations that cut the other way

1. **The m1Ψ condition has no replicate.** `GSM3130440_egfp_m1pseudo_2` turned out to be a
   different library — 54 nt, no constant suffix — and was excluded. The within-condition
   denominator is therefore **borrowed from the unmodified pair**, and is recorded as borrowed
   on every feature. For GC to become "consistent with constant", m1Ψ replicates would have
   to be roughly 14× noisier than unmodified ones.
2. **A declared preprocessing step was corrected mid-run.** The protocol tied the 9-nt
   `ATGGGCGAA` trim to the m1Ψ condition; it is a per-file export convention, and the
   unmodified replicate carries it too. Detection is now per file, from observed suffix
   frequency. Features and the decision rule were untouched.
3. **This is a translation readout.** It says nothing about the stability side.
4. **This is not the project's construct.** A 50-nt random UTR on eGFP in HEK293T is not an
   1,811 nt mRNA with a 44 nt 5′UTR in A549 and T cells.
5. **Three features are not a complete account** of what determines ribosome load. They were
   declared for being mechanistically motivated and cheap.
6. **A slope is an association** within a random library, not causation.

### N12.5 What this does to addendum 2

| | addendum 2 | this addendum |
|---|---|---|
| nucleoside | Ψ — wrong one | **m1Ψ — the right one** |
| n | 6 constructs | **40,000 sequences per arm** |
| readout | protein output and half-life | ribosome load |
| finding | effect construct-dependent on expression, sign could invert | effect **rescales GC specifically**; uAUG and structure stable |

Addendum 2 stands as what it was. This addendum **strengthens** its conclusion by reaching it
with the correct nucleoside and vastly more data, and **narrows** it by localising the effect
to composition rather than leaving it general.

---

## What must not be claimed, as of this addendum

Carried from addenda 1 and 2, with one item made more precise:

- That a predicted ordering of **modified** constructs is the expected measured ordering.
  **Specifically**: any ordering that depends on GC content is unsupported, because m1Ψ
  rescales that relationship by roughly 3.7×.
- That the uAUG or structure relationships are **known** to be preserved under m1Ψ. Their
  verdicts are *ambiguous*, which is not the same as supported.
- That m1Ψ's effect on **stability** is known. Nothing here tests it.
- That any molecule in this project has been measured. None has.
