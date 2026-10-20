# RNA-StableAI — Handoff 2026-10-19 V16

- **Project:** RNA-StableAI
- **Date:** 2026-10-19 (America/Los_Angeles)
- **Version:** V16
- **Absolute workspace path:** `/home/zyliu/Documents/rna-stable-ai`
- **Supersedes nothing.** V1–V15 remain as written.
- **Published:** `github.com/zyliu-OU/rna-stable-ai`, live HEAD **`27d43f0`**
- **Scope of this handoff:** the work after V15. For the earlier part of
  2026-10-19 — transcript assembly, the reference fold, RiboNN scoring, the
  Fluc/Fluc-PEST comparison and the withdrawn coupling finding — see **V15**,
  which also carries the correction notice.

---

## 1. Headline

Three decisions were frozen, one investigation was closed without resolution,
the project's **first two-sided score record** was built, and the **first gate
requirement** was satisfied — by narrowing a claim, not by improving anything.

**Gate state: `requirements_satisfied` moved 0 → 1 of 6.** Every other scope flag
is unchanged:

- `new_sequence_scoring_enabled: false`
- `expression_candidate_design_enabled: false`
- `floors_frozen: false`
- `stage3_ready: false`
- `stage3_development_started: false`

---

## 2. Commits since V15

| Commit | What |
|---|---|
| `b8865da` | `alo` engine disagreement investigated; two hypotheses excluded, unresolved |
| `ea2c3ad` | Poly(A) and base-pair span decisions frozen; `alo` investigation closed |
| `bdb961b` | First score record carrying both stability and translation sides |
| `b39d0b8` | Remaining-limitations document (gate requirement 6) |
| `27d43f0` | **Gate v3**: 2,000–2,999 nt band accepted as a documented limitation |

---

## 3. Frozen decisions

All three were taken by the user on 2026-10-19 and are backed by measurements
already in the repository.

### 3.1 Poly(A): the modelled transcript is the 1,811 nt core

The 103 nt template-encoded tail is **not** part of the modelled transcript, for
both arms and for both folding and RiboNN inputs.

Basis: the tail is thermodynamically inert — MFE identical to six decimal places,
ensemble free energy shifted 0.017 of 772 kcal/mol, core MFE structure an exact
prefix of the tailed one, tail entirely unpaired, every other region unchanged to
the fourth decimal. RiboNN moves 0.085%, or **0.019 of the between-fold SD**.
Only `strand_alo` responds, falling 48%, and that is **dilution of a positional
mean**, not signal.

**Scope limit:** this decides the *modelled* transcript only. The real
transfected molecule still carries the tail. Appending it remains available
behind `--poly-a`; what changed is that the default is now a recorded decision.

### 3.2 Base-pair span: `max_bp_span: -1`, adopted explicitly

Basis: on the burned STRAND selection set, bounding the span degrades agreement
with the released LinearPartition features **monotonically** — 13/18 within
tolerance at unlimited, 7/18 at 600, 2/18 at 200, 1/18 at 100 — and at unlimited
`energy_per_length` agrees to **1.4 × 10⁻⁵**.

**The caveat is frozen alongside the decision, not dissolved by it.** Features on
1–2 kb transcripts remain partly set by kilobase-range pairs, in the regime where
an equilibrium MFE model is least trustworthy for mRNA that folds
co-transcriptionally and is traversed by ribosomes. The released STRAND features
**share** this property, so it is inherent to the feature definition rather than
introduced here. A test asserts that caveat text cannot quietly disappear.

**Not claimed:** that unlimited span is physically correct. Only that it
reproduces the reference engine best.

### 3.3 `alo` investigation: closed, unresolved

The blinded **85-record evaluation set remains UNSPENT**.

---

## 4. The `alo` investigation (closed)

`alo` is the sole reason the frozen verdict `feature_level_compatible: false`
stands: `energy_per_length` agrees 6/6 (to 1.4e-5) and `aup` 5/6, while `alo`
agrees 2/6.

**Excluded — the clipping convention.** STRAND's own R source
(`Figure_Scripts_2.R` lines 100–102) clips only values at or beyond the bounds
with ε = 1e-10, *not* the two-sided 1e-5 clamp the frozen criterion selected.
Matching STRAND exactly gives **1/6 — worse** than the frozen choice's 2/6.

**Excluded — the CONTRAfold model.** LinearPartition defaults to CONTRAfold and
needs `-V` for Vienna. Run directly from the vendored copy, CONTRAfold misses
`aup` by 0.082–0.169 and `alo` by 0.87–2.47, scoring **0/6 on both**. **STRAND
used Vienna parameters** — previously unrecorded, now established. ViennaRNA
exact agrees *better* than LinearPartition-Vienna on both features.

**Partially supported, not adopted.** A per-pair cutoff at 1e-6 improves `alo`
from 1/6 to 3/6 and leaves `aup` unchanged; three records land within 0.04, three
still miss by 0.085–0.266.

**Why it stopped.** The cutoff was chosen by scanning against six records whose
differences were already visible. At n = 6 that is indistinguishable from fitting
noise, and the obvious continuation — scanning until 6/6 passes — would almost
certainly succeed and mean nothing. The evaluation set can be spent once, and
spending it on a hypothesis tuned against the burned set is exactly what the
criterion's cohort split exists to prevent.

**Reopening condition:** a single pre-registered hypothesis — one cutoff, one
clipping rule, one pass criterion — written down before any evaluation-set run
and executed once.

*Artifacts:* `reports/alo_convention_investigation_2026-10-19.md`,
`results/alo_convention/alo_convention_investigation.json`.

---

## 5. First score record with both sides

Every prior record carried one side only: 91 STRAND reference sequences with
stability and no translation, 7 synthetic RiboNN inputs with the reverse.
`records_with_both_sides` was **0**.

`results/reference_score_record/FLUC-REF-V1_score_record.json`:

```
records_with_both_sides   1
joint_scoring_available   true
stability     1.319711 hours   strand_rnafold_calibration_v1, without_alo arm
translation   0.827672         RiboNN predicted_TE_A549, A549 arm
composite     None
```

**No composite is emitted.** Having both sides on one record is exactly when
combining them becomes tempting; the `score_record_schema_v1` prohibition stands
— hours on the released STRAND in-solution scale against a task scale with no
inverse transform, and no floor selected.

### The stability number's limitations are inside the record, not beside it

- A **separately named refit**, not the published STRAND model, which the frozen
  criterion rejected for RNAfold-derived features.
- **Unvalidated** — no independent evaluation; `independent_validation: false`.
- Predicts **in-solution half-life of purified RNA in buffer**; the assay
  measures **in-cell decay by RT-qPCR**. Different quantities.
- **EXTRAPOLATION.** The construct's **GC is 64.44%**; the calibration trained on
  **39.44–60.24%**. One of three features is outside the training domain. Stated
  in the payload, in the interpretation string, and pinned by a test.

The rejected published-STRAND component is carried as an **explicit exclusion**
with reason and run; the schema does not permit silence about a component.

**22 tests** pin what keeps the record honest, including that the stability value
is **recomputable from the features the record itself carries**, and one that
reproduces the calibration formula against the original R fit.

**This is an integration milestone, not a scientific one.** The stack is now
wired end-to-end on a real construct — sequence → assembly → folding → both model
arms → one provenance-bound record. No benefit is established.

---

## 6. Gate requirement 6 — remaining limitations documented

`reports/remaining_limitations_before_candidate_design_2026-10-19.md`, 20
limitations across five areas, each bound to the artifact establishing it. Every
cited path was verified to resolve.

Sections: (A) limitations bounding what any score can mean — m1Ψ unrepresented,
incommensurable units, nothing predicting the assay's units; (B) the stability
arm — published STRAND inapplicable, refit unvalidated, `alo` unresolved, span
caveat, GC extrapolation, and the withdrawn coupling finding retained as a
caution; (C) the translation arm — T-cell model-blindness, RiboNN OOD for a
designed reporter, the unconfirmed out-of-fold assumption, blindness to
protein-level effects; (D) the structure side and the gate itself; (E) the
planned experiment — underpowered, no floor freezable, construct provenance
partly unconfirmed.

**This document does not mark requirement 6 satisfied.** That is a gate-review
judgement. Requirement 6 remains `partially_satisfied`.

**Two corrections surfaced while writing it:** requirements **5 and 6 were
already `partially_satisfied`**, not unsatisfied as earlier summaries implied.

---

## 7. Gate v3 — the 2,000–2,999 nt band accepted as a limitation

`configs/stage2_to_stage3_gate_v3_2026-10-19.json`. v2 is superseded **as a new
file and retained unedited** at hash
`8ca6b32e8aa9389037c299a6d1cbcb47f41dc3b0cd35f806931c17fba40bceef`, exactly as v2
did with the 2026-10-18 gate. v2's amendment of the Stage 3 target to transfected
cells carries forward unchanged.

**Requirement 3 is satisfied by narrowing a claim, not by improving coverage.**
The band still rests on exactly **one record**, family RF02541, clan CL00112, so
its per-band accuracy figure carries **no dispersion and no family or clan
contrast**. Nothing about the model changed.

### Binding consequence

| Range | Claimable? |
|---|---|
| 1–1,999 nt | without caveat |
| 2,000–2,999 nt | **only with the recorded limitation** |
| full 1–2,999 nt | **may not be claimed** |

The **active scope is unchanged** at 1–2,999 nt: the band stays in scope for
inference and leaves only unqualified accuracy claims.

### What was available and not taken

- **Family-level expansion: available.** 56 eligible records locally — RF02540
  (31) and RF02541 (25) — with **RF02540 a family not currently in the
  selection**.
- **Clan-level expansion: not available.** The only out-of-baseline band clan,
  CL00004 via RF02462, is blocked by `prior_exposure_overlap` on both its records.

This is recorded in the gate so a later reader does not mistake a **choice** for
an impossibility. An earlier note in this project described the band as
"unreachable"; **that applied to clan coverage only**, and the distinction is now
explicit.

**11 tests** pin the amendment, including that the claim actually narrows, the
other five requirements are untouched, the superseded gate stays frozen at its
hash, and that satisfying one requirement **does not open the gate**.

---

## 8. Verification actually run

| Check | Outcome |
|---|---|
| **Full suite** | **1,274 passed, 1 skipped, 0 failed** in 218.85 s |
| Lint | `ruff check` clean on every file changed |
| Score record | 22 tests; stability value recomputable from the record's own features |
| Calibration formula | reproduces the original R predictions to 1e-9 across ≥10 training records |
| Gate v3 | 11 tests; v2 verified unedited at its recorded hash |
| Limitations doc | every cited artifact path verified to resolve |
| LinearPartition | run directly from `external/LinearPartition`, both model modes |

Suite trajectory this session: 1,238 → 1,241 → 1,263 → **1,274**, zero failures
throughout. Python **3.12.14**, scipy **1.18.1**, ViennaRNA **2.7.2**.

**Environment note.** Use `/home/zyliu/Documents/rna-stable-ai/.venv/bin/python`.
The default `python3` is Anaconda base (3.14.6) and lacks biopython, producing 15
collection errors that are an environment artifact, not code defects.

### File hashes at session end

| File | SHA-256 |
|---|---|
| `configs/stage2_to_stage3_gate_v3_2026-10-19.json` | `2ef91eb9a5c02da0e23c69165ac3f2efa9a578b5de4173cf01ade16a34b3e012` |
| `configs/transcript_inputs_v1_2026-10-19.json` | `3c36ed171621bde6fdfe34cf938838da4d2dbefc2f5cbe67333d6db9ebe94dc9` |
| `scripts/build_reference_score_record.py` | `36acaabc8750ce4f88595a50a6d7f8d9489485eeaa5f6f7b72540e295c450e75` |
| `tests/test_reference_score_record.py` | `adb29c6dbe161438f3c33d3e4930b75c70b65b4249450afae3b0f55c0b16dafe` |
| `tests/test_stage2_gate_v3.py` | `97d1f54da54a3e177b74fbd04c7176d13dd8db053af1416c4246d1b618e9d076` |
| `results/reference_score_record/FLUC-REF-V1_score_record.json` | `49ce691894e4ce9f2043fadc66f344d94ce81fdff6c21a9ba774f71483b4f576` |
| `reports/remaining_limitations_before_candidate_design_2026-10-19.md` | `f007b1cb8250f805e417ae67fb72e7968654f9acdbfe17952e56602766329282` |
| `reports/alo_convention_investigation_2026-10-19.md` | `84aba697d678c895dec409c5883dbbe3b6021462048192436ec8188baa4633a4` |

---

## 9. Unverified / not done

- **No measured CV exists.** All power figures are arithmetic on an assumed bound.
- **Nothing has been compared to a measurement.** No cell data exists.
- **Requirement 6 is not marked satisfied**; the document addresses it but the
  gate-review judgement was not taken.
- The evaluation set is **unspent** and the `alo` question is **unresolved**.
- The archive `build` was again **not** re-run (V12 §6 item 7 still undecided).
- `assay_definition_v3` was **not** edited; the V13 power-convention decision is
  still open.
- The 5′UTR shortening relative to mRNA-1273 is **not confirmed** as deliberate.
- `classify_construct_edit` has still **never been run against a candidate**.
- RiboNN run directories are kept local, as with every prior inference run.

---

## 10. Prioritized next steps

**The gate is the bottleneck, and the remaining requirements need modelling work,
not decisions.**

1. **Requirement 4 is the hard one.** `Demonstrate_credible_structure_accuracy`
   is `not_satisfied`, and the limitations document records that **the learned
   model is below both LinearFold and ViennaRNA on development references**.
   Credible accuracy is difficult to argue while that holds. This probably
   deserves an explicit decision about whether the structure model is the right
   thing to keep investing in.
2. **Requirement 1** — frozen independent family/clan-separated validation. The
   in-scope selection is 6 records across 3 families and 2 clans, and every
   reference is a computational Rfam consensus, not experimental.
3. **Requirements 2 and 5** are `partially_satisfied` and may be closable with
   bounded work.

**Needs a user decision:**

4. Mark requirement 6 satisfied, or state what more it needs.
5. **Measured CVs** and the **decision cost** — the last inputs any floor needs.
6. Does **Fluc-PEST** enter the panel?
7. Power convention → `assay_definition_v4`, or leave v3 (V13 §6 item 1).
8. OpenVaccine acquisition (V6); archive `build` re-run (V12 §6 item 7).

**Worth asking Ping:**

9. Is the 5′UTR shortening (omitted `GGG`, internal `CCCCGGCGCC`) deliberate?
10. Is the parent the same GenScript F-Luc + alpha-globin composition used as the
    mRNAutilus baseline?

---

## 11. Exact safe continuation commands

Run from `/home/zyliu/Documents/rna-stable-ai`. All are read-only or test-only.

```bash
# Full suite — MUST use the project virtualenv
timeout 3000 .venv/bin/python -m pytest -q

# This session's tests
.venv/bin/python -m pytest tests/test_reference_score_record.py tests/test_stage2_gate_v3.py -q

# Rebuild the score record without writing
.venv/bin/python scripts/build_reference_score_record.py --dry-run

# Current gate state
.venv/bin/python -c "
import json; d=json.load(open('configs/stage2_to_stage3_gate_v3_2026-10-19.json'))
print('satisfied:', d['requirements_satisfied'], 'of', len(d['requirements_before_stage3']))
print('stage3_ready:', d['stage3_ready'])
print('claimable without caveat:', d['claimed_length_range']['claimable_without_caveat'])
"

# Confirm the superseded gate is still unedited at its recorded hash
sha256sum configs/stage2_to_stage3_gate_v2_2026-10-19.json
# expect 8ca6b32e8aa9389037c299a6d1cbcb47f41dc3b0cd35f806931c17fba40bceef

# Re-run the span diagnostic (burned selection set only)
.venv/bin/python scripts/diagnose_bp_span_policy.py --spans="-1,600,200,100"

# Confirm live publication state
git ls-remote https://github.com/zyliu-OU/rna-stable-ai.git main   # 27d43f0
```

Do **not** run `scripts/archive_replay_sources.py` without `--verify`. The
assembly, fold and score-record scripts refuse to overwrite existing artifacts.

---

## 12. What must not be claimed

- **One requirement satisfied is not progress toward structure accuracy.** It was
  satisfied by narrowing a claim; the band still rests on one record and nothing
  about the model changed.
- **The full 1–2,999 nt range may not be claimed.** Any statement spanning
  2,000–2,999 nt must carry the recorded limitation.
- A green suite of 1,274 tests is **not** evidence of structure accuracy,
  stability, translation or expression benefit.
- **A two-sided score record is not a joint prediction.** The two scores are
  incommensurable and are deliberately not combined; no composite exists.
- The stability score is **unvalidated and extrapolated** on GC. It is not a
  predicted half-life for the assayed molecule.
- **No computed structure or free energy is the assayed molecule's**, because
  every U is actually m1Ψ and no component models it.
- The published STRAND verdict stands: `feature_level_compatible: false`,
  `outcome: rejected`. The `alo` question is unresolved, not answered.
- **Fluc-PEST is not shown to translate less well** (V15 §3.6).
- The **withdrawn** UTR–ORF coupling conclusion must not be re-derived from the
  earlier report without its correction notice (V15 §4).
- The T-cell arm remains **model-blind**; PARADE's Jurkat data does not fill it.
- The power figures are planning arithmetic on an **assumed** CV.
- No floor is selected or frozen; sequence scoring and candidate design remain
  disabled.
