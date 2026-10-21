# RNA-StableAI — Handoff 2026-10-20 V8

- **Project:** RNA-StableAI
- **Date:** 2026-10-20 (America/Los_Angeles; the run timestamps are UTC and read 2026-10-21)
- **Version:** V8 — supersedes V7 for this date; V1–V7 remain and are not edited
- **Absolute workspace path:** `/home/zyliu/Documents/rna-stable-ai`
- **Remote:** `https://github.com/zyliu-OU/rna-stable-ai.git` — **PUBLIC**
- **Publication clone (recreated this stretch):** `/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad/pub2`
- **Project interpreter:** `/home/zyliu/Documents/rna-stable-ai/.venv/bin/python` (Python 3.12).
  **Bare `python3` in this workspace is anaconda 3.14 and lacks biopython**; running the
  suite with it produces 11 collection errors that are an environment artifact, not
  failures. This cost a confused minute this stretch and is recorded so it does not again.

---

## 1. What this stretch was

One task, asked for explicitly and run before any change to this project's code:

> "before we change our code, lets run a test for mRNAutilus, you can use the sequence we
> ran, then compare the our result with their model result"

mRNAutilus is the method behind the collaborator's paper (`papers/mRNAutilus_NBT.pdf`,
weights at `https://huggingface.co/atombio/mrnautilus`). This is the first time an
independent published model has scored the same sequences as this project's objective.

**It produced one favourable result and one genuinely useful one.** The favourable result
is the less important of the two and is the one most at risk of being quoted without its
caveat.

---

## 2. Current user priorities and scope boundaries

Unchanged from V7 except as noted:

- Production path is **ViennaRNA/LinearFold → STRAND calibration + RiboNN → BoTorch**. The
  learned pair model is retired and purged (gate v7); nothing in the path imports it.
- **No new model is to be developed.** The user's standing framing is validation and
  combination of existing components.
- Stage 2 is **closed at 6/6** on the gate v5 basis, two requirements by accepted
  limitation. Stage 3 target is `transfected_cell_expression`.
- Length scope: **< 3000 nt**. The 2000–2999 nt band is an accepted documented limitation.
- Lengths are **fixed** in the whole-transcript design space (user: "fixed length is fine").
- Third-party data and weights are **not redistributed**; URLs and sha256 only.
- **Decision deferred by this stretch:** whether to act on the comparison. Gate v13 states
  explicitly that the comparison authorizes no change to the production path. The user's
  earlier question — "what aspect do you think we can build and improve based on
  mRNAutilus" — was answered in chat (tiers below, §8) and **no code was changed**.

---

## 3. Completed work, with paths

### 3.1 Protocol, declared before any number was seen

`configs/mrnautilus_comparison_v1_2026-10-20.json`
sha256 `d78be7429af18ef4012615d5a7eb623eb9bfd1b92e4bdb41629ec94039c3c3ff`

Declared in advance, and pinned by a test:

1. **Rank statistics only.** Their `config.yaml` carries `avg` normalisers (0.0212, −0.613,
   1.503), so their head outputs are not physical units. Absolute values are never compared
   to hours.
2. **The half-life test set is asymmetric.** Their head is Saluki-trained on **in-cell
   decay**; the Leppek records measure **in-solution** degradation. On that set this project
   is in-domain and mRNAutilus is not.
3. **A declared ORF-finding step is required**, because the Leppek records carry no declared
   CDS boundaries and their tokeniser needs three segments: longest `ATG`..in-frame-stop with
   no internal stop. 123 of 123 records yielded an ORF.
4. **The metric is the already-frozen one** from `stability_feature_ablation_v1`: pairwise
   concordance binned by measured fold difference, chance = 0.50.

### 3.2 Their environment, and three API-drift adaptations

Isolated venv at `…/scratchpad/mrna_env` (Python 3.12, torch 2.8.0+cu126, cxx11abi True,
flash-attn 2.8.3.post2, xgboost 3.4.1). Checkpoint 1.78 GB,
sha256 `07e1b534008df579c58d65d5df6ec6c4dcf944d149133330049cbc054c1c4e29`,
**strict load verified: 399 state-dict entries, 399 after prefix strip, 0 missing,
0 unexpected, 148.1M parameters.**

Three upstream drifts had to be worked around. Each was verified equivalent **before**
being applied, and all three are recorded in the protocol:

| Drift | Fix | Why it is not a maths change |
|---|---|---|
| `torch >= 2.6` defaults `weights_only=True`; their loader does not pass it | patched at the call site **in the comparison script only** | the checkpoint is the authors' own file at the pinned hash, whose strict load this project had already verified |
| flash-attn 2.8.3 made fp32 rotary position indices unconditional, so `RotaryEmbedding` no longer accepts `pos_idx_in_fp32` | kwarg dropped; original kept at `…/scratchpad/attention.py.orig` | verified in flash-attn source that `t = torch.arange(seqlen, dtype=torch.float32)` is now always taken |
| flash-attn ≥ 2.7 appends `used_seqlens_in_batch` to `unpad_input`'s return; their call unpacks four | unpack with trailing `*_` | verified in `flash_attn/bert_padding.py` that the fifth value is informational and **unused by their code** |

No mRNAutilus code or weights are vendored into this repository. A test asserts this by
globbing for `scoring_functions.py` and `*.ckpt`.

### 3.3 Run A — the same 512-member pool, both methods

Script: run from the isolated env; pool **regenerated deterministically** with
`build_pool` at the frozen seed then `assemble_designed`, and the script **aborts** unless
every transcript hash matches the stored run. **512 of 512 matched**, so this is provably the
same pool as `results/full_transcript_design_runs/20261020T232952.639002Z/`.
(The stored artifact deliberately strips `utr5`/`utr3`/`orf`, so regeneration was required.)

| Their head | r vs **transcript GC** | r vs **our objective** | members above reference |
|---|---|---|---|
| `halflife` | **−0.2636** | **−0.2262** | 196 / 512 |
| `translation_rate` | **+0.6811** | +0.6852 | 8 / 512 |
| `ribo_seq` | +0.3017 | +0.3023 | 467 / 512 |

This project's objective on the same pool: **r = +0.9897 vs transcript GC** (gate v12).

**The useful result.** An independent model scores the same 512 transcripts with near-zero
GC dependence on its stability head, and disagrees with this project's objective **in sign**.
The GC collapse recorded in v12 is therefore a property of **this project's one-component
PLS calibration**, not an unavoidable consequence of the design pool. **It is escapable. It
has not been escaped.**

**The counterweight, recorded in the same place.** Their `translation_rate` head correlates
with transcript GC at **+0.6811**. A learned representation escaped the composition confound
on one head and not on another, so "use a learned model" is not by itself the remedy.

**What was NOT concluded.** Their scores spread across the pool (`halflife` stdev 0.1206,
range −0.0178 to 0.7917, reference 0.5129), but on an arbitrary normalised scale with no
measurement-derived error model. This project's resolution floor was derived from replicate
measurement error **in hours** and cannot be transferred. **Spread is not resolution**, and a
test pins that this was not claimed.

### 3.4 Run B — the 123 held-out measured records (the decisive one)

Same set as `external_validation_leppek_v1`. 49 distinct (5′UTR length, CDS length) layouts,
because their scorer slices at fixed offsets; the language model is loaded once and reused
across all of them (`ScoringFunctions` honours `model is not None`).

**Spearman vs measured in-solution half-life:**

| Predictor | ρ |
|---|---|
| **This project (frozen calibration)** | **+0.32677** |
| free EternaFold, per nucleotide | +0.32479 |
| mRNAutilus `halflife` head | **+0.17470** |

**Pairwise concordance by measured fold difference** (chance 0.50):

| Bin | pairs | **ours (frozen)** | mRNAutilus | free EternaFold/nt | ours (OLS refit arm) |
|---|---|---|---|---|---|
| 1.00–1.10 | 2958 | 0.4936 | **0.5250** | 0.5247 | 0.5007 |
| 1.10–1.25 | 2230 | **0.5650** | 0.5538 | 0.5807 | 0.5735 |
| 1.25–1.50 | 1091 | **0.6654** | **0.4033** | 0.6013 | 0.6902 |
| 1.50–2.00 | 230 | **0.7522** | **0.3783** | 0.7000 | 0.7826 |
| above 2.00 | 994 | **0.9668** | 0.8722 | 0.9608 | 0.9598 |

Three things in that table matter, and the third is the one to carry forward:

1. This project ranks better **overall** and in **every bin at or above 1.25×**.
2. mRNAutilus is **nominally ahead in the narrowest bin** (0.5250 vs 0.4936). Both are at
   chance there and the pairs are not independent. **Neither side may claim that bin**, and a
   test pins that the bin we lose is recorded alongside the ones we win.
3. **Their head inverts.** It is strongly concordant above 2× (0.8722) yet **below chance** in
   the 1.25–1.50 and 1.50–2.00 bins. A predictor that inverts on moderate differences while
   succeeding on large ones is not simply weaker — it is ordering something else. The most
   likely explanation is the one declared in advance: in-cell decay and in-solution
   degradation agree about which RNAs are grossly unstable and need not agree in between.

**This is not a symmetric comparison and must not be reported as one.** On this test set this
project is in-domain and mRNAutilus is out-of-domain. The only sound conclusion is about
in-solution stability specifically. It says nothing about their head on in-cell decay, which
is what it was trained for and **was not tested here**.

### 3.5 A correction carried into the record

Earlier narrative in this project (including chat and the V7-era discussion) quoted
**0.5007** as this project's narrowest-bin concordance. That is the **OLS-refit arm** used
inside `stability_ablation_v1` so its variants were internally comparable. The **frozen
production calibration** — the one-component PLS whose predictions the pipeline actually
emits — gives **0.4936** on that bin. Its held-out Spearman +0.32677 reproduces
`frozen_pls_reference.held_out_spearman` exactly, which is how the arm was confirmed.

Both are at chance and **no conclusion anywhere in this project depends on which is cited**,
but they are different arms. The artifact now carries both as separate labelled columns and a
test asserts they stay distinct.

### 3.6 Artifacts written

| Path | What |
|---|---|
| `configs/mrnautilus_comparison_v1_2026-10-20.json` | protocol, hash above |
| `configs/stage2_to_stage3_gate_v13_2026-10-20.json` | gate v13, sha256 `a5c83ce443f5579919be8b1af67c62980103e66c6499c26a510f8fae0448c704` |
| `scripts/build_mrnautilus_comparison.py` | assembles the artifact from the two run files and re-derives this project's side from its own stored artifacts |
| `results/mrnautilus_comparison_runs/20261021T032048.592878Z/summary.json` | the comparison |
| `…/their_scores_pool.json`, `…/their_scores_held_out.json` | their raw per-sequence scores |
| `tests/test_mrnautilus_comparison.py` | 17 tests |
| `tests/test_stage2_gate_v13.py` | 10 tests |

One superseded run directory, `results/mrnautilus_comparison_runs/20261021T031955.508546Z/`,
was **removed** before publication. It was 15 minutes old, unreferenced and unpublished, and
labelled this project's side ambiguously (§3.5). Removing it avoided shipping two artifacts
that disagreed about what "ours" meant. No frozen protocol, gate or handoff was touched.

### 3.7 Gate v13

Supersedes v12 at sha256 `29d26b2700fa3a90f38250ac46d25a62be44136be4e30f3a5c05ebfc2a13e79e`,
retained frozen and unedited. **No switch moves. No requirement is reopened or
re-ratified.** Stage 2 stays closed at 6/6 on the v5 basis.

Prohibitions **21 → 24**. The three added:

- Do not claim this project's method is better than mRNAutilus. On one held-out in-solution
  half-life set it ranks better overall and in every bin at or above 1.25×, on a test set
  where mRNAutilus is out of domain and this project is in domain. That is the only
  comparison that was run.
- Do not claim mRNAutilus resolves this project's design pool. Spread is not resolution.
- Do not claim the GC collapse has been fixed or avoided. The comparison establishes only
  that it is **escapable**. This project's objective still collapses to GC at r = +0.99.

v13 also records `what_this_does_not_authorize`: no change to the production path, no
adoption of mRNAutilus, no new switch. Acting on the comparison is a separate, separately
recorded decision.

---

## 4. Verification actually run

| Check | Command | Outcome |
|---|---|---|
| New tests | `.venv/bin/python -m pytest tests/test_mrnautilus_comparison.py tests/test_stage2_gate_v13.py -q` | **27 passed** |
| Full suite | `.venv/bin/python -m pytest -q` | **1,102 passed, 0 skipped**, 1 warning (the known Ninja/fused-qLogEHVI fallback) |
| Pool identity | enforced inside the scoring script | **512/512 transcript hashes matched** the stored run |
| Their checkpoint | strict `load_state_dict` | **399/399 keys, 0 missing, 0 unexpected, 148.1M params** |
| Arm identity | ρ reproduced against `frozen_pls_reference` | **+0.32677251679973174**, exact |
| README picture | `sha256sum diagram_10182026.png` in the clone | `baa831ce16df27ed…` **byte-unchanged** |

Suite count 1,075 → **1,102** (+27, all new).

**Not run, and not claimed:** no construct was made or measured; RiboNN was not run on the
pool in this stretch; `ruff` was run on nothing this stretch (the repo carries ~2,882
pre-existing errors, so "ruff clean" would only ever mean the files written).

---

## 5. Scientific interpretation

The comparison moves one thing and settles nothing about the pipeline's output quality.

**What moved.** For five gate versions this project has been circling a single finding: its
stability objective is, on the reachable design domain, a GC meter. v9 measured m1Ψ
rescaling the GC→ribosome-load slope by ~3.7×; v10 found ordering at chance in the regime the
design space occupies; v12 measured r = +0.99 between transcript GC and predicted half-life
and found that entering the calibration's fitted GC domain **requires lowering GC**, which the
model scores as worse. The open question was whether this was a property of the **calibration**
or of the **pool**. It is the calibration: an independent model, on byte-identical transcripts,
scores stability with r = −0.26 against GC. That is the first evidence that a non-degenerate
stability objective over this pool exists to be found.

**What did not move.** Neither method resolves the narrow bin. Both are at chance below
1.10×, which is the regime synonymous and composition-level design actually produces. The
practical conclusion from V7 stands: the output of this pipeline is a **coarse filter plus a
diversity panel**, not a ranking.

**What the favourable result is worth.** Less than it looks. It is one test set, chosen
because this project already had measured labels for it, on which the other model is out of
domain. The honest reading is narrow: for **in-solution** half-life on Leppek-style
constructs, a three-feature physics-based calibration ranks better than a 148M-parameter
embedding model's in-cell-decay head — and a **free per-nucleotide EternaFold score ranks
essentially as well as the calibration** (+0.3248 vs +0.3268), which is the same uncomfortable
finding the v10 ablation recorded and which this comparison does nothing to relieve.

**Limitations.** Their heads were run through their own `ScoringFunctions` with
`hidden.mean(dim=1)` pooling as shipped; no fine-tuning, no m1Ψ handling (they have none),
and the three API adaptations in §3.2. The ORF-finding step for Run B is a declared
substitute for CDS boundaries the records do not carry, and a different rule would give
different segment splits and therefore different embeddings. Their scale is arbitrary; only
ranks were used.

**Rejected this stretch.** Keying held-out records by "Human readable name" — three records
share a name, which silently gave 120 predictions for 123 rows and let three rows borrow a
neighbour's score; switched to row index, after which 123/123 scored and the bin pair counts
matched this project's own run exactly (2,958 in the narrowest bin). Also rejected: flipping
`use_flash_attn: False` to dodge the rotary drift, because the rotary convention would then
be unverifiable; and reporting their pool spread as resolution.

---

## 6. Outstanding, prioritized

1. **Decide whether to act on the comparison.** Gate v13 deliberately authorizes nothing.
   The answer given in chat, unimplemented, was tiered: **Tier 1** — m1Ψ-aware modelling,
   position-preserving pooling instead of `hidden.mean(dim=1)`, calibrated predictive
   uncertainty; **Tier 2** — LoRA fine-tuning on this project's labels, multi-task heads, a
   physics channel; **Tier 3** — true Pareto handling, constraint enforcement,
   declared-protocol discipline. Tier 1's first item is the only one that both addresses the
   measured GC degeneracy and needs no new training data.
2. **RiboNN vs Sample-2019 MRL** — the translation side has no external validation at all.
3. **`Fig_S7a` SHAPE on ~2,000 constructs** for requirement 1; the ~2,000-row
   `Fig_3b`/`Fig_S7a` label sets as a larger training basis (the current calibration has 69).
4. Region-local features; C++ toolchain for the fused qLogEHVI kernel; V12 §6 item 7 archive
   build re-run.

**Still blocked on others:** assay CVs; false-accept/false-reject cost; whether Fluc-PEST
enters the panel; panel capacity; and the two questions for Ping (5′UTR shortening; parent
construct).

---

## 7. Exact safe continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai

# Full suite — use the PROJECT interpreter, not bare python3
.venv/bin/python -m pytest -q                       # expect 1,102 passed

# Just this stretch
.venv/bin/python -m pytest -q tests/test_mrnautilus_comparison.py \
                               tests/test_stage2_gate_v13.py

# Rebuild the comparison artifact from the two run files (writes a NEW timestamped dir)
S=/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad
.venv/bin/python scripts/build_mrnautilus_comparison.py \
  "$S/their_hl_result.json" "$S/their_pool_scores.json"

# Inspect the gate chain
.venv/bin/python -c "import json;d=json.load(open('configs/stage2_to_stage3_gate_v13_2026-10-20.json'));print(len(d['what_must_not_be_claimed']),'prohibitions')"
```

**Re-running their model requires the isolated environment**, which is in the scratchpad and
is **not** part of this repository and will not survive the session:

```bash
S=/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad
# repo:       $S/mrnautilus_run/repo   (clone of huggingface.co/atombio/mrnautilus)
# checkpoint: $S/mrnautilus_run/best.ckpt   sha256 07e1b534008df579c…
# venv:       $S/mrna_env/bin/python
# scripts:    $S/compare_mrnautilus.py   $S/score_pool_mrnautilus.py
# MUST run with the mRNAutilus repo root as cwd: their HalfLife loads
#   xgb.Booster(model_file='classifiers/hl/best_model.json')  -- a RELATIVE path
cd "$S/mrnautilus_run/repo" && "$S/mrna_env/bin/python" "$S/compare_mrnautilus.py" ...
```

To rebuild it from scratch: clone the HF repo, fetch the checkpoint from the Google Drive
link in their README (`id=1mU37sSkEPNClR0OYBpLLF66g44TJEL3i`), verify the sha256, create a
Python 3.12 venv with torch 2.8.0+cu126 / flash-attn 2.8.3.post2 / xgboost, and apply the
three adaptations in §3.2.

### Publishing

```bash
PUB=/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad/pub2
git -C "$PUB" fetch origin && git -C "$PUB" status --short
sha256sum "$PUB/diagram_10182026.png"   # must stay baa831ce16df27ed…
```

**Note:** the working directory `/home/zyliu/Documents/rna-stable-ai` has **no commits** and
its `origin` is the placeholder `https://github.com/YOUR_USERNAME/RNA-StableAI.git`.
Publication is done from a separate clone of the real remote. Earlier clones were deleted
this session to free disk; `pub2` was recreated for this stretch.

---

## 8. Published state

| Item | Value |
|---|---|
| Commit before this stretch | `855345e` Widen the design domain to UTRs plus codons: the threshold clears, the objective turns out to be a GC meter |
| Commits published with this handoff | see §8.1 |
| README picture | `diagram_10182026.png`, sha256 `baa831ce16df27ed44a41c2a3b481455a213b328122227b9b2a3820dda47cff1`, **byte-unchanged**; `workflow_10202026.svg` unchanged |
| Gates | v5–v12 frozen; **v13 current**. v13 opens no switch and reopens no requirement. |
| Diagram | **not regenerated.** The workflow did not change this stretch; nothing was added to the production path. |

### 8.1 Publication record

Recorded by the commit immediately after, per the established pattern.
