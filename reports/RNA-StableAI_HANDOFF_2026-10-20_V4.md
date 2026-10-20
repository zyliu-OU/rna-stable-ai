# RNA-StableAI — Handoff 2026-10-20 V4

- **Project:** RNA-StableAI
- **Date:** 2026-10-20 (America/Los_Angeles)
- **Version:** V4 (follows [V1](RNA-StableAI_HANDOFF_2026-10-20_V1.md) the gate review,
  [V2](RNA-StableAI_HANDOFF_2026-10-20_V2.md) BoTorch and the Pareto formulation, and
  [V3](RNA-StableAI_HANDOFF_2026-10-20_V3.md) the design space; all three stand unedited)
- **Workspace:** `/home/zyliu/Documents/rna-stable-ai`
- **Publication clone:** `/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad/verify`
- **Remote:** `https://github.com/zyliu-OU/rna-stable-ai.git` — **PUBLIC**
- **Headline:** the **whole workflow now runs end to end**, twice, on 512 synonymous
  variants each. **Gate v6** records the decision to build before the validating data
  exists. The window widened 30 → 50 codons and the measured result is **mixed**: the
  stability spread grew sub-linearly (1.21× for 1.67× the sequence) and the translation
  spread **did not grow at all** (0.94×). **The window is not the lever.**

---

## 1. User instructions in this stretch

| Instruction | Reading | Consequence |
|---|---|---|
| "currently I dont have experimental data, maybe just build the whole workflow, later we can verify and improve it?" | Build the full pipeline on predictions now; verify later. This **opens two gate switches**. | Gate v6; the variant assembly path; the workflow driver; one 512-member run. |
| "wider window then, 50 codons" | Widen the design window in response to the measured flatness. | Design-space v2; a second 512-member run. |
| "run both and compare the spreads" | Measure the widening rather than assume it. | The comparison script, artifact and verdict. |

**What was opened, stated plainly.** `new_sequence_scoring_enabled` and
`expression_candidate_design_enabled` moved **false → true**. I did not flip them quietly:
`configs/stage2_to_stage3_gate_v6_2026-10-20.json` records the authority, the reason, the
binding conditions and what still must not be claimed. v5 stays frozen at
`sha256 175046a34e94a1c7…`, its six-requirement basis is carried forward **verbatim**, and
both accepted limitations survive as accepted limitations.

**What was deliberately not done.** The blinded 85-record evaluation set is **unspent**, and
gate v6 states it must not be spent to unblock this workflow. The base-pair span policy is
**still unresolved**; the workflow reuses the frozen reference record's folding settings for
comparability, recorded as a **provisional convention, not a resolution**.

---

## 2. Gate v6

`configs/stage2_to_stage3_gate_v6_2026-10-20.json`, tested by `tests/test_stage2_gate_v6.py`
(14 tests).

- Supersedes v5, retained unedited at its recorded hash. Chain names v5, v4, v3, v2 and the
  original; all frozen.
- `requirements_before_stage3` and `requirements_satisfied: 6` **identical to v5**. v6
  re-opens no requirement and re-ratifies none.
- `stage3_development_started` moves to **true**; `expression_benefit_established`,
  `model_defaults_changed`, `stability_score_calibrated_to_the_assay` and
  `independent_biological_validation` stay **false**.
- Labels the decision as engineering, not evidence: *"BEFORE the data that would validate it
  exists"*, *"not a finding that the pipeline's outputs are correct"*, *"does not lower any
  evidential standard"*.
- `what_remains_absent` opens with *"Any experimental measurement of any construct in this
  project. There is none, and the user has stated so."*
- `how_to_verify_this_later` requires reporting the comparison **whichever way it comes
  out**, including the case where the predicted front is uninformative.

---

## 3. The variant assembly path

`src/rnastable/transcript_assembly.py::assemble_variant`, tested by
`tests/test_transcript_assembly_variant.py` (15 tests).

`assemble` hash-gates the CDS and therefore refuses a designed variant **by design**. That
gate was **not relaxed**. The new path is **stricter**:

1. the reference is read from the config's recorded `sequence_file` and still verified
   against `sha256_dna_uppercase`;
2. the supplied variant must then prove it is a synonymous variant of **that exact
   sequence** — same length, same translated protein, valid reading frame;
3. both hashes, the substituted codon indices and the protein hash are recorded, so a
   variant can never be mistaken for the reference in an artifact, or the reverse.

The strongest consistency check available without a measurement: **passing the reference
itself through the variant path reproduces the reference assembly byte for byte**
(`transcript_sha256_rna` identical, `substituted_codon_indices == ()`).

A deliberate non-feature: a synonymous change **outside** the window is still accepted. The
assembler's job is synonymy; enforcing which positions a generator may touch is the design
space's job. Conflating them would let a future generator bug pass silently.

`AssemblyReport` gained five optional fields, `None` on a reference assembly:
`variant_of`, `reference_cds_sha256_dna_uppercase`, `synonymous_verified`,
`substituted_codon_indices`, `protein_sha256`. The existing 57 assembly tests pass unchanged.

---

## 4. The workflow

`scripts/run_design_workflow.py`, tested by `tests/test_design_workflow_run.py` (20 tests).

| Stage | What runs |
|---|---|
| 1 pool | `build_pool`, windowed synonymous variants, GC-neutral |
| 2 assemble | `assemble_variant`; refuses to continue unless all members share one length and one protein hash |
| 3 fold | ViennaRNA ensemble via the isolated worker, `ProcessPoolExecutor`, 24 jobs |
| 4 stability | `strand_rnafold_calibration_v1`, `without_alo` arm, extrapolation flagged per member |
| 5 translation | the existing RiboNN driver, 50 checkpoints, `predicted_TE_A549` |
| 6 select | Pareto front, then `get_hypervolume_maximizing_subset` for the panel |
| 7 bo replay | sequential qLogNEHVI over the pool with the precomputed objectives as oracle, against random at equal budget |

Features come from the worker's own `feature_candidates`, so the energy hypothesis stays the
`ensemble_energy_per_nt` the frozen agreement criterion selected, and `GC` is
**whole-transcript GC in percent**, the form the calibration was fitted on.

### 4.1 RiboNN driver extension

`scripts/run_ribonn_fixed_inference.py` gained `design_pool_records()` beside
`reference_records()`. Its guard previously refused any run with `candidate_design_enabled`
or `stage3_ready` set. It now **checks the authority rather than the flag**: the config must
name an `authorizing_gate`, and that gate must itself record the switch as open, so **a
config cannot grant itself permission**. `summary.json` reports the real flag values instead
of hardcoded `false`. The 31 existing RiboNN tests pass unchanged.

### 4.2 Guards in the driver

- refuses to start unless gate v6 records **both** switches open;
- refuses to continue if assembled variants differ in length or protein;
- refuses if any member fails synonymy verification or its pool hash disagrees.

---

## 5. Results — two matched 512-member runs

Matched on GC mode, pool size, seed, transcript length, folding settings, calibration run
and RiboNN checkpoints. The **only** deliberate difference is the window width, and hence
the number of substitutable positions.

| | 30 codons | 50 codons |
|---|---|---|
| run | `results/design_workflow_runs/20261020T174606.887363Z` | `results/design_workflow_runs/20261020T181317.731918Z` |
| design space | `…v1_2026-10-20.json` | `…v2_2026-10-20.json` |
| window | 90 nt, 5.0% of transcript | 150 nt, 8.3% |
| substitutable positions | 13 | 24 |
| folds ok | **512/512** | **512/512** |
| mean fold | 32.95 s | 34.77 s |
| extrapolating | 512/512 (GC) | 512/512 (GC) |
| half-life | 1.3070–1.3414 h | 1.3096–1.3512 h |
| half-life stdev | 0.00582 | 0.00702 |
| half-life IQR | 0.00803 | 0.01010 |
| half-life range as % of the 1.310 h training range | **2.62%** | **3.18%** |
| TE | 0.7756–0.8446 | 0.7863–0.8516 |
| TE stdev | 0.01206 | **0.01137** |
| Pareto front | 10 of 512 | 6 of 512 |
| RiboNN run | `…/20261020T175803.350148Z` | `…/20261020T182555.022132Z` |

Panels (hypervolume-maximising subsets, placeholder size 12, capped by the front):
30 codons `[200, 354, 294, 220, 465, 444, 238, 126, 183, 439]`;
50 codons `[300, 267, 400, 96, 5, 484]`.

### 5.1 The comparison

`scripts/compare_window_width_spreads.py` →
`results/window_width_comparison_runs/20261020T184036.680844Z/summary.json`, tested by
`tests/test_window_width_comparison.py` (13 tests).

| ratio wide/narrow | value |
|---|---|
| window nt | 1.67× |
| substitutable positions | 1.85× |
| half-life range | 1.21× |
| half-life stdev | **1.21×** |
| half-life IQR | 1.26× |
| TE range | **0.95×** |
| TE stdev | **0.94×** |
| feature `energy_per_length` stdev | 1.20× |
| feature `aup` stdev | 1.16× |
| feature `GC` stdev | undefined, **0 in both** |

`expectation_held: true`, computed from the stdev ratio rather than asserted; a test pins
that the flag cannot disagree with the numbers.

**GC stdev is exactly 0 in both runs**, which confirms the GC-neutral mode does what it
claims and localises all half-life movement to `energy_per_length` and `aup`.

---

## 6. Scientific interpretation

**The window is not the lever.** Widening it 1.67× bought 1.21× the stability spread and
**nothing** on the translation side. Fitting a power law to the two points gives
spread ∝ window^0.372. On that scaling:

- editing the **entire 551-codon ORF** would reach only about **7.8%** of the calibration's
  training target range;
- spanning half that range would need roughly **1,600×** the current window — far more
  sequence than the gene contains.

**Two points do not establish an exponent**, so treat that as an indication rather than a
result. A whole-ORF window run would turn it into a measurement; it has **not** been run.

**The diagnosis stands.** The design space is **local**; every calibration feature is a
**transcript-wide mean**. 150 nt of 1,811 cannot move a mean far. The remedy is
**region-local features** — unpaired probability over the window itself rather than `aup`
averaged across the whole transcript — which changes what the objective can *see*. That is
recorded as open in design-space v2 and was **not** quietly substituted.

**One result that does hold up.** The BO replay worked at both widths: at a budget of 32 of
512, qLogNEHVI recovered **5 of 10** front members at 30 codons and **5 of 6** at 50,
against random finding **1** in both, reaching 91% and 80% of the exhaustive hypervolume.
That is the first evidence in this project that the optimizer buys anything. Its scope is
narrow: the oracle was the precomputed predictions, so it measures **search efficiency over
a known landscape**, not that the landscape is right.

**The translation side did not respond at all.** RiboNN's spread fell slightly. No
explanation is offered here; it was not investigated, and guessing would be worse than
saying so.

---

## 7. Verification actually run

| Check | Outcome |
|---|---|
| `run_design_workflow.py --size 8 --skip-ribonn` | 8/8 folds, 8 stability predictions |
| `run_design_workflow.py --size 8 --panel 3 --bo-budget 5` | full pipeline, exit 0 |
| `run_design_workflow.py --size 512 --jobs 24 --panel 12 --bo-budget 32` (30 codons) | exit 0 |
| `run_design_workflow.py --size 512 --jobs 24 --panel 12 --bo-budget 32` (50 codons) | exit 0 |
| `compare_window_width_spreads.py` | exit 0; verdict computed |
| `pytest tests/test_stage2_gate_v6.py` | 14 passed |
| `pytest tests/test_transcript_assembly_variant.py` | 15 passed |
| `pytest tests/test_design_workflow_run.py` | 20 passed |
| `pytest tests/test_design_space_v2.py` | 11 passed |
| `pytest tests/test_window_width_comparison.py` | 13 passed |
| `pytest tests/test_transcript_assembly.py` (existing) | 57 passed, unchanged |
| `pytest tests/ -k ribonn` (existing) | 31 passed, unchanged |
| `ruff check` on the six new/changed files I wrote | All checks passed |
| **Full suite** | **1467 passed, 38 skipped** in 136.17 s |

Suite arithmetic: 1394 (V3) → 1467 with 73 added (14 + 15 + 20 + 11 + 13). The 38 skips are
unchanged retired-checkpoint replays.

**A correction to an earlier claim of mine.** `ruff check src/rnastable scripts tests` reports
**2,882 pre-existing errors** under ruff's default rules, because the project has no ruff
configuration. Every "ruff clean" in this and earlier handoffs means **the specific files I
wrote**, not the repository. `scripts/run_ribonn_fixed_inference.py` carries 23 pre-existing
style errors in its compressed style; my additions to it introduce none.

### Not verified / not claimed

- **No molecule in this project has been measured.** Every value is a prediction from an
  unvalidated model on a quantity the planned assay does not measure.
- A **wider spread of predictions is not evidence the predictions are right**, and a spread
  is not an effect.
- The panels are **illustrations of the pipeline**, not recommendations to synthesise or
  assay anything, and are not known to beat the reference.
- The panel size 12 is a **declared placeholder**; the assay's capacity is unknown, and the
  front was smaller than 12 in both runs so both panels are front-sized.
- The reference points are declared from each pool's own minima and are comparable **within
  a run only**.
- The whole-ORF extrapolation in §6 is a **two-point fit**, not a measurement.

---

## 8. Known limitations introduced here

1. **The design feature representation includes constant coordinates.** It uses all window
   positions (30 or 50), but in GC-neutral mode only 13 or 24 can ever be non-zero, so the
   remainder are constant zero in the GP input. Correctness is unaffected; it slightly
   dilutes length-scale fitting. Fixing it means re-running both 512-member runs, about an
   hour, and was not done.
2. **The stability side extrapolates on GC for every member of every run**, because the
   construct is 64.4% GC against a 39.4–60.2% training range. This is a property of the
   reference construct, not of the design.
3. **The RiboNN run directories are not published.** The snapshot has never bundled full run
   artifacts, so the `translation.run` paths in both summaries will not resolve in a fresh
   clone. The joined predictions are embedded in `scored_members.json`.
4. **Two early smoke runs are retained locally and not published**
   (`20261020T174358.140695Z`, `20261020T174422.363296Z`, `20261020T174516.591695Z`). The
   8-member one is complete and the workflow tests will bind to whichever complete run is
   latest, which in a fresh clone is a 512-member run.
5. **The BO replay's oracle is the pipeline's own predictions.** It cannot detect a wrong
   landscape, only an inefficient search over it.

---

## 9. Open decisions, in priority order

1. **Region-local features, or accept the flat landscape.** This is now the critical path.
   The measured sub-linear scaling says the window cannot fix it. Replacing transcript-mean
   `aup` with window-local unpaired probability would change what the objective sees — but it
   also means the STRAND calibration no longer applies as fitted, because it was fitted on
   transcript-wide features. That is the real cost and it needs deciding, not assuming.
2. **Whether to run a whole-ORF window** to replace the two-point extrapolation with a
   measurement. ~30 minutes; it would settle whether the window is ever the answer.
3. **Free vs GC-neutral**, still formally undecided. Both 512-member runs used neutral.
4. **The assay panel size**, still unknown, and still the real bound on everything.
5. Carried forward: assay CVs and decision costs; whether Fluc-PEST enters the panel; the
   power convention; the span policy and the unspent blinded set; the two questions for
   Ping; experimental-structure references in scope; the C++ toolchain for the fused
   qLogEHVI kernel; V12 §6 item 7.

**No process is running.** Every run completed with exit 0 and wrote a complete artifact.

---

## 10. Exact safe continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai

# Full suite (expect 1467 passed, 38 skipped)
.venv/bin/python -m pytest -q

# Just this stretch
.venv/bin/python -m pytest -q \
  tests/test_stage2_gate_v6.py \
  tests/test_transcript_assembly_variant.py \
  tests/test_design_workflow_run.py \
  tests/test_design_space_v2.py \
  tests/test_window_width_comparison.py

# Re-run the comparison without writing (seconds)
.venv/bin/python scripts/compare_window_width_spreads.py \
  --narrow results/design_workflow_runs/20261020T174606.887363Z \
  --wide   results/design_workflow_runs/20261020T181317.731918Z \
  --dry-run

# Quick end-to-end mechanics check (about a minute)
.venv/bin/python scripts/run_design_workflow.py --size 8 --jobs 8 --panel 3 --bo-budget 5

# Stability side only, no RiboNN
.venv/bin/python scripts/run_design_workflow.py --size 8 --jobs 8 --skip-ribonn

# A full 512-member run at the current window (about 45 minutes)
.venv/bin/python scripts/run_design_workflow.py --size 512 --jobs 24 --panel 12 --bo-budget 32

# The same at an explicit older design space
.venv/bin/python scripts/run_design_workflow.py \
  --spec configs/synonymous_window_design_space_v1_2026-10-20.json \
  --size 512 --jobs 24

# Lint only the files written here; the repository has 2,882 pre-existing ruff errors
ruff check src/rnastable/synonymous_window.py src/rnastable/pareto.py \
  src/rnastable/multi_objective_bo.py scripts/run_design_workflow.py \
  scripts/compare_window_width_spreads.py tests/test_design_workflow_run.py
```

Every driver writes a **new** timestamped directory and never overwrites one
(`mkdir(exist_ok=False)`). `run_design_workflow.py` exits non-zero rather than writing if
the gate is closed, a member fails synonymy, or the assembled variants disagree.

### Publishing

```bash
PUB=/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad/verify
git -C "$PUB" fetch origin && git -C "$PUB" status --short
sha256sum "$PUB/diagram_10182026.png"   # must stay baa831ce16df27ed…
diff "$PUB/README.md" README.md          # merge upstream edits before copying
```

The local repository has **no commits**; `origin` is the placeholder
`https://github.com/YOUR_USERNAME/RNA-StableAI.git`. Publication goes through the clone
above, with `git -c user.name=zyliu-OU -c user.email=<the user's address> commit`, because
that clone has no committer identity.

---

## 11. Published state

| Item | Value |
|---|---|
| Commit before this stretch | `9657ee0` Record the design-space commit hash in handoff 2026-10-20 V3 |
| Commit published with this handoff | see §11.1 |
| README picture | `diagram_10182026.png`, `sha256 baa831ce16df27ed44a41c2a3b481455a213b328122227b9b2a3820dda47cff1`, **byte-unchanged**, re-verified before publishing |
| Gates | v5 frozen; **v6 is now current** |
| Design spaces | v1 frozen; **v2 is now current** |

The README diagram still reads "0 of 6" because the user supplied that SVG; a caption below
it carries the correction. **Regenerating it needs the user's say-so and has not been done.**

### 11.1 Publication record

This handoff is published in the commit titled *"Build the design workflow end to end and
measure the window-width effect"*. Its hash is recorded by the commit immediately after it,
since a file cannot contain the hash of the commit that adds it.
