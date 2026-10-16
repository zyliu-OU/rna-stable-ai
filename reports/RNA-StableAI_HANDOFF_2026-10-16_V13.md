# RNA-StableAI handoff — 2026-10-16 V13

Project: RNA-StableAI. Date: 2026-10-16 (America/Los_Angeles). Version: V13.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Active scope: 1–4,999 nt; retain historical data at 5,000 nt and above.

## Completed work

- Accepted the user's pivot: independent structure validation remains unresolved, but it no longer blocks separate core-model development. The user now prefers the assistant to run local commands/tests directly.
- Inspected the current pair-set training cohort: 61 train records of 61–360 nt and 22 validation records of 46–387 nt. The three helix heads were the strongest prior matched family-pair-set development models, with mean selected validation F1 0.481688 across seeds. This cohort does not establish accuracy for longer active-scope RNA.
- Added a frozen, development-only equal-logit ensemble experiment in `scripts/run_helix_ensemble_development.py`, combining the three existing helix checkpoints without refitting or changing core modules. The first run computed its score but failed final self-audit because integer seed keys became JSON string keys. The failed run was preserved.
- Added `scripts/run_helix_ensemble_development_v2.py` to normalize those keys with a separately frozen corrected runner, while retaining the original ensemble rule and failed-run provenance. Completed and replayed `results/helix_ensemble_development_v2_runs/20261016T173017.563888Z/summary.json`.
- On the same reused 22-record validation set, equal-logit ensemble mean full-reference pair F1 was **0.497332** versus **0.489149** for the best individual checkpoint; difference +0.008183. Against that checkpoint, 9 records improve, 10 regress, and 3 tie. This small mixed result is development-only and does not justify changing inference defaults.
- Added focused tests in `tests/test_helix_ensemble_development.py` and a detailed review in `reports/helix_ensemble_development_review_2026-10-16.md`. No independent panel labels, new contacts, new model fit, GitHub publication, or README changes occurred.

## Verification

- Original ensemble protocol freeze replay passed. The original run failed its summary-value self-audit; it is retained as a failed attempt, not a completed artifact.
- Corrected runner freeze, run self-audit, and separate acquisition-style replay all passed.
- Focused ensemble tests: 3 passed in 0.92 seconds. Combined ensemble, family-pair-set and project-scope tests: **11 passed in 1.01 seconds**.
- Ruff executable was not installed in `.venv`; no lint pass is claimed.

## Pending work

Keep the existing inference default unchanged. The next core-development step should address the substantial length-coverage gap (training/validation currently below 400 nt) or a separately declared model design with matched controls and fresh development data, while preserving all completed checkpoints and source hashes. Do not claim the reused-validation ensemble delta is independent biological improvement. Continue the independent structure-lineage work only as a bounded, separate track; contact acquisition and model inference on that panel remain unauthorized.

Before any future GitHub publication, inspect the latest live README and preserve the user's picture markup and image assets.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/run_helix_ensemble_development_v2.py --verify results/helix_ensemble_development_v2_runs/20261016T173017.563888Z/summary.json
.venv/bin/python -m pytest -q tests/test_helix_ensemble_development.py tests/test_family_pair_set_training.py tests/test_project_scope.py
jq '{record_count,ensemble_mean_full_pair_f1,best_individual_validation_f1,beats_best_individual_on_reused_validation,test_evaluated,inference_defaults_changed}' results/helix_ensemble_development_v2_runs/20261016T173017.563888Z/summary.json
cat reports/helix_ensemble_development_review_2026-10-16.md
```

The assistant should run local commands/tests as needed; do not hand routine execution back to the user.
