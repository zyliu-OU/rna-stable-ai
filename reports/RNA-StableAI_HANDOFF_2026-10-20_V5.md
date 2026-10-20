# RNA-StableAI — Handoff 2026-10-20 V5

- **Project:** RNA-StableAI
- **Date:** 2026-10-20 (America/Los_Angeles)
- **Version:** V5 (follows [V1](RNA-StableAI_HANDOFF_2026-10-20_V1.md) the gate review,
  [V2](RNA-StableAI_HANDOFF_2026-10-20_V2.md) BoTorch and the Pareto formulation,
  [V3](RNA-StableAI_HANDOFF_2026-10-20_V3.md) the design space, and
  [V4](RNA-StableAI_HANDOFF_2026-10-20_V4.md) the end-to-end workflow; all stand unedited)
- **Workspace:** `/home/zyliu/Documents/rna-stable-ai`
- **Publication clone:** `/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad/verify`
- **Remote:** `https://github.com/zyliu-OU/rna-stable-ai.git` — **PUBLIC**
- **Headline:** the whole-ORF window was run. **The two-point extrapolation held**: predicted
  7.82% of the calibration's training range, measured **8.39%**, ratio 1.07×. A clean
  sub-linear power law fits all three widths (exponent 0.42, R² 0.9995) across an 18-fold
  range. **Window width is exhausted as a lever**, and this was its ceiling.

---

## 1. User instruction in this stretch

| Instruction | Reading | Consequence |
|---|---|---|
| "yes, run the whole ORF window" | Replace the two-point extrapolation with a measurement. | `configs/whole_orf_window_diagnostic_v1_2026-10-20.json`, a third 512-member run, the scaling fit, and 19 tests. |

**What this run is, and is not.** It is a **diagnostic probe of a scaling relationship**. It
is **not** a campaign design space and it **supersedes nothing**: design-space v2 remains the
campaign domain, recorded in the diagnostic config with v2's hash
`d77a8482b583eb63…`. Editing 90.9% of the transcript destroys the regional attribution a
window existed to provide, so nothing should be designed in this space.

---

## 2. The diagnostic design space

`configs/whole_orf_window_diagnostic_v1_2026-10-20.json`.

| | value |
|---|---|
| window | **549 codons = 1,647 nt = 90.9%** of the 1,811 nt transcript |
| positions | every codon except the start and the terminator |
| GC-neutral substitutable positions | **291** (24 at 50 codons, 13 at 30) |
| GC-neutral space | ~10^92.5 |
| free space | ~10^272.7 |

This is **the ceiling of the window axis**: every codon the constraints permit. There is no
wider case to try for this construct.

**Both outcomes were written down before the run.** `prediction_being_tested` recorded
0.078 with the basis and the caveat that a two-point fit does not establish an exponent;
`what_a_confirmation_would_mean` and `what_a_refutation_would_mean` were both stated, ending
*"Either outcome is reported."*

---

## 3. The run

`results/design_workflow_runs/20261020T190152.300973Z/`

| | value |
|---|---|
| members | 512, GC-neutral, seed 1729 |
| folds | **512/512 ok**, mean 35.95 s |
| stability | 512 predicted, **512 extrapolating on GC** |
| half-life | 1.2912 – 1.4012 h |
| TE | 0.7462 – 0.9740 |
| Pareto front | **5 of 512** |
| panel | `[505, 66, 95, 273, 427]` (placeholder size 12, capped by the front) |
| RiboNN run | `results/ribonn_fixed_inference_runs/20261020T191453.027049Z` |
| BO replay | budget 32: hv 0.019256 vs random 0.017755; front found **1 of 5** vs random **0** |

---

## 4. The scaling result

`scripts/fit_window_width_scaling.py` →
`results/window_scaling_runs/20261020T192957.720587Z/summary.json`, tested by
`tests/test_window_scaling.py` (19 tests).

| window | nt | % of transcript | subst. positions | half-life stdev | range as % of training | TE stdev | front |
|---|---|---|---|---|---|---|---|
| 30 codons | 90 | 5.0% | 13 | 0.00582 | **2.62%** | 0.01206 | 10 |
| 50 codons | 150 | 8.3% | 24 | 0.00702 | **3.18%** | 0.01137 | 6 |
| 549 codons | 1,647 | 90.9% | 291 | 0.01964 | **8.39%** | 0.03279 | 5 |

### 4.1 The held-out test

The fit was made from the **30 and 50 codon runs only**, so the third run could refute it. A
test pins that the predicted width is not among the fitted widths.

| | value |
|---|---|
| fitted on | 90 and 150 nt |
| exponent used | 0.376 |
| **predicted** at 1,647 nt | **7.82%** of the training range |
| **measured** | **8.39%** |
| measured / predicted | **1.07×** |

**The extrapolation held.** A fit from two points 60 nt apart predicted, to within 7%, the
spread at a window eleven times wider.

### 4.2 Refit across all three widths

| quantity | exponent | R² |
|---|---|---|
| half-life stdev | **0.422** | 0.9995 |
| half-life range as fraction of training range | 0.402 | 0.9999 |
| TE stdev | 0.375 | 0.9546 |

A clean sub-linear power law over an 18-fold range of window widths. R² values that high on
three points are not strong evidence of a law, but they do mean no point is an outlier.

---

## 5. Scientific interpretation

**Window width is exhausted.** At the ceiling — 90.9% of the transcript, 291 substitutable
positions, 10^92.5 variants available — the predicted in-solution half-life spans **8.39%**
of the calibration's training target range. Going from 5.0% to 90.9% of the transcript, an
18× increase in edited sequence, bought **3.37×** the spread. There is no wider window, so
this axis is finished.

**The limit is the features, not the design space.** Every calibration feature is a
transcript-wide mean, and a mean is insensitive to synonymous rewriting by construction: the
protein is fixed, so the amino-acid composition is fixed, and synonymous codon choice moves
whole-transcript GC, ensemble energy per nucleotide and mean unpaired probability only at
the margin. This is now measured rather than argued.

**A correction to V4 and to what I told the user.** V4 reported that *"the translation side
did not respond at all"*, on the 30→50 comparison where TE stdev fell 0.94×. With three
points that is wrong: TE stdev is **2.72× larger** at the whole-ORF width, scaling with
exponent 0.375, essentially the same as the stability side. The 30→50 step was simply too
small to show it, and the dip at 50 codons was noise on a non-monotone pair. **Two points
misled me about the translation side; they happened to be right about the stability side.**
A test now pins the non-monotonicity so the earlier reading cannot quietly return.

**The BO replay degraded at this width** — 1 of 5 front members found, against 0 for random.
The front shrank from 10 to 5 members as the window widened, so the target is a smaller
fraction of the pool and 32 draws of 512 is a harder search. It is still better than random,
but this is the weakest of the three replays and should not be reported as a success.

**What this does not say.** Nothing here is a measurement of a molecule. The spread is a
spread of predictions from an unvalidated model, so the scaling law describes the model's
sensitivity to sequence, not biology. A model that is insensitive to synonymous rewriting may
be insensitive because the biology is, or because the features are too coarse to see it.
**These runs cannot distinguish those two cases**, and that distinction is exactly what an
experiment would settle.

---

## 6. What follows from this

The window axis is closed, so the open options are:

1. **Region-local features.** Replace transcript-mean `aup` with unpaired probability over
   the edited window, and transcript GC with window GC. This changes what the objective can
   see. **Cost:** `strand_rnafold_calibration_v1` was fitted on transcript-wide features, so
   it would no longer apply as fitted — a more sensitive objective in exchange for a
   calibrated one. That trade is the decision, and it has not been made.
2. **Accept the flat landscape** and treat the pipeline as a ranking device whose
   differences are small, documenting that any selected panel differs from the reference by
   under a tenth of the calibration's training range.
3. **Get a measurement** and find out whether the flatness is the model's or the biology's.
   This is the only option that resolves the ambiguity in §5.

My recommendation is 3 before 1. Reworking the features to make the objective more sensitive,
with no measurement to say whether the extra sensitivity is real, risks building a more
confident pipeline on the same unverified ground.

---

## 7. Verification actually run

| Check | Outcome |
|---|---|
| `run_design_workflow.py --spec whole_orf_window_diagnostic_v1 --size 512 --jobs 24` | exit 0; 512/512 folds |
| `fit_window_width_scaling.py` with three runs | exit 0; held-out prediction 7.82% vs measured 8.39% |
| `pytest tests/test_window_scaling.py` | 19 passed |
| `ruff check` on the two files written here | All checks passed |
| **Full suite** | **1486 passed, 38 skipped** in 134.88 s |

Suite arithmetic: 1467 (V4) -> 1486 with the 19 tests added here. The 38 skips are
unchanged retired-checkpoint replays.

### Not verified / not claimed

- **No molecule in this project has been measured.**
- A power law over three points is a **description of three points**.
- R² of 0.9995 on three points is not evidence of a law; it means no point is an outlier.
- The 512-member sample is a **vanishing fraction** of a 10^92.5 space and characterises the
  sample, not the space. The sampler draws edit counts uniformly, so the sample spans the
  edit-distance axis by construction, but no claim is made about the space's extremes.
- The whole-ORF run's panel is an **illustration**; nothing is recommended for synthesis.

---

## 8. Known limitations carried and added

Carried from V4 §8 unchanged: the constant coordinates in the design feature representation
(now 549 coordinates of which 291 can be non-zero); GC extrapolation on every member of
every run; RiboNN run directories not published; early smoke runs retained locally and not
published; the BO replay's oracle being the pipeline's own predictions.

Added here:

1. **The whole-ORF run has no regional attribution.** 90.9% of the transcript varies per
   member, so no result from it can be attributed to any part of the sequence. That is
   inherent and is why the config refuses to be a design space.
2. **The three widths differ in the number of substitutable positions as well as width**
   (13, 24, 291). The two covary by construction — opening more window opens more positions
   — so the fit cannot separate "more sequence" from "more editable positions". Neither can
   any experiment that varies a window, which is why it is recorded rather than controlled.

---

## 9. Open decisions, in priority order

1. **Region-local features, accept the flat landscape, or get a measurement first.** See §6.
   My recommendation is a measurement first.
2. **Free vs GC-neutral**, still formally undecided; all three runs used neutral.
3. **The assay panel size**, still unknown, and still the real bound on everything.
4. Carried forward: assay CVs and decision costs; whether Fluc-PEST enters the panel; the
   power convention; the span policy and the unspent blinded set; the two questions for
   Ping; experimental-structure references in scope; the C++ toolchain for the fused
   qLogEHVI kernel; V12 §6 item 7.

**No process is running.** Every run completed with exit 0 and wrote a complete artifact.

---

## 10. Exact safe continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai

# Full suite (expect 1486 passed, 38 skipped)
.venv/bin/python -m pytest -q

# Just this stretch
.venv/bin/python -m pytest -q tests/test_window_scaling.py

# Re-run the scaling fit without writing (seconds)
.venv/bin/python scripts/fit_window_width_scaling.py \
  --run results/design_workflow_runs/20261020T174606.887363Z \
  --run results/design_workflow_runs/20261020T181317.731918Z \
  --run results/design_workflow_runs/20261020T190152.300973Z \
  --dry-run

# The two-width comparison, still valid
.venv/bin/python scripts/compare_window_width_spreads.py \
  --narrow results/design_workflow_runs/20261020T174606.887363Z \
  --wide   results/design_workflow_runs/20261020T181317.731918Z \
  --dry-run

# A fourth width, if one is ever wanted (about 45 minutes)
.venv/bin/python scripts/run_design_workflow.py \
  --spec configs/whole_orf_window_diagnostic_v1_2026-10-20.json \
  --size 512 --jobs 24 --panel 12 --bo-budget 32

# Quick mechanics check (about a minute)
.venv/bin/python scripts/run_design_workflow.py --size 8 --jobs 8 --panel 3 --bo-budget 5

# Lint only the files written here; the repository has 2,882 pre-existing ruff errors
ruff check scripts/fit_window_width_scaling.py tests/test_window_scaling.py
```

`fit_window_width_scaling.py` refuses fewer than three widths, and refuses runs that differ
in GC mode, pool size or seed, so a confounded comparison cannot be produced by accident.

### Publishing

```bash
PUB=/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad/verify
git -C "$PUB" fetch origin && git -C "$PUB" status --short
sha256sum "$PUB/diagram_10182026.png"   # must stay baa831ce16df27ed…
diff "$PUB/README.md" README.md          # merge upstream edits before copying
```

The local repository has **no commits**; `origin` is the placeholder
`https://github.com/YOUR_USERNAME/RNA-StableAI.git`. Publication goes through the clone
above, with `git -c user.name=zyliu-OU -c user.email=<the user's address> commit`.

---

## 11. Published state

| Item | Value |
|---|---|
| Commit before this stretch | `716558e` Record the design-workflow commit hash in handoff 2026-10-20 V4 |
| Commit published with this handoff | `2263a91` |
| README picture | `diagram_10182026.png`, `sha256 baa831ce16df27ed44a41c2a3b481455a213b328122227b9b2a3820dda47cff1`, **byte-unchanged**, re-verified before publishing |
| Gates | v5 frozen; **v6 current** |
| Design spaces | v1 and v2 frozen; **v2 remains the campaign domain**; the whole-ORF config is a parallel diagnostic and supersedes nothing |

### 11.1 Publication record

`2263a91` — Run the whole-ORF window and close the window-width axis. The hash is recorded
by the commit immediately after it, since a file cannot contain the hash of the commit that
adds it.
