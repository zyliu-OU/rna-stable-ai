# RNA-StableAI handoff — 2026-10-19 V9

Project: RNA-StableAI
Date: 2026-10-19, America/Los_Angeles
Version: V9
Workspace: `/home/zyliu/Documents/rna-stable-ai`
Selected architecture: **RNAfold + STRAND + RiboNN + BoTorch**
Immediately previous handoff: [V8](RNA-StableAI_HANDOFF_2026-10-19_V8.md), which froze assay definition v1 and raised the Stage 3 target conflict. Questions posed in [V6](RNA-StableAI_HANDOFF_2026-10-19_V6.md#six-questions-the-user-is-preparing-answers-to). Band availability: [V7](RNA-StableAI_HANDOFF_2026-10-19_V7.md). Publication: [V5](RNA-StableAI_HANDOFF_2026-10-19_V5.md).

## Scope of this session

The user clarified two of the outstanding assay inputs: the design space covers **5′ UTR, ORF and 3′ UTR**, with codon usage named as one tunable factor for the ORF; and the **cell-assay CV is usually 0–20%**. The exact T-cell type is still being checked.

Delivered: a power analysis over the stated CV range, and assay definition **v2** superseding v1. **The power analysis produces an actionable experimental-design finding that should be settled before the experiment runs.** No task selected, no floor frozen, no gate amended, no inference run, no publication.

## Finding that affects the experiment: the stated design is underpowered at the top of the CV range

The design is 3 replicates aiming to detect a 1.5-fold enhancement. Computed on log2-transformed readout with a two-sample t-test, α = 0.05 two-sided, CV converted as log2(1+CV), using the non-central t distribution:

| CV | power at n=3 | power at n=4 | power at n=5 | power at n=6 |
| --- | --- | --- | --- | --- |
| 5 % | 100 % | 100 % | 100 % | 100 % |
| 10 % | 96.7 % | 99.8 % | 100 % | 100 % |
| 15 % | **75.7 %** | 92.4 % | 97.9 % | 99.4 % |
| 20 % | **54.2 %** | 74.6 % | 86.7 % | 93.3 % |

**At CV 20 % with n = 3, power for a 1.5-fold effect is 54.2 %** — a real effect of exactly the target size would be missed roughly half the time. Equivalently, the minimum effect detectable at 80 % power with n = 3 is:

| CV | minimum detectable fold change at n=3 |
| --- | --- |
| 5 % | 1.16× |
| 10 % | 1.34× |
| 15 % | 1.54× |
| **20 %** | **1.75×** |

So at the top of the stated range the smallest detectable effect is **larger than the 1.5× target**. Replicates needed for 80 % power at 1.5-fold: n = 2 at CV 5 %, **n = 3 at CV 10 %**, n = 4 at CV 15 %, **n = 5 at CV 20 %**.

Four options, recorded in the config:

1. **Raise to 5 replicates per group**, which restores 80 % power at CV 20 %.
2. **Reduce CV with dual-reporter normalization**, which typically moves a transfection luciferase assay toward the low end of the stated range. This is probably the cheapest fix.
3. **Analyse the two cell types as paired units rather than pooled groups.** At CV 20 %, 3 paired units give 53.9 % but **6 paired units give 98.9 %**. Pairing exploits the fact that the same construct pair is measured in each cell type, and is materially more efficient than adding independent replicates.
4. **Restate 1.5-fold as the target** and report the minimum detectable effect actually achieved, rather than assuming 1.5× is detectable.

A caveat on reading this: "0–20 %" is a usual-range statement, not a measured CV for this reporter in these cell types, so the table is a sensitivity analysis rather than a verdict on the design. If the real CV sits near 10 %, n = 3 is fine at 96.7 %. **The measured CV remains the single input that decides which column applies, and the only one still needed for a floor.**

These figures concern the experiment's ability to detect an effect. They are **not** an acceptance threshold on any model score and do **not** constitute a floor.

## Design space, clarified — and one consequential question it raises

All three regions are tunable: **5′ UTR, ORF, 3′ UTR**, with codon usage named as "one of the tunable factors for ORF", implying others exist that are not yet stated.

**New question that must be answered before any ORF edit is proposed: must ORF edits preserve the firefly luciferase amino acid sequence exactly, that is synonymous-only?**

This is not pedantry. A luciferase reporter has to stay catalytically active for luminescence to mean anything. If non-synonymous changes are permitted, luminescence confounds mRNA-level effects — which is what the pipeline is trying to optimize — with changes in **enzyme specific activity**, and the assay stops isolating the quantity of interest. Synonymous-only is the natural assumption, but I have deliberately recorded `assumed_default: null` rather than assume it, because getting this wrong would invalidate the readout's interpretation rather than merely add noise.

Two further consequences now recorded:

- **The three regions are not independent in their effect on model scores.** Edits in any of them move GC content and folding free energy, which are STRAND features, and ORF and UTR sizes are RiboNN inputs. Any per-region attribution of a predicted change needs an explicit decomposition rather than an assumption of additivity.
- **The reference CDS is already at GC3 0.996**, so codon-usage variation from this parent can realistically only *reduce* GC3. Any claim that the pipeline "optimizes codon usage" relative to this parent must state the direction and the rationale.

## Completed work

**`configs/assay_definition_v2_2026-10-19.json`** — SHA-256 **`4e32c4d153b34f3f2cd955ae9716c93d40f61ffb4ce3bc694b5906dd45f5b98b`**, 10,186 bytes, `status: incomplete_pending_inputs`. All six mutation flags false, verified programmatically.

It supersedes v1 and records: the clarified three-region design space with the protein-invariance question and the coupling warning; the stated CV range quoted verbatim with the note that it is a range not a measurement; the full power analysis with the four options; the reference construct and the still-missing UTRs; the RiboNN candidates and four remaining selection blockers; both floors unselected with blockers; the gate conflict with the three further inconsistent artifacts now enumerated; the three quantity mismatches; and six outstanding inputs.

**`configs/assay_definition_v1_2026-10-19.json` was not edited** — confirmed still at SHA-256 `37d47273…`. V2 supersedes by addition, per the project's freeze discipline.

## Still outstanding: the Stage 3 target conflict

Unchanged and still the most consequential open item. The gate records `stage3_target = cell_free_expression`; the assay is transfected cells. V2 now additionally enumerates the artifacts that carry the stale framing:

- the published README's cell-free first-target statement, live at commit `1ca32bb3`,
- V13's cell-free first target,
- **`diagram_10192026.svg`, whose gated box reads "Cell-free expression / Stage 3 target"** — the diagram I generated and you approved this morning is now known to be inconsistent with how your lab works.

That last one is worth stating plainly: the diagram is accurate about what is implemented and gated, but its Stage 3 label follows the gate file rather than your practice. If you amend the target, the diagram needs its box relabelled and the README corrected in the same publication.

I have not amended the gate, the scope, the README or the diagram.

## Verification performed

- Power figures computed with `scipy.stats.nct`, bisecting on standard deviation for the required-n and minimum-detectable-effect tables; CV mapped to log2 SD as log2(1+CV).
- **A numerical defect was found and fixed before any figure was recorded.** The first run returned `nan` for three high-power cells because `nct.cdf` loses precision at large noncentrality. The computation was guarded, so the recorded table contains no fabricated or interpolated value. The affected cells are the 100 % entries at CV 5 % and the paired CV 10 % 6-unit entry.
- Assay v2 mutation flags asserted false; v1 re-hashed and confirmed unchanged.
- The gate conflict was re-grounded by reading the gate file, not recalled.

**Not run and therefore unverified:** no sequence was folded, scored or submitted to any component, because the UTR scaffold is still missing; the CDS was not aligned to a reference database; upstream RiboNN per-task metrics were not retrieved; no inference, refit, census or publication occurred; no module or test changed, so the suite was not re-run and **220 focused tests** remains the last recorded state from V7.

## Scientific state

Unchanged. Stage 2 gate **open, 0 of 6 requirements satisfied**; RNAfold substitution into published STRAND **rejected**; `strand_rnafold_calibration_v1` has **no independent validation**; **no composite score permitted**; **no sequence carries both a stability and a translation score**; the 2,000–2,999 nt band unresolvable from Rfam seed and the PDB. No stability, translation or expression benefit established. Published snapshot remains `1ca32bb3ea4eaf05c4931fa1060be64c6d1cd82d`; V6–V9 are **local and unpublished**.

## Pending work, prioritized

1. **Decide the Stage 3 target conflict.** Gate, README, V13 and the diagram all say cell-free; your lab does transfected cells.
2. **Answer whether ORF edits must be synonymous.** Blocks any ORF proposal, and determines whether luminescence isolates mRNA-level effects at all.
3. **Supply the UTR scaffold and Ping's authoritative sequence.** Nothing can be scored until then.
4. **Supply the measured CV**, which decides whether n = 3 suffices and is the last input any floor needs. Consider the paired-across-cell-types analysis regardless, since it is the most efficient of the four options.
5. **Pin the T-cell type** (you are checking).
6. **State which ORF factors beyond codon usage are in scope.**
7. **Retrieve upstream RiboNN per-task accuracy and training-overlap evidence** — bounded, needs no decision from you, would clear two of the four remaining task-selection blockers. I can do this now.
8. **Decide band requirement 3** from V7: retrain to free the two RF02462 records, amend by gate review, or accept as a documented limitation.
9. **Decide the OpenVaccine acquisition** from V6 — still the only route to evaluating the calibration against its *own* target, which the luciferase assay cannot do.
10. **Publish V6–V9** if wanted. If the Stage 3 target is amended, correct the README statement and the diagram's Stage 3 box in the same publication.

Do not infer expression benefit from software execution, and do not optimize actual expression candidates while the gate stays open.

## Outstanding processes

None. All computation was synchronous. No background job or pending approval remains. The example CDS is recorded by hash only; the authoritative sequence should go into a proper versioned input inventory when it arrives.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-19_V9.md
cat configs/assay_definition_v2_2026-10-19.json
cat configs/stage2_to_stage3_gate_2026-10-18.json    # stage3_target still reads cell_free_expression

# Reproduce the power analysis:
.venv/bin/python -I -c "
import math
from scipy import stats
sd=lambda cv: math.log2(1+cv)
def power(fold,cv,n,alpha=0.05,paired=False):
    d=math.log2(fold)/sd(cv)
    nc,df=(d*math.sqrt(n),n-1) if paired else (d*math.sqrt(n/2),2*n-2)
    t=stats.t.ppf(1-alpha/2,df)
    p=1-stats.nct.cdf(t,df,nc)+stats.nct.cdf(-t,df,nc)
    return 1.0 if not math.isfinite(p) and nc>t+6 else min(max(p,0),1)
for cv in (0.05,0.10,0.15,0.20):
    print(cv, [round(power(1.5,cv,n),3) for n in (3,4,5,6)])
"

# Local verifications, all offline, unchanged from V7:
PYTHONPATH=src:scripts .venv/bin/python scripts/audit_band_clan_availability.py \
  --verify-run results/band_clan_availability_runs/20261019T185713.116447Z
PYTHONPATH=src:scripts .venv/bin/python scripts/build_score_records.py \
  --verify-run results/score_record_runs/20261019T175011.658062Z
PYTHONPATH=src:scripts .venv/bin/python scripts/fit_strand_rnafold_calibration.py \
  --verify-run results/strand_rnafold_calibration_runs/20261019T174049.053308Z
```

Focused suite, 220 tests, is listed in [V7](RNA-StableAI_HANDOFF_2026-10-19_V7.md#exact-continuation-commands); no code changed this session.

All seven 2026-10-19 configs are frozen; do not edit any to change an outcome. Assay definition v2 is `incomplete_pending_inputs` and should be superseded by a v3 when the UTR scaffold, authoritative sequence, measured CV, T-cell type and ORF constraints arrive — supersede, do not edit. Selecting a RiboNN task or freezing a floor each need their own versioned config with evidence. Amending the Stage 3 target needs an explicit gate review and a new versioned gate file; no config, module or script may do it. Preserve all previous versioned handoffs.
