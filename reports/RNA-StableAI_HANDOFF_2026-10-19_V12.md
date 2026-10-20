# RNA-StableAI — Handoff 2026-10-19 V12

- **Project:** RNA-StableAI
- **Date:** 2026-10-19 (America/Los_Angeles)
- **Version:** V12
- **Absolute workspace path:** `/home/zyliu/Documents/rna-stable-ai`
- **Supersedes nothing.** V1–V11 of 2026-10-19 remain as written. This handoff
  records (a) the publication of the corrected README/diagram/roadmap, which V11
  carried as pending item 2, and (b) unblocked build work done while the 5′/3′ UTR
  sequences are still outstanding.
- **Session ended by user instruction:** "after current running thing finished,
  stop the build, I need to restart my computer." The build was stopped
  immediately after the full test suite completed. Nothing was left running.

---

## 1. Current user priorities and scope

The user asked, verbatim: **"can you start work on other things before I give you
5' and 3' UTR sequences?"** This session therefore took up only work that does
**not** depend on the pending transcript.

Scope boundaries unchanged and still binding:

- `new_sequence_scoring_enabled: false`
- `expression_candidate_design_enabled: false`
- `floors_frozen: false`
- `stage3_ready: false`
- Stage 2 gate: **0 of 6** requirements satisfied
  (`configs/stage2_to_stage3_gate_v2_2026-10-19.json`).

Nothing in this session changed any of those flags, and nothing in this session
satisfied any gate requirement.

### Decisions carried from V11 (unchanged)

| Decision | Value | Source |
|---|---|---|
| Stage 3 target | `transfected_cell_expression` | user: "for stage 3, amend the gate to transfected cells" |
| ORF edits | synonymous only | user: "yes, ORF edits must be synonymous" |
| T-cell arm | model-blind, no RiboNN task | user: "Declare the t-cell arm model-blind" |
| CV | below 20% for both readouts, **planning bound, not a measurement** | user: "lets just use below 20% for two CVs" |

---

## 2. Completed work

### 2.1 Publication of the corrected cell-free artifacts (V11 pending item 2)

Triggering request: **"fix the readme, diagram and roadmap, then publish"**.

- **Commit:** `d16b68c737478387ef6136f4e0ecb2c6693ff62a`
- **Base:** `1ca32bb3ea4eaf05c4931fa1060be64c6d1cd82d`, re-fetched and confirmed
  unchanged immediately before committing. No rebase, no force push.
- **Diff:** 39 files, 6,067 insertions, 18 deletions, **no file deletions**.
- Published from a fresh isolated clone at
  `/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/854cc336-3973-4ac5-9775-bc9c0e2d5fc8/scratchpad/pub2`.

Corrected artifacts, with the hashes that are now live:

| File | SHA-256 | Edits |
|---|---|---|
| `README.md` | `b207a2ca90f2d3255def3a0e62b9daf099a8393098cb405193019f0fdc2b229c` (20,135 B) | 6 |
| `diagram_10192026.svg` | `f2384a66b2034784e0c935334e936f3798abee1177c2507b2c004bda811d74c1` (11,670 B) | 8, incl. 2 `<desc>` |
| `reports/PROJECT_ROADMAP_2026-10-18.md` | `a6e6492d485ce9749c9ac0abd65705d992bdc84e2dd66c97ad5c6e59fab2beb0` (6,063 B) | 4 |

Every edit was applied through an assertion-guarded script asserting
`s.count(old) == 1` per replacement, so no edit could land in the wrong place or
silently fail.

Live verification after push (all passed):

- live `main` = `d16b68c737478387ef6136f4e0ecb2c6693ff62a`
- live `README.md` byte-identical to local; **1** remaining "cell-free" mention,
  which is the deliberate sentence recording that the target *was amended from*
  cell-free
- live `diagram_10192026.svg` byte-identical to local; **0** cell-free mentions
- live roadmap hash matches local
- live gate v2 parses with `stage3_target: transfected_cell_expression` and
  `requirements_satisfied: 0`
- the user's own `diagram_10182026.png` still live and unchanged
  (`56e1c7b0…`, 1,693,715 B) — the README picture was preserved per AGENTS.md
- old gate `configs/stage2_to_stage3_gate_2026-10-18.json` still live and
  unchanged at `956fef4d171a2d33d16a16e36b80d3def4696d321f930c74ea3396acbbd030dd`

The `<desc>` correction matters on its own: the SVG description still said no
RiboNN task had been selected. That text is what screen readers receive, so
leaving it would have published a false statement to exactly the readers least
able to detect it.

**Deliberately not redistributed:** the pinned Rfam archives (6,316,083 B across
5 excluded artifacts) and the copyrighted Nature supplementary files. Both are
identified by URL and SHA-256 only. Evidence directory published:
`reports/assay_definition_and_band_availability_publication_2026-10-19/`
(23 code files, 15 evidence files).

**Handoffs V1–V10 were deliberately left describing the cell-free target.** They
are historical records that were correct when written; rewriting them would erase
the fact that the target changed.

### 2.2 Fixed the ripgrep dependency — the 8 full-suite failures are gone

**Defect.** `scripts/archive_replay_sources.py` built its source inventory by
shelling out to `rg`:

```python
subprocess.run(["rg", "--files", "--hidden", "--no-ignore", *directories, "-g", pattern], ...)
```

`rg` is **not installed as a binary** on this machine. `which rg` finds nothing;
`type rg` shows it is only a **shell function** injected by the Claude Code
environment, which a `subprocess` call never sees. So the call raised
`FileNotFoundError` for anyone running the script, including the user directly.
ripgrep was never declared in `pyproject.toml` dependencies.

Both `scripts/archive_replay_sources.py` and `tests/test_replay_source_archive.py`
are dated 2026-10-13: **this defect pre-dates all of 2026-10-19's work and was
not caused by it.**

**Fix.** Replaced the subprocess call with a pure-Python `pathlib` inventory
(`src`… see `scripts/archive_replay_sources.py`, function `files`), preserving the
original semantics: basename glob match, hidden files included, ignore files
disregarded. `.git` is skipped explicitly. Results are de-duplicated and sorted,
so the inventory is deterministic. The docstring records *why* it must stay pure
Python: a missing external binary would silently shrink the recovered source set
rather than fail loudly.

The three `git` subprocess calls elsewhere in the file were left alone; git is a
real declared dependency of that script's purpose.

**Equivalence evidence (read-only, nothing mutated).** Compared the new inventory
against the inventory `rg` produced when
`results/replay_source_archive_summary.json` was frozen (file mtime
2026-10-14T20:36:40):

| Inventory | Found by `rg` at freeze | Still on disk | **Missed by new code** | Extra now |
|---|---|---|---|---|
| `src` + `scripts`, `*.py` | 174 | 174 | **0** | 109 |
| `results`, `manifest.json` | 84 | 84 | **0** | 237 |

All 109 extra Python files were checked by mtime: **0** of them pre-date the
freeze, so none is a file `rg` had missed. They are genuinely new since
2026-10-14 (91 under `scripts/`, 18 under `src/`). The replacement is therefore
behaviorally equivalent, not merely passing its tests.

**`build` was deliberately NOT re-run.** Doing so would overwrite the frozen
`results/replay_source_archive_summary.json`. Rewriting a frozen artifact is not
a decision to take unasked. The existing summary was instead verified in place:

```
$ .venv/bin/python scripts/archive_replay_sources.py --verify
Source archive audit passed:271/281 exact Python bindings; 10 missing versions remain explicit.
```

### 2.3 New region-aware edit validator for the v3 design space

**Gap found.** `configs/assay_definition_v3_2026-10-19.json` sets
`regions_subject_to_change: ["5_utr", "orf", "3_utr"]` with
`orf_constraint: synonymous_only`. But the only existing validator,
`check_synonymous_edit`, holds a **narrower frozen contract**: it requires
identical transcript geometry and untouched UTRs. `tests/test_component_integration.py:46`
asserts explicitly that it *rejects* a UTR change. So a legal v3 candidate that
substitutes a 5′UTR was rejected **as if it were a missense edit** — the function
conflates "UTRs unchanged" with "ORF synonymous". There was no validator capable
of expressing the recorded design space.

**Resolution.** `check_synonymous_edit` was **not modified**; its frozen contract
and its tests stand untouched. Added a separate function
`classify_construct_edit(parent, candidate)` in
`src/rnastable/component_integration.py`, which separates the two questions and
never proposes an edit.

Design points:

- **Protein invariance is the binding constraint.** The candidate CDS must
  translate to exactly the parent protein. An in-frame indel that keeps the frame
  and the stop codon but changes protein length is **invalid, not merely
  flagged** — "in frame" must not be mistaken for "synonymous". This is tested.
- Per-region accounting for `utr5` / `orf` / `utr3`: parent and candidate length,
  length delta, identity, and substitution count. Substitution count is `None` at
  unequal length, because position-wise substitution is undefined there, rather
  than a misleading zero.
- UTR length change is permitted and reported, since v3 allows it.
- Carries `parent_identity_sha256` / `candidate_identity_sha256` and both protein
  hashes, for provenance binding per `configs/score_record_schema_v1_2026-10-19.json`.
- Reports `model_input_coupling`, recording v3's own warning that the regions are
  not independent: whether STRAND features move, whether RiboNN region sizes
  move, and the candidate's RiboNN exclusion if any (e.g. a 5′UTR edit pushing
  past the 1,381 nt upstream-domain limit, which is an invalid reason).
- Carries an explicit `no_claim` string: edit validity is a sequence-level check
  and establishes no stability, translation or expression benefit.

New tests: `tests/test_construct_edit_classification.py`, **11 tests**, including
one that asserts the exact gap — the same UTR substitution is valid under
`classify_construct_edit` and rejected by `check_synonymous_edit`.

---

## 3. Verification actually run

| Check | Command | Outcome |
|---|---|---|
| Previously failing file | `.venv/bin/python -m pytest tests/test_replay_source_archive.py -q` | **9 passed** (was 8 failing) |
| New tests + frozen contract | `.venv/bin/python -m pytest tests/test_construct_edit_classification.py tests/test_component_integration.py -q` | **26 passed** |
| **Full suite** | `timeout 3000 .venv/bin/python -m pytest -q` | **1,103 passed, 1 skipped, 0 failed** in 216.73 s |
| Archive artifact replay | `.venv/bin/python scripts/archive_replay_sources.py --verify` | passed, 271/281 bindings, 10 missing stated explicitly |
| Lint | `ruff check` on the three changed files | 1 finding, `F401 io imported but unused`, **pre-existing** in `component_integration.py` and not introduced here; left untouched to avoid widening scope |

The full suite was **1,086 passed / 8 failed** before this session and is now
**1,103 passed / 1 skipped / 0 failed**. This is the first fully green full-suite
run recorded for this project. Note that handoffs before V11 reported a *focused
subset*, not the full suite.

**Environment note, important for the next session.** The full suite must be run
with the project virtualenv: `/home/zyliu/Documents/rna-stable-ai/.venv/bin/python`.
The default `python3` is Anaconda base (3.14.6) and **lacks biopython**, which
produces 15 collection errors (`ModuleNotFoundError: No module named 'Bio'`) that
are an environment artifact, not code defects.

### Changed files and hashes at session end

| File | SHA-256 | Git state |
|---|---|---|
| `src/rnastable/component_integration.py` | `9ef50ff82e10a75ab6d3de30f2195d72e4ecaad6281f48304a660936d502b00c` | untracked locally |
| `scripts/archive_replay_sources.py` | `fbd073cd42a3fd93891b5439d66f55897d8bdcd600d32b63c3362c54ee1a2943` | untracked locally |
| `tests/test_construct_edit_classification.py` | `36735e0520621c9087cf18c51d12d6c418355f5068044c4f0e18d77477cef49a` | untracked locally |

**Not yet published.** These three files exist only in the workspace. The local
repository has **no commits** (`fatal: your current branch 'main' does not have
any commits yet`); publication has always been done from a fresh isolated clone.
Publishing this work is a pending item, see §6.

---

## 4. Unverified / not done

- **`classify_construct_edit` has never been run on a real construct.** It has
  only unit tests on synthetic 9–15 nt transcripts. It has not seen the Fluc CDS,
  because no complete transcript exists yet.
- **`build` of the replay source archive was not re-run**, so there is no new
  archive run demonstrating the pure-Python inventory end-to-end on the live tree.
  Only `--verify` and the read-only equivalence comparison were run.
- No folding, no scoring, no RiboNN inference was run this session.

### RiboNN primary CD4+ activation state: attempted, unresolved

V11 listed as optional, needing no user input: pin down whether RiboNN's
`Primary_CD4+_T-cells` samples were resting or activated. **Attempted and not
resolved.** Four routes, all failed, with the reason recorded:

1. Local artifacts — carry the **task name only**, no sample provenance.
   `grep` over `results/`, `configs/`, `reports/` found `Primary_CD4` in config
   and prediction-column contexts only.
2. `Sanofi-Public/RiboNN` GitHub repo (full recursive tree listed, 22 files) —
   **no cell-type metadata at all**; only code, `config/conf.yml` and tiny example
   inputs.
3. Europe PMC — the published paper is `PMC12323635`, `isOpenAccess: N`;
   `fullTextXML` returns **HTTP 500** for both the article and preprint
   (`PPR893800`).
4. bioRxiv preprint `10.1101/2024.08.11.607362` — **HTTP 429** on every client
   tried (WebFetch on both `.full` and `.full.pdf`, and `curl` with a browser
   user agent). The UT Austin dissertation mirror fails with a self-signed
   certificate in the chain.

The information lives in the paper's supplementary dataset table, which is the
same copyrighted Nature supplementary this project deliberately does not retain.
The compendium is 3,819 ribosome profiling datasets condensed to 10,348 human
genes × 78 cell types.

**This cannot change the user's decision**, and that is the reason not to spend
more on it: the T-cell arm is model-blind on a **subset-composition** mismatch
(the task is CD4-only; the lab's cells are activated CD3+ containing both CD4+
and CD8+ populations). That mismatch holds whether the task's samples were
resting or activated. Resolving activation state would only sharpen the record,
not reopen the decision.

---

## 5. Scientific interpretation and limitations

- The `rg` fix is **infrastructure, not science**. It changes no result, no
  prediction and no recorded hash. Its value is that the source-recovery audit —
  the mechanism that proves which exact Python bytes produced which frozen run —
  now runs for anyone, instead of failing on a tool that happened to be a shell
  function in one environment. A provenance tool that cannot run is not provenance.
- `classify_construct_edit` likewise establishes **no biological claim**. It makes
  the recorded design space checkable. Its real contribution is forcing protein
  identity, not frame arithmetic, to be the test of "synonymous": a one-codon
  in-frame deletion passes every frame and stop check and still changes the
  protein, which would have broken the entire logic by which luminescence is read
  as an mRNA-level effect (that logic depends on enzyme specific activity being
  constant across the panel).
- The `assay_definition_v3` power problem is **unchanged and still unresolved**.
  At the stated CV bound of 20%, n=3 gives 54.2% power for the 1.5-fold target and
  the minimum detectable effect is 1.75-fold, which exceeds the target. The design
  is underpowered for its own goal unless the measured CV lands nearer 10%, or
  replicates rise to 5, or the analysis is paired (6 paired units reach 98.9%), or
  the reported outcome becomes the MDE rather than the 1.5-fold target.
- Rejected this session: re-running the archive `build` to showcase the fix
  (would overwrite a frozen artifact); modifying `check_synonymous_edit` to accept
  UTR edits (would break a frozen contract and its test, and would destroy the
  narrower guarantee some callers may want); fixing the pre-existing `io` lint
  finding (unrelated scope).

---

## 6. Prioritized next steps

**Blocked on the user (unchanged from V11):**

1. **The transcript.** 5′UTR and 3′UTR sequences, which construct is the
   parent/baseline, plasmid DNA vs IVT mRNA, poly(A) presence and length, cap
   chemistry and nucleoside modifications, and Ping's authoritative CDS. Nothing
   can be folded or scored without these. User: "I need to wait for other people
   tell me."
2. **Measured CVs** for luciferase normalized expression and the RT-qPCR
   half-life estimate, to replace the 20% planning bound.
3. **Decision cost** of a false accept vs a false reject — the last input any
   floor needs.
4. **Band requirement 3** (V7): retrain to free the two RF02462 records, amend the
   requirement by gate review, or accept it as a documented limitation.
5. **OpenVaccine acquisition decision** (V6): the only route to evaluating
   `strand_rnafold_calibration_v1` against its own target.

**Not blocked:**

6. **Publish this session's three files** (§3). Nothing has been published yet.
7. Optionally re-run the archive `build` to produce a fresh run under the
   pure-Python inventory — **requires a decision** on whether the frozen
   `replay_source_archive_summary.json` may be superseded, and if so it should be
   written as a new versioned artifact rather than an overwrite.

---

## 7. Exact safe continuation commands

Run from `/home/zyliu/Documents/rna-stable-ai`. All are read-only or test-only.

```bash
# Full suite — MUST use the project virtualenv, not the Anaconda base python3
timeout 3000 .venv/bin/python -m pytest -q

# This session's new tests only
.venv/bin/python -m pytest tests/test_construct_edit_classification.py -q

# The previously failing file
.venv/bin/python -m pytest tests/test_replay_source_archive.py -q

# Verify the frozen source archive without recomputing it
.venv/bin/python scripts/archive_replay_sources.py --verify

# Re-derive this session's file hashes
sha256sum src/rnastable/component_integration.py \
          scripts/archive_replay_sources.py \
          tests/test_construct_edit_classification.py

# Confirm the live publication state
git ls-remote origin main
```

Do **not** run `.venv/bin/python scripts/archive_replay_sources.py` without
`--verify` until the question in §6 item 7 is decided: it overwrites the frozen
`results/replay_source_archive_summary.json`.

---

## 8. What must not be claimed

- This session satisfied **no** Stage 2 gate requirement. Still 0 of 6.
- A green full test suite is **not** evidence of structure accuracy, stability
  benefit, translation benefit or expression benefit.
- `classify_construct_edit` returning `valid_under_assay_v3: true` means only
  that a supplied pair is legal under the recorded design space. It is not a
  recommendation, not a prediction, and not evidence that an edit helps.
- No floor is selected or frozen. No sequence may be scored until the transcript
  inputs in `configs/assay_definition_v3_2026-10-19.json` are supplied.
- The T-cell arm carries no translation-side model score, and none may be
  inferred from the A549 arm.
- The RiboNN A549 per-task accuracy still rests on the unconfirmed assumption
  that the released prediction table holds out-of-fold predictions.
