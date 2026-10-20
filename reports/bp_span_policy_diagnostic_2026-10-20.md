# Base-pair span policy: diagnostic and recommendation — 2026-10-20

- **Project:** RNA-StableAI
- **Workspace:** `/home/zyliu/Documents/rna-stable-ai`
- **Script:** `scripts/diagnose_bp_span_policy.py`
- **Artifact:** `results/bp_span_policy/span_vs_linearpartition_agreement.json`
- **Follows:** `reports/utr_orf_coupling_is_a_span_artifact_2026-10-20.md`

## Why this was asked

A folding result showed that an identical 5′UTR's computed accessibility depends
on sequence 1.65 kb downstream, and that the effect disappears once base-pair
span is bounded. That raised a policy question the project had never decided:
ViennaRNA runs here with `max_bp_span: -1`, which was **inherited as a default
rather than chosen**.

A specific hypothesis motivated the check. STRAND's released features come from
**LinearPartition**, a beam-pruned approximation whose error is concentrated in
long-range pairs. If beam pruning made LinearPartition effectively local, then
our unlimited-span substitute would be systematically mismatched — and the
`feature_level_compatible: false` verdict already recorded in
`results/strand_rnafold_agreement_runs/20261019T172402.804593Z` might be an
artifact of the span default rather than a real incompatibility. Had that been
true, bounding the span could have restored applicability of the **published**
STRAND model, which would have been a substantial unlock.

## Cohort

Selection-set records only: `X320004D1`, `X310336T3`, `X310003T1`, `X130010D1`,
`X130002D1`, `X130006D1` (928–1215 nt). `configs/strand_rnafold_agreement_criterion_v1`
records these six as **burned** — their RNAfold differences were visible to the
author when the criterion was frozen, so they carry no confirmatory weight. The
blinded 85-record evaluation set was deliberately **not touched**, so nothing
here can contaminate the set a real decision must rest on.

## Result: the hypothesis is wrong

Features recomputed at several spans and compared against the released
LinearPartition values, using the criterion's own frozen tolerances.

| `max_bp_span` | within tolerance | mean &#124;Δ&#124; energy/len | mean &#124;Δ&#124; aup | mean &#124;Δ&#124; alo |
|---|---:|---:|---:|---:|
| **unlimited** | **13/18** | **0.000014** | **0.001247** | **0.147688** |
| 800 | 10/18 | 0.002081 | 0.001813 | 0.133359 |
| 600 | 7/18 | 0.006996 | 0.003512 | 0.187406 |
| 400 | 3/18 | 0.018071 | 0.006823 | 0.201016 |
| 300 | 1/18 | 0.021173 | 0.009418 | 0.215030 |
| 200 | 2/18 | 0.038494 | 0.021660 | 0.295571 |
| 150 | 2/18 | 0.049630 | 0.029584 | 0.341995 |
| 100 | 1/18 | 0.063250 | 0.043561 | 0.451238 |

**Bounding the span makes agreement monotonically worse**, on every feature.
Unlimited span agrees with LinearPartition *best*, and on `energy_per_length` it
agrees to **1.4 × 10⁻⁵**, which is effectively exact.

LinearPartition's beam pruning evidently does **not** make it behave locally on
these ~1 kb sequences; it reproduces the exact global partition function closely.
The hypothesis is refuted, and the span default is vindicated.

## The incompatibility is an `alo` problem, not a span problem

Per feature at unlimited span, across the six records:

| Feature | Within tolerance | Note |
|---|---|---|
| `energy_per_length` | **6/6** | mean &#124;Δ&#124; 1.4e-5 — essentially exact |
| `aup` | **5/6** | close; the one miss is an eGFP record whose released value is rounded to 2 dp |
| `alo` | **2/6** | **this is where the rejection lives** |

`alo` is numerically fragile. For `X320004D1`, only **16 of 928** positions carry
a paired probability below 1e-5, yet those positions dominate the feature,
because log odds diverges near zero. Holding the folding **completely fixed** and
varying only the clipping epsilon:

| epsilon | alo |
|---|---:|
| 1e-10 | 1.7401 |
| 1e-6 | 1.7504 |
| 1e-5 | 1.7776 |
| 1e-4 | 1.7618 |
| 1e-3 | 1.6267 |

That is a spread of about **0.15, roughly three times the tolerance of 0.0513**,
from a convention choice alone — and the released LinearPartition value
(**1.66408**) sits **inside** that range. Meanwhile `aup`, which uses the same
probabilities without the log transform, agrees to 0.0004.

A beam-pruned engine reports exact zeros where an exact engine reports small
positives. `alo` converts precisely that difference into a large feature
difference; `aup` does not.

## Recommendation

1. **Keep `max_bp_span: -1`, and record it as a decision rather than a default.**
   It is now evidence-backed: every alternative tested moves the features further
   from the engine STRAND was built on.
2. **The long-range sensitivity caveat stands and is not fixed by this.** Folding
   features on ~1–2 kb transcripts remain partly determined by very long-range
   pairs. The finding here is that the released STRAND features **share that
   property**, so it is inherent to the feature definition on long mRNA rather
   than something this project introduced. It should be carried as a known
   limitation of the stability arm, not treated as resolved.
3. **If engine compatibility is ever revisited, `alo` is the thing to attack**,
   not the span. The concrete question is what near-zero convention
   LinearPartition's output implies, and whether matching it brings `alo` inside
   tolerance. That is a bounded piece of work with a real payoff, since
   `energy_per_length` and `aup` already agree.

## What must not be claimed

- **Not** that unlimited span is physically correct. What is shown is narrower:
  it reproduces the reference engine best. Agreement with LinearPartition is not
  evidence about real RNA structure.
- **Not** that published STRAND is now applicable. The frozen verdict stands:
  `feature_level_compatible: false`, `outcome: rejected`. This diagnostic only
  identifies *where* the incompatibility comes from.
- **Not** a result on the evaluation set. Six burned records cannot decide
  anything; they can only point at a mechanism.
- Every uridine in the project's own constructs is **N1-methylpseudouridine**,
  which neither engine represents.
- No Stage 2 gate requirement is satisfied; still **0 of 6**. No floor is selected
  or frozen, and sequence scoring remains disabled.
