# RNA-StableAI — Handoff 2026-10-20 V10

- **Project:** RNA-StableAI
- **Date:** 2026-10-20 (America/Los_Angeles; run timestamps are UTC and read 2026-10-21)
- **Version:** V10 — supersedes V9 for this date; V1–V9 remain and are not edited
- **Absolute workspace path:** `/home/zyliu/Documents/rna-stable-ai`
- **Remote:** `https://github.com/zyliu-OU/rna-stable-ai.git` — **PUBLIC**
- **Publication clone:** `/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad/pub2`
- **Project interpreter:** `.venv/bin/python` (3.12). Bare `python3` is anaconda 3.14 without biopython.

---

## 1. What this stretch was

> "sure, do 1, then do 2 and 3, see whether it will improve test results"

Three steps, from the V9 plan: (1) run the free-baseline panel, (2) install EternaFold,
(3) refit on EternaFold features. The goal was a concrete improvement to the in-solution
stability objective.

**Result: no improvement, and the step that was supposed to motivate the work turned out to
be my own measurement error.** Step 1 killed the hypothesis, step 2 was skipped as pointless,
and step 3 showed refitting makes the objective strictly worse. Gate v15 **withdraws a
prohibition from v14** — the first withdrawal in the gate chain — because that prohibition was
derived from the defective number.

---

## 2. The correction, first, because it changes a published claim

### 2.1 What V9 and gate v14 claimed

Both recorded, as **the most adverse finding in any gate version**, that a free
per-nucleotide EternaFold score reaches **+0.4190** on in-solution half-life against the frozen
calibration's **+0.3200** — i.e. the calibration is beaten on its own home axis by an untrained
baseline. That was published in commit `5bc4bf2`.

### 2.2 Why it is wrong

I computed that score as `SUP EternaFold / RNA length`. In the **PERSIST-seq Supplementary
Data 1** table, `SUP` is summed over a **sub-region**, not the molecule:

- implied region length (`SUP ÷ AUP`): **median 673 nt**, range 243–954
- actual RNA length: **median 1034 nt**, range 504–1588
- the ratio is identical across all three engines, so it is a pure geometric factor
- it matches no simple segment combination exactly (closest: CDS, median off by 52 nt), and
  the paper's field descriptions say only "sum unpaired probability" / "average unpaired
  probability" without naming a region

So dividing by RNA length yields **AUP × (region length ÷ RNA length)** — structure multiplied
by a length-composition ratio. Decomposed on the 122 constructs:

| Component | ρ vs in-solution |
|---|---|
| AUP EternaFold alone (the structure term) | −0.2648 |
| **region fraction alone (the artifact)** | **−0.3850** |
| their product, as reported in v14 | −0.4190 |

**The length ratio, not the structure, was the dominant factor.**

### 2.3 A second wrong inference, from the same cause

Step 1's verdict was that all three engines clustering near 0.42 (DegScore −0.4225, EternaFold
−0.4190, Vienna −0.3947) meant "the feature family is at its ceiling." It meant nothing of the
kind: **all three share the one artifact**, because the region-fraction factor is engine-
independent. The verdict text is preserved as-run in the panel artifact and corrected in the
refit artifact and in gate v15.

### 2.4 Scope — bounded, and the earlier result is explicitly defended

**The error is confined to `two_axis_comparison_v1` and the v14 entry reporting it.**

On the 123-record `Fig_S8a` sheet the columns are labelled `SUP … FULL`, and I verified
`SUP FULL ÷ length == AUP FULL` **exactly on 123 of 123 records**, with both giving the same
ρ to four decimals:

| Engine | SUP/length | AUP FULL |
|---|---|---|
| EternaFold | −0.3248 | −0.3248 |
| Vienna | −0.2829 | −0.2829 |
| DegScore2.1 | −0.2166 | −0.2166 |

So the post-hoc correction recorded in `external_validation_leppek_v1` was **correct** and its
−0.3248 figure stands. Over-correcting would have been as wrong as the original error. No other
artifact or gate entry is affected.

### 2.5 The corrected comparison — and why it is not an exoneration

Against **properly normalised** free structure scores, the frozen calibration **wins**:

| Predictor | ρ vs in-solution |
|---|---|
| **ours, frozen calibration** | **+0.3200** |
| AUP EternaFold | −0.2648 |
| AUP Vienna | −0.2589 |
| AUP DegScore 2.1 | −0.2170 |

**But the adverse conclusion survives, with a different baseline.** `GC content (CDS)` is a
single free column with no normalisation ambiguity:

| Predictor | in-solution | in-cell |
|---|---|---|
| **GC content (CDS)** | **+0.3651** | +0.0771 |
| ours, frozen calibration | +0.3200 | **+0.2208** |
| transcript GC (whole molecule) | +0.2979 | +0.2253 |

A free single column still beats the fitted calibration on its home axis. **The identity of the
baseline changed; the conclusion about the calibration did not.** And it is axis-specific:
GC (CDS) collapses to +0.0771 on in-cell where the frozen arm reaches +0.2208 — consistent with
the two axes ranking at +0.0545.

---

## 3. The three steps as run

Protocol `configs/folding_engine_swap_v1_2026-10-20.json`,
sha256 `ad804b82…` is the two-axis protocol; this one's hash is recorded in both run artifacts.
Decision rule, success criterion **and** the conclusion to record on failure were all declared
before any number was seen.

### 3.1 Step 1 — free baseline panel

`scripts/run_free_baseline_panel.py` → `results/free_baseline_panel_runs/20261021T052432.989885Z/`.
Nothing fitted, nothing installed. Ten columns the paper already provides, scored on the same
122 constructs the two-axis run defined.

| column | form | in-solution | in-cell | vs length |
|---|---|---|---|---|
| SUP DegScore2.1 | per nt | −0.4225 | +0.1586 | −0.4194 |
| SUP EternaFold | per nt | −0.4190 | +0.1313 | −0.4247 |
| SUP Vienna | per nt | −0.3947 | +0.1552 | −0.4125 |
| **GC content (CDS)** | as given | **+0.3651** | +0.0771 | −0.2620 |
| AUP EternaFold | as given | −0.2648 | +0.0350 | +0.0498 |
| AUP Vienna | as given | −0.2589 | +0.1161 | −0.0261 |
| AUP DegScore 2.1 | as given | −0.2170 | −0.0208 | −0.0179 |
| dG(MFE) EternaFold | as given | −0.1563 | −0.0209 | −0.5606 |
| CAI | as given | +0.0539 | +0.0045 | +0.1981 |
| dG(MFE) Vienna | as given | +0.0362 | +0.1072 | **−0.9447** |

Two things visible here that matter: the "per nt" rows all carry a strong **negative** length
coupling (≈ −0.42) that the AUP rows do not (≈ −0.02), which is the artifact; and
`dG(MFE) Vienna` is almost a pure length ruler (−0.9447).

**Verdict: the engine-swap hypothesis is dead.** Once properly normalised the engines agree
within 0.05.

### 3.2 Step 2 — skipped, with reason

Installing EternaFold and reproducing its column locally was **not done**. Step 1 showed the
engines agree and the apparent EternaFold advantage was an artifact, so there is no engine
advantage to capture. Spending the integration effort would have been work on a dead
hypothesis. Recorded in the refit artifact under `step_2_skipped` and in gate v15.

### 3.3 Step 3 — refit, and it actively hurts

`scripts/run_feature_refit.py` → `results/feature_refit_runs/20261021T052825.459523Z/`.
OLS (same estimator as `stability_ablation_v1`, since the frozen PLS was fitted in R), on the
**same 69 training records** as the frozen arm, tested on the **122** held-out constructs.
**No in-cell label and no held-out label touched a coefficient.**

| arm | features | **train** | **test in-solution** | test in-cell |
|---|---|---|---|---|
| `gc_cds_only` | 1 | +0.3617 | **+0.3651** | +0.0771 |
| `gc_cds_plus_structure_plus_energy` | 3 | +0.5443 | +0.3062 | −0.0321 |
| `gc_cds_plus_structure` | 2 | +0.5353 | +0.2956 | −0.0224 |
| `frozen_form_from_table` | 3 | +0.5818 | +0.1286 | +0.1197 |
| `all_free_columns` | 7 | **+0.6454** | **−0.0022** | −0.1275 |
| *frozen ViennaRNA arm (reference)* | 3 | — | +0.3200 | +0.2208 |

**Train rises monotonically with feature count (+0.3617 → +0.6454) while held-out falls
(+0.3651 → −0.0022).** The seven-feature arm has no out-of-sample signal at all. With 69
training records this feature family supports **about one feature**.

**Best arm is `gc_cds_only` — which is just the single free column, unfitted.** It beats the
frozen arm (+0.3651 vs +0.3200) but does not beat itself, so by the declared criterion
(*"must beat BOTH the frozen arm and the best free single column; beating only the frozen arm
is not success"*) the result is **`success: false`**.

**Criterion amendment, recorded not applied silently:** the protocol named the free EternaFold
score at +0.4190 as the bar. That score is defective, so the bar was restated as the best
*valid* free single column, GC (CDS) at +0.3651. **This lowers the bar**, and it is stated
explicitly for that reason. The refit fails even against the lowered bar.

### 3.4 The conclusion the protocol declared in advance for exactly this outcome

> "if the refit arm does not beat the free structure score, the conclusion to record is that
> the fitted layer adds no value over a single free structure feature on this axis, and the
> objective should be **reduced** to that feature rather than defended."

That is the outcome, and that is the conclusion.

---

## 4. Gate v15

Supersedes v14 at sha256 `27dd7af27867cb6967425b94b282f5d461b47a5690669c42338fb115227f3e34`,
retained frozen and unedited. **No switch moves. No requirement reopened or re-ratified.**
Stage 2 stays closed at 6/6 on the v5 basis.
File: `configs/stage2_to_stage3_gate_v15_2026-10-20.json`,
sha256 `eb0b06808093f1c9c89efb374c2c261660f695c02f1eb153ce88c82a3cd755fa`.

Prohibitions **28 → 31**: **one withdrawn**, four added.

**Withdrawn** (the first withdrawal in the chain): *"Do not claim the frozen stability
calibration beats free folding…"* — derived from the defective baseline, therefore factually
wrong. `prohibition_withdrawn_here` records the exact text, the reason, and the rule that a
prohibition is withdrawn **only when shown false**.

**Added:**
- Do not claim the calibration **loses** to free folding — against properly normalised scores it
  wins (+0.3200 vs −0.2648).
- Do not claim it is the **best** in-solution predictor either — GC (CDS) reaches +0.3651.
- Do not claim refitting on more/better features improves this objective — every multi-feature
  refit overfits.
- Do not claim a folding-engine swap is an available improvement.

v15 also records `what_this_does_not_authorize`: reducing the objective to a single free column
is **indicated, not taken**, because it interacts with the unresolved axis question.

---

## 5. Verification actually run

| Check | Command | Outcome |
|---|---|---|
| New tests | `pytest -q tests/test_folding_engine_swap.py tests/test_stage2_gate_v15.py` | **23 passed** |
| Full suite | `.venv/bin/python -m pytest -q` | **1,153 passed, 0 skipped**, 1 known Ninja warning |
| Archive + table hashes | enforced in both scripts before any row is read | match |
| Train/test split | enforced | exactly 69 / 122 |
| SUP==AUP check, 123 records | computed directly | **123/123 exact**, both −0.3248 |
| Region identification, 122 records | tested against 6 candidate regions | **no exact match**; closest CDS, median off 52 nt |
| README picture | `sha256sum` in the clone | `baa831ce…` **byte-unchanged** |

Suite 1,130 → **1,153** (+23).

**Not run, not claimed:** EternaFold was not installed; no construct was measured; RiboNN was
not run; `ruff` was not run this stretch.

---

## 6. Scientific interpretation

The stability objective is now, on the evidence, **not worth defending in its current form on
the in-solution axis**.

Three independent attempts to improve it have each failed in a different way. Gate v12 found it
collapses to GC on the synthetic pool (+0.99). Gate v14 found the collapse reproduces on real
measured constructs (+0.78). This stretch found that the one apparent route to improvement —
a better folding engine — does not exist, and that refitting on any larger feature set makes
held-out performance **worse**, monotonically, to the point of zero signal at seven features.
Meanwhile a single free column nobody fitted, `GC content (CDS)`, outranks the fitted
three-feature model.

The honest reading is that in-solution half-life on these constructs is **largely a
base-composition phenomenon**, that ~69 labelled records is far too few to fit anything beyond
one feature, and that the project's fitted layer is an elaborate way of approximating GC
content. That is not a tuning problem.

**What this does not say.** It says nothing about the in-cell axis, where the ordering is
different and more interesting: the frozen arm reaches +0.2208 while GC (CDS) manages +0.0771.
Whatever the frozen arm is doing on in-cell, it is **not** reproduced by CDS composition. That
is the one place in this stretch where the fitted model holds an advantage over every free
baseline tested, and it is on the axis the project has **not** been optimising.

**A note on process.** The error corrected here was mine, it was published, and it was found by
running the cheap diagnostic the user asked for rather than by accepting the favourable framing
it created. It is worth recording that the defective number was **adverse** to this project —
it made the objective look worse than it is — which is precisely why it went unchallenged for a
stretch. Adverse findings need the same verification as favourable ones.

**Limitations.** 122 constructs, one paper, one assay pair, mostly UTR variants, no Nluc coding
variants. The refit used the paper's precomputed columns, not locally recomputed features.
`GC content (CDS)` is a column I did not verify by recomputation. The region underlying `SUP`
remains unidentified; it is known only to be ~673 nt median and not any simple segment sum.

**Rejected this stretch.** Installing EternaFold (dead hypothesis). Silently restating the
success criterion when its bar turned out defective. Regenerating the step-1 panel artifact to
erase its wrong verdict — the as-run record is kept and corrected elsewhere instead. Editing
v14 in place.

---

## 7. Outstanding, prioritized

1. **The axis decision, unchanged and now more urgent.** It gates everything. Note the new
   asymmetry: on in-solution the objective should arguably be reduced to one free column; on
   in-cell the fitted arm is the only thing that beats the free baselines.
2. **If in-solution is the target: reduce the objective** to `GC content (CDS)` (or verify it by
   recomputation first) rather than maintain a three-feature calibration that underperforms it.
   This is indicated by v15 and not taken.
3. **If in-cell is the target: the 203 in-cell records in the same table are the basis**, and
   nothing has been fitted to them. Note 69/122 of the in-solution split does not apply there.
4. **More labels are the binding constraint, not more features.** The overfitting curve says
   69 records supports one feature. `Fig_3b` (2,165 rows) and `Fig_S7a` (2,037 rows) are the only
   large label sets available, and both are 107-nt ORF-less fragments — usable for a
   fragment-scale model only.
5. Tier-1 items from V8 remain unimplemented: m1Ψ-aware modelling, position-preserving pooling,
   calibrated uncertainty.
6. RiboNN vs Sample-2019 MRL (not comparable against mRNAutilus's translation head, which shares
   RiboNN's training source). Region-local features. ninja/C++ for fused qLogEHVI. V12 §6 item 7.

**Still blocked on others:** assay CVs; false-accept/false-reject cost; whether Fluc-PEST enters
the panel; panel capacity; the two questions for Ping.

---

## 8. Exact safe continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
S=/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad

.venv/bin/python -m pytest -q                      # expect 1,153 passed
.venv/bin/python -m pytest -q tests/test_folding_engine_swap.py tests/test_stage2_gate_v15.py

# Step 1 and step 3 both re-runnable; each writes a NEW timestamped run and verifies hashes
.venv/bin/python scripts/run_free_baseline_panel.py --archive "$S/acq_persist/MOESM4.zip"
.venv/bin/python scripts/run_feature_refit.py       --archive "$S/acq_persist/MOESM4.zip"
```

Re-fetching the source archive if the scratchpad is gone:

```bash
curl -L -o MOESM4.zip "https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-022-28776-w/MediaObjects/41467_2022_28776_MOESM4_ESM.zip"
sha256sum MOESM4.zip   # must be 849ed7b49198c5b97049fec8d3636deea8812db4dd45ce0bcc448297703511c2
```

Both scripts depend on the newest `results/two_axis_comparison_runs/*/summary.json` to define
the 122-construct test set, so re-run that first if the test set must change.

### Publishing

```bash
PUB=$S/pub2
git -C "$PUB" fetch origin && git -C "$PUB" status --short
sha256sum "$PUB/diagram_10182026.png"   # must stay baa831ce16df27ed…
```

---

## 9. Published state

| Item | Value |
|---|---|
| Commit before this stretch | `e0303d7` Record the two-axis comparison commit hash in handoff 2026-10-20 V9 |
| Commits published with this handoff | see §9.1 |
| README picture | `diagram_10182026.png`, sha256 `baa831ce16df27ed44a41c2a3b481455a213b328122227b9b2a3820dda47cff1`, **byte-unchanged**; `workflow_10202026.svg` unchanged |
| Gates | v5–v14 frozen; **v15 current**. Opens no switch, reopens no requirement, withdraws one prohibition as false. |
| Diagram | **not regenerated.** Nothing was added to the production path. |

### 9.1 Publication record

Recorded by the commit immediately after, per the established pattern.
