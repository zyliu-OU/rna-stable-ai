# RNA-StableAI handoff — 2026-10-18 V4

Project: RNA-StableAI
Date: 2026-10-18 (America/Los_Angeles)
Version: V4
Workspace: `/home/zyliu/Documents/rna-stable-ai`

## User direction

The user narrowed active length scope, selected **cell-free expression** for Stage 3, and explicitly required Stage 2 to be good for lengths **smaller than 3,000 nt before Stage 3**. Use the latest wording: 1–2,999 nt active; 3,000 nt and longer deferred. Keep Stage 2 as the immediate priority. Do not start expression candidate design or continue above-cap source acquisition.

## Completed work

- Added `configs/project_scope_2026-10-18.json`; changed the scope helper default and active/deferred labels. Explicit loading of the immutable October 16 policy retains its old 5,000-nt boundary and labels. Prior scope code/tests/docs were saved in `reports/source_snapshots/20261018T223458.718948Z/`.
- Added `configs/stage2_to_stage3_gate_2026-10-18.json`, recording cell-free expression as the queued target and keeping Stage 2 quality, coverage, independence and engineering checks ahead of Stage 3.
- Added `scripts/audit_stage2_under3000.py` and boundary/weighting tests. Its replay restricts historical longer-reference accuracy to six in-scope records: five of 1,000–1,999 nt and one of 2,000–2,999 nt. Historical extended top-32 mean F1 is 0.2965, versus 0.4381 LinearFold and 0.4215 ViennaRNA.
- Added and executed `scripts/run_under3000_development.py`: three matched seeds, 88-record control versus 103-record extension (15 in-scope additions), ten epochs, fixed-final checkpoints, exact sparse top-32 decoding. Every newly trained/evaluated sequence is below 3,000 nt. Top-32 was chosen from prior exposed development diagnostics, not preregistered independent evidence.
- Fresh mean pair F1: longer six-reference cohort **0.2695 control / 0.3174 extension**; shorter 13-reference cohort **0.1357 / 0.1561**. Native values are **0.4381/0.4215** on the longer cohort and **0.3301/0.3346** on the shorter cohort (LinearFold/ViennaRNA). The learned models remain below native controls; Stage 2 is **not ready** for the Stage 3 transition.
- Updated local README, `docs/LENGTH_SCOPE.md`, and `reports/PROJECT_ROADMAP_2026-10-18.md`. Wrote `reports/stage2_under3000_review_2026-10-18.md`. Preserved the README picture, historical runs and all pre-existing staged/unstaged work. No checkpoint promotion, model inference-default change or publication occurred.

## Verification

- 21 tests passed across `test_project_scope.py`, `test_sequence_diverse_structure_panel.py`, `test_stage2_scope_audit.py`, `test_long_exact_sparse_pairs.py` and `test_sampled_pair_supervision.py`.
- Historical scoped audit replay passed through original candidate-budget, cohort, native raw-output and five-clan checks.
- All six fresh fits completed. Artifact/score replay passed: checkpoint/prediction hashes, exposure events, cohort scoring and matched initial weights. This replay checks saved artifacts and does not retrain models.
- All three fresh control models reproduce the historical top-32 structures exactly on the six in-scope longer references.
- Changed-file whitespace checks and exact README image-markup preservation passed before the final documentation write; final link/whitespace checks are recorded below if reported by the assistant.

## Pending work

- Improve learned pair ranking/training objectives in a new frozen development protocol. Keep this 88/103 baseline and native controls. Decoder widening and additive score offsets were already explored; further reuse of these cohorts remains development tuning.
- Preregister quantitative application-specific accuracy acceptance criteria before independent evaluation. Neither the historical nor the fresh study qualifies as independent validation: longer references have exposed training family/clan/segment relationships and were label-informed; the shorter cohort also has computational labels and prior exposure.
- Obtain genuinely independent sequence/family/clan-separated evidence within 1–2,999 nt, especially beyond the single 2,000–2,999 nt reference. Resource/constraint/replay checks alone do not establish structure accuracy.
- Keep Qβ/AP205 (4,217/4,269 nt) source leads and all other 3,000+ nt work deferred. Do not truncate sequences or remove historical records to make them active.
- Stage 3 remains queued for cell-free expression. Specific platform, CDS/UTR constraints and measured expression assays can be defined after Stage 2 quality review. No expression benefit is established.
- Changes remain local. Before publishing, fetch/inspect the live GitHub README and preserve its picture and upstream edits.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/stage2_under3000_review_2026-10-18.md
cat reports/PROJECT_ROADMAP_2026-10-18.md
.venv/bin/python -m pytest -q tests/test_project_scope.py tests/test_sequence_diverse_structure_panel.py tests/test_stage2_scope_audit.py tests/test_long_exact_sparse_pairs.py tests/test_sampled_pair_supervision.py
.venv/bin/python scripts/run_under3000_development.py --verify-run results/under3000_development_runs/20261018T223810.974436Z/summary.json
.venv/bin/python scripts/audit_stage2_under3000.py --verify-run results/stage2_under3000_audit_runs/20261018T223708.786045Z/summary.json
cat results/under3000_development_protocol_runs/20261018T223802.654756Z/manifest.json
sed -n '120,185p' scripts/train_sampled_long_development.py
cat src/rnastable/sampled_pair_supervision.py
```

The next training-objective experiment needs a new driver/protocol; do not edit the already frozen training or scoring modules in place without preserving replay sources.
