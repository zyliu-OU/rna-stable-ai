# RNA-StableAI — Handoff 2026-10-20 V11

- **Project:** RNA-StableAI · **Date:** 2026-10-20 (America/Los_Angeles) · **Version:** V11
- **Workspace:** `/home/zyliu/Documents/rna-stable-ai` · **Remote:** `https://github.com/zyliu-OU/rna-stable-ai.git` (PUBLIC)
- **Interpreter:** `.venv/bin/python` (3.12). Bare `python3` is anaconda 3.14 without biopython.
- **Session ended early at the user's request** ("stop when you can, clade limit almost
  reached"). This handoff is deliberately shorter than the project standard, and §6 lists
  exactly what was left undone so the next session can finish it.

---

## 1. User decisions recorded this stretch

1. **The target axis is IN-CELL mRNA STABILITY** (half-life / decay). Not in-cell expression.
2. **The EternaFold refit direction is retired.** "we dont do that".
3. **The architecture is unchanged:** RNAfold + STRAND + RiboNN + BoTorch.
4. Open question answered for the user: the "in-cell" results are **stability**, not expression.
   The source table keeps `Ribosome load` as a separate measurement and `Predicted expression`
   as a derived value; neither was the target.

---

## 2. EternaFold retirement — what was removed and what was kept

`scripts/run_feature_refit.py` now carries only ViennaRNA/composition arms
(`gc_cds_only`, `frozen_form_from_table`, `vienna_plus_composition`). The old run directory was
deleted and regenerated: `results/feature_refit_runs/20261021T055502.531513Z/`.

**Deliberately kept, and the next session must not remove it:** the defective-baseline
correction. It corrects a claim already **published** in commit `5bc4bf2` (the +0.4190 "free
EternaFold" figure that was actually AUP × a region-length ratio). Deleting it would leave a
wrong published number standing. The overfitting finding is also kept, now carried by the
ViennaRNA arms alone: train **+0.3617 → +0.5972** while held-out falls **+0.3651 → +0.1317**.

---

## 3. In-cell feature screen — the substantive result

Protocol `configs/in_cell_feature_screen_v1_2026-10-20.json` (hashed before any number was
seen). Script `scripts/run_in_cell_feature_screen.py`. **Univariate by design**, because gate
v15 measured that this label-set size supports about one feature. Nothing was fitted or adopted.

**Bar to beat:** transcript GC alone on in-cell = **+0.2253**.

### 3.1 The first split could not answer the question

`--split preserved` (81 train / 122 held out) → `results/in_cell_feature_screen_runs/20261021T055712.830701Z/`.
**Zero of 24 features cleared the bar.** Cause: the training half is 78/81 **CDS (Nluc)
variants**, which hold the UTRs fixed — `utr5_gc` has **2 distinct values in training against
46 in the held-out set**, `utr5_length` 2 against 44. The screen was structurally blind to UTR
features, and the held-out set is mostly UTR variants.

### 3.2 Family-stratified split — two additions worth building

`--split stratified --seed 1729` (105 train / 98 held out), balanced within each design family
→ `results/in_cell_feature_screen_runs/20261021T055854.371752Z/`.
**This is an amendment to the protocol's "preserve the existing split" clause**, recorded for
the reason above. *Consequence to carry: in-cell results on this split are NOT comparable to
the in-solution results, which keep the 122-record set. Any in-cell claim must state its split.*

Five features beat the bar on held-out:

| feature | train | **held-out** |
|---|---|---|
| `utr5_frac_C` | +0.4242 | **+0.3857** |
| `cds_energy_per_nt` | −0.2979 | **−0.3864** |
| `cds_aup` | −0.2860 | **−0.3310** |
| `utr5_upa` | −0.3573 | −0.2776 |
| `cds_length` | +0.2414 | +0.2802 |
| *transcript GC (bar)* | — | *+0.2253* |

**They collapse to TWO nearly orthogonal signals** (`utr5_frac_C` ↔ `utr5_upa` = −0.758;
`cds_energy_per_nt` ↔ `cds_aup` = +0.830; the two families only **−0.182** apart):

1. **CDS-local structure** — best `cds_energy_per_nt`, held-out **−0.3864**. The production
   path already folds with ViennaRNA but folds the **whole transcript**; this is the same engine
   called on the **CDS alone**. A change in how an existing component is used, not a new
   dependency. Notably **stronger on held-out than on training**, the opposite of overfitting.
2. **5′UTR composition** — best `utr5_frac_C`, held-out **+0.3857**. No folding, no model, no
   dependency.

**Resolution is unchanged.** All five sit between **0.500 and 0.523** in the 1.00–1.10 bin
against chance 0.50. Only the Spearman improved. The v11 coarse-filter-plus-diversity framing
stands.

**Multiplicity warning:** 37 features screened on 105 training records; 14 promoted; 5 cleared
held-out. Several would clear by chance, which is why only the held-out column counts.

### 3.3 RiboNN must NOT be wired into the stability model

This was the most promising-looking addition and it fails. Measured `Ribosome load` vs in-cell
half-life is **−0.3286** over the 122-record set — better than the GC bar — but **the sign
reverses by design family**:

| family | n | ρ |
|---|---|---|
| CDS (Nluc) variants | 78 | **+0.4916** |
| UTR (3′) variants | 19 | **+0.5842** |
| CDS (MEV) | 9 | +0.3167 |
| CDS (eGFP) | 14 | +0.1121 |
| **UTR (5′) variants** | 49 | **−0.5551** |
| UTR (5′/3′) variants | 31 | −0.1988 |

The −0.3286 aggregate was the 5′UTR families outvoting the rest; on the family-balanced split
the ceiling collapses to **−0.1018 train / +0.0879 held out**.

**Interpretation:** translation and stability are positively coupled when the **coding
sequence** is varied (codon-optimality coupling) and negatively coupled when the **5′UTR** is
varied. A pipeline editing both regions cannot use one signed coupling for both.

**Conclusion:** RiboNN stays a separate Pareto axis — which is what the architecture already
does. This is also the **first measured evidence that keeping the two objectives as separate
incommensurable axes was correct**, rather than merely cautious.

---

## 4. Verification actually run

| Check | Outcome |
|---|---|
| Full suite, `.venv/bin/python -m pytest -q` | **1,153 passed, 0 skipped**, 1 known Ninja warning |
| Archive + table hashes | enforced before any row read; match |
| Region folding | 609 regions, 0 failures |
| Held-out size, preserved split | 122, enforced |

One test assertion was loosened: `test_the_refit_overfits_monotonically` required the widest
arm to fall below |0.10|, which the retired EternaFold arm did (−0.0022). The surviving
ViennaRNA arms bottom out at +0.1317, so the bound is now 0.20 with the reason recorded in the
assertion message. **The finding is unchanged; only the arm demonstrating it changed.**

---

## 5. What was NOT done — next session starts here

- **Gate v16 was not written.** The script failed with `KeyError: 'split'` because the
  preserved-split artifact predates the `split` field added for the stratified run. Fix: read
  `split` with `.get()`, or take the note from the stratified artifact only. The intended v16
  content is fully specified in §1–3 above, including three prohibitions to add:
  1. Do not wire RiboNN into the stability objective; measured ribosome load does not predict
     in-cell stability (sign reverses by family, +0.4916 vs −0.5551, balanced ceiling +0.0879).
  2. Do not claim any screened feature is adopted or validated for production.
  3. Do not claim the screen improved resolution (0.500–0.523 in the narrow bin).
- **No tests were written** for `in_cell_feature_screen_v1` or its runs.
- **No combined two-feature model** was fitted or tested — this is the obvious next experiment
  given the two signals are only −0.182 apart. It needs its own declared protocol and must
  respect the ~1–2 feature budget from v15.
- `cds_length` among the held-out performers is a length ruler and was not discounted.
- `utr5_frac_C` has no mechanistic explanation yet; it may be a proxy for something else.

---

## 6. Exact safe continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
S=/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad

.venv/bin/python -m pytest -q                       # expect 1,153 passed

.venv/bin/python scripts/run_in_cell_feature_screen.py --archive "$S/acq_persist/MOESM4.zip" \
    --jobs 24 --split stratified --seed 1729        # reproduces the headline screen
.venv/bin/python scripts/run_feature_refit.py --archive "$S/acq_persist/MOESM4.zip"
```

Re-fetch the source archive if the scratchpad is gone:

```bash
curl -L -o MOESM4.zip "https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-022-28776-w/MediaObjects/41467_2022_28776_MOESM4_ESM.zip"
sha256sum MOESM4.zip   # must be 849ed7b49198c5b97049fec8d3636deea8812db4dd45ce0bcc448297703511c2
```

---

## 7. Published state

| Item | Value |
|---|---|
| Commit before this stretch | `4f1fda7` Record the correction commit hash in handoff 2026-10-20 V10 |
| Commit published with this handoff | recorded by the commit immediately after |
| README picture | `diagram_10182026.png`, sha256 `baa831ce16df27ed44a41c2a3b481455a213b328122227b9b2a3820dda47cff1`, **byte-unchanged** |
| Gates | v5–v15 frozen; **v15 still current — v16 NOT written** (see §5) |
| Diagram | not regenerated; nothing was added to the production path |
