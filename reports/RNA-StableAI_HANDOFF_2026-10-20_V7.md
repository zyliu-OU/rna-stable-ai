# RNA-StableAI — Handoff 2026-10-20 V7

- **Project:** RNA-StableAI
- **Date:** 2026-10-20 (America/Los_Angeles)
- **Version:** V7 (follows V1–V6 of this date; all stand unedited)
- **Workspace:** `/home/zyliu/Documents/rna-stable-ai`
- **Publication clone:** `/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad/verify`
- **Remote:** `https://github.com/zyliu-OU/rna-stable-ai.git` — **PUBLIC**
- **Headline:** the **first external validation in this project's history**.
  `strand_rnafold_calibration_v1` was tested against 123 measured in-solution half-lives it
  was never fitted on: **Spearman +0.3268**, not falsified, and **statistically
  indistinguishable from a free per-nucleotide EternaFold score (−0.3248)**. Suite:
  **916 passed, 0 skipped**.

---

## 1. User instructions in this stretch

| Instruction | Consequence |
|---|---|
| "where I can find more sequence database and the correspond experiment data for training and test? can you search online?" | Searched; four candidate sources assessed and ranked by quantity match. |
| "can you use these papers sequence to verify our code and compare with paper's experiment results?" | Acquisition of the best-matched dataset, and the training-overlap discovery below. |
| "run it on the 123 held-out records" | The validation run. |
| "sure" | Tests, this handoff, publication; the translation side is next and not yet started. |

---

## 2. Dataset search, and why this one

Four candidates were assessed. The selection criterion was **quantity match**, because a
mismatched quantity makes a negative result uninterpretable.

| Source | Measures | Verdict |
|---|---|---|
| **Leppek et al. 2022, PERSIST-seq / In-line-seq** | in-cell stability, ribosome load, **in-solution stability in hours** | **chosen** — the third is exactly what the calibration predicts |
| Eterna OpenVaccine | per-base degradation, 107 nt | rejected: not a transcript half-life, 17× shorter than our construct |
| Saluki compendium (Agarwal & Kelley 2022) | in-cell decay of endogenous transcripts | rejected: different quantity |
| Sample et al. 2019 5′UTR MPRA | mean ribosome load, 200k+ 50-nt UTRs | **deferred** — tests the translation side, next job |

- Source: `10.1038/s41467-022-28776-w`, Supplementary Data `MOESM6`
- `sha256 9a8b6b4314ab892aa3e4a4476993189dff1245d4ab55494723782e6afebae0e7`, 6,256,259 bytes
- Sheet `Fig_S8a`: 192 rows with both `RNA_sequence` and `half_life`
- **Not redistributed.** The URL and hash are pinned so it can be re-acquired; only derived
  metrics are published. Same treatment as RiboNN weights and Rfam sources.

The workbook was downloaded into its own empty scratch directory and parsed with the standard
library under `python -I`, as untrusted third-party data.

---

## 3. The training-overlap discovery

**This nearly produced a circular validation.** Before building anything, the paper's measured
half-lives were checked against the calibration's own training table:

```
GC matches        : 69 of 69 training rows match a paper sequence's GC exactly
half-life matches : 69 of 69 training rows match a paper half-life exactly
training GC range : 39.4397 .. 60.2371   — identical to the paper's
```

`strand_rnafold_calibration_v1` was fitted on a subset of this very dataset. Scoring the full
192 rows would have been testing the model on its training data.

- **Join method:** exact numeric match on whole-sequence GC **and** half-life, because the
  training table uses barcodes (`X310001T1`) while the sheet uses human-readable names, with
  **zero** overlap by name.
- **Join risk, recorded:** this is an **inferred** provenance link, not a documented one. Two
  independent float columns agreeing across all 69 records makes coincidence implausible, but
  it is reconstructed.
- **Useful side effect:** because training GC matches GC of the **full** `RNA_sequence`, the
  training features were computed on the full sequence, not the RT-PCR amplicon window. That
  settled which window to fold — verified, not guessed.

### 3.1 The split

| | training subset | held out |
|---|---|---|
| n | 69 | **123** |
| experiment | NLuc Eterna only | NLuc Barna lab 101, eGFP 13, MEV 9 |
| length | 928–984 nt | **504–1,588 nt** |
| half-life | 0.720–2.030 h | **0.865–4.360 h** |
| beyond training max | 0 | **9** |

**Declared before the result:** this is a **distribution shift**, not only a split. The
held-out records are a different reporter over wider ranges, so poor transfer could be the
shift rather than the model, and these data cannot separate the two.

---

## 4. Protocol, frozen first

`configs/external_validation_leppek_v1_2026-10-20.json`, whose `status` field records that the
criteria were written **before any correlation was computed**, and whose hash is pinned in the
run artifact.

- **Primary:** Spearman over the 123 held-out records. Chosen because the project permits
  ranking and correlation claims only.
- **Secondary:** Pearson on log half-life; MAE in hours, explicitly not a claim of absolute
  accuracy; the training subset as an **upper bound, not a result**.
- **Expected direction:** positive.
- **Falsification:** ρ ≤ 0 means no transfer, and would be reported.
- **Weak-transfer threshold:** ρ < 0.3 to be described as no useful transfer.
- **Baselines:** the paper's own `DegScore2.1`, `Vienna`, `EternaFold` columns on the same
  records; if the calibration loses to all of them, the refit adds nothing.
- **Extrapolation:** flagged per record; the metric reported over all 123 and over the
  in-domain subset, neither alone as the headline.
- **No refitting.** Frozen coefficients applied as recorded.

---

## 5. Results

`results/external_validation_leppek_runs/20261020T210948.866079Z/summary.json`

| | n | Spearman | Pearson (log) | MAE (h) |
|---|---|---|---|---|
| **held out, all** | 123 | **+0.3268** | +0.5871 | 0.413 |
| held out, in-domain | 122 | +0.3237 | +0.5951 | 0.413 |
| training subset — upper bound | 69 | +0.5290 | — | 0.236 |

The paper's own predictors, same 123 records:

| predictor | raw ρ | raw vs **length** | **per-nucleotide ρ** |
|---|---|---|---|
| DegScore 2.1 | −0.0616 | **+0.9807** | −0.2166 |
| Vienna | −0.0608 | **+0.9454** | −0.2829 |
| EternaFold | −0.0760 | **+0.9433** | **−0.3248** |

Length vs measured half-life: ρ −0.0530, so length is not a confound in our prediction.

**Verdict against the declared criteria:** not falsified; over the ρ > 0.3 line by 0.027, on a
threshold set by this project. Reported as **real but weak transfer**, not a success.

### 5.1 A correction to my own analysis, recorded as post-hoc

The protocol declared the baseline comparison on the predictor columns **raw**. That was
wrong: those columns are **sums over nucleotides** and correlate with sequence length at
ρ +0.94 to +0.98 across 504–1,588 nt, so raw they encode length rather than degradation rate.

The first run therefore reported the published predictors at |ρ| ≈ 0.06 and this project five
times better — an artifact of misusing their column, not a property of their predictor.
Per nucleotide they behave correctly, and **EternaFold's 0.3248 is indistinguishable from our
0.3268**.

The correction is recorded in the artifact under `baseline_post_hoc_correction`: what was
declared, what was wrong, when it was changed (**after** the primary result), the
justification (**mechanical** — a sum over a variable-length sequence), and that the primary
metric was untouched. A test asserts the raw-vs-length evidence rather than just the claim.

### 5.2 Interpretation

**The calibration is not fitting noise.** It carries real signal to records it never saw,
across a reporter change, a wider length range, and half-lives up to 2× beyond its training
maximum. That was genuinely in doubt before this run.

**It adds nothing over a free baseline.** A per-nucleotide EternaFold score matches it without
any refit. The honest framing is that the pipeline **reproduces** the state of the art on this
quantity rather than improving on it.

**The generalisation gap is now measured:** 0.529 training against 0.327 held out.

**Pearson on log (+0.587) well above Spearman (+0.327)** means the model separates fast- from
slow-degrading RNA better than it orders similar ones. That is exactly the regime the
synonymous-variant work lives in, where predicted differences span a few percent, and **this
result does not rescue it**.

**It says nothing about the project's own construct**, at 1,811 nt and 64.4% GC, outside this
dataset's 504–1,588 nt and 42–60% GC entirely.

---

## 6. Verification actually run

| Check | Outcome |
|---|---|
| workbook sha256 verified before any row was read | pass |
| `--dry-run`: row counts and split | 192 / 69 / 123 as declared |
| full run, 123 + 69 folds | exit 0 |
| `pytest tests/test_external_validation_leppek.py` | 20 passed |
| `ruff check` on the two new files | All checks passed |
| broken local links in README | 0 |
| **Full suite** | **916 passed, 0 skipped** in 10.26 s |

One bug found and fixed during the run: `component_integration.fold_fixed_input` builds a
`Transcript`, which validates its CDS as a real reading frame. These records are full mRNAs
with their own UTRs and the sheet gives no CDS boundaries, so a whole-sequence CDS failed with
`First codon 'GGG' is not a start codon`. Fixed by calling `rnastable.ensemble_worker`
directly, since the three calibration features need no CDS annotation; **inventing a CDS to
satisfy a validator was rejected** and the reason is recorded in the script.

### Not verified / not claimed

- A correlation is **not** a calibration. No absolute accuracy is established.
- Model failure and distribution shift cannot be separated with this data alone.
- The training-subset figures are an upper bound, not a result.
- Nothing here touches the translation side, in-cell stability, or our own construct.
- A positive result does **not** validate the design workflow, whose predicted differences
  between synonymous variants are far below the spread tested here.

---

## 7. Next: the translation side

Not started. The plan is the same discipline against **Sample et al. 2019**, the 5′UTR MPRA
with ~200,000 random 50-nt UTRs on eGFP and measured **mean ribosome load**, testing RiboNN's
`predicted_TE_A549` usage rather than the stability calibration.

Expected obstacles, worth knowing before starting:

1. **Quantity match is weaker than for the stability side.** MRL is a ribosome-load proxy;
   RiboNN's task is translational efficiency of endogenous human transcripts. Close, not
   identical.
2. **Construct shape.** The MPRA records are 50-nt UTRs on a fixed eGFP CDS, so a full
   transcript must be reconstructed to give RiboNN the `utr5_size`/`cds_size` it requires. That
   reconstruction is a declared choice and must be frozen before scoring.
3. **Scale.** 200k records at 50 checkpoints each is far beyond the 512-record runs done so
   far; a declared subsample with a frozen seed is likely necessary.
4. **Training overlap must be checked first**, exactly as it was here. RiboNN was trained on
   human transcript data; whether any MPRA-derived data entered it is unknown and is the first
   thing to establish.

---

## 8. Open items

1. **The translation-side validation** above.
2. **Experimental data from Ping** — the P0–P3 specification is unchanged: CV first, then the
   pool-extremes go/no-go, then the flatness-diagnostic pairs, then the Pareto panel.
3. **Region-local features, or accept the flat landscape.** This result sharpens the question
   rather than settling it: the calibration ranks dissimilar RNAs adequately and similar ones
   poorly, which is the wrong way round for synonymous design.
4. **Requirement 1 remains an accepted limitation.** `Fig_S7a` in the same workbook carries
   **SHAPE** data on ~2,000 constructs — experimental structure probing, in scope by length.
   That is the most promising route to closing it and has not been touched.
5. Carried: free vs GC-neutral; the span policy and the unspent blinded set; the power
   convention; the two questions for Ping; the C++ toolchain for the fused qLogEHVI kernel.

**No process is running.**

---

## 9. Exact safe continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai

# Full suite (expect 916 passed, 0 skipped)
.venv/bin/python -m pytest -q

# This stretch
.venv/bin/python -m pytest -q tests/test_external_validation_leppek.py

# Re-acquire the source (it is not in the repo), into its own empty directory
mkdir -p /tmp/leppek && cd /tmp/leppek
curl -sL -o MOESM6.xlsx \
  "https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-022-28776-w/MediaObjects/41467_2022_28776_MOESM6_ESM.xlsx"
sha256sum MOESM6.xlsx   # must be 9a8b6b4314ab892aa3e4a4476993189dff1245d4ab55494723782e6afebae0e7

# Verify the split without folding anything
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/validate_against_leppek_half_life.py \
  --workbook /tmp/leppek/MOESM6.xlsx --dry-run

# Re-run the validation (writes a NEW timestamped run; about 3 minutes)
.venv/bin/python scripts/validate_against_leppek_half_life.py \
  --workbook /tmp/leppek/MOESM6.xlsx --jobs 24

# Lint only the files written here
ruff check scripts/validate_against_leppek_half_life.py \
  tests/test_external_validation_leppek.py
```

The script **refuses to run** on a workbook whose sha256 does not match the protocol, and
refuses if the row count or the held-out count differs from the declared 192 / 123.

### Publishing

```bash
PUB=/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad/verify
git -C "$PUB" fetch origin && git -C "$PUB" status --short
sha256sum "$PUB/diagram_10182026.png"   # must stay baa831ce16df27ed…
diff "$PUB/README.md" README.md
```

---

## 10. Published state

| Item | Value |
|---|---|
| Commit before this stretch | `dce6141` Record the purge commit hash in handoff 2026-10-20 V6 |
| Commit published with this handoff | see §10.1 |
| README picture | `diagram_10182026.png`, `sha256 baa831ce16df27ed44a41c2a3b481455a213b328122227b9b2a3820dda47cff1`, **byte-unchanged** |
| Gates | v5 and v6 frozen; **v7 current**. This validation does not change a gate: it adds external evidence and opens no switch. |

### 10.1 Publication record

This handoff is published in the commit titled *"Validate the stability calibration against
123 held-out measured half-lives"*. Its hash is recorded by the commit immediately after it.
