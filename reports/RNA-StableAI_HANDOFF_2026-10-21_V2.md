# RNA-StableAI — Handoff 2026-10-21 V2

- **Project:** RNA-StableAI
- **Date:** 2026-10-21 (America/Los_Angeles)
- **Version:** V2 — **supersedes V1 of this date on the Stage 3 target**, and supersedes
  handoff 2026-10-20 V11 §1 item 1 as a statement about the *goal*. V1 and V11 remain and are
  not edited.
- **Absolute workspace path:** `/home/zyliu/Documents/rna-stable-ai`
- **Remote:** `https://github.com/zyliu-OU/rna-stable-ai.git` — **PUBLIC**
- **Publication clone:** `/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad/pub2`
- **Project interpreter:** `.venv/bin/python` (3.12). Bare `python3` is anaconda 3.14 without
  biopython and must not be used.

---

## 1. Why this handoff exists: V1 published a wrong target statement

V1 of this date published a README that restated the **Step 3 goal** as in-cell mRNA stability,
on the authority of V11 §1 item 1 ("The target axis is IN-CELL mRNA STABILITY … Not in-cell
expression"). The user corrected it:

> "wait, for development, plan, we still want expression."

**The user is right, and the frozen record proves it.** `configs/stage2_to_stage3_gate_v15_2026-10-20.json`
carries `stage3_target: "transfected_cell_expression"`, and so does every gate from v2 forward.
**The gate chain never changed the goal to stability.** V11's statement was about which
*measured label* the model is fitted and screened against — in-cell half-life — and V1
over-applied it to the project's objective. The README, not the gate, was out of step.

**Root cause, recorded so it is not repeated:** V1 read a target decision out of a handoff's
prose and published it without checking it against the frozen artifact that actually holds
`stage3_target`. The gate chain is the authority on the target; a handoff sentence is not.

### 1.1 The second decision taken this stretch

Asked whether cell-free / in-vitro-translation expression should return to scope, the user
chose **"Yes — bring it back as an active target."** This **reverses the 2026-10-19
amendment** that set the target to transfected cells, and it is an addition, not a
replacement: both arms are now active.

### 1.2 The question that prompted all of this, and the answer given

> "is there difference between in solution expression and in-cell expression?"

Answered as follows, and the answer is why the cell-free arm needed its own status fields
rather than being folded into the existing assay definition:

| | Translation machinery? | What is measurable |
|---|---|---|
| **In solution (buffer)** | No | **Degradation only.** No expression exists to measure. This is the project's in-solution half-life axis (PERSIST-seq `Fig_S8a`). "In-solution expression" is a category error in this sense. |
| **Cell-free / IVTT** (lysate or reconstituted) | Yes | Expression is real and measurable. No delivery step, no membrane, cellular decay pathways absent or attenuated, no innate-immune sensing, short reactions. **This is the only sense in which "in-solution expression" exists — and it was this project's Stage 3 target until 2026-10-19.** |
| **In-cell (transfected)** | Yes | Protein output, confounded by uptake/delivery, innate immunity and in-cell decay. |

Three measured results from this project bear on the distinction and are now cited in the
gate as prohibitions:

1. **The two measured stability axes rank at only +0.0545**
   (`results/two_axis_comparison_runs/20261021T042044.996926Z`,
   `measured_axes.spearman_between_the_two_measured_axes`). Solution and cell disagree even
   about *stability*, which is simpler than expression.
2. **Stability gains do not imply expression gains.** On the six constructs measured both
   ways, pseudouridine moved in-solution half-life the **same direction for all six**, while
   protein output spanned **13-fold and changed sign** (0.234× to 3.309×). Six constructs
   support no significance claim and none is made.
3. **Translation is not a single coupled axis.** Ribosome load vs in-cell half-life flips sign
   by design family: +0.4916 on 78 CDS (Nluc) variants, −0.5551 on 49 UTR (5′) variants.

**Transfer from cell-free to transfected cells is unmeasured in this project.** No data here
bears on it, and the nearest evidence (point 1) is adverse.

---

## 2. Decisions now in force

1. **The Step 3 goal is protein expression.** Two active arms: **cell-free (IVTT) expression**
   (reinstated 2026-10-21) and **transfected-cell expression**.
2. **In-cell mRNA stability (half-life / decay) is the axis currently fitted and screened**,
   not the goal and not a validated proxy for it. Basis: 122–203 records carry measured
   half-lives against **6** constructs with measured protein output, so expression is not
   currently trainable on this data.
3. **Translation stays a separate, incommensurable Pareto axis.** Never folded into the
   stability objective, never combined into a composite score.
4. **The cell-free arm is declared but NOT defined.** No scoring, no candidate design, no
   assumed transfer until its parameters are supplied.
5. The architecture is unchanged: RNAfold + STRAND + RiboNN + BoTorch.
6. Reinstating cell-free does **not** withdraw the 2026-10-19 reason the transfected-cell arm
   exists: the lab works in transfected cells.

---

## 3. Artifacts created this stretch

### 3.1 `configs/assay_definition_v4_2026-10-21.json`

Supersedes `assay_definition_v3_2026-10-19.json` (sha256 recorded:
`97be8d631c563e1ba36c4ebaa41d8648d9c7e8319b9e7bbaf7ede34df2e0272b`). v1–v3 remain frozen and
unedited, and **code and tests continue to pin v3 by name**
(`src/rnastable/assay_power.py`, `src/rnastable/component_integration.py`,
`scripts/fold_reference_transcript.py`, `scripts/assemble_reference_transcript.py`,
`tests/test_transcript_assembly*.py`, `tests/test_assay_power.py`,
`tests/test_construct_edit_classification.py`). **v4 changes the target set and nothing else**;
every assay parameter, constraint, reference-construct field and power calculation is carried
forward unchanged, so no value those modules read has moved.

What it records: both decisions with the user's quotes; `not_cell_free` flipped to `false` with
its history preserved; `stage3_target` as a structured object (goal, two arms, modeled axis);
and a `cell_free_arm` block holding **8 blocking inputs** (which IVTT system; lysate vs
reconstituted; temperature/duration/time points; input form and whether capped and
polyadenylated; cap chemistry and modifications; the readout and whether RNA abundance is
measured in parallel; replicate structure and whether a measured CV exists; whether the parent
construct is shared with the other arm), **5 known biological differences** from the
transfected-cell arm, and an explicit `transfer_is_unmeasured` field. The v3 power calculation
is carried forward with a note that **it was not redone for a cell-free arm**.

### 3.2 `configs/stage2_to_stage3_gate_v16_2026-10-21.json`

Supersedes v15 (sha256 `eb0b06808093f1c9c89efb374c2c261660f695c02f1eb153ce88c82a3cd755fa`),
which remains frozen and unedited. **This is the gate V11 left unwritten.** V11 recorded that
the writing script failed with `KeyError: 'split'` because the preserved-split screen artifact
predates the `split` field added for the stratified run; v16 was therefore **written by hand
from V11 §1–3. No screen artifact was re-read and no number was recomputed.**

- `stage3_target` becomes the structured object, with `prior_value_in_v2_through_v15` recorded
  as `transfected_cell_expression` so the chain's actual history stays visible.
- **Five prohibitions added, none withdrawn.** The three from V11 (RiboNN must not be wired
  into the stability objective; no screened feature is adopted; the screen did not improve
  resolution) plus two that follow from extending the target set (no candidate ordering
  transfers across systems; in-cell stability is not a validated expression proxy). Each
  carries its measured basis, not just its text.
- `requirements_satisfied` stays **6**, `requirements_before_stage3` is byte-identical to v15,
  `switches_unchanged_from_v6` is byte-identical to v15, and `prohibition_withdrawn_here` is
  `null`.
- One switch added: **`cell_free_scoring_enabled: false`** — opened as an explicitly closed
  switch rather than left unrepresented.
- The RiboNN prohibition records `what_is_still_permitted`: RiboNN remains a separate Pareto
  axis. The prohibition is about wiring it into stability, not about using it at all.

### 3.3 `tests/test_stage2_gate_v16.py` — 13 tests

Mirrors the intent of `test_stage2_gate_v15.py`. Pins the v15 and assay-v3 hashes; that
nothing was reopened or re-ratified; that **no prohibition was withdrawn** (v15 withdrew one
with cause, and that must not become a habit); that the **goal is expression and the chain
never said otherwise**, using v15's own `stage3_target` as the witness; that the
transfected-cell arm survives the reinstatement; that the cell-free arm is declared but not
defined with its switch closed and at least 5 blocking inputs; that the reinstatement does not
erase why cell-free was retired; that `expression_benefit_established` is still false; and
that each of the five prohibitions carries its measured numbers (+0.4916/−0.5551/+0.0879,
37 features on 105 records, 0.500–0.523, +0.0545, 13-fold and the sign change).

### 3.4 `README.md` — five corrections

| Location | Correction |
|---|---|
| Plan header paragraph | Goal is protein expression, two arms, both configs linked. In-cell stability named as the **modeled axis** with its label-count basis (122–203 vs 6) and the explicit statement that it is **not a validated proxy**, citing the 13-fold sign change. |
| Step 3 table row | "RNA sequence optimization for protein expression", two arms, modeled axis named, cell-free declared-not-defined and unscoreable. |
| Architecture note | Records the 2026-10-19 amendment **and** the 2026-10-21 reinstatement, and that the reversal does not withdraw the lab-practice reason. |
| `### Step 3 goal and plan` | Heading and objective restored to protein expression efficiency, two arms named, with an italic note on how the modeled axis relates to the goal and where the cell-free open questions live. |
| 2026-10-21 section | Heading changed from "the target axis is fixed as in-cell stability" to "the target set is extended"; opening paragraph rewritten; gate-state paragraph rewritten from "v16 has not been written" to v16 current, with all five prohibitions and the closed switch. |

The four numbered steps of the Step 3 plan are **unchanged from the original expression
wording** — V1 had edited step 1 to "target cell system", which is now back to "each target
system" to cover both arms.

---

## 4. Verification actually run

| Check | Command | Outcome |
|---|---|---|
| New gate tests alone | `.venv/bin/python -m pytest -q tests/test_stage2_gate_v16.py` | **13 passed** |
| Full suite | `.venv/bin/python -m pytest -q` | **1,166 passed** (1,153 baseline + 13 new), 1 known Ninja/BoTorch warning, 13.70 s |
| Stale target claims | `grep -n -iE "target axis is in-cell\|target is in-cell mRNA stability\|amended again on 2026-10-20 to" README.md` | no matches |
| Image references | `grep -c -E "workflow_10202026.svg\|diagram_10182026.png" README.md` | 2 |
| v15 / assay-v3 hashes | pinned inside `test_stage2_gate_v16.py` | match |
| Two-axis figure quoted | `results/two_axis_comparison_runs/20261021T042044.996926Z/summary.json` | `+0.05452694955075821`, read directly |
| Gate v15 target field | read from the frozen config | `"transfected_cell_expression"` |

**Not run, and not claimed:** no experiment, no protocol replay, no screen or refit re-run, no
inference, no retraining, no power recalculation for the cell-free arm. Every measured number
in the new configs and README text was transcribed from existing handoffs and run artifacts.

---

## 5. What must not be claimed

Carried from gate v16 `no_claim_permitted` and the five prohibitions:

1. Extending the target set satisfies **no** Stage 2 requirement; 6 of 6 remain satisfied on
   the v5 basis, and nothing is reopened.
2. Naming expression as the goal establishes **no expression benefit**. None has been measured.
3. Reinstating the cell-free arm establishes nothing about it and permits **no scoring** for it.
4. No candidate ordering transfers across systems — not cell-free to cells, not solution to
   cell (+0.0545).
5. In-cell stability is **not** a validated proxy for expression (13-fold span, sign change).
6. RiboNN / measured ribosome load must not be wired into the stability objective.
7. No screened in-cell feature is adopted or validated, and the screen did not improve
   resolution (0.500–0.523 against chance 0.50).
8. The calibration is not independently validated, and GC content (CDS) at +0.3651 still beats
   it on its home axis.

---

## 6. Pending work — prioritized

1. **Supply the cell-free arm's 8 blocking inputs** (`assay_definition_v4`,
   `cell_free_arm.blocking_inputs`). Until then the arm is a declared target with no assay and
   `cell_free_scoring_enabled` stays false. The power calculation also needs redoing for it.
2. **Decide whether the cell-free arm needs its own feature screen.** The in-cell screen's two
   signals were selected against in-cell half-life; nothing in this project has been evaluated
   against any cell-free readout.
3. **Tests for `in_cell_feature_screen_v1`** and its run artifacts. Still none.
4. **The combined two-feature model** — the obvious next experiment, since the two surviving
   signals are only −0.182 apart. Needs its own declared protocol and must respect the ~1–2
   feature budget from gate v15.
5. Discount `cds_length` as a length ruler, or show it is not one.
6. Find a mechanism for `utr5_frac_C`, or state it stands as an unexplained correlate.
7. The reference transcript is still blocked on the v3 `blocking_inputs` (5′/3′ UTR sequences,
   parent construct identity, plasmid vs IVT mRNA, poly(A), cap chemistry, authoritative CDS).

No process from this stretch is still running; no partial run was left behind.

---

## 7. Exact safe continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
S=/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad

.venv/bin/python -m pytest -q                               # expect 1,166 passed
.venv/bin/python -m pytest -q tests/test_stage2_gate_v16.py  # expect 13 passed

# Reproduce the screen and the refit (each writes a NEW timestamped run):
.venv/bin/python scripts/run_in_cell_feature_screen.py --archive "$S/acq_persist/MOESM4.zip" \
    --jobs 24 --split stratified --seed 1729
.venv/bin/python scripts/run_feature_refit.py --archive "$S/acq_persist/MOESM4.zip"
```

Re-fetch the source archive if the scratchpad is gone:

```bash
curl -L -o MOESM4.zip "https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-022-28776-w/MediaObjects/41467_2022_28776_MOESM4_ESM.zip"
sha256sum MOESM4.zip   # must be 849ed7b49198c5b97049fec8d3636deea8812db4dd45ce0bcc448297703511c2
```

### Publishing

```bash
PUB=$S/pub2
git -C "$PUB" fetch origin && git -C "$PUB" status --short
git -C "$PUB" rev-list --left-right --count origin/main...HEAD   # expect 0 0 when in sync
sha256sum "$PUB/diagram_10182026.png"   # must stay baa831ce16df27ed…
```

The clone needs `git config user.name zyliu-OU` and
`git config user.email liuzongyuan1993@gmail.com` if it is ever recreated; it had no local
identity this stretch and the first commit failed until both were set.

**If `pub2` is gone**, do not publish from `/home/zyliu/Documents/rna-stable-ai`: that
directory has **no commits** and its `origin` is the placeholder
`https://github.com/YOUR_USERNAME/RNA-StableAI.git`. Clone the real remote into the session
scratchpad, copy the changed files in, and commit there.

---

## 8. Published state

| Item | Value |
|---|---|
| Commit before this stretch | `58fc810` Record the publication commit hash in handoff 2026-10-21 V1 |
| Commits published with this handoff | `399a9ed` (configs, test, README, this handoff), then the commit recording its hash |
| README picture | `diagram_10182026.png`, sha256 `baa831ce16df27ed44a41c2a3b481455a213b328122227b9b2a3820dda47cff1`, **byte-unchanged**; `workflow_10202026.svg` unchanged; both still referenced |
| Gates | v5–v15 frozen; **v16 current** (written this stretch) |
| Assay definition | v1–v3 frozen; **v4 current**; code and tests still pin v3 by name |
| Diagram | **not regenerated.** It is now stale in one respect: its gated box shows a single transfected-cell target and does not show the reinstated cell-free arm. Nothing was added to the production path, so the implementation state it depicts is still accurate. |
| Tests | 1,166 passed |

### 8.1 Diagram staleness, recorded rather than fixed

The 2026-10-19 precedent (handoff V11 §34) was that a published diagram whose gated box named
the wrong Stage 3 target counted as a **stale published artifact needing correction**. The same
is now true of `workflow_10202026.svg`: it does not show the cell-free arm. It was not
regenerated this stretch because the production path did not change and regenerating it was not
requested. **This is the one known stale published artifact.**
