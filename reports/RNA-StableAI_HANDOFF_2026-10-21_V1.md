# RNA-StableAI — Handoff 2026-10-21 V1

- **Project:** RNA-StableAI
- **Date:** 2026-10-21 (America/Los_Angeles)
- **Version:** V1 — first handoff of this date; supersedes 2026-10-20 V11 only where stated
  below. V11 and all earlier handoffs remain and are not edited.
- **Absolute workspace path:** `/home/zyliu/Documents/rna-stable-ai`
- **Remote:** `https://github.com/zyliu-OU/rna-stable-ai.git` — **PUBLIC**
- **Publication clone:** `/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad/pub2`
  (survived from the V8–V11 session; it was in sync with `origin/main` and clean at the start
  of this stretch, so no upstream README edits had to be merged)
- **Project interpreter:** `.venv/bin/python` (3.12). Bare `python3` is anaconda 3.14 without
  biopython and must not be used for this project.

---

## 1. What this stretch was

The user's request, in full: *"since our development plan changed, could you update on github
based on lastest handoff and development progress?"*

This was a **publication stretch, not an experimental one**. No experiment was run, no
protocol was declared, no model was fitted, and no number in this project changed. The work
was to bring the public-facing record into line with decisions and measurements that already
existed in the handoffs but had never reached the README.

### 1.1 The gap that was found

The published README's last content update was commit `855345e`. Three publication stretches
had landed since then — `5bc4bf2` (two-axis comparison), `0dabc3c` (the baseline correction)
and `b1cccb9` (EternaFold retirement plus the in-cell feature screen) — and **all three
published their findings into `reports/`, `configs/` and `results/` only**. The README
therefore still told a reader that:

1. the Stage 3 target was **transfected-cell expression**, amended 2026-10-19; and
2. the free per-nucleotide EternaFold baseline on in-solution half-life was **+0.4190**, the
   figure `0dabc3c` had already established was a measurement error.

The second of those is the serious one: a wrong number was standing in the most-read file in
the repository, on the project's own home axis, having already been corrected elsewhere.

### 1.2 State of the workspace at the start

`find` over `src scripts tests configs docs reports README.md DEVELOPMENT.md AGENTS.md
RESEARCH_USE_NOTICE.md pyproject.toml` newer than the `b1cccb9` commit time
(2026-10-20 23:02:23 −0700) returned **zero files**, and `results/` likewise. So there was no
unpublished development progress to publish — the code, protocols and run artifacts on GitHub
were already current. The entire gap was documentation.

---

## 2. User decisions this stretch rests on

These are carried forward from V11 §1 unchanged; none of them was re-opened or re-litigated
here, and they supersede any earlier statement of the same thing:

1. **The target axis is IN-CELL mRNA STABILITY (half-life / decay).** Not in-cell expression.
2. **The EternaFold refit direction is retired** — the user's words were "we dont do that".
3. **The architecture is unchanged:** RNAfold + STRAND + RiboNN + BoTorch.
4. The "in-cell" results are **stability**, not expression. The source table keeps
   `Ribosome load` as a separate measurement and `Predicted expression` as a derived value;
   neither was ever the target.

---

## 3. What was changed — the only edited file

**`README.md`** (workspace copy and publication copy, byte-identical; they were already
byte-identical before the edit, so no path-rewrite step was needed).

### 3.1 Development-plan statements corrected

| Location | Before | After |
|---|---|---|
| Plan header date | "Updated October 18, 2026" | "Updated October 21, 2026", plus a new paragraph stating the target is in-cell mRNA stability, that it supersedes the 2026-10-19 expression amendment and **every earlier statement of the Stage 3 target in the file**, and that translation stays a separate incommensurable axis |
| Step 3 table row | "RNA sequence optimization for stability and protein expression … **transfected-cell expression** … measured protein output and time-matched RNA abundance" | "RNA sequence optimization for in-cell mRNA stability … **in-cell mRNA stability (half-life / decay)** … time-matched RNA abundance as the measured outcome. Translation stays a separate Pareto axis. No stability or expression benefit is verified." |
| Architecture note | "The Stage 3 target was amended on 2026-10-19 to **transfected-cell expression**" | records both amendments in order — 2026-10-19 to expression, 2026-10-20 to in-cell mRNA stability — and states the architecture is unchanged by the amendment |
| `### Step 3 goal and plan` | heading "protein expression efficiency"; objective "measured protein expression efficiency"; step 1 "target expression system" | heading "in-cell mRNA stability"; objective "measured in-cell mRNA stability — half-life and decay"; step 1 "target cell system" |

The four numbered steps of the Step 3 plan were **deliberately not rewritten**. They were
written for the expression target, and an italic note now says so explicitly, keeping them for
their process content — prespecification, held-out evaluation, separated outcomes — with
protein output demoted to a secondary observation rather than the objective. Rewriting them to
fit the new target would have invented a plan the user has not reviewed.

### 3.2 One new dated section added

`### 2026-10-21: the target axis is fixed as in-cell stability, a published number is
corrected, and translation is measured to be unusable as a stability feature`, inserted as the
newest entry, immediately above the 2026-10-20 design-domain section. It carries four parts,
all sourced from V9–V11 and from the run artifacts, with **no number computed in this
stretch**:

1. **The correction.** States plainly that `5bc4bf2` published +0.4190 and that the figure was
   `SUP ÷ RNA length` where `SUP` sums over an unnamed sub-region (implied median 673 nt
   against an actual median 1,034 nt), i.e. AUP × a length ratio. Carries the decomposition
   table (structure term −0.2648, region fraction −0.3850, product −0.4190), notes the ratio
   is engine-independent so the "feature family is at its ceiling" reading also falls, and
   **explicitly defends the separate −0.3248 external-validation figure** as unaffected
   (`SUP FULL ÷ length == AUP FULL` verified on 123 of 123 records). Then carries the
   corrected comparison — GC (CDS) +0.3651 in-solution / +0.0771 in-cell, frozen calibration
   +0.3200 / +0.2208, transcript GC +0.2979 / +0.2253 — and states that **the adverse
   conclusion survives with a different baseline**, which is the load-bearing point.
2. **The retirement**, with the overfitting measurement that justifies it: train
   +0.3617 → +0.5972 against held-out +0.3651 → +0.1317, and the three surviving arms named.
3. **The in-cell screen**, with the bar (+0.2253), the reason the first split could not answer
   the question (78 of 81 training records are CDS variants; `utr5_gc` has 2 training values
   against 46 held out; zero of 24 cleared), the stratified split recorded as a protocol
   amendment, **the non-comparability warning**, the five-feature held-out table, the collapse
   to two orthogonal signals, and three limits stated with the result rather than after it
   (37 features on 105 records so several clear by chance and only held-out counts;
   `cds_length` is a length ruler; `utr5_frac_C` has no mechanism). It states twice that
   nothing is adopted and that resolution is unchanged at 0.500–0.523.
4. **The RiboNN prohibition**, with the per-family sign-reversal table and the collapse to
   −0.1018 train / +0.0879 held out on the balanced split, and the conclusion that this is the
   first *measured* evidence that incommensurable axes were correct rather than cautious.

The section closes with the gate state: **v5–v15 frozen, v15 still current, v16 not written**,
and names the three prohibitions that are consequently recorded in prose but **not yet in the
gate chain**.

### 3.3 What was deliberately not touched

- **Both images and both image references.** `workflow_10202026.svg` in the header and the
  retained `diagram_10182026.png` link are byte-unchanged and still referenced; the
  `grep -c` for both references returns 2 after the edit, and `diagram_10182026.png` still
  hashes `baa831ce16df27ed44a41c2a3b481455a213b328122227b9b2a3820dda47cff1`. The publication
  clone was confirmed in sync with `origin/main` and clean before editing, so the live README
  carried no upstream user edits that needed merging.
- **The diagram was not regenerated.** Nothing was added to the production path this stretch,
  so the 2026-10-20 implementation-state picture and its caption are still accurate.
- **No earlier dated README section was edited or deleted.** The correction is recorded as a
  new, later entry that names the commit it corrects, which keeps the error visible in the
  record instead of erasing it.
- **No handoff, protocol, config, run artifact or test was modified.**

---

## 4. Verification actually run

| Check | Command | Outcome |
|---|---|---|
| Full suite | `.venv/bin/python -m pytest -q` | **1,153 passed**, 1 known Ninja/BoTorch warning, 17.04 s — matches the V11 baseline exactly |
| Publication clone vs remote | `git fetch origin; git rev-list --left-right --count origin/main...HEAD` | `0 0` before the edit; clean working tree |
| Workspace drift since `b1cccb9` | `find … -newermt "2026-10-20 23:02:23"` | zero files, in the published roots and in `results/` |
| README ↔ publication copy | `diff README.md "$PUB/README.md"` | identical before the edit; identical again after the copy |
| Image references preserved | `grep -c -E "workflow_10202026.svg|diagram_10182026.png"` | 2 |
| Picture hash | `sha256sum diagram_10182026.png` | `baa831ce…cff1`, unchanged |
| Image lines in the diff | diff filtered for `.png`/`.svg`/`img` | no matches — no image line was added, removed or reworded |

**Not run, and not claimed:** no experiment, no protocol replay, no re-run of the feature
screen or the refit, no inference, no retraining. Every number published in the new README
section was transcribed from V9–V11 and their run artifacts, not recomputed here. A reader who
wants those numbers re-derived should use the continuation commands in §7.

---

## 5. Scientific interpretation and what must not be claimed

Nothing in this stretch adds scientific evidence. What it changes is **what the public record
says**, and two of those changes are substantive:

- The repository no longer presents a free EternaFold baseline of +0.4190 on in-solution
  half-life. That number was an artifact of a region-length ratio. It is replaced by the
  corrected decomposition **and** by the finding that a free single column — GC (CDS),
  +0.3651 — still beats the fitted calibration's +0.3200 on its home axis. The correction
  is not an exoneration, and the README now says so in those terms.
- The repository no longer presents transfected-cell expression as the Stage 3 target.

**Must not be claimed, in any future update:**

1. That RiboNN or measured ribosome load predicts in-cell stability. It does not: the sign
   reverses by design family (+0.4916 on CDS variants against −0.5551 on 5′UTR variants) and
   the family-balanced ceiling is +0.0879 held out.
2. That any screened feature — `utr5_frac_C`, `cds_energy_per_nt` or any other — is adopted,
   validated, or in the production path. They are screened univariate candidates.
3. That the screen improved the objective's resolving power. It did not; all five candidates
   sit between 0.500 and 0.523 in the 1.00–1.10 bin against chance 0.50.
4. That in-cell and in-solution results are comparable across the two splits. The in-cell
   headline uses the family-stratified 105/98 split; the in-solution results keep the
   122-record set. Any in-cell claim must state its split.
5. That the calibration is independently validated, or that any candidate benefit exists.

---

## 6. Pending work — prioritized, and unchanged from V11 except where noted

1. **Write gate v16.** Still the first task. V11 §5 recorded that the script failed with
   `KeyError: 'split'` because the preserved-split artifact predates the `split` field added
   for the stratified run; the fix is to read `split` with `.get()` or to take the note from
   the stratified artifact only. The intended content is fully specified in V11 §1–3 and is
   now also summarised in the README's 2026-10-21 section, including the three prohibitions in
   §5.1–5.3 above. **This stretch did not write it, by choice** — the gate chain is a frozen
   scientific record and authoring a new link in it is not a documentation task.
2. **Tests for `in_cell_feature_screen_v1`** and its run artifacts. None exist.
3. **The combined two-feature model.** The obvious next experiment, since the two surviving
   signals are only −0.182 apart. It needs its own declared protocol and must respect the
   ~1–2 feature budget measured by gate v15.
4. Discount `cds_length` as a length ruler, or show it is not one.
5. Find a mechanism for `utr5_frac_C`, or state that it stands as an unexplained correlate.

No process from this stretch is still running. No partial run was left behind.

---

## 7. Exact safe continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
# The scratchpad that holds the source archive and the publication clone:
S=/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad

.venv/bin/python -m pytest -q                       # expect 1,153 passed

# Reproduce the headline screen and the refit (each writes a NEW timestamped run):
.venv/bin/python scripts/run_in_cell_feature_screen.py --archive "$S/acq_persist/MOESM4.zip" \
    --jobs 24 --split stratified --seed 1729
.venv/bin/python scripts/run_feature_refit.py --archive "$S/acq_persist/MOESM4.zip"
```

Re-fetch the source archive if the scratchpad is gone:

```bash
curl -L -o MOESM4.zip "https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-022-28776-w/MediaObjects/41467_2022_28776_MOESM4_ESM.zip"
sha256sum MOESM4.zip   # must be 849ed7b49198c5b97049fec8d3636deea8812db4dd45ce0bcc448297703511c2
```

Both the refit and the free-baseline panel depend on the newest
`results/two_axis_comparison_runs/*/summary.json` to define the 122-construct test set, so
re-run that first if the test set must change.

### Publishing

```bash
PUB=$S/pub2
git -C "$PUB" fetch origin && git -C "$PUB" status --short
git -C "$PUB" rev-list --left-right --count origin/main...HEAD   # expect 0 0
sha256sum "$PUB/diagram_10182026.png"   # must stay baa831ce16df27ed…
```

**If `pub2` is gone**, do not publish from `/home/zyliu/Documents/rna-stable-ai`: that
directory has **no commits** and its `origin` is the placeholder
`https://github.com/YOUR_USERNAME/RNA-StableAI.git`. Clone the real remote fresh into the
session scratchpad, copy the changed files in, and commit there.

---

## 8. Published state

| Item | Value |
|---|---|
| Commit before this stretch | `b1cccb9` Retire the EternaFold direction and screen features for in-cell stability |
| Commits published with this handoff | `README_COMMIT` (README + this handoff), then the commit recording its hash |
| README picture | `diagram_10182026.png`, sha256 `baa831ce16df27ed44a41c2a3b481455a213b328122227b9b2a3820dda47cff1`, **byte-unchanged**; `workflow_10202026.svg` unchanged; both still referenced |
| Gates | v5–v15 frozen; **v15 still current — v16 NOT written** (see §6) |
| Diagram | not regenerated; nothing was added to the production path |
| Tests | 1,153 passed |

### 8.1 Note on the hash-recording pattern

V11 was published by `b1cccb9` but **the follow-up commit that records its hash was never
made**, because that session ended early at the user's request. V11 §7 consequently still
reads "recorded by the commit immediately after". That is corrected by this handoff: `b1cccb9`
is named in §8 above as the commit that published V11, so the chain is closed here rather than
by editing V11, which is preserved unedited per project policy.
