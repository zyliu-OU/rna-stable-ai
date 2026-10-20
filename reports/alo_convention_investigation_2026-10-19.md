# Why `alo` fails engine agreement — investigation, unresolved — 2026-10-19

- **Project:** RNA-StableAI
- **Workspace:** `/home/zyliu/Documents/rna-stable-ai`
- **Artifact:** `results/alo_convention/alo_convention_investigation.json`
- **Follows:** `reports/bp_span_policy_diagnostic_2026-10-20.md`
- **Status:** **CLOSED, unresolved.** Two hypotheses excluded, one partially
  supported and deliberately **not adopted**.
- **Closed by user decision, 2026-10-19:** do not spend the blinded evaluation
  set on the cutoff hypothesis. The frozen `rejected` verdict stands, and the
  **85-record evaluation set remains unspent** for a better-motivated,
  pre-registered hypothesis later.

## The question

The span diagnostic established that `energy_per_length` agrees with the released
LinearPartition features to 1.4 × 10⁻⁵ (6/6) and `aup` agrees 5/6, while `alo`
agrees only 2/6. The frozen verdict `feature_level_compatible: false` therefore
rests almost entirely on `alo`. If `alo` could be reconciled, the **published
STRAND model** might become applicable — a substantial unlock.

**Cohort discipline.** Everything below uses the six burned selection-set records
only. The blinded 85-record evaluation set was **not touched**, and §4 explains
why it must stay that way for now.

## Hypothesis 1 — the clipping convention. **Excluded.**

STRAND's own R source (`Figure_Scripts_2.R`, lines 100–102) does this:

```r
bpp_data[bpp_data >= 1] = 1-(1e-10)
bpp_data[bpp_data <= 0]  = 1e-10
lo_data = log(bpp_data/(1-bpp_data))
```

That is ε = 1e-10, clipping **only** values at or beyond the bounds — tiny
positives are left untouched. The frozen criterion instead selected a two-sided
1e-5 clamp, which raises *everything* below 1e-5 up to 1e-5. These are materially
different rules, and matching STRAND's exactly looked like an obvious fix.

| Transform | `alo` within tolerance |
|---|---|
| STRAND's own rule (1e-10, clip only ≤0 / ≥1) | **1/6** |
| Two-sided 1e-5 clamp (the frozen choice) | **2/6** |

Matching STRAND's documented convention makes agreement **worse**. Excluded.

## Hypothesis 2 — the wrong LinearPartition model. **Excluded.**

LinearPartition defaults to the **CONTRAfold** model; Vienna parameters require
`-V`. If STRAND used the default, our Turner-based substitute would be comparing
against a machine-learned energy model. `external/LinearPartition` is vendored
here, so this was run directly rather than argued.

| Model | `aup` | `alo` |
|---|---|---|
| CONTRAfold (default) | 0/6 — off by **0.082 to 0.169** | 0/6 — off by **0.87 to 2.47** |
| **Vienna (`-V`)** | 3/6; ~1e-4 on the nLuc records | 1/6 |

CONTRAfold is decisively excluded: it cannot even reproduce `aup`. **STRAND used
Vienna parameters.** (The three `aup` misses under `-V` are the eGFP records,
whose released values are rounded to two decimals — 0.34000, 0.39000, 0.41000 —
so they are rounding artifacts rather than real disagreement.)

Note that ViennaRNA exact actually agrees *better* than LinearPartition-Vienna on
both features, which reinforces the span diagnostic's conclusion.

## Hypothesis 3 — a small-pair cutoff. **Partially supported, not adopted.**

A beam-pruned engine, or an output writer with a print threshold, would simply
omit very small pair probabilities. Those absent pairs become zero, get clipped
to 1e-10, and drag `alo` down — which is the observed direction for most records.

Applying a per-pair cutoff before summing to per-position probability, on
ViennaRNA exact folding:

| Cutoff | `alo` within tolerance | mean &#124;Δ&#124; |
|---|---|---:|
| none | 1/6 | 0.13358 |
| 1e-8 | 1/6 | 0.12997 |
| 3e-7 | 3/6 | 0.11685 |
| **1e-6** | **3/6** | **0.10630** |
| 3e-6 | 2/6 | 0.13270 |
| 1e-5 | 1/6 | 0.16185 |

At 1e-6, `aup` is **unchanged** (0.34294) — the cutoff touches only the regime
`alo` is sensitive to. Per record:

| Record | released | computed @1e-6 | &#124;Δ&#124; |
|---|---:|---:|---:|
| X320004D1 | 1.66408 | 1.67421 | 0.01013 ✓ |
| X310336T3 | 0.98619 | 1.02639 | 0.04020 ✓ |
| X130010D1 | 1.63763 | 1.63538 | 0.00224 ✓ |
| X130006D1 | 0.61149 | 0.69676 | 0.08527 ✗ |
| X130002D1 | 0.92012 | 1.15417 | 0.23405 ✗ |
| X310003T1 | 3.67087 | 3.40493 | 0.26594 ✗ |

Three records land very close; three still miss badly. **This does not resolve
the question**, and it was selected by scanning cutoffs against six records whose
differences were already visible. That is hypothesis generation, not evidence.

## Why this stops here

With n = 6 burned records, a cutoff chosen to maximise hits is **indistinguishable
from fitting noise**. The temptation is to keep scanning — more cutoffs, cutoffs
combined with clipping variants, per-cohort cutoffs — until 6/6 passes. That
search would almost certainly succeed and would mean nothing.

The blinded 85-record evaluation set is the only thing that can decide, and it
can be spent **once**. Spending it on a hypothesis tuned against the burned set
is precisely the failure the frozen criterion's cohort split exists to prevent.

So the investigation stops in an explicitly unresolved state rather than
manufacturing a result.

## What was established

1. **The folding is not the problem.** `energy_per_length` agrees to 1.4e-5 and
   `aup` agrees well under two independent engines. Whatever differs, it is not
   the structure prediction.
2. **The disagreement is specific to `alo`'s small-probability regime**, where
   the log-odds transform amplifies differences that `aup` averages away.
3. **STRAND used Vienna parameters, not CONTRAfold.** This was unrecorded and is
   now established.
4. The released engine's **version, beam size and parameterisation remain
   unknown** — `strand_rnafold_agreement_criterion_v1` already records all three
   as `null`, and nothing in the released materials resolves them.

## If this is pursued

Pre-register a **single** fixed hypothesis — one cutoff, one clipping rule, one
pass criterion — written down **before** any evaluation-set run, then run it
once. If it fails, the frozen verdict stands and the matter is closed. Anything
less disciplined will produce a number that cannot be trusted.

Given that `strand_rnafold_calibration_v1` already exists as a separately named
refit, the practical cost of leaving this unresolved is low. **Doing nothing is a
defensible option.**

## What must not be claimed

- **The frozen verdict stands:** `feature_level_compatible: false`,
  `outcome: rejected`. Nothing here changes it.
- The 1e-6 cutoff is **not** adopted, not recommended as a default, and not
  evidence of anything. It is a lead.
- Six burned records cannot establish a convention; they can only exclude
  hypotheses, which is what two of the three did.
- Agreement with a reference engine is **not** evidence about real RNA structure.
- Every uridine in this project's own constructs is **N1-methylpseudouridine**,
  which neither engine represents.
- No Stage 2 gate requirement is satisfied; still **0 of 6**. No floor is
  selected or frozen, and sequence scoring remains disabled.
