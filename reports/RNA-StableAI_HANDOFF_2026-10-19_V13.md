# RNA-StableAI — Handoff 2026-10-19 V13

- **Project:** RNA-StableAI
- **Date:** 2026-10-19 (America/Los_Angeles)
- **Version:** V13
- **Absolute workspace path:** `/home/zyliu/Documents/rna-stable-ai`
- **Supersedes nothing.** V1–V12 of 2026-10-19 remain as written. This handoff
  records one new unblocked build item: the assay power arithmetic is now
  executable code pinned by tests, and a discrepancy in the frozen figures was
  found in the process.
- **Session trigger:** user asked to "check the handoff and continue the build"
  after a computer restart. V12 ended with nothing running; that was confirmed.

---

## 1. Current user priorities and scope

Unchanged from V12. The 5′/3′ UTR sequences are still outstanding, so this
session again took up only work that does **not** depend on the pending
transcript.

Scope flags, all unchanged and still binding:

- `new_sequence_scoring_enabled: false`
- `expression_candidate_design_enabled: false`
- `floors_frozen: false`
- `stage3_ready: false`
- Stage 2 gate: **0 of 6** requirements satisfied
  (`configs/stage2_to_stage3_gate_v2_2026-10-19.json`).

Nothing in this session changed any flag or satisfied any gate requirement.

Decisions carried from V11/V12 are unchanged: Stage 3 target
`transfected_cell_expression`; ORF edits synonymous only; T-cell arm model-blind
with no RiboNN task; CV below 20% as a **planning bound, not a measurement**.

---

## 2. State inherited from V12, verified before any change

| Check | Command | Outcome |
|---|---|---|
| Full suite as inherited | `timeout 3000 .venv/bin/python -m pytest -q` | **1,103 passed, 1 skipped, 0 failed** in 220.39 s — matches V12 exactly |
| Frozen source archive | `.venv/bin/python scripts/archive_replay_sources.py --verify` | passed, 271/281 bindings, 10 missing stated explicitly |
| V12's three files intact | `sha256sum` | all three match the hashes recorded in V12 §3 |

So V12's work survived the restart unchanged, and the build was green before
this session touched anything.

---

## 3. Completed work: the power arithmetic is now replayable

### 3.1 The gap

`configs/assay_definition_v3_2026-10-19.json` records four specific numerical
claims under `assay.measurement_error.power_consequence`:

- `power_at_n3`: `{cv_10: 0.967, cv_15: 0.757, cv_20: 0.542}`
- `required_n_at_cv_20_for_80pct: 5`
- a minimum detectable effect of **1.75-fold** at n=3, CV 20%
- a paired alternative: **6 paired units reach 98.9%** power at CV 20%

These figures carry the design conclusion that the assay is underpowered for its
own 1.5-fold target. A grep over `src/`, `scripts/`, `tests/`, `configs/` and
`results/` found them **only** in the v2/v3 config files and in handoff prose:
**no code computed them and no test checked them.** A design conclusion that
rests on arithmetic nobody can replay is not auditable. That gap needs no
transcript to close, which is why it was the right item to take up.

### 3.2 Method recovery

The recorded figures were reproduced exactly by identifying the convention used.
The model is a two-sided two-sample t-test on the natural-log scale, with the
log-scale standard deviation taken as **`ln(1 + CV)`**:

| CV | Replayed under `ln(1+CV)` | Config value |
|---|---|---|
| 0.10 | 0.9668 | 0.967 |
| 0.15 | 0.7567 | 0.757 |
| 0.20 | 0.5418 | 0.542 |

Maximum deviation **0.0003**, which is rounding. The other three claims also
replay exactly under the same convention: `required_n = 5`, MDE
**1.7505-fold** (recorded 1.75), paired n=6 power **0.9892** (recorded 0.989).
The frozen config is therefore internally consistent, and its method is now
fully recovered rather than inferred.

Conventions ruled out, each reproducing none of the four figures: exact
log-normal `sqrt(ln(1+CV²))`; CV used directly as a log-scale sd; `CV/(1+CV)`;
one-sided variants of all of these; and normal-approximation power in place of
noncentral t.

### 3.3 Finding: the frozen figures are optimistic

`ln(1 + CV)` is **not** the log-normal relation. For a log-normal with
coefficient of variation CV, the log-scale standard deviation is
`sqrt(ln(1 + CV²))`. The two agree to first order in CV and diverge as CV grows,
with `ln(1+CV)` the smaller and so the more optimistic of the pair. Recomputing
under the exact relation at CV 20%:

| Quantity | Frozen (`ln(1+CV)`) | Exact (`sqrt(ln(1+CV²))`) | Direction |
|---|---|---|---|
| Power at n=3, 1.5-fold | 0.542 | **0.479** | less favourable |
| Smallest n for 80% power | 5 | **5** | **unchanged** |
| MDE at n=3 | 1.75-fold | **1.84-fold** | less favourable |
| Paired power at n=6 | 0.989 | **0.976** | less favourable |

Three of four figures move against the design; one is robust. **Every
qualitative conclusion already recorded in the config survives**: n=3 is
underpowered at the stated bound, n=5 is the replicate count that reaches 80%,
the MDE exceeds the 1.5-fold target, and a paired analysis at 6 units is
adequate. This is a sharpening of the numbers, **not a reversal of any
decision**, and it makes the recorded design problem slightly worse rather than
better.

### 3.4 What was built

**`src/rnastable/assay_power.py`** (new). Pure planning arithmetic, no
measurement, no biological claim.

- `log_scale_sd(cv, convention)` — both conventions, named explicitly:
  `lognormal_exact` and `log1p_cv`.
- `power(cv, n, fold_change, convention, design, alpha)` — two-sided, noncentral
  t. The normal approximation is deliberately **not** used: at n=3, CV 20% it
  returns 0.708 against the correct 0.542, overstating power by 0.166. A test
  pins that gap so the shortcut cannot be reintroduced quietly.
- `required_replicates(...)` — returns `None`, not an exception and not 0, when
  the target is unreachable within `max_n`, so a caller can report "not
  reachable at this CV" instead of treating an exhausted search as an error.
- `minimum_detectable_fold_change(...)` — bisection on the log effect, with a
  grown rather than fixed upper bracket so extreme CVs stay solvable.
- `assess(...)` → frozen `PowerAssessment` dataclass carrying the convention,
  the design, both power and MDE, and an explicit `no_claim` string.

Two deliberate design points, both tested:

1. **The dispersion convention has no default.** Defaulting either way would
   silently pick a side of the §3.3 discrepancy. Callers must state it.
2. **`target_reachable_at_this_size`** is true only if the design both reaches
   target power on the target effect *and* resolves an effect no larger than
   that target. Power alone would call a design adequate while its MDE still
   exceeded the effect it was built to find.

A percentage-shaped CV (`20` meaning 20%) is rejected loudly rather than
silently modelled as CV 2000%.

**`tests/test_assay_power.py`** (new), **46 tests**. Four of them replay the
frozen config's four claims by reading
`configs/assay_definition_v3_2026-10-19.json` directly, so the config can no
longer drift away from the arithmetic unnoticed. Others pin the direction of the
convention discrepancy, the robustness of `n=5` to it, the convergence of the two
conventions as CV shrinks, monotonicity in n / effect / CV, the power-MDE
inverse relation, two-sided symmetry, and the full input-validation surface.

### 3.5 The frozen config was deliberately NOT edited

`configs/assay_definition_v3_2026-10-19.json` is unchanged, hash
`97be8d631c563e1ba36c4ebaa41d8648d9c7e8319b9e7bbaf7ede34df2e0272b`. Rewriting a
frozen artifact's recorded numbers is not a decision to take unasked, and the
figures are not wrong *under their own stated convention* — they are merely
optimistic relative to the exact one. The correct resolution is a user decision,
recorded as pending item 1 in §6. This follows the precedent set in V12, where
`check_synonymous_edit`'s frozen contract was left intact and a separate
function was added alongside it.

---

## 4. Verification actually run

| Check | Command | Outcome |
|---|---|---|
| New tests | `.venv/bin/python -m pytest tests/test_assay_power.py -q` | **46 passed** in 0.60 s |
| **Full suite** | `timeout 3000 .venv/bin/python -m pytest -q` | **1,149 passed, 1 skipped, 0 failed** in 220.70 s |
| Lint | `ruff check src/rnastable/assay_power.py tests/test_assay_power.py` | **All checks passed** |
| Frozen config untouched | `sha256sum configs/assay_definition_v3_2026-10-19.json` | `97be8d63…` |

Suite went from 1,103 → **1,149** passed (+46), still 0 failures. Runtime
versions: Python **3.12.14**, scipy **1.18.1**.

**Environment note, still important.** The suite must be run with
`/home/zyliu/Documents/rna-stable-ai/.venv/bin/python`. The default `python3` is
Anaconda base (3.14.6) and lacks biopython, producing 15 collection errors that
are an environment artifact, not code defects.

### Files changed this session

| File | SHA-256 | Git state |
|---|---|---|
| `src/rnastable/assay_power.py` | `301dd9a67b9a5b1f41daa4ca4219e394641cff5af0b35d1a7910253f229233a3` | new, untracked locally |
| `tests/test_assay_power.py` | `75e7a1ef5e31174a6b596e4a30f77f8801b18161511d274097f34d29d92f0ba6` | new, untracked locally |

Carried forward from V12, still unpublished and unchanged:

| File | SHA-256 |
|---|---|
| `src/rnastable/component_integration.py` | `9ef50ff82e10a75ab6d3de30f2195d72e4ecaad6281f48304a660936d502b00c` |
| `scripts/archive_replay_sources.py` | `fbd073cd42a3fd93891b5439d66f55897d8bdcd600d32b63c3362c54ee1a2943` |
| `tests/test_construct_edit_classification.py` | `36735e0520621c9087cf18c51d12d6c418355f5068044c4f0e18d77477cef49a` |

**Nothing was published this session.** The local repository still has no
commits; publication has always been done from a fresh isolated clone. Five
files now await publication. See §6 item 2.

---

## 5. Unverified / not done

- **No measured CV exists.** Every figure in §3 is planning arithmetic from an
  assumed bound. `assay_power.py` measures nothing.
- The log-normal model itself is **an assumption about the readouts'
  distribution**, not a fit to lab data. Neither convention is validated against
  any measurement, because none has been supplied.
- `classify_construct_edit` (V12) has still **never been run on a real
  construct** — blocked on the transcript.
- The archive `build` was again **not** re-run; only `--verify`. The question in
  V12 §6 item 7 is still undecided.
- No folding, no scoring, no RiboNN inference was run this session.
- RiboNN primary CD4+ activation state: **not revisited.** V12 §4 records four
  exhausted routes and the reason it cannot change the model-blind decision.

---

## 6. Prioritized next steps

**New, and a user decision:**

1. **Decide how to resolve the convention discrepancy (§3.3).** Three options:
   (a) issue `assay_definition_v4` recomputing the four figures under
   `lognormal_exact`, superseding v3 and leaving v3 frozen and intact;
   (b) keep v3's figures and record the convention explicitly in it as an
   acknowledged approximation; (c) leave as is, since no qualitative conclusion
   changes. Recommendation: **(a)**, because the figures are quoted as the reason
   the design is underpowered, and the exact convention makes that case stronger
   while `n=5` — the actionable number — does not move at all.

**Blocked on the user (unchanged from V11/V12):**

2. The transcript: 5′UTR and 3′UTR sequences, which construct is the
   parent/baseline, plasmid DNA vs IVT mRNA, poly(A) presence and length, cap
   chemistry and nucleoside modifications, and Ping's authoritative CDS.
3. **Measured CVs** for luciferase normalized expression and the RT-qPCR
   half-life estimate, to replace the 20% planning bound. §3 is the direct
   argument for why this matters: at CV 10% the design works, at 20% it does not.
4. Decision cost of a false accept vs a false reject.
5. Band requirement 3 (V7); OpenVaccine acquisition decision (V6).

**Not blocked:**

6. **Publish the five unpublished files** (§4). Nothing is published yet.
7. Optionally re-run the archive `build` — still requires the V12 §6 item 7
   decision on whether the frozen summary may be superseded.

---

## 7. Exact safe continuation commands

Run from `/home/zyliu/Documents/rna-stable-ai`. All are read-only or test-only.

```bash
# Full suite — MUST use the project virtualenv, not the Anaconda base python3
timeout 3000 .venv/bin/python -m pytest -q

# This session's new tests only
.venv/bin/python -m pytest tests/test_assay_power.py -q

# Replay the frozen config's four power claims and print both conventions
.venv/bin/python -c "
from rnastable.assay_power import assess
for c in ('log1p_cv','lognormal_exact'):
    r = assess(0.20, 3, 1.5, c)
    print(c, 'power', round(r.power_at_target,4),
          'MDE', round(r.minimum_detectable_fold_change,4),
          'n_needed', r.required_replicates_for_target_power)
"

# Verify the frozen source archive without recomputing it
.venv/bin/python scripts/archive_replay_sources.py --verify

# Re-derive this session's file hashes
sha256sum src/rnastable/assay_power.py tests/test_assay_power.py

# Confirm the frozen assay config is still untouched
sha256sum configs/assay_definition_v3_2026-10-19.json

# Confirm the live publication state
git ls-remote origin main
```

Do **not** run `scripts/archive_replay_sources.py` without `--verify` until V12
§6 item 7 is decided: it overwrites the frozen
`results/replay_source_archive_summary.json`.

---

## 8. What must not be claimed

- This session satisfied **no** Stage 2 gate requirement. Still **0 of 6**.
- A green suite of 1,149 tests is **not** evidence of structure accuracy,
  stability benefit, translation benefit or expression benefit.
- **The power figures are not measurements.** They are arithmetic on an assumed
  CV bound the user supplied as a planning figure. No CV has been measured, so
  no statement about the actual sensitivity of the planned experiment is
  supported — only about what it would be *if* the assumed dispersion held.
- Reproducing the frozen config's figures validates **the arithmetic**, not the
  design, the assumed CV, or the log-normal distributional assumption.
- The §3.3 discrepancy does **not** reverse any recorded decision; it makes the
  already-recorded underpowering slightly worse. It must not be reported as
  "the config was wrong".
- No floor is selected or frozen. No sequence may be scored until the transcript
  inputs in `configs/assay_definition_v3_2026-10-19.json` are supplied.
- The T-cell arm carries no translation-side model score, and none may be
  inferred from the A549 arm.
- The RiboNN A549 per-task accuracy still rests on the unconfirmed assumption
  that the released prediction table holds out-of-fold predictions.
