# RNA-StableAI — Handoff 2026-10-20 V6

- **Project:** RNA-StableAI
- **Date:** 2026-10-20 (America/Los_Angeles)
- **Version:** V6 (follows V1 the gate review, V2 BoTorch and Pareto, V3 the design space,
  V4 the end-to-end workflow, V5 the whole-ORF scaling; all stand unedited)
- **Workspace:** `/home/zyliu/Documents/rna-stable-ai`
- **Publication clone:** `/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad/verify`
- **Remote:** `https://github.com/zyliu-OU/rna-stable-ai.git` — **PUBLIC**
- **Headline:** the retired learned pair model was **purged entirely** and **all data at or
  above 3,000 nt was removed** — 792 MB across 9 recorded passes. Requirement 5's evidence
  was re-issued on the in-scope cohort first. Suite: **896 passed, 0 skipped**, down from
  1,486 passed and 38 skipped. Recorded in
  [gate v7](../configs/stage2_to_stage3_gate_v7_2026-10-20.json).

---

## 1. User instructions in this stretch

| Instruction | Consequence |
|---|---|
| "why keep these old trained model data? remove all these old trained model data, only keep the RNAfold / ViennaRNA data" | The purge below. |
| "remove all old model related things" | Extended to source modules, drivers, configs and tests, not only artifacts. |
| "remove all data for RNA length longer than 3000nt" | The length-scope removal, reversing `docs/LENGTH_SCOPE.md`. |

Two scope choices were put to the user before anything was deleted, because both changed the
outcome materially:

- **Model purge scope → "purge everything now"**, over extracting the shared primitives
  first, accepting that the native-control evidence generators break.
- **≥3,000 nt → "delete, then re-issue requirement 5"**, over leaving the evidence stale or
  keeping the 11-record cohort.

**Why asking was necessary.** The instruction rested on a premise that did not hold: the
learned-model modules were not separable. `pair_model.py` held `CANONICAL` and
`pair_set_training.py` held pair-scoring helpers, and **three current evidence generators
imported them**. And requirement 5's evidence was 22 folds over 11 records, **5 of them
≥3,000 nt**, so deleting long data would have made a live gate claim unverifiable.

---

## 2. Order of operations, and why it mattered

Requirement 5 had to be re-issued **before** the purge, because its generator was one of the
scripts the purge would have broken. Doing it in the other order would have left a gate claim
with no way to regenerate it.

1. `scripts/verify_native_path_requirement5.py` was changed to drop its `pair_model` import —
   the six-element `CANONICAL` set is now **inlined** — and to filter the frozen selection to
   the in-scope subset.
2. Re-issued: `results/native_path_requirement5_runs/20261020T202050.166787Z/`
   — **12/12 replay exact, 12/12 constraints honoured**, both tools refuse an unsatisfiable
   constraint, max 6.73 s and 96.9 MiB against limits of 30 s and 4 GiB, and **no out-of-band
   resource rows**, which is itself a check that no out-of-scope record survived.
3. `tests/test_native_path_requirement5.py` updated: 6 records, 12 folds, and an assertion
   that `out_of_band` is absent.
4. Only then the purge.

---

## 3. The purge

`scripts/purge_retired_model_and_long_data.py`. Nine passes, each writing a manifest to
`results/model_purge_runs/<timestamp>/manifest.json` **before removing anything**.

| Category | Removed |
|---|---|
| learned-model source modules | 29 |
| driver scripts | 130 |
| unit and replay tests | 76 |
| run directories | 75 |
| configs | 21 |
| out-of-scope run directories, found by content | 33 |
| synthetic inputs ≥3,000 nt | 4 |
| **total** | **792.3 MB** |

`results/` fell from 2.0 GB to about 1.2 GB.

### 3.1 Why it took nine passes

A hand-written list of "model modules" was not enough, and each pass exposed the next layer:

1. the 13 named modules, their runs, configs, scripts and tests;
2. **15 more src modules** that imported them — found by a computed transitive closure, not
   by name, and checked against `CURRENT_PIPELINE_MODULES` so the production path could not
   be caught; the script **refuses to run** if the closure ever reaches one;
3. tests whose plain imports no longer resolved;
4. **scripts importing deleted scripts**, iterated to a fixed point, because removing a
   driver leaves other drivers importing it;
5. tests that load their subject by path with `importlib`, which no import scan catches;
6. tests asserting against deleted run artifacts, which import only surviving code;
7. a **content** sweep: 33 run directories still carrying a ≥3,000 nt sequence, in
   directories whose names say nothing about length;
8. stripping out-of-scope records from retained artifacts;
9. the last three degradation tests, recorded by hand in the manifest.

### 3.2 Stripping rather than deleting

Twenty retained artifacts carried in-scope **and** out-of-scope records in the same files —
the cohort selection, the native-control rows, several exposure journals, a binding record.
Deleting them would have destroyed the provenance of surviving in-scope evidence, so the
out-of-scope records were pruned and **every file's pre-removal hash recorded**:

| File | Kept | Removed |
|---|---|---|
| `long_validation_coverage_runs/…/selection.json` | 6 | 5 |
| `long_validation_coverage_runs/…/candidates.json` | 284 | 54 |
| `long_native_controls_runs/…/rows.json` | 12 | 10 |
| 17 further retained files | — | 21,593 records |

**21,662 out-of-scope records pruned in total.** This is the only place in the purge where
frozen artifacts were edited, against the project's usual convention, and it is recorded in
the manifest and in gate v7 for that reason.

### 3.3 Verification

A content scan over `results/` finds **zero** files carrying a sequence of 3,000 nt or more.
A test (`test_no_file_under_results_still_carries_an_out_of_scope_sequence`) re-checks that
claim rather than trusting it.

---

## 4. What this destroyed

Stated before what it preserved, because that is the part a later reader needs.

- **Requirements 2, 3 and 4 can no longer be regenerated from source.**
  `scripts/validate_native_controls_stage2.py`, `scripts/expand_band_native_controls.py` and
  `scripts/evaluate_bprna_five_clan_feasibility.py` imported the model's shared constants and
  are gone. **Their artifacts remain and are unchanged**, and gate v5 and v6 still cite them;
  a check confirms every path those gates cite still exists.
- `scripts/verify_long_native_controls.py` is gone, having imported a deleted cohort verifier.
- **609 tests** were removed with their subject. The suite went from 1,486 passed and 38
  skipped to **896 passed and 0 skipped**. `tests/conftest.py` was deleted outright: its
  retired-checkpoint skip guard guarded runs that no longer exist.
- **Most of `results/` was never published**, so those run artifacts are **not recoverable
  from git history**. That asymmetry is the whole reason for the manifests.

## 5. What this preserved

- **Every figure the gate chain cites**, because v4, v5 and v6 embed them as literal values
  rather than by reference. The retirement rests on 0.2965 against 0.4381 and 0.3255 against
  0.6261, recorded in v4 and still there.
- All handoffs and reports — the narrative record of both the model and the long-length work.
- The manifests, which record what existed so a later reader can tell **"never run"** from
  **"run and then deliberately removed"**.
- The whole current pipeline: native controls, STRAND calibration, RiboNN, the design
  workflow, the three 512-member runs, the scaling fit. A test asserts the eleven production
  modules survived.

---

## 6. Gate v7 and the reversed policy

`configs/stage2_to_stage3_gate_v7_2026-10-20.json`, tested by `tests/test_stage2_gate_v7.py`
(19 tests). It supersedes v6, retained unedited at its recorded hash, carries the
six-requirement basis forward **untouched** — two still accepted limitations, not evidence —
and changes no switch.

`docs/LENGTH_SCOPE.md` previously recorded material ≥3,000 nt as **preserved** as deferred
scope, and that the classification "deletes or truncates nothing". **That policy is
reversed**, and the document now carries the reversal notice rather than contradicting the
tree.

**What must not be claimed**, recorded in the gate: that the learned model's results were
never obtained; that work above 3,000 nt was never done; that removing the artifacts changed
any measurement, which it did not; or that a smaller test suite means a sounder project.

---

## 7. Verification actually run

| Check | Outcome |
|---|---|
| requirement 5 re-issue | exit 0; 12/12 replay, 12/12 constraints, both refusals |
| purge, 9 passes with manifests | 792.3 MB removed; closure guard never tripped |
| content scan for ≥3,000 nt sequences | **0 files** |
| gate-cited evidence paths, v5 and v6 | **none missing** |
| `pytest tests/test_stage2_gate_v7.py` | 19 passed |
| `pytest tests/test_native_path_requirement5.py` | 11 passed |
| `ruff check` on the files written here | All checks passed |
| broken local links in README | **0 of 63** |
| **Full suite** | **896 passed, 0 skipped** in 10.24 s |

The suite now runs in **10 seconds** rather than 136, because the replay-heavy model tests
are gone. That is a consequence of the deletion, not an improvement in the project.

### Not verified / not claimed

- No measurement of any molecule exists; nothing about the pipeline's correctness changed.
- The purge's counts are the manifests' own counts, and a test compares the gate's recorded
  figures against them.
- Whether 792 MB of deleted development evidence should have been kept is a judgement the
  user made, not a finding.

---

## 8. Open items

1. **Experimental data.** The specification is in the previous turn's reply and unchanged:
   P0 the CV from the reference construct alone, P1 the pool-extremes go/no-go, P2 the
   flatness-diagnostic pairs, P3 the Pareto panel. Plus panel capacity, decision cost, and
   whether Fluc-PEST enters.
2. **Region-local features, or accept the flat landscape** — unchanged from V5 §6. My
   recommendation is still a measurement first.
3. **Three evidence generators no longer exist.** If requirements 2, 3 or 4 ever need
   regenerating, they must be rewritten against the native path. The artifacts and the
   configs that describe them remain.
4. Carried: free vs GC-neutral; the span policy and the unspent blinded set; the power
   convention; the two questions for Ping; experimental-structure references in scope; the
   C++ toolchain for the fused qLogEHVI kernel.

**No process is running.**

---

## 9. Exact safe continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai

# Full suite (expect 896 passed, 0 skipped)
.venv/bin/python -m pytest -q

# This stretch
.venv/bin/python -m pytest -q tests/test_stage2_gate_v7.py \
  tests/test_native_path_requirement5.py

# Confirm nothing out of scope survived
.venv/bin/python -I -c "
import re
from pathlib import Path
p = re.compile(r'\"sequence\"\\s*:\\s*\"[ACGUTacgut]{3000,}\"')
bad = [q for q in Path('results').rglob('*.json')
       if q.is_file() and q.stat().st_size < 20_000_000 and p.search(q.read_text(errors='ignore'))]
print('files with a >=3000 nt sequence:', len(bad))"

# Re-issue requirement 5 (writes a NEW timestamped run)
.venv/bin/python scripts/verify_native_path_requirement5.py --dry-run

# The purge tool is idempotent; a dry run on a clean tree reports zero paths
.venv/bin/python scripts/purge_retired_model_and_long_data.py --dry-run

# Read any purge manifest
ls results/model_purge_runs/
```

**The purge tool is destructive and takes `--apply`.** It refuses to run if its computed
closure ever reaches a module in `CURRENT_PIPELINE_MODULES`, and it writes its manifest
before removing anything. On a clean tree `--dry-run` reports zero paths, so re-running it is
safe.

### Publishing

```bash
PUB=/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad/verify
git -C "$PUB" fetch origin && git -C "$PUB" status --short
sha256sum "$PUB/diagram_10182026.png"   # must stay baa831ce16df27ed…
diff "$PUB/README.md" README.md
```

Publishing this change requires **deleting** files from the clone, not only copying: the
purge removed 200-plus tracked paths. `git -C "$PUB" add -A` after mirroring the tree picks
the deletions up.

---

## 10. Published state

| Item | Value |
|---|---|
| Commit before this stretch | `df0ee14` Replace the workflow diagram with the state the finished pipeline is actually in |
| Commit published with this handoff | `188a78e` |
| README picture | `diagram_10182026.png`, `sha256 baa831ce16df27ed44a41c2a3b481455a213b328122227b9b2a3820dda47cff1`, **byte-unchanged** |
| Workflow diagram | `workflow_10202026.svg`; it needs no change, since it never depicted the learned model as live |
| Gates | v5 and v6 frozen; **v7 current** |

### 10.1 Publication record

`188a78e` — Purge the retired learned model and all data at or above 3,000 nt. The hash is
recorded by the commit immediately after it.
