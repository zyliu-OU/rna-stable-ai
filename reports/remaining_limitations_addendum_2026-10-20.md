# Remaining limitations — addendum, 2026-10-20

- **Project:** RNA-StableAI
- **Workspace:** `/home/zyliu/Documents/rna-stable-ai`
- **Purpose:** Stage 2 gate requirement 6,
  `Document_remaining_limitations_before_expression_candidate_design`.
- **Relationship to the earlier document:** this **extends** and does not replace
  `reports/remaining_limitations_before_candidate_design_2026-10-19.md`, which
  remains accurate and is unedited. Everything in that document still stands.
  This addendum records what changed on 2026-10-20 and what that change cost.
- **Status of this document:** a statement of limitations, not a gate decision.
  **It does not mark requirement 6 satisfied** — that is a gate-review judgement,
  recorded in `configs/stage2_to_stage3_gate_v5_2026-10-20.json`.

---

## N1. The learned pair model is retired, and with it the ability to re-run its replays

The learned pair-structure model was retired on 2026-10-20 by user decision, on
the evidence in `reports/structure_model_gap_diagnosis_2026-10-20.md`: it reached
0.2965 mean pair F1 on the long Rfam consensus references against 0.4381 for
LinearFold and 0.4215 for ViennaRNA, and 0.3255 against 0.6261 on the
structure-derived references.

886 checkpoint files (~90 MB, 97 of them tracked in git) were deleted from the
working tree.

**What this costs.** 38 replay tests reload those checkpoints and can no longer
run. They were **not** deleted; `tests/conftest.py` converts the resulting
`FileNotFoundError` into a skip with an explicit retirement reason, and only
when the missing path ends in `.pt`/`.pth`, lies under `results/`, and is not a
RiboNN weight. The practical limitation:

- Those frozen development runs **can no longer be re-verified from the tree**.
  Their metrics and summaries are retained, so the evidence behind the
  retirement is auditable, but reproducing the predictions requires recovering
  the weights from git history, and only the 97 tracked files are recoverable.
  The remaining 789 are gone.
- Any future claim about the learned model must be read as **archival**, resting
  on retained metrics rather than on a replayable artifact.

## N2. Requirement 5's replay leg was re-scoped, not restored

`Pass_constraint_decoder_resource_and_replay_checks` was written when the
learned model was the structure component, and its replay leg meant reloading
those checkpoints. That leg is now permanently unrunnable as written.

The checks were moved onto the components the project actually relies on, and
the evidence is `results/native_path_requirement5_runs/` (see the gate for the
exact run). All three legs pass:

| Leg | Result |
|---|---|
| replay | 22/22 (11 records × 2 methods) reproduce the frozen structure **and** MFE exactly |
| constraint decoder | 22/22 folds honour every enforced reference pair |
| refusal control | both tools refuse an unsatisfiable pair rather than reporting a fold |
| resources | max 8.18 s and 101 MiB against limits of 30 s and 4 GiB |

**What this does not cover.** The learned-model replay leg is not reinstated and
has no artifact to replay. A reader comparing gate versions should not read
requirement 5 as having been satisfied on its original terms.

## N3. ViennaRNA silently drops an unsatisfiable hard constraint

Established directly while building the check above, and worth recording because
it is a trap for any future constrained-design code.

Given an enforced pair that violates the minimum hairpin size — constraint
`(.)` on `GGGAAACCCUUU` — ViennaRNA 2.7.2 with
`CONSTRAINT_DB_DEFAULT | CONSTRAINT_DB_ENFORCE_BP` **drops the pair, folds
without it, and returns a finite energy** (`(((...)))...`, −2.40 kcal/mol). It
raises nothing. A caller that trusts the returned energy has silently asked a
different question.

- Mitigated only inside `src/rnastable/vienna_constraint_worker.py`, which
  verifies every enforced pair against the returned structure and exits non-zero
  when any is absent.
- **Any other code path that calls `hc_add_from_db` directly does not have that
  protection.** There is currently no such path, and this is the reason to keep
  it that way.
- LinearFold's behaviour on the same input differs: it emits no parseable
  structure at all. That is a refusal in effect, but it is not an explicit
  diagnostic, so a caller must treat an unparseable LinearFold output as a
  possible constraint refusal rather than a tool failure.

## N4. The 2,000–2,999 nt band expanded from 1 record to 5, and the earlier availability figure was wrong

The band was expanded with native controls, since a per-family cap that existed
to bound a learned model's exposure has nothing to protect when the folders have
no training set. Evidence: `results/band_native_control_runs/` (see the gate for
the exact run).

| Method | n | mean pair F1 | stdev | range |
|---|---|---|---|---|
| LinearFold | 5 | 0.5273 | 0.0805 | 0.3945 – 0.6034 |
| ViennaRNA | 5 | 0.5056 | 0.1116 | 0.3086 – 0.5863 |

**Correction to an earlier statement.** The census recorded 55 further eligible
band records (RF02540 31, RF02541 25, minus the one selected), and that figure
was repeated in gate v3's `requirement_3_resolution` as
`"available: 56 eligible records locally"`. It overstates what is usable:
selection checks the fixed family cap **before** attempting to bind a pair
reference, so those records were never binding-tested. **Only 5 of the 55
bind.** The other 50 fail with a missing annotated paired column and an
incomplete reference. Gate v3 is frozen and is not edited; the correction is
recorded here and in gate v5.

**What remains limited.** All 5 bound records are RF02540, so this cohort gives
the band dispersion but **no family contrast within itself**. With the frozen
RF02541 record the band spans two families in one clan. No clan contrast within
the band exists, and the v3 acceptance of the band as a documented limitation
still governs what may be claimed: the full 1–2,999 nt range must not be claimed
without it.

## N5. Native-control structure accuracy is modest, and it is the input to everything downstream

Requirement 4 now concerns the accuracy of LinearFold and ViennaRNA, and the
evidence is `results/native_control_validation/native_control_validation.json`:

| Cohort | n | LinearFold | ViennaRNA |
|---|---|---|---|
| long Rfam consensus (in scope) | 6 | 0.4381 | 0.4215 |
| short bpRNA five-clan | 13 | 0.3301 | 0.3346 |
| structure-derived feasibility | 10 | 0.6261 | 0.6261 |

Roughly **0.42–0.44 pair F1** against computational consensus on the in-scope
long references. The architecture is `LinearFold / ViennaRNA → STRAND + RiboNN +
BoTorch`, so this is not an isolated structural metric: it is the quality of the
**input** to the STRAND calibration and to the optimiser. Structure-derived
features carry this error forward, and no component downstream estimates or
propagates it.

Separation is satisfied by construction here — both tools are Turner-model
thermodynamic folders with no training set, so there is no exposure to separate
from — but that argument applies **only** to these two tools. It is not a claim
that the cohorts are large, diverse or representative, and it would not apply to
any learned component, including a future replacement for the retired model.

## N6. Requirement 1 is not satisfied, and no run today makes it satisfiable

`Frozen independent sequence_and_family_clan_separated_validation_within_scope`
remains unsatisfied. Retiring the learned model removed the *exposure* concern;
it did nothing about the cohort:

- **6 in-scope records**, across **3 families** and **2 clans**. (The frozen
  cohort holds 11; the other 5 are ≥3,000 nt and outside the active scope — see
  the `out_of_band` rows in the requirement 5 resource summary.)
- **Every one is a computational Rfam consensus annotation.** There is **no
  experimental-structure reference in scope at all**, and none for the
  2,000–2,999 nt band.
- The structure-derived cohort's own run records
  `broad_validation_gate_satisfied false` and `independence_certified false`. It
  is a feasibility set, not independent validation.

This is a **data acquisition problem**, not a compute problem. It is closable
only by acquiring experimental references in scope, or by an explicit
accepted-limitation decision of the same kind made for the band in v3.

## N7. BoTorch is absent, so the optimisation stage is unexercised

`botorch` is not installed in `.venv`, and `tests/test_discrete_bo.py` skips.
The final stage of the stated architecture has therefore **never been run
end-to-end against a real candidate set**. Nothing about the optimiser's
behaviour on this problem — acquisition cost, batch behaviour, or whether the
discrete design space is tractable at the intended sizes — has been measured.

## N8. Carried forward unresolved from 2026-10-19

These are unchanged and are listed so this addendum can be read alone:

- **m1Ψ is unrepresented** by RNAfold, STRAND, the calibration or RiboNN. Every
  uridine in the assayed molecules is modified. The ranking argument assumes the
  effect is sequence-independent, which is unverified.
- **The two score sides are incommensurable.** No composite is permitted, and
  the one record carrying both sides emits none.
- **No component predicts the assay's own units.** Permitted claims are
  correlation or ranking, explicitly labelled.
- **The base-pair span policy investigation is closed unresolved.** Unlimited
  span agrees best with LinearPartition; the incompatibility localises to `alo`,
  which moves about 3× tolerance from the clipping convention alone. The blinded
  85-record evaluation set is **unspent**.
- **The assay side is blocked on measurements that do not exist yet:** measured
  CVs for both readouts, the decision cost of a false accept against a false
  reject, and whether Fluc-PEST enters the panel.
- **The power convention is unresolved** between `lognormal_exact` and
  `log1p_cv`; `assay_definition_v3` has not been superseded.
- **Open questions for the collaborator:** whether the 5′UTR shortening relative
  to mRNA-1273 is deliberate, and whether the parent construct is the GenScript
  F-Luc plus alpha-globin baseline.

---

## What must not be claimed

- That requirement 5 passed on its original terms. It was re-scoped.
- That the band is resolved. It was accepted as a documented limitation in v3
  and expanded to 5 same-family records; the limitation still governs.
- That native-control accuracy against computational consensus is biological
  validation, or that any structure, stability or expression benefit has been
  established.
- That the retired model's development runs can be reproduced from the tree.
- That the full 1–2,999 nt length range is claimable without the recorded
  limitation.
