# RNA-StableAI — Handoff 2026-10-20 V9

- **Project:** RNA-StableAI
- **Date:** 2026-10-20 (America/Los_Angeles; run timestamps are UTC and read 2026-10-21)
- **Version:** V9 — supersedes V8 for this date; V1–V8 remain and are not edited
- **Absolute workspace path:** `/home/zyliu/Documents/rna-stable-ai`
- **Remote:** `https://github.com/zyliu-OU/rna-stable-ai.git` — **PUBLIC**
- **Publication clone:** `/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad/pub2`
- **Project interpreter:** `.venv/bin/python` (3.12). Bare `python3` is anaconda 3.14 without
  biopython and produces 11 spurious collection errors.

---

## 1. What this stretch was

The user asked for two checks and then the test:

> "do those two checks next — the real overlap count, and a hunt for option-3 datasets,
> then start the test"

Both checks were done, the second one changed the plan, and the test ran. **The test was
designed to be the fair version of the earlier mRNAutilus comparison. It produced this
project's three most adverse recorded findings.** All three are now in gate v14.

---

## 2. The two checks

### 2.1 Overlap check — completed enough to make the decision, then deliberately stopped

Their half-life head's training data, from their paper verbatim (`papers/mRNAutilus_NBT.pdf`,
"Regressor Training"):

> "Paired data was collected from [Agarwal and Kelley, 2022], which sourced
> transcriptome-wide half-life data from human samples across **16 publications and
> deposits**. Overall, this dataset spans nearly **13,000 transcripts across 39 human
> samples**."

**This corrects a shorthand used throughout V8 and the chat:** their head is trained on the
**Saluki paper's dataset**, not on Saluki the model. The in-cell-decay domain claim stands.

**A second thing found in the same paragraph, not previously noticed:** their translation head
is trained on **Zheng et al. 2025**, which is **RiboNN's own paper**. mRNAutilus's translation
head and this project's RiboNN component share a training source, so any translation-side
comparison between the two methods is partly circular. That axis is now explicitly out of
scope and the exclusion is recorded in the protocol and in `no_claim`.

Agarwal & Kelley's human compendium, from the paper's Table 1: cell lines HeLa, K562, HEK293,
HepG2, MCF-7, A549, GM12878, H1-ESC, RPE, LCLs and B cell; methods BRIC-seq, SLAM-seq,
TimeLapse-seq, TT-seq, actinomycin D, 4sU and α-amanitin; **39 human samples** after excluding
the Gejman outlier, **13,921 human genes** after harmonization.

Candidate atlas: **RNAdecayCafe** (Vock, Tang, Giraldez & Simon, bioRxiv 2025.08.19.671151),
Zenodo `16884513`. Downloaded `SampleDetails_v1.1.csv`, `FeatureDetails_genes_v1.1.csv`,
`AvgKdegs_genes_v1.1.csv` (sha256 `f85db0b2…`, `26e89f91…`, `b8869c74…`). Measured from the
files: **17,412 distinct genes, 11 cell lines, 15 datasets, 64 samples**, 122,235
gene×cell-line rows. Source datasets split by date — pre-2022 and plausibly inside Agarwal's
compendium: Schofield 2018, Muhar 2018, Mowery 2018, Zuckerman 2020, Luo 2020, Thiecke 2020,
Narain 2021, Finkel 2021, Sheppard 2021, Harada 2022, Swartzel 2022; **post-2022 and therefore
impossible to be in it**: Ietswaart 2024, Zhou 2024, Mabin 2025, Williams 2025.

**The gene-level intersection was NOT computed, deliberately.** The reason is that computing it
would not have changed the decision: both Agarwal's compendium and RNAdecayCafe are **gene-level
averages** (RNAdecayCafe states it is "gene-wise averages rather than isoform-specific"), so
leakage is at the **gene**, not the dataset. A 2025 measurement of a gene's half-life correlates
with the 2018 measurement their head trained on, and date-filtering source datasets does not
remove that. The route was abandoned in favour of one with no gene identity at all. If the count
is still wanted, the remaining work is to pull Agarwal's harmonized gene list from the Genome
Biology additional files and intersect — the 18.8 GB Saluki Zenodo archive is not needed.

### 2.2 Option-3 hunt — found, and it was already in hand

Searching for designed constructs with measured in-cell decay led back to **Leppek K, Byeon GW,
Kladwang W, et al., Nat Commun 13, 1536 (2022)** — the **PERSIST-seq** paper, which is **the same
paper this project's existing in-solution workbook (MOESM6) comes from**. Its supplementary
archive **MOESM4** (zip, sha256 `849ed7b4…`) contains **"Supplementary Data 1 — Attributes for
pooled 233 sequences.xlsx"** (sha256 `be534d17…`), which carries, per construct:

- `In-cell half-life` **and** `In-solution half-life` — **both axes, same constructs**
- `Sequence 5 UTR`, `Sequence CDS`, `Sequence 3 UTR` — **declared boundaries, so no ORF-finding
  substitute is needed** (the earlier comparison required one)
- `Ribosome load`, CAI, GC, and the SUP/AUP DegScore/Vienna/EternaFold baselines

Counts measured from the table: 233 records, **191 with both half-lives**, all 191 with all three
segments, lengths **504–1588 nt** (entirely inside the sub-3000 nt scope), **69 in this project's
calibration training set** → **122 clean test constructs**.

This is strictly better than the atlas route on every axis: identical sequences for both columns,
so no cell-line, assay-harmonisation, gene-identity or length confound; declared segments; and
designed constructs carry no gene identity, so they are leakage-free for their head by construction.

---

## 3. The test

Protocol `configs/two_axis_comparison_v1_2026-10-20.json`,
sha256 `ad804b82c4db7995a61848410431e76b60e8a4ec5210e0d2e3728feec522282f`, **written and hashed
before any number was seen**, including the expected pattern and an explicit falsification
criterion for this project's own side. Nothing was refitted.

Scripts: `scripts/run_two_axis_comparison.py` (this project's half, plus the test-set export) and
`scripts/build_two_axis_comparison.py` (merges mRNAutilus's half). Their half was scored in the
isolated environment with the declared offsets `five_utr_ind = 3 + len(5'UTR)`,
`cds_length = len(CDS)`; 49 distinct layouts, LM loaded once, **122/122 scored**.

Run: `results/two_axis_comparison_runs/20261021T042044.996926Z/` — `summary.json` (our side),
`two_axis_summary.json` (the 2×2), `test_set.csv` (the exported input).

### 3.1 The 2×2, Spearman against measured half-life, n = 122

| Predictor | in-solution | in-cell |
|---|---|---|
| **This project (frozen calibration)** | **+0.3200** | +0.2208 |
| mRNAutilus `halflife` head | +0.1449 | +0.1396 |
| **free EternaFold, per nucleotide** | **+0.4190** | −0.1313 |
| **transcript GC alone** | +0.2979 | **+0.2253** |

### 3.2 The number that dominates the artifact

**In-solution and in-cell half-life of the SAME 122 constructs rank at Spearman +0.0545.**

They are very nearly unrelated orderings. Consequences, all recorded:

- No predictor can rank both axes well. The two columns are **separate tasks**, not two views
  of one quantity called "stability".
- Winning one column implies nothing about the other, which is why the earlier one-column
  comparison could never have been repaired by more in-solution data.
- Any claim in this project about predicting "stability" **must name the axis**. This is now
  prohibition 25.

### 3.3 Three adverse findings

1. **A free baseline now beats the calibration on the calibration's own axis.** Free
   per-nucleotide EternaFold reaches **+0.4190** on in-solution against the frozen
   calibration's **+0.3200**. The earlier 123-record test showed a tie (+0.3248 vs +0.3268);
   on this set the untrained baseline **wins**. This is the most adverse finding about the
   stability objective in any gate version.
2. **GC alone ranks both axes about as well as the three-feature calibration** — +0.2979 vs
   +0.3200 on in-solution, and on in-cell **GC alone is better** (+0.2253 vs +0.2208). The
   calibration adds little to nothing over base composition on either axis.
3. **The GC collapse reproduces on real measured constructs.** The objective correlates with
   transcript GC at **+0.7812** here — lower than the +0.99 on the synthetic pool recorded in
   v12, but still dominant. The collapse is a property of the **objective**, not an artifact of
   the design pool's composition. That removes the most hopeful reading of v13.

### 3.4 What it overturned in v13, in the direction against this project's interest

v13 attributed mRNAutilus's weak in-solution ranking to domain mismatch, and recorded that as
why this project's win was not symmetric. On the two-axis test their head ranks **in-cell at
+0.1396 and in-solution at +0.1449** — essentially flat, and weakly predictive on both. **The
measurement-domain excuse offered on their behalf in v13 does not hold on this test set.**

The narrowing is **partial, not a withdrawal**: their head's home domain is in-cell decay of
**endogenous** human mRNAs, and these are **designed reporter constructs**. The measurement type
is theirs; the sequence type is not. They are half in domain here.

Net effect: this project still ranks in-solution better than they do, and still **may not claim
general superiority** — on in-cell the two are close (+0.2208 vs +0.1396) and **mRNAutilus is
clearly better in the above-2× in-cell bin** (0.7269 vs this project's 0.5110, where this
project falls to chance).

### 3.5 Concordance, both axes (chance 0.50)

| Bin | in-solution pairs | ours | mRNAutilus | in-cell pairs | ours | mRNAutilus |
|---|---|---|---|---|---|---|
| 1.00–1.10 | 2899 | 0.4878 | 0.5254 | 1830 | 0.4918 | 0.5169 |
| 1.10–1.25 | 2188 | 0.5622 | 0.5334 | 2108 | 0.5508 | 0.5228 |
| 1.25–1.50 | 1081 | 0.6642 | 0.3626 | 1972 | 0.6197 | 0.5538 |
| 1.50–2.00 | 228 | 0.7500 | 0.3684 | 1244 | 0.6568 | 0.5916 |
| above 2.00 | 985 | 0.9665 | 0.8812 | 227 | **0.5110** | **0.7269** |

**Neither method resolves the narrow bin on either axis.** Both sit within 0.05 of chance below
1.10×, which remains the regime the design space occupies.

### 3.6 Falsification criterion: not triggered, narrowly

The protocol declared that if the frozen calibration ranked in-cell as well as or better than
in-solution, its apparent in-solution competence would not be domain-specific and the
in-solution framing of the objective would be wrong. Measured: **+0.3200 in-solution vs +0.2208
in-cell**, so the framing survives. The margin is small and GC alone explains most of both
columns, so this is a survival, not a vindication.

---

## 4. Two bugs found and fixed during the run

1. **The ensemble worker takes RNA, not DNA.** The first run folded nothing: all 122 failed
   because `sequence_dna` was passed with `T`. Fixed by converting to `U`, matching
   `validate_against_leppek_half_life.py`.
2. **The library has two constant-region layouts, and the first parse silently dropped 24
   records.** Most constructs are `GGG + 5'UTR + CDS + Constant1 + Barcode + Constant2 + 3'UTR
   + Constant3`; the 24 **"CDS (Nluc) variants"** are `GGG + 5'UTR + CDS + 3'UTR + Constant1 +
   Barcode + Constant2 + Constant3`. Same length, different order, first difference at
   position 719.

   **This bug was masked by a coincidence worth recording.** With the 24 dropped, the test set
   was still exactly 122 — but reached as 191 − 24 mismatches − 45 training, not the declared
   191 − 69 training. The declared count check passed for the wrong reason. After the fix:
   `reconstruction_mismatch: 0`, `in_training_set: 69`, test set 122. A test now asserts both
   numbers, so the coincidence cannot recur silently.

   **Consequence worth knowing:** all 24 layout-2 constructs are "CDS (Nluc) variants", and that
   entire design category **is** this project's 69-record training set. The 122-record test set
   therefore contains **no Nluc coding variants at all** — it is 98 UTR variants plus 13 eGFP and
   9 MEV coding variants and 2 controls. More independent than a random split, and also a
   distribution shift. A test pins this.

---

## 5. Verification actually run

| Check | Command | Outcome |
|---|---|---|
| New tests | `.venv/bin/python -m pytest -q tests/test_two_axis_comparison.py tests/test_stage2_gate_v14.py` | **28 passed** |
| Full suite | `.venv/bin/python -m pytest -q` | **1,130 passed, 0 skipped**, 1 known Ninja warning |
| Archive + table hashes | enforced in the script before any row is read | both match the protocol |
| Test-set size | enforced against the protocol | 122, with dropped counts 42 / 0 / 69 |
| Folding | 122 constructs, 24 workers | 0 failures after the RNA fix |
| Extrapolation | frozen calibration feature domain | **1 of 122** outside the training range |
| Their scoring | isolated venv, declared offsets | **122/122**, 49 layouts, LM loaded once |

Suite 1,102 → **1,130** (+28).

**Not run, not claimed:** no construct was made or measured by this project; RiboNN was not run
here; the translation axis is deliberately out of scope; `ruff` was not run this stretch.

---

## 6. Gate v14

Supersedes v13 at sha256 `a5c83ce443f5579919be8b1af67c62980103e66c6499c26a510f8fae0448c704`,
retained frozen and unedited. **No switch moves. No requirement reopened or re-ratified.**
Stage 2 stays closed at 6/6 on the v5 basis.
File: `configs/stage2_to_stage3_gate_v14_2026-10-20.json`,
sha256 `27dd7af27867cb6967425b94b282f5d461b47a5690669c42338fb115227f3e34`.

Prohibitions **24 → 28**. The four added:

- Do not describe anything in this project as predicting "mRNA stability" **without naming the
  axis** — the two axes rank at +0.0545 on identical constructs.
- Do not repeat v13's explanation that mRNAutilus's weak in-solution ranking is domain mismatch
  **alone**; on its own in-cell axis it ranks no better.
- Do not claim the frozen calibration beats free folding — on in-solution, free EternaFold ranks
  **above** it.
- Do not claim the three-feature calibration adds predictive value over **transcript GC**.

v14 also records `what_this_does_not_authorize`: no production-path change, no new switch.

---

## 7. Scientific interpretation

The honest reading is that this stretch cost the stability objective most of its remaining
claim, and bought something more valuable in exchange.

**What was lost.** The objective's in-solution competence is now bounded from below by two free
alternatives: a per-nucleotide EternaFold score ranks better, and transcript GC alone ranks
nearly as well. Its GC dependence is +0.78 on real measured constructs, so v12's collapse was
not a quirk of the synthetic pool. Across five gate versions the same finding has now arrived
from four independent directions, and this is the first time it arrived on measured data with a
free baseline beating the fitted model.

**What was gained.** The axis question is settled, and it is the kind of result that prevents a
category of wasted work. In-solution and in-cell stability are nearly orthogonal on identical
constructs (+0.0545). Every "mRNA stability" number in this project, and in the literature it
draws on, is a number about one of two unrelated orderings. A design pipeline optimising
in-solution half-life is **not** optimising in-cell persistence, and no amount of accuracy on
one transfers to the other. That reframes the deliverable more sharply than any accuracy
improvement would have.

**What is still true of the comparison with mRNAutilus.** Neither method is usable as a ranker in
the regime that matters. Both are at chance below 1.10× on both axes. Their head is weakly and
uniformly predictive (~+0.14) across both; this project's is better on in-solution, comparable on
in-cell, and collapses to chance on the largest in-cell differences where theirs does not.

**Limitations.** 122 constructs from one paper, one lab, one assay pair, mostly UTR variants, with
no Nluc coding variants because that category is the training set. Their head was run as shipped,
with mean pooling, no fine-tuning and no m1Ψ handling. Their scale is arbitrary; only ranks were
used. The in-cell measurement is PERSIST-seq on designed reporters, not endogenous decay, so
their head is half in domain. The two-axis orthogonality is measured on these constructs and need
not hold for endogenous mRNAs.

**Rejected this stretch.** The endogenous atlas route, for gene-level leakage that date-filtering
cannot fix (§2.1). Force-feeding the 2,165-row `Fig_3b` and 2,037-row `Fig_S7a` sheets, which are
107-nt fragments with **no ORF**, into a three-segment tokeniser — that would have been a rigged
test in this project's favour and was declined before any number was produced. Dropping the 24
layout-2 records rather than parsing them. Refitting anything on in-cell labels.

---

## 8. Outstanding, prioritized

1. **Decide which axis this project is for.** This is now the gating question and it is the
   user's call. In-solution half-life is what the frozen calibration addresses and what shelf
   stability means; in-cell persistence is what protein output depends on. The pipeline
   currently optimises the first and the program cares about the second.
2. **If in-cell is the target, the stability objective needs rebuilding, not tuning.** The
   PERSIST-seq table supplies 203 constructs with in-cell half-life (122 untouched by this
   project), which is a starting basis, and GC alone already matches the current calibration
   there.
3. **Tier-1 improvements from the V8 list remain unimplemented**: m1Ψ-aware modelling,
   position-preserving pooling, calibrated uncertainty.
4. RiboNN vs Sample-2019 MRL for the translation side — note this is **not** comparable against
   mRNAutilus's translation head, which shares RiboNN's training source.
5. `Fig_S7a` SHAPE for requirement 1; the ~2,000-row sheets as a larger basis for a
   fragment-scale model only, since they have no ORFs.
6. Region-local features; C++/ninja toolchain for the fused qLogEHVI kernel; V12 §6 item 7
   archive build re-run.

**Still blocked on others:** assay CVs; false-accept/false-reject cost; whether Fluc-PEST enters
the panel; panel capacity; the two questions for Ping (5′UTR shortening; parent construct).

---

## 9. Exact safe continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
S=/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad

.venv/bin/python -m pytest -q                      # expect 1,130 passed
.venv/bin/python -m pytest -q tests/test_two_axis_comparison.py tests/test_stage2_gate_v14.py

# Re-run this project's half (writes a NEW timestamped run; verifies both hashes first)
.venv/bin/python scripts/run_two_axis_comparison.py --archive "$S/acq_persist/MOESM4.zip" --jobs 24

# Merge mRNAutilus's half into the newest run
.venv/bin/python scripts/build_two_axis_comparison.py "$S/their_two_axis.json"
```

Re-fetching the source archive, if the scratchpad is gone:

```bash
curl -L -o MOESM4.zip "https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-022-28776-w/MediaObjects/41467_2022_28776_MOESM4_ESM.zip"
sha256sum MOESM4.zip   # must be 849ed7b49198c5b97049fec8d3636deea8812db4dd45ce0bcc448297703511c2
```

Re-running their side needs the isolated environment (scratchpad, not in this repo, does not
survive the session). Script: `$S/score_two_axis_mrnautilus.py`. **Must run with the mRNAutilus
repo root as cwd** — their `HalfLife` loads `classifiers/hl/best_model.json` by a relative path:

```bash
cd "$S/mrnautilus_run/repo" && "$S/mrna_env/bin/python" "$S/score_two_axis_mrnautilus.py" \
  "$S/mrnautilus_run/repo" "$S/mrnautilus_run/best.ckpt" \
  "$S/mrnautilus_run/repo/configs/experiment/lm/mdlm_150m.yaml" \
  results/two_axis_comparison_runs/<stamp>/test_set.csv "$S/their_two_axis.json"
```

### Publishing

```bash
PUB=$S/pub2
git -C "$PUB" fetch origin && git -C "$PUB" status --short
sha256sum "$PUB/diagram_10182026.png"   # must stay baa831ce16df27ed…
```

The working directory has **no commits** and `origin` is the placeholder
`https://github.com/YOUR_USERNAME/RNA-StableAI.git`; publication is from the separate clone.

---

## 10. Published state

| Item | Value |
|---|---|
| Commit before this stretch | `488cb1b` Record the comparison commit hash in handoff 2026-10-20 V8 |
| Commits published with this handoff | `5bc4bf2` (content + this handoff), then the commit recording its hash |
| README picture | `diagram_10182026.png`, sha256 `baa831ce16df27ed44a41c2a3b481455a213b328122227b9b2a3820dda47cff1`, **byte-unchanged**; `workflow_10202026.svg` unchanged |
| Gates | v5–v13 frozen; **v14 current**. Opens no switch, reopens no requirement. |
| Diagram | **not regenerated.** Nothing was added to the production path. |

### 10.1 Publication record

`5bc4bf2` — Test both stability axes on the same constructs: they are nearly unrelated, and the
objective loses to free folding. The hash is recorded by the commit immediately after it, per the
established pattern.
