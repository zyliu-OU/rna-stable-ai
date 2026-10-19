# RNA-StableAI handoff — 2026-10-19 V4

Project: RNA-StableAI
Date: 2026-10-19, America/Los_Angeles
Version: V4
Workspace: `/home/zyliu/Documents/rna-stable-ai`
Selected architecture: **RNAfold + STRAND + RiboNN + BoTorch**
This session's starting point: [V3](RNA-StableAI_HANDOFF_2026-10-19_V3.md) (score records). Named calibration: [V2](RNA-StableAI_HANDOFF_2026-10-19_V2.md). Engine agreement: [V1](RNA-StableAI_HANDOFF_2026-10-19_V1.md).
Publication, scope and component records: [V13](RNA-StableAI_HANDOFF_2026-10-18_V13.md). Full scientific/inference record: [V12](RNA-StableAI_HANDOFF_2026-10-18_V12.md). STRAND record: [V11](RNA-StableAI_HANDOFF_2026-10-18_V11.md).

## Scope of this session

The user asked to start **V13 prioritized item 3**: "Complete Stage 2 independent/native/resource/constraint/replay requirements, especially 2,000–2,999 nt. Only after explicit gate review freeze parents/allowed edits, biological objective, budgets and cell-free assay protocol."

What was built: a frozen **band coverage census** that answers, from existing artifacts, whether the sparse 2,000–2,999 nt requirement can be resolved with local data, plus an explicit **per-requirement status record** for all six gate requirements.

**No gate requirement was satisfied, and none can be satisfied by this census by construction** — the module raises if any requirement is marked satisfied. No selection was changed, no cap was raised, no inference was run, no model default changed, and **no gate review occurred**, so nothing downstream of the gate was frozen. No GitHub publication, no network access.

## Decisions that supersede earlier handoffs

- V13 and the 2026-10-18 audit recorded "Only one long development reference lies in 2000-2999 nt" as a blocker without quantifying what was available. That is now **measured**: the band holds 138 candidates, of which **56 are eligible** (reference-supported and unexposed) across **2 families** but only **1 clan**.
- **New measured finding, and the central result: the band's sparsity is resolvable at family level but not at clan level from local data.** Verdict `resolvable_at_family_level_only_clan_coverage_unchanged`. Raising the per-family cap would add up to 56 band records and one new family (RF02540, 31 eligible records), but **zero new clans** — RF02540 and RF02541 are both CL00112, already represented by the selected baseline.
- **New measured finding: the one local opportunity for a new band clan is blocked by training exposure.** RF02462 is the only band family outside the selected baseline's clans (CL00004), and both of its band records carry `prior_exposure_overlap`, so they are ineligible as independent validation. This is recorded in the artifact as `new_clan_opportunities_blocked: {"CL00004": {"family": "RF02462", "records": 2, "reasons": {"prior_exposure_overlap": 2}}}`.
- Therefore the gate's sparse-band requirement is now classified **`blocked_on_acquisition`**, not merely unmet. Closing it needs band-length references from a clan outside the baseline, or retraining that removes the RF02462 exposure.
- **Clarified: raising the family cap is not progress toward the gate.** The frozen config states that records from an already-represented family or clan are pseudo-replicates for the family-and-clan-separated requirement, so every count is reported by family and clan, not only by record.
- **New measured finding: the in-scope frozen selection is thinner than the raw count suggests.** 11 selected references exist, but only **6** are under 3,000 nt, spanning **3 families** (RF00177 ×3, RF02541 ×1, RF02542 ×2) and **2 clans** (CL00111, CL00112). All six are `reference_kind: computational` Rfam-consensus references, not experimental structures.
- The existing Stage 2 audit **replays cleanly as of today**, including the budget-matched, native-control and five-clan feasibility checks, so replay evidence genuinely exists for those runs. That is why requirement 5 is `partially_satisfied` rather than unknown.

## Constraints and scope, unchanged

Active scope stays **1–2,999 nt**; historical 3,000+ nt evidence preserved; no truncation. Stage 2 remains **open**; cell-free Stage 3 queued. [Scope](../configs/project_scope_2026-10-18.json) and [gate](../configs/stage2_to_stage3_gate_2026-10-18.json) remain authoritative and were **not modified**. Nothing behind the gate — parents, allowed edits, biological objective, budgets, cell-free assay protocol — was frozen, because the gate review that V13 requires has not happened. `new_sequence_scoring_enabled`, `expression_candidate_design_enabled` and `stage3_ready` are false in every artifact written.

## Completed work

### Frozen census protocol

**`configs/stage2_band_coverage_census_v1_2026-10-19.json`** — SHA-256 **`81c6c89190da3c2d3f8c09c50526e24110902e20bc101339fdf09172691dd209`**, 5,842 bytes. Fixes:

- **What it is not**, stated first: a census of existing artifacts that runs no inference, produces no accuracy measurement, changes no selection, and satisfies no gate requirement.
- **Four pinned sources with SHA-256**: the candidate pool and frozen selection decisions from `long_validation_coverage_runs/20261017T033935.363253Z`, the family-clan map from `crw_panel_exposure_runs/20261018T221708.139284Z`, and a secondary band survey from `rfam_seed_long_candidate_audit_runs/20261017T191603.870444Z`. The census fails if any pinned hash changes.
- **Decision taxonomy** mapping the four frozen selection reasons onto `reference_supported` and `exposed` flags. `prior_exposure_overlap` carries `reference_supported: null`, so an exposed record can never be counted eligible on unknown support.
- **Eligibility rule**: in band, reference-supported, not exposed — "about availability, not about accuracy."
- **Independence rule** with the baseline defined as the in-scope selected records, separate `new_family` and `new_clan` definitions, a requirement that clan comes from the pinned sources with `clan_unresolved` never counted as new, an **unresolved-visibility rule** ("a family that is ineligible must not become invisible, because an unresolved or blocked clan is itself a finding"), and the cap warning above.
- **Requirement rule**: status assigned from existing verified artifacts only, and the census "may not mark any requirement satisfied on the strength of the census itself."
- **Five no-claim statements**, including that the available band references are computational Rfam-consensus references and so cannot by themselves satisfy a native-control comparison.

### Implementation

- **`src/rnastable/stage2_census.py`** (new, 129 lines). `band_of` (half-open intervals), `classify`, `eligible`, `clan_of`, `baseline_lineage`, `band_census`, `resolution_verdict`, `requirement_status`. `requirement_status` raises on a missing assignment, an invalid status, missing evidence, missing blockers, and on any attempt to mark a requirement `satisfied`.
- **`scripts/audit_stage2_band_coverage.py`** (new, 301 lines). Re-verifies all four pinned source hashes, asserts the census band ends at the active scope boundary and that the assessed requirements are exactly the gate's, merges clan assignments from both pinned sources with per-family provenance and an error on disagreement, builds the per-record lineage table, computes the census and verdict, and binds all six requirements to a status with evidence and blockers. Blocker text for the band requirement is **generated from the computed census** rather than written by hand. `--verify-run` re-checks artifact hashes, replays the verdict from stored counts and fails if any stored requirement is marked satisfied.
- **`tests/test_stage2_census.py`** (new, 27 tests). Config/gate requirement agreement and band boundary; all six mutation flags false; the cap and visibility rules present; eight band-boundary cases and four invalid lengths; decision classification including the unknown-reason error; eligibility including the exposed-with-unknown-support case; unmapped-clan handling; baseline unresolved reporting; the full band census including blocked new-clan visibility, all-band-family reporting when every record is ineligible, and a genuine new-clan credit; all four verdict states; and requirement-status enforcement including the refusal to mark anything satisfied.

No existing module, config, protocol or canonical run was edited.

### Canonical run

**`results/stage2_band_coverage_census_runs/20261019T180243.655199Z/`** — 9 files, `manifest.json` lists **8** artifacts.

| Artifact | SHA-256 | Bytes |
| --- | --- | --- |
| `summary.json` | `1003804749e1789fa5f86a2cd3f6c061a9f9e16e1e7f76e5eb5f0ece9f197424` | 8,318 |
| `band_records.json` | `d764ca029f01287e951ce8484c3a6e90106a98e603fb4d10c58c132096a62563` | 34,487 |
| `all_candidate_lineage.json` | `e0e4ebd434f900048fef9deff7bfa1d3b6b4f35e1d74ead5d939ec86c4b8cebb` | 83,817 |
| `family_clan_map.json` | `a2ee814ddf12063dddd1c0f9a33f39edda9ad09daf819e004c6c77c74734b241` | 1,017 |
| `identity.json` | `f1c5bdbd52a54f839d5f7592df2362cf27b3b3026d23363e1e1ee27c38328a76` | 1,288 |
| `protocol.json` | `1cc0390a68a754853a5a69ad8322dc8cc6b41906b0c02addbfd26301bb1b78a6` | 5,944 |
| `manifest.json` | `4232372806a9b36b06cd00a3ec38260efa4f6746219df72ed3e8b90fc4c8692d` | 850 |

Plus `source/` copies of the two implementation files. `family_clan_map.json` records each family's clan **and the pinned source role it came from**.

**A superseded earlier run exists and is deliberately retained:** `results/stage2_band_coverage_census_runs/20261019T180142.314049Z/`. Its clan map was loaded from the primary source only, so RF02462 had no clan assignment, `new_clan_opportunities_blocked` came out empty, and a hand-written blocker sentence asserted a blocked new-clan opportunity the artifact did not show. The protocol was corrected (second pinned clan source declared, unresolved-visibility rule added, blocker text made data-driven) and the census re-run. **Use `20261019T180243.655199Z`.** The earlier run is preserved rather than deleted, per the standing preservation rule, and must not be cited.

## Results

In-scope frozen selection: **6 records**, families `["RF00177", "RF02541", "RF02542"]`, clans `["CL00111", "CL00112"]`, no clan-unresolved families.

Coverage by band:

| Band | candidates | selected in scope | selected families | selected clans | eligible records |
| --- | --- | --- | --- | --- | --- |
| 1–999 | 14 | 0 | — | — | 0 |
| 1000–1999 | 132 | 5 | RF00177, RF02542 | CL00111 | 40 |
| **2000–2999** | **138** | **1** | RF02541 | CL00112 | **56** |

Band census, 2,000–2,999 nt:

| Measure | Value |
| --- | --- |
| records | 138 |
| `unsupported_reference` | 79 |
| `fixed_family_cap` | 55 |
| `prior_exposure_overlap` | 3 |
| `selected_complete_reference` | 1 |
| eligible records | **56** (RF02540 31, RF02541 25) |
| band families | RF02462, RF02540, RF02541 |
| band clans | CL00004, CL00112 |
| clan-unresolved band families | none |
| eligible families | RF02540, RF02541 |
| eligible clans | **CL00112 only** |
| new families available | **RF02540** |
| new clans available | **none** |
| new-clan opportunities blocked | CL00004 via RF02462, 2 records, both `prior_exposure_overlap` |
| verdict | **`resolvable_at_family_level_only_clan_coverage_unchanged`** |

Secondary local survey band families (leads only — their reference support was never screened by the frozen selection, so they are **not** eligible records): RF01960 ×16, RF02462 ×2, RF02540 ×55, RF02541 ×81, RF02543 ×2. Note RF01960 is CL00111 and RF02543 is CL00112, both already represented, so even as leads they offer no new clan; RF02462 (CL00004) is the only new-clan lead and it is the exposed one.

Gate requirement status, all six, **zero satisfied**:

| # | Requirement | Status |
| --- | --- | --- |
| 1 | Frozen independent sequence/family/clan-separated validation in scope | **not_satisfied** |
| 2 | Accuracy and failures by length band and family vs native controls | partially_satisfied |
| 3 | Resolve sparse 2,000–2,999 nt coverage | **blocked_on_acquisition** |
| 4 | Credible structure accuracy with explicit native-baseline-gap review | **not_satisfied** |
| 5 | Constraint, decoder, resource and replay checks | partially_satisfied |
| 6 | Document remaining limitations before candidate design | partially_satisfied |

Recorded blockers, in brief: (1) only 6 in-scope records over 3 families and 2 clans, all computational references, with independent complete-reference validation unestablished and existing checkpoints trained with now-deferred sequences; (2) the band figure rests on one record, so it carries no dispersion and no family contrast, and the learned model stays below both native controls; (3) the verdict and counts above; (4) the learned model below both native controls, and no native experimental-structure control for the band at all; (5) the three upstream replays passed on re-verification today but cover only existing development runs — no constraint, decoder or resource check exists for an expanded band cohort because no such cohort exists; (6) limitations are documented across handoffs and this census but are not frozen as a gate-review artifact, and no gate review has occurred.

## Scientific interpretation and limits

1. **The band blocker is a lineage blocker, not a volume blocker.** 56 eligible band records exist locally — far more than the single selected one — but they collapse into one clan that is already represented. The gate asks for family *and clan* separation, so adding them would raise record counts and leave the thing the gate actually measures unchanged. This is the clearest statement yet of why the band cannot be closed by reprocessing what is on disk.
2. **The single new-clan opportunity is foreclosed by past training.** RF02462 would have supplied clan CL00004 in the band; both its band records are training-exposed. Retraining to drop that exposure is a legitimate route, and it is a larger undertaking than acquisition.
3. **The native-control requirement is structurally unmet in the band.** Every available band reference is computational Rfam-consensus. Even a perfect expansion of computational references would not produce the experimental native control requirement 4 implies.
4. **Replay health is genuinely good and genuinely narrow.** The budget-matched, native-control and five-clan feasibility replays all passed today. They say the existing development evidence is reproducible; they say nothing about an expanded cohort.

What must **not** be claimed: that the band is resolved or resolvable in the sense the gate means; that 56 eligible records constitute independent evidence; that any requirement is satisfied; that the census measured accuracy, structure quality or expression benefit; that raising the cap would preserve or improve measured accuracy — that is untested and would require new inference and an explicit gate review.

Rejected and not done: raising the per-family cap; expanding or re-freezing the validation selection; running inference on any expanded cohort; editing the gate or scope; marking any requirement satisfied; freezing parents, allowed edits, the biological objective, budgets or the cell-free assay protocol; treating the secondary survey's unscreened leads as eligible records.

## Verification performed

- **`--verify-run`** on the canonical census: **8 artifacts** re-hashed and matched, verdict replayed from the stored census counts, and zero requirements marked satisfied. Mode: artifact and stored-census audit, no new inference.
- **Existing Stage 2 audit replayed today and passed**: `scripts/audit_stage2_under3000.py --verify-run` on `results/stage2_under3000_audit_runs/20261018T223708.786045Z/summary.json` printed matched candidate-budget replay, long development coverage replay (11 refs), long native control replay (LinearFold 11 ok / 0.4742, ViennaRNA 11 ok / 0.4500), five-clan feasibility replay, and the overall audit replay pass.
- **193 focused tests passed in 1.94 s** — 27 new, plus V3's 36, V2's 12, V1's 27 and the fifteen V13 suites. No regression.
- All four pinned census source hashes re-verified inside the run; clan assignments merged from two sources with conflict detection and no conflict found; census band confirmed to end at the active scope boundary; assessed requirements confirmed to be exactly the gate's six.

**Not run and therefore unverified:** no folding, no refit, no RiboNN inference, no BoTorch run, no training, no inference on any band cohort, no full repository suite, no GitHub publication, no network access. No accuracy number in this handoff is new — every figure quoted is either a count from the census or a replayed figure from existing runs.

## Pending work, prioritized

1. **Acquire band-length (2,000–2,999 nt) structure references from a clan outside CL00111 and CL00112.** This is the specific, now-quantified blocker for gate requirement 3. Needs network and a versioned acquisition protocol with lineage screening against prior exposure.
2. **Decide the RF02462 question.** Either acquire unexposed CL00004 band references, or retrain without the exposed records so the existing two become usable. Record the choice and its cost before acting.
3. **Obtain experimental native structure controls in the band**, or formally narrow requirement 4's claim to computational references and say so in the gate. The second option is a gate amendment and needs explicit review, not a quiet redefinition.
4. **Only then consider an expanded band cohort**, as a separately frozen protocol: state the cap change, the lineage guarantees, the budget match against BO/random/greedy, and the constraint/decoder/resource checks in advance, and run inference once.
5. **Hold the gate review** when 1–4 produce evidence. Until the review happens, do not freeze parents, allowed edits, the biological objective, budgets or the cell-free assay protocol.
6. **Still outstanding from V3/V2 and unchanged**: transcripts carrying both a measured stability readout and numeric coding annotation (no sequence yet carries both a stability and a translation score); a defined intended assay before any RiboNN task or floor selection; independent lineage-safe evaluation of `strand_rnafold_calibration_v1`.
7. **Optional**: publish V1–V4 configs, modules, scripts, tests and concise run evidence to GitHub. Not done. If done, fetch latest upstream first and preserve the repository README diagram `diagram_10182026.png` and its Markdown, per the standing rule. Publish concise summaries rather than bulk arrays; note `all_candidate_lineage.json` is 84 KB, `score_records.json` 472 KB and the V1 run's `folds/` hold full probability arrays.

Do not infer expression benefit from software execution, and do not optimize actual expression candidates while the Stage 2 gate stays open.

## Outstanding processes

None. The census is synchronous and completed in about two seconds. No background job, partial run or pending approval remains from this session. Other system processes were not exhaustively audited.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-19_V4.md
cat reports/RNA-StableAI_HANDOFF_2026-10-19_V3.md
cat reports/RNA-StableAI_HANDOFF_2026-10-18_V13.md
cat configs/stage2_band_coverage_census_v1_2026-10-19.json
cat configs/stage2_to_stage3_gate_2026-10-18.json

# This session's result, cheapest first:
cat results/stage2_band_coverage_census_runs/20261019T180243.655199Z/summary.json
PYTHONPATH=src:scripts .venv/bin/python scripts/audit_stage2_band_coverage.py \
  --verify-run results/stage2_band_coverage_census_runs/20261019T180243.655199Z

# Prior Stage 2 audit replay, re-verified today:
PYTHONPATH=src:scripts .venv/bin/python scripts/audit_stage2_under3000.py \
  --verify-run results/stage2_under3000_audit_runs/20261018T223708.786045Z/summary.json

# Earlier sessions:
PYTHONPATH=src:scripts .venv/bin/python scripts/build_score_records.py \
  --verify-run results/score_record_runs/20261019T175011.658062Z
PYTHONPATH=src:scripts .venv/bin/python scripts/fit_strand_rnafold_calibration.py \
  --verify-run results/strand_rnafold_calibration_runs/20261019T174049.053308Z
PYTHONPATH=src:scripts .venv/bin/python scripts/audit_strand_rnafold_agreement.py \
  --verify-run results/strand_rnafold_agreement_runs/20261019T172402.804593Z

# Earlier canonical local artifact/cached checks, unchanged from V13:
PYTHONPATH=src .venv/bin/python scripts/verify_four_component_build.py results/four_component_build_runs/20261019T041458.024816Z
PYTHONPATH=src .venv/bin/python scripts/reproduce_strand_reference.py --verify-run results/strand_reference_reproduction_runs/20261019T042427.196161Z
PYTHONPATH=src .venv/bin/python scripts/run_ribonn_fixed_inference.py --verify-run results/ribonn_fixed_inference_runs/20261019T045101.117038Z
```

Focused suite, 193 tests:

```bash
cd /home/zyliu/Documents/rna-stable-ai
PYTHONPATH=external/four_component_deps:src:scripts .venv/bin/python -m pytest -q \
  tests/test_stage2_census.py tests/test_score_records.py tests/test_strand_agreement.py \
  tests/test_strand_rnafold_calibration.py tests/test_component_integration.py tests/test_discrete_bo.py \
  tests/test_strand_reference.py tests/test_ribonn_integration.py tests/test_crw_panel_exposure.py \
  tests/test_crw_original_provenance.py tests/test_rcsb_long_source_survey.py tests/test_project_scope.py \
  tests/test_stage2_scope_audit.py tests/test_endpoint_ranking.py tests/test_hard_negative_supervision.py \
  tests/test_recovery_ceiling.py tests/test_endpoint_assignment.py tests/test_sampled_pair_supervision.py \
  tests/test_long_exact_sparse_pairs.py
```

Re-running the census creates a **new** timestamped run directory, reads only pinned artifacts, and performs no inference:

```bash
cd /home/zyliu/Documents/rna-stable-ai
PYTHONPATH=src:scripts .venv/bin/python scripts/audit_stage2_band_coverage.py
```

The census config, the score-record schema and both STRAND criterion files are frozen; do not edit any of them to change an outcome. Expanding the band cohort, raising the family cap, selecting a RiboNN task or freezing a floor each require a new versioned config and, where accuracy is involved, new inference under an explicit gate review. Cite `20261019T180243.655199Z`, not the superseded `20261019T180142.314049Z`. Preserve all previous versioned handoffs.
