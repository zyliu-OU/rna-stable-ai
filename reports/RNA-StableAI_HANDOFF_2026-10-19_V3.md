# RNA-StableAI handoff — 2026-10-19 V3

Project: RNA-StableAI
Date: 2026-10-19, America/Los_Angeles
Version: V3
Workspace: `/home/zyliu/Documents/rna-stable-ai`
Selected architecture: **RNAfold + STRAND + RiboNN + BoTorch**
This session's starting point: [V2](RNA-StableAI_HANDOFF_2026-10-19_V2.md) (named RNAfold calibration). Engine agreement: [V1](RNA-StableAI_HANDOFF_2026-10-19_V1.md).
Publication, scope and component records: [V13](RNA-StableAI_HANDOFF_2026-10-18_V13.md). Full scientific/inference record: [V12](RNA-StableAI_HANDOFF_2026-10-18_V12.md). STRAND record: [V11](RNA-StableAI_HANDOFF_2026-10-18_V11.md). Architecture decision: [V9](RNA-StableAI_HANDOFF_2026-10-18_V9.md).

## Scope of this session

The user asked to start **V13 prioritized item 2**: "Connect versioned score records with sequence/annotation/tool/settings/weight identities, explicit units or target scale, exclusion reason and raw artifact paths. RiboNN named task and stability/translation floor must be selected for the intended assay with supporting evidence."

The **first half is built**: a frozen record schema, an enforcing module, a builder over the three existing scoring runs, and a canonical run of 99 fully bound records.

The **second half is blocked, and this session establishes why rather than resolving it.** No RiboNN task was selected and no stability or translation floor was frozen, because the intended assay is undefined and the required evidence is absent. The blockers are now recorded as artifacts instead of being carried as prose. V13 item 3 remains unstarted. No GitHub publication, no network access.

## Decisions that supersede earlier handoffs

- V13 item 2 is now **half done and half formally blocked**, with the blocking reasons written into a frozen config and a run artifact rather than restated each handoff.
- **No composite or combined score exists or may exist.** The schema forbids it and the module refuses to build it. The stability side is in hours on the released STRAND half-life scale; the translation side is on a released RiboNN task scale with no inverse transform. V12/V13 implied a future combined objective; the recorded position is now that no aggregate is permitted until a floor and an assay exist.
- **New measured finding: no sequence anywhere in the project currently carries both a stability and a translation score.** 91 records have stability scores, 7 have translation scores, **0 have both**, and `joint_scoring_available` is false. The two sides have never met on a single sequence.
- **New measured finding: the 91 released STRAND records cannot be fed to RiboNN as they stand.** The released tables give UTR5/CDS/UTR3 *descriptions* and types only — every nLuc record carries UTR5 `hHBB` and UTR3 `hHBB` with a design CDS name — and no numeric coding boundaries. RiboNN requires integer `utr5_size` and `cds_size`. Only 8 of 99 records carry numeric boundaries, all of them the synthetic RiboNN mechanics inputs.
- **New measured finding: none of the 78 released RiboNN human output tasks is a cell-free task.** All are cell-type or tissue translational-efficiency tasks, so no released task matches the queued Stage 3 cell-free target.
- **New measured finding: per-task released accuracy evidence is not present locally.** Local artifacts retain released validation R² per selected checkpoint only, 0.4847 to 0.5372 across the 50 selected human checkpoints. No task can therefore be compared against another on evidence held here.
- `predicted_TE_HEK293T` remains a **demonstration column**, now labelled `task_selection: demonstration_only_not_assay_selected` inside every affected record, consistent with the V13 RiboNN protocol's own `task_choice` statement.

## Constraints and scope, unchanged

Active scope stays **1–2,999 nt**, historical 3,000+ nt evidence preserved, no truncation, valid annotated-CDS limits. Stage 2 remains **open**; cell-free Stage 3 is queued. [Scope](../configs/project_scope_2026-10-18.json) and [gate](../configs/stage2_to_stage3_gate_2026-10-18.json) remain authoritative. No acceptance threshold, translation floor, assay platform/replicates or candidate budget is newly frozen — this session's main output is the explicit record that the floors are **not** selected. `new_sequence_scoring_enabled`, `expression_candidate_design_enabled` and `stage3_ready` are false in every artifact written.

## Completed work

### Frozen schema

**`configs/score_record_schema_v1_2026-10-19.json`** — SHA-256 **`3fbdec9d9120998f9557affbf4a5aecdc35910650097f15193c89a28d00d4d56`**, 6,107 bytes. Fixes:

- **Binding requirements.** Each score entry must carry all twelve of `component`, `score_name`, `value`, `units`, `target_scale`, `model_identity`, `tool_identity`, `settings`, `raw_artifact_paths`, `run`, `interpretation`, `independent_validation`. Identities must carry at least one hash, commit or version string: "a score whose producing identity cannot be named is not a score record." Units must be an explicit unit or a named released target scale; `unknown` is forbidden. Raw artifact paths must be workspace-relative, non-empty and must exist at build time.
- **Annotation rule.** Either numeric coding boundaries validated against length, or explicit null with a stated reason. Descriptive annotation alone does not satisfy a numeric-boundary requirement.
- **Exclusion rule.** Every component that did not score a record must appear as an explicit exclusion with a reason. "Silence is not permitted."
- **Composite prohibition.** `composite_score_permitted` false, with the incommensurability reason recorded, and an enforcement clause forbidding any field that ranks, weights or sums across components.
- **RiboNN task selection:** `status: blocked`, with four requirements for selection and the four blockers measured today.
- **Floor selection:** both floors `not_selected` with `value: null`, four evidence requirements listed, and a rule that a floor must be frozen in its own versioned config, "never inside a score record or a builder default."
- **Four no-claim statements**, including that a record is a provenance binding rather than evidence of accuracy, and that coverage counts describe what has been computed, not what has been validated.

### Implementation

- **`src/rnastable/score_records.py`** (new, 131 lines). `sequence_identity`, `coding_annotation`, `score_entry`, `exclusion_entry`, `build_record`, `coverage`. Enforces every rule above and additionally rejects records carrying any field whose name suggests a cross-component aggregate (`composite`, `combined_score`, `total_score`, `rank`, `weighted_score`, `overall_score`, `priority`). `coverage` separates stability-side from translation-side components and reports the joint intersection.
- **`scripts/build_score_records.py`** (new, 310 lines). Ingests the three runs, re-verifies pinned STRAND source hashes, re-derives sequence identities and checks them against each run's stored hashes, builds per-record score and exclusion entries, writes the released-task inventory, and emits run artifacts. `--verify-run` re-checks artifact hashes, replays coverage from the stored records and fails if any stored record carries a composite score.
- **`tests/test_score_records.py`** (new, 36 tests). Schema gates, composite prohibition, both floors unselected, task selection blocked; sequence identity and rejection of non-canonical input; numeric annotation with derived segment sizes and four invalid-bound cases; absent annotation requiring a reason; score entries accepted when fully bound and rejected for missing fields, extra fields, vague units, empty target scale, non-finite or non-numeric values, identities without hash/commit/version, empty, absolute or non-existent artifact paths, and any claim of independent validation; exclusion field and reason enforcement; record building refusing a missing or duplicated component; and coverage reporting both the real joint gap and a synthetic both-sides record.

No existing module, config or canonical run was edited.

### Canonical run

**`results/score_record_runs/20261019T175011.658062Z/`** — 9 files, 518,522 bytes, `manifest.json` lists **8** artifacts.

| Artifact | SHA-256 | Bytes |
| --- | --- | --- |
| `summary.json` | `5da5f5a39583f5f007c00eefc7ddf94d606de27f3326770eae37f713b725f806` | 3,080 |
| `score_records.json` | `bb479c0049830ae269d5ec22a72f2e541251df39024e0f628a15ff96ee328912` | 471,583 |
| `ribonn_task_inventory.json` | `93033968bfa81994e7a968bbac1045492146a339e4657fe33b6d0024478ae5f9` | 4,184 |
| `identity.json` | `c3b7ad74cb314cec5bd9530a8b85ca1b221dd48f927afa00c6c75ea80405c4d9` | 1,100 |
| `protocol.json` | `9ae5a82a4eadcdd83ff36d32b788d146cccd228b65e824aaf1fef20cbaecc456` | 6,272 |
| `manifest.json` | `2aea6d933cf43ba3c8b679e7eda49c32d63b0fbf772f31f6bb50d922f277ffb6` | 864 |

Plus `source/` copies of the three implementation files with their hashes. `protocol.json` is the schema re-serialized at indent 2, so its hash differs from the config file's; `identity.json` records `schema_sha256` = `3fbdec9d…`.

Ingested runs with their manifest hashes recorded in `identity.json`:

| Component | Run | Manifest SHA-256 |
| --- | --- | --- |
| `strand_reference_replay` | `results/strand_reference_reproduction_runs/20261019T042427.196161Z` | pinned in `identity.json` |
| `strand_rnafold_calibration_v1` | `results/strand_rnafold_calibration_runs/20261019T174049.053308Z` | pinned in `identity.json` |
| `ribonn_released_task` | `results/ribonn_fixed_inference_runs/20261019T045101.117038Z` | pinned in `identity.json` |

## Results

99 records built. Cohorts: 69 train, 13 eGFP, 9 MEV exploratory, 8 RiboNN fixed synthetic.

| Component | scored | excluded |
| --- | --- | --- |
| `strand_reference_replay` | 91 | 8 |
| `strand_rnafold_calibration_v1` | 91 | 8 |
| `ribonn_released_task` | 7 | 92 |

| Coverage | Value |
| --- | --- |
| records with a stability score | 91 |
| records with a translation score | 7 |
| **records with both sides** | **0** |
| `joint_scoring_available` | **false** |
| records with numeric coding boundaries | 8 of 99 |
| composite score emitted | false |

RiboNN released-task inventory: **78** tasks, all cell-type or tissue TE; `cell_free_task_present` **false**; `per_task_released_accuracy_available_locally` **false**; available evidence is per-checkpoint released validation R² over 50 checkpoints, min 0.4847, max 0.5372; `selection_status` **blocked**.

Floors: `stability_floor` **not_selected**, `translation_floor` **not_selected**.

Example binding, eGFP record `X130010D1` (1,215 nt, observed half-life 1.47 h): stability scores 1.342494 h from `strand_reference_replay` and 1.291097 h from `strand_rnafold_calibration_v1`, each carrying model hashes, the source commit, tool identity, feature source, component count and two raw artifact paths; `ribonn_released_task` excluded with the numeric-boundary reason; `composite_score` null. The eight synthetic records instead carry full numeric annotation (for example `utr5_size` 12, `cds_size` 45, `utr3_size` 7) and one `predicted_TE_HEK293T` score of 1.691884 on the released task scale, with the 50-checkpoint identity and the `demonstration_only_not_assay_selected` label; one record is excluded with reason `utr5_exceeds_1381_nt`.

## Scientific interpretation and limits

1. **The provenance layer is the deliverable; it is not evidence.** Every score now names the sequence, the model or weight identity, the tool and settings, the units or target scale, and the raw artifacts it came from, and every missing score names its reason. That makes the pipeline auditable. It makes nothing accurate.
2. **The architecture has a structural hole that the records now make explicit.** A four-component design whose stability and translation sides have never scored the same sequence cannot yet produce a joint objective, and the blocker is not compute — it is that the STRAND reference sequences lack the numeric coding boundaries RiboNN consumes, while the RiboNN inputs are synthetic sequences with no measured half-life. Closing it needs real transcripts carrying both a measured stability readout and numeric annotation.
3. **RiboNN task selection is blocked on the assay, not on effort.** All 78 released human tasks are cell-type TE tasks; the queued Stage 3 target is cell-free. Even if the assay were defined, no per-task accuracy evidence is held locally, and training overlap per task remains unknown as V12/V13 recorded. Selecting a task now would be an arbitrary choice dressed as a decision.
4. **Deriving the missing boundaries is possible but was deliberately not done.** The UTR5/UTR3 are described as `hHBB` and the CDS by design name, so boundaries could in principle be located by sequence matching or ORF finding. That would be new derived annotation requiring its own provenance, validation and error analysis. It is recorded as a required acquisition, not invented here.

What must **not** be claimed: that any score is validated or calibrated; that coverage counts are validation; that a combined or ranked candidate score exists; that any floor, threshold or named assay objective has been chosen; that any Stage 2 requirement is satisfied. The 91 released records remain highly redundant (68 of 91 at 928 nt) and the 8 synthetic inputs are software-mechanics fixtures with no measurement.

Rejected and not done: emitting any composite, weighted or ranked score; selecting a RiboNN task; freezing either floor; deriving coding boundaries for the released STRAND sequences; wiring any scoring path for new sequences.

## Verification performed

- **`--verify-run`**: **8 artifacts** re-hashed and matched, coverage replayed from the stored records and equal to the stored summary, and every stored record confirmed to carry a null composite score. Mode: artifact and stored-record audit, no new scoring.
- **166 focused tests passed in 1.92 s** — 36 new, plus V2's 12, V1's 27 and the fifteen V13 suites. No regression.
- Pinned STRAND source hashes re-verified; every sequence identity re-derived and checked against the stored per-run hashes; RiboNN source commit confirmed unique across the pinned file set.
- Builder gate checks: schema composite prohibition, both floor values null, and all three scoring/design/stage flags false, each asserted before any record was written.

**Not run and therefore unverified:** no folding, no STRAND refit, no RiboNN inference, no BoTorch run, no training, no full repository suite, no GitHub publication, no network access. No previously measured result was re-measured. No new scientific measurement was produced this session — the outputs are provenance bindings over existing runs plus four measured inventory facts.

## Pending work, prioritized

1. **Acquire transcripts that carry both a measured stability readout and numeric coding annotation.** This is now the single highest-value blocker: it gates the joint objective, V13 item 2's remaining half, and the independent evaluation of `strand_rnafold_calibration_v1` that V2 identified. Without it the four-component design cannot be exercised end to end on any sequence.
2. **Define the intended assay** before any RiboNN task or floor is chosen: platform, readout, units, dynamic range, replicate structure and measurement error. Items 3 and 4 below both depend on it.
3. **Then select the RiboNN named task** against the assay, with per-task released accuracy evidence retrieved from upstream (not present locally) and per-task training overlap established. Freeze the selection in its own versioned config.
4. **Then freeze the stability and translation floors** in their own versioned config with the four evidence requirements the schema lists, including the stated cost of a false accept and a false reject. Never inside a record or a builder default.
5. **If and only if boundaries are derived** for the released STRAND sequences, do it as a separate versioned annotation run with its own provenance and an error analysis against any available reference, then rebuild the records and re-check coverage.
6. **V13 item 3** (unstarted): Stage 2 independent/native/resource/constraint/replay requirements, especially sparse 2,000–2,999 nt coverage. Only after explicit gate review should parents/allowed edits, biological objective, budgets and the cell-free assay protocol be frozen. Keep BO/random/greedy feasibility and evaluation budgets matched.
7. **Optional**: publish V1–V3 criteria, schema, modules, scripts, tests and concise run evidence to GitHub. Not done. If done, fetch latest upstream first and preserve the repository README diagram `diagram_10182026.png` and its Markdown, per the standing rule. Note `score_records.json` is 472 KB and the V1 run's `folds/` hold full probability arrays; publish concise summaries, not the arrays.

Do not infer expression benefit from software execution, and do not optimize actual expression candidates while the Stage 2 gate stays open. No combined biologically validated candidate-scoring command exists yet, and this session's records make the reason explicit rather than removing it.

## Outstanding processes

None. The build is synchronous and completed in under two seconds. No background job, partial run or pending approval remains from this session. Other system processes were not exhaustively audited.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-19_V3.md
cat reports/RNA-StableAI_HANDOFF_2026-10-19_V2.md
cat reports/RNA-StableAI_HANDOFF_2026-10-19_V1.md
cat reports/RNA-StableAI_HANDOFF_2026-10-18_V13.md
cat configs/score_record_schema_v1_2026-10-19.json
cat configs/stage2_to_stage3_gate_2026-10-18.json

# This session's result, cheapest first:
cat results/score_record_runs/20261019T175011.658062Z/summary.json
cat results/score_record_runs/20261019T175011.658062Z/ribonn_task_inventory.json
PYTHONPATH=src:scripts .venv/bin/python scripts/build_score_records.py \
  --verify-run results/score_record_runs/20261019T175011.658062Z

# Upstream sessions:
PYTHONPATH=src:scripts .venv/bin/python scripts/fit_strand_rnafold_calibration.py \
  --verify-run results/strand_rnafold_calibration_runs/20261019T174049.053308Z
PYTHONPATH=src:scripts .venv/bin/python scripts/audit_strand_rnafold_agreement.py \
  --verify-run results/strand_rnafold_agreement_runs/20261019T172402.804593Z

# Earlier canonical local artifact/cached checks, unchanged from V13:
PYTHONPATH=src .venv/bin/python scripts/verify_four_component_build.py results/four_component_build_runs/20261019T041458.024816Z
PYTHONPATH=src .venv/bin/python scripts/reproduce_strand_reference.py --verify-run results/strand_reference_reproduction_runs/20261019T042427.196161Z
PYTHONPATH=src .venv/bin/python scripts/run_ribonn_fixed_inference.py --verify-run results/ribonn_fixed_inference_runs/20261019T045101.117038Z
```

Focused suite, 166 tests:

```bash
cd /home/zyliu/Documents/rna-stable-ai
PYTHONPATH=external/four_component_deps:src:scripts .venv/bin/python -m pytest -q \
  tests/test_score_records.py tests/test_strand_agreement.py tests/test_strand_rnafold_calibration.py \
  tests/test_component_integration.py tests/test_discrete_bo.py \
  tests/test_strand_reference.py tests/test_ribonn_integration.py tests/test_crw_panel_exposure.py \
  tests/test_crw_original_provenance.py tests/test_rcsb_long_source_survey.py tests/test_project_scope.py \
  tests/test_stage2_scope_audit.py tests/test_endpoint_ranking.py tests/test_hard_negative_supervision.py \
  tests/test_recovery_ceiling.py tests/test_endpoint_assignment.py tests/test_sampled_pair_supervision.py \
  tests/test_long_exact_sparse_pairs.py
```

Rebuilding the records creates a **new** timestamped run directory and re-reads the three ingested runs; it performs no folding, fitting or inference:

```bash
cd /home/zyliu/Documents/rna-stable-ai
PYTHONPATH=src:scripts .venv/bin/python scripts/build_score_records.py
```

The schema and both earlier criterion files are frozen; do not edit them to change an outcome. Selecting a RiboNN task or a floor requires a new versioned config plus the evidence the schema enumerates, never a builder default. Fresh STRAND reference refit and RiboNN inference commands remain in V12/V11 and the integration guide and need the retained local sources, weights and environments. Do not pass concise published summaries as full local runs. Preserve all previous versioned handoffs.
