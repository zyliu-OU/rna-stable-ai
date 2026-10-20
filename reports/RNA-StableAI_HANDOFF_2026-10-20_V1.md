# RNA-StableAI — Handoff 2026-10-20 V1

- **Project:** RNA-StableAI
- **Date:** 2026-10-20 (America/Los_Angeles)
- **Version:** V1 (first handoff of this date; previous was
  [2026-10-19 V16](RNA-StableAI_HANDOFF_2026-10-19_V16.md))
- **Workspace:** `/home/zyliu/Documents/rna-stable-ai`
- **Publication clone:** `/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad/verify`
- **Remote:** `https://github.com/zyliu-OU/rna-stable-ai.git` — **PUBLIC**
- **Headline:** the learned pair model was **retired**, and the Stage 2 gate was then
  **reviewed and closed at 6 of 6** in
  [`configs/stage2_to_stage3_gate_v5_2026-10-20.json`](../configs/stage2_to_stage3_gate_v5_2026-10-20.json).
  **Two of the six are satisfied by accepting a documented limitation, not by improving
  the data.** `stage3_ready` is true; candidate design, new-sequence scoring and the
  assay remain disabled.

---

## 1. Current user priorities and decisions that supersede earlier handoffs

| Decision | Instruction | Consequence |
|---|---|---|
| Retire the learned pair model | "also remove our old trained model, it was done in codex, later I found its bad compare to LinearFold / ViennaRNA, now we just use LinearFold / ViennaRNA result as input for next step" | Checkpoints deleted. Architecture is fixed as **LinearFold / ViennaRNA → STRAND + RiboNN + BoTorch**. Supersedes every earlier handoff that treats the learned model as the structure component. |
| Redo whatever the deletion broke | "after remove the old trained model, if need any redo test, just do it"; "if retired model removed and need ViennaRNA / LinearFold to redo it , then redo it" | Authorised the native-control validation, the band expansion and the requirement 5 re-scope. |
| Amend requirement 4 | "amend requirement 4 to reference native controls" | Gate v4. |
| Finish Stage 2 today | "we have to finish the stage 2 today, is it possbile? you dont need to develop any new models right? just validate this RNAfold + STRAND + RiboNN + BoTorch combination I guess?" | Correct — **no new model was developed.** Everything below is folding, scoring against frozen references, and gate bookkeeping. |
| Close the gate as proposed | "sure", approving: ratify 2, 4 and 6; re-scope 5 to the native path; accept requirement 1's cohort limitation | Gate v5. |
| Publish everything | "push everything" (2026-10-19) | Standing clearance, treated as informed: the repo is **public** and carries Ping's unpublished Fluc/Fluc-PEST ORFs, IVT conditions and the cap supplier part number. |
| Preserve the README picture | AGENTS.md | `diagram_10182026.png` is byte-unchanged at `baa831ce16df27ed44a41c2a3b481455a213b328122227b9b2a3820dda47cff1`. Verified again before this publication. |

### Scope boundaries, unchanged

- **Active length scope:** 1–2,999 nt. Work at ≥3,000 nt is deferred, not deleted.
- **Claimable without caveat:** 1–1,999 nt only. The 2,000–2,999 nt band may be claimed
  **only** with the v3 limitation attached.
- **No composite score.** The two score sides are incommensurable; `score_record_schema_v1`
  forbids combining them and the one record carrying both sides emits none.
- **Permitted claims** are correlation or ranking, explicitly labelled. No stability,
  translation or expression benefit is established by anything in this handoff.

---

## 2. What was done today, with exact paths

### 2.1 Learned pair model retired

Decided on the evidence in
[`reports/structure_model_gap_diagnosis_2026-10-20.md`](structure_model_gap_diagnosis_2026-10-20.md)
(`sha256 b4cc597815d95f344d36906805072ebfac82a9242f8364a3aa36bf00df8ad409`):

| Cohort | Learned best | LinearFold | ViennaRNA | Learned as fraction of native |
|---|---|---|---|---|
| long Rfam consensus | 0.2965 | 0.4381 | 0.4215 | 0.677 |
| structure-derived | 0.3255 (helix head) | 0.6261 | 0.6261 | 0.52 |

Loss attribution: **56.6 %** of missed gold pairs lost at **score selection**, not at
thresholding — the predicted-to-reference pair-count ratio is 1.056 with precision 0.311
beside recall 0.325. Training scale: **61 records, 1,235 positive pairs against 216,942
negatives.**

- **Deleted:** 886 checkpoint files (`.pt`/`.pth`), ~90 MB, of which **97 were tracked in
  git** and remain recoverable from history. The other **789 are gone.**
- **Explicitly excluded from deletion:** RiboNN's 180 released weights, and everything
  under `external/`.
- **Retained:** every run summary, metric and F1 figure, and the model source code.
- **Test consequence:** 38 replay tests reload those checkpoints and can no longer run.
  They were **not** deleted. [`tests/conftest.py`](../tests/conftest.py) converts the
  resulting `FileNotFoundError` into a skip with an explicit retirement reason, and only
  when the missing path ends in `.pt`/`.pth`, resolves under `results/`, and does **not**
  contain `ribonn` (so a missing third-party weight still fails).

### 2.2 Gate v4 — requirement 4 amended

[`configs/stage2_to_stage3_gate_v4_2026-10-20.json`](../configs/stage2_to_stage3_gate_v4_2026-10-20.json)
(`sha256 1beeb67371fc0336a218387006d6770a56ec1ee6380cd8b19ea337862fa4f7f6`), tested by
[`tests/test_stage2_gate_v4.py`](../tests/test_stage2_gate_v4.py) (16 tests). It retains
v3 unedited at its recorded hash, changes **only** requirement 4, keeps
`requirements_satisfied` at 1, and carries an explicit `DOES_NOT_SATISFY_ITSELF` clause.

One correction made during the day: v4 originally said the model would be "retained… not
deleted", which the user's later instruction contradicted. `learned_model_status.disposition`
was corrected to `RETIRED…` and the corresponding test updated. **Corrected before
publication**, so no published version carried the wrong text.

### 2.3 Requirement 2 and 4 evidence — native-control validation

- Script: [`scripts/validate_native_controls_stage2.py`](../scripts/validate_native_controls_stage2.py)
- Artifact: `results/native_control_validation/native_control_validation.json`
  (`sha256 2e5aa6082f7789566493c240bb4749dc73f5f0af4c72e1c74e6b3b68e35e5d48`)
- Tests: [`tests/test_native_control_validation.py`](../tests/test_native_control_validation.py) (12)

**No new inference was performed.** Every number is scored from predictions already frozen
in earlier runs. Sources:

| Role | Path |
|---|---|
| long rows | `results/long_native_controls_runs/20261017T034318.804594Z/rows.json` |
| short predictions | `results/bprna_five_clan_feasibility_evaluation_runs/20261017T191445.852927Z/` |
| short references | `results/bprna_five_clan_reference_screen_runs/20261017T191404.643416Z/references.json` |
| structure-derived | `results/raw_structure_feasibility_runs/20261015T025936.192087Z/summary.json` |
| clan mapping | `results/band_clan_availability_runs/20261019T185713.116447Z/summary.json` + census |

Results (mean pair F1):

| Cohort | n | LinearFold record / family / clan | ViennaRNA record / family / clan | fam, clan |
|---|---|---|---|---|
| long Rfam consensus (in scope) | 6 | 0.4381 / 0.4350 / 0.4574 | 0.4215 / 0.4136 / 0.4339 | 3, 2 |
| short bpRNA five-clan | 13 | 0.3301 / 0.3726 / 0.3726 | 0.3346 / 0.3816 / 0.3816 | 5, 5 |
| structure-derived feasibility | 10 | 0.6261 | 0.6261 | 6 families |

Family and clan means are reported **beside** the record mean, because a record mean on
cohorts this small is dominated by whichever family contributes most records.

A defect found and fixed during this work: `family_to_clan()` initially resolved only 1
clan where the gate records 2. It now also infers from census bands that resolve to
exactly one clan, and **declines to assign** where a band resolves to more than one rather
than guessing.

### 2.4 Requirement 3 — the 2,000–2,999 nt band expanded 1 → 5

- Script: [`scripts/expand_band_native_controls.py`](../scripts/expand_band_native_controls.py)
- Artifact: `results/band_native_control_runs/20261020T162419.296842Z/summary.json`
  (`sha256 e2473cf7feba9e8c6d3a5b5a082c716aa1f0647862996cc870bbc46814a587ac`)
- Earlier run of the same script, retained: `results/band_native_control_runs/20261020T145441.999923Z/`
  (identical figures; re-run only to correct two text fields — see §5)
- Tests: [`tests/test_band_native_controls.py`](../tests/test_band_native_controls.py) (8)

Rationale: the per-family cap that held the band at one record existed to bound how much
data a **learned model** could be trained and evaluated on. The thermodynamic folders have
no training set, so evaluating them on more references is **folding, not fitting**.

| Method | n | mean pair F1 | stdev | min | max |
|---|---|---|---|---|---|
| LinearFold | 5 | 0.5273 | 0.0805 | 0.3945 | 0.6034 |
| ViennaRNA | 5 | 0.5056 | 0.1116 | 0.3086 | 0.5863 |

Records (all RF02540, extracted from `results/rfam_release_15_1_clan_source/Rfam.seed.gz`):
`AE000666.1/1604009-1607048`, `CP001688.1/618088-615166` (2,923 nt),
`CP001719.1/762872-765862` (2,991 nt), `CP002278.1/26764-23775` (2,990 nt),
`CR937012.1/19041-21972` (2,932 nt). Zero fold failures across 10 folds.

- **The frozen selection was not modified** (`frozen_selection_modified: false`). This runs
  beside it as a separately named cohort.
- **All five are RF02540**, so the cohort carries dispersion but **no family contrast of
  its own**. With the frozen RF02541 record the band spans two families in one clan. No
  clan contrast within the band exists.

### 2.5 Requirement 5 re-scoped onto the native path, and satisfied there

- Script: [`scripts/verify_native_path_requirement5.py`](../scripts/verify_native_path_requirement5.py)
- New worker: [`src/rnastable/vienna_constraint_worker.py`](../src/rnastable/vienna_constraint_worker.py)
- Artifact: `results/native_path_requirement5_runs/20261020T162226.011664Z/summary.json`
  (`sha256 a13c44be79a2394bc9ac12978b15bb8a45d5eaa6f529bc67fb5dc90e1d41a6d5`)
- Tests: [`tests/test_native_path_requirement5.py`](../tests/test_native_path_requirement5.py) (11)

**Why re-scoped.** The replay leg meant reloading learned-model checkpoints, e.g.
`results/sampled_long_development_runs/20261017T034847.147062Z/control_88_seed7/final_model.pt`,
which no longer exist. The leg is permanently unrunnable as written, and nothing in the
production path loads them. **The learned-model leg is not restored and has no artifact to
replay.** Requirement 5 must not be read as satisfied on its original terms.

Protocol: cohort `results/long_validation_coverage_runs/20261017T033935.363253Z/selection.json`
(11 records, hash-gated by the evaluator's own `inputs()` check), methods LinearFold and
ViennaRNA, config `{temperature_c: 37, beam_size: 100, timeout_seconds: 30,
memory_limit_gib: 4}` imported from `scripts/evaluate_long_native_controls.py` rather than
restated.

| Leg | Criterion | Result |
|---|---|---|
| replay | dot-bracket structure **and** MFE identical to the frozen row | **22/22 exact** |
| constraint decoder | every enforced reference pair present in the returned structure, ≤20 pairs per record, same time/memory bounds | **22/22 honoured** |
| refusal control | a pair below the minimum hairpin size must be refused, not dropped while a fold is reported | **both tools refuse** |
| resource | within the frozen limits of 30 s and 4 GiB | **max 8.18 s, 101.5 MiB** |

Measured resources (unconstrained folds, this machine only):

| Method | band | n | max wall | max peak RSS |
|---|---|---|---|---|
| LinearFold | 1,000–1,999 | 5 | 0.67 s | 50.7 MiB |
| LinearFold | 2,000–2,999 | 1 | 1.32 s | 97.2 MiB |
| LinearFold | ≥3,000 (out of scope) | 5 | 1.37 s | 101.5 MiB |
| ViennaRNA | 1,000–1,999 | 5 | 1.77 s | 36.6 MiB |
| ViennaRNA | 2,000–2,999 | 1 | 7.08 s | 68.9 MiB |
| ViennaRNA | ≥3,000 (out of scope) | 5 | 8.18 s | 73.5 MiB |

Constrained folds: max 5.62 s (ViennaRNA). The `out_of_band` rows are why the in-scope
cohort is **6** records while the frozen cohort holds 11 — the other five are ≥3,000 nt.

### 2.6 Requirement 6 — limitations documented

- [`reports/remaining_limitations_before_candidate_design_2026-10-19.md`](remaining_limitations_before_candidate_design_2026-10-19.md)
  (`sha256 f007b1cb8250f805e417ae67fb72e7968654f9acdbfe17952e56602766329282`) — **unedited,
  stands in full.**
- [`reports/remaining_limitations_addendum_2026-10-20.md`](remaining_limitations_addendum_2026-10-20.md)
  (`sha256 8562652a87039d2545da90012d41ecc074541be2818d05953348ba832d374bc1`) — extends it,
  sections N1–N8.

### 2.7 Gate v5 — the gate review

[`configs/stage2_to_stage3_gate_v5_2026-10-20.json`](../configs/stage2_to_stage3_gate_v5_2026-10-20.json),
tested by [`tests/test_stage2_gate_v5.py`](../tests/test_stage2_gate_v5.py) (20 tests).

| # | Requirement | Basis |
|---:|---|---|
| 1 | Frozen independent sequence/family/clan-separated validation | **accepted as documented limitation** |
| 2 | Accuracy and failures by band and family against native controls | satisfied on evidence |
| 3 | Resolve sparse 2,000–2,999 nt coverage | **accepted as documented limitation** (v3), expanded |
| 4 | Credible accuracy from the relied-upon native controls | satisfied on evidence |
| 5 | Constraint-decoder, resource and replay checks **on the native path** | satisfied on evidence, after re-scoping |
| 6 | Document remaining limitations | satisfied on evidence |

`requirements_satisfied: 6`, `stage3_ready: true`. Requirement 5's text is the **only** one
changed from v4. Every evidence hash is recorded in the gate and re-verified by the tests,
and the tests also check that the gate's quoted figures match their source artifacts to 4
decimal places, so a paraphrase cannot drift.

**Deliberately left false:** `stage3_development_started`, `new_sequence_scoring_enabled`,
`expression_candidate_design_enabled`, `model_defaults_changed`,
`expression_benefit_established`. Opening the gate did not open these; each is its own
decision, and the gate records what each needs.

---

## 3. Verification actually run

| Check | Command | Outcome |
|---|---|---|
| requirement 5, smoke | `.venv/bin/python scripts/verify_native_path_requirement5.py --limit 2 --dry-run` | 4/4 replay, 4/4 constraints, both refusals |
| requirement 5, full | `.venv/bin/python scripts/verify_native_path_requirement5.py` | exit 0; 22/22, 22/22, both refusals |
| band expansion | `.venv/bin/python scripts/expand_band_native_controls.py` | exit 0; 5 records, figures identical to the earlier run |
| gate v5 tests | `.venv/bin/python -m pytest tests/test_stage2_gate_v5.py -q` | 20 passed |
| requirement 5 tests | `.venv/bin/python -m pytest tests/test_native_path_requirement5.py -q` | 11 passed |
| band tests | `.venv/bin/python -m pytest tests/test_band_native_controls.py -q` | 8 passed |
| lint | `ruff check` on all six new/changed files | All checks passed |
| full suite | `.venv/bin/python -m pytest -q` | **see §3.1** |

Runtime: Python 3.12.14, ViennaRNA python bindings 2.7.2, torch 2.14.1+cu130. **`botorch`
is not installed**; `tests/test_discrete_bo.py` skips. `ruff` resolves to
`/home/zyliu/anaconda3/bin/ruff`, not the venv.

### 3.1 Full suite

`1303 passed, 39 skipped` in 133.79 s (0 failed). The 39 skips are the retired-checkpoint replay tests
(38) plus `tests/test_discrete_bo.py`. The pass count rose from 1,264 by the 39 tests added
today (20 + 11 + 8).

### 3.2 Not verified / not claimed

- **No deterministic retraining was run**, because no model is trained any more.
- Resource figures are from **this machine and this cohort only**.
- Reproducing a frozen fold is **determinism, not accuracy**.
- Honouring a constraint is **decoder correctness, not structural correctness** — a
  constrained fold is no evidence that the constrained pairs are real.
- The retired model's development runs **cannot be reproduced from the tree**.

---

## 4. Scientific interpretation

**What closing the gate does and does not mean.** Six of six satisfied means the gate's
conditions, as written and as twice amended, are met and the limitations are recorded and
binding. It does **not** mean the structure evidence is strong. Two of the six are
satisfied by narrowing what may be claimed.

**The accuracy level matters downstream.** 0.42–0.44 pair F1 against computational
consensus is unremarkable for a published thermodynamic folder, and that is the point: the
architecture is `LinearFold / ViennaRNA → STRAND + RiboNN + BoTorch`, so this is the
quality of the **input** to the STRAND calibration and the optimiser. Structure-derived
features carry this error forward, and **no component downstream estimates or propagates
it**. Band accuracy is higher (0.51–0.53) than the in-scope mean, which is a property of
RF02540's references rather than evidence that longer sequences fold better.

**Separation is satisfied by construction, and that argument is narrow.** Both tools are
Turner-model thermodynamic folders whose parameters come from published optical-melting
measurements, not from these references, so there is no exposure to separate from. That
applies **only** to these two tools. It would not apply to any learned component, including
a future replacement for the retired model, and it is not a claim that the cohorts are
large, diverse or representative.

**Requirement 1 is a data problem.** Retiring the learned model removed the exposure
concern and nothing else. Six in-scope records across three families and two clans, every
one a computational Rfam consensus, with no experimental-structure reference in scope at
all and none for the band. No run can close that.

---

## 5. Errors, corrections and rejected approaches, today

1. **Gate v4 contradicted the user's deletion instruction** ("retained… not deleted").
   Corrected to `RETIRED` before publication, with the test updated.
2. **Deleting checkpoints broke 38 replay tests.** Surfaced to the user *before* acting by
   staging the files aside reversibly, restoring them, and reporting. After authorisation:
   deleted, and a **narrow** `conftest.py` guard added rather than deleting the tests, so
   the runs stay re-verifiable if the weights are ever restored from history.
3. **Census eligibility was overstated, and I repeated it.** I told the user ~56 band
   records were available; gate v3 records `"available: 56 eligible records locally"`.
   Selection checks the fixed family cap **before** attempting `bind_pair_reference`, so
   those records were never binding-tested. **Only 5 of the 55 bind**; the other 50 fail
   with `Missing annotated paired column; incomplete`. v3 is frozen and **not edited**; the
   correction is recorded in gate v5 (`requirement_3_resolution.correction_to_v3`) and in
   the addendum §N4.
4. **ViennaRNA silently drops an unsatisfiable hard constraint.** Found while building the
   decoder check. With `CONSTRAINT_DB_DEFAULT | CONSTRAINT_DB_ENFORCE_BP`, an enforced pair
   violating the minimum hairpin size — constraint `(.)` on `GGGAAACCCUUU` — is dropped,
   the fold proceeds without it, and a finite energy is returned (`(((...)))...`, −2.40
   kcal/mol). Nothing is raised. `vienna_constraint_worker.py` therefore verifies every
   enforced pair against the returned structure and exits non-zero. **Any other code path
   calling `hc_add_from_db` directly lacks that protection**; none currently does.
5. **The two tools' constraint conventions are not interchangeable.** ViennaRNA treats `.`
   as unconstrained; LinearFold treats `.` as forced-unpaired and `?` as unconstrained.
   Using one convention with the other silently changes the question. Each string is built
   with its own filler, pinned by a test.
6. **LinearFold's refusal is not a diagnostic.** On the same unsatisfiable input it emits
   no parseable structure at all. That is a refusal in effect, recorded as
   `status: parse_error`, but a caller must treat an unparseable LinearFold output as a
   possible constraint refusal rather than a tool failure.
7. **Re-ran the band expansion rather than editing its artifact.** The first run's
   `no_claim` said "two families in one clan", which is wrong for a cohort that is all
   RF02540. The script text was fixed, `census_eligibility_correction` added, and the
   script re-run to a new timestamped directory. Figures are identical, which also
   demonstrates determinism. The earlier run is retained.

**Rejected:** deleting the 38 broken replay tests; editing frozen gate v3 to fix its
availability figure; recomputing both sides of the replay comparison (which would have made
that leg unfalsifiable); and inferring a clan for census bands resolving to more than one
clan.

---

## 6. Outstanding work, prioritised

1. **Decide whether requirement 1's acceptance stands.** It is recorded in v5 on the
   user's approval. If the user would rather leave it open, **supersede with v6 — do not
   edit v5.**
2. **Install `botorch`.** The final stage of the stated architecture has never run
   end-to-end against a real candidate set. `tests/test_discrete_bo.py` skips.
3. **Unblock the assay side.** Still missing, and none of it is derivable here: measured
   CVs for both readouts; the decision cost of a false accept against a false reject;
   whether Fluc-PEST enters the panel.
4. **Resolve the power convention** (`lognormal_exact` vs `log1p_cv`) → either
   `assay_definition_v4` or an explicit decision to keep v3.
5. **Base-pair span policy** — investigation closed unresolved; unlimited span agrees best
   with LinearPartition, and the incompatibility localises to `alo`, which moves ~3×
   tolerance from the clipping convention alone. The blinded **85-record evaluation set is
   unspent** and should stay that way until the policy is decided.
6. **Ask Ping** whether the 5′UTR shortening relative to mRNA-1273 is deliberate (38 nt
   shared prefix; omits `GGG` and an internal `CCCCGGCGCC`), and whether the parent is the
   GenScript F-Luc + alpha-globin mRNAutilus baseline.
7. **Acquire experimental-structure references in scope** — the only proper cure for
   requirement 1, and for the band.
8. Carried from V12 §6 item 7: re-run the `archive` build.

**No process is running.** Nothing was left partially written; every run below completed
with exit 0 and wrote a complete `summary.json`.

---

## 7. Exact safe continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai

# Full suite (long; expect 1,303 passed, 39 skipped)
.venv/bin/python -m pytest -q

# Just today's gate review and its evidence
.venv/bin/python -m pytest -q \
  tests/test_stage2_gate_v5.py \
  tests/test_stage2_gate_v4.py \
  tests/test_native_path_requirement5.py \
  tests/test_native_control_validation.py \
  tests/test_band_native_controls.py

# Re-verify the native path without writing anything
.venv/bin/python scripts/verify_native_path_requirement5.py --dry-run

# Re-verify the band without writing anything
.venv/bin/python scripts/expand_band_native_controls.py --dry-run

# Smoke versions, seconds rather than minutes
.venv/bin/python scripts/verify_native_path_requirement5.py --limit 2 --dry-run
.venv/bin/python scripts/expand_band_native_controls.py --limit 2 --dry-run

# Lint (ruff is NOT in the venv)
ruff check src/rnastable scripts tests
```

Re-running either script **without** `--dry-run` writes a **new** timestamped directory and
never overwrites an existing one (`mkdir(exist_ok=False)`).
`scripts/validate_native_controls_stage2.py` refuses outright if its artifact already
exists, so re-running it requires removing
`results/native_control_validation/native_control_validation.json` deliberately.

### Publishing

```bash
PUB=/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad/verify
git -C "$PUB" fetch origin && git -C "$PUB" status --short
sha256sum "$PUB/diagram_10182026.png"   # must stay baa831ce16df27ed…
diff "$PUB/README.md" README.md          # merge upstream edits before copying
```

The local `/home/zyliu/Documents/rna-stable-ai` repository **has no commits** and its
`origin` is the placeholder `https://github.com/YOUR_USERNAME/RNA-StableAI.git`. Publication
goes through the clone above. Other clones exist in the scratchpad at earlier commits
(`pub`, `check`, `final`, `final2`, `f3`); `verify` is the one tracking `origin/main`.

---

## 8. Published state

| Item | Value |
|---|---|
| Commit before today's gate review | `9ed3fdf` Validate the native controls and expand the 2000-2999 nt band |
| Commit published with this handoff | `dec1397` |
| README picture | `diagram_10182026.png`, `sha256 baa831ce16df27ed44a41c2a3b481455a213b328122227b9b2a3820dda47cff1`, byte-unchanged |
| README diagram | `workflow_10192026.svg` (the superseded `diagram_10192026.svg` was removed on user instruction) |
| Disclosed by the public repo | Ping's unpublished Fluc and Fluc-PEST ORFs, IVT conditions, cap supplier part number (Hongene ON-134), under the user's "push everything" |

The README's diagram alt text still describes the gate as "0 of 6", because the SVG itself
says so and was not regenerated. A caption immediately below the picture records that the
diagram predates the v5 review and links the gate. **Regenerating the SVG is a candidate
next step; the picture itself must not be touched.**

### 8.1 Publication record

`dec1397` — Close the Stage 2 gate: ratify requirements 2, 4 and 6, re-scope 5 onto the
native path, accept requirement 1's cohort limitation. The hash is recorded by the commit
immediately after it, since a file cannot contain the hash of the commit that adds it.

One incidental fix went out with it. `tests/test_stage2_gate_v4.py::test_every_cited_evidence_path_exists`
**failed from a fresh clone**, because two artifacts gate v4 cites were never bundled into
the public snapshot: `results/stage2_under3000_audit_runs/20261018T223708.786045Z/summary.json`
and `results/under3000_recovery_ceiling_runs/20261018T234344.201186Z/summary.json`. Both are
now published, and the published v4 and v5 gate tests pass from the clone (36 passed). This
was pre-existing, introduced with v4 in commit `9ed3fdf`; it is recorded here rather than
fixed silently.
