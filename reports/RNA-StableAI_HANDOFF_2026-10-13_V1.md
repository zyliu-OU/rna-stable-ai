# RNA-StableAI handoff

Project: RNA-StableAI. Date: 2026-10-13 (America/Los_Angeles). Version: V1.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Current roadmap step: **4 — declared development candidate-budget comparison completed**.

## Completed work

Implemented `scripts/compare_candidate_budgets.py`, its focused tests and
`docs/CANDIDATE_BUDGET_DEVELOPMENT.md`; updated README. Evaluated declared
16/32/64 candidate budgets for all nine frozen checkpoints and all 47 reused
validation records. Retained all 1269 predictions, 270 fixed slices (27 empty),
contact partitions, F1 changes, runtime and candidate/DP array costs.
All 423 top-16 structures exactly reproduce original saved predictions.
Pools are nested and exact objectives never decrease. Input/checkpoint/code/
exposure/outcome hashes bind the unique run; failures preserve partial outcomes.

Run: `/home/zyliu/Documents/rna-stable-ai/results/candidate_budget_development_runs/20261014T001919.742401Z`.
Review: `reports/candidate_budget_development_review_2026-10-13.md`.
Published data: `results/candidate_budget_development.csv` and
`results/candidate_budget_development_summary.json`.

Helix mean record F1 across the same three model seeds: 0.503523/0.498461/0.497651
for budgets16/32/64. Top-64 regresses for every helix seed despite better gold
retention. Baseline and stack improve at top-64 for two seeds, regress for one.
Larger pools add competing false positives and decoder cost. **Keep top-16 defaults
unchanged.** Checkpoint epochs were selected with top-16; this is posthoc
development tuning, not joint epoch/budget selection or independent testing.
Repeated model seeds share biological records. Single CPU timings were collected
while tests ran and do not establish speed significance. Array costs are not
whole-process memory. No fitting, checkpoint selection, native folds or
prospective-panel input occurred. No Git index edit, commit, push or publication.

## Verification

- Original diagnostic replay: all 423 predictions and contact partitions pass.
- Budget replay: all 1269 predictions, structures, partitions, objectives,
  array costs, bindings and aggregates pass. Historical times remain hash-bound
  finite nonnegative observations; replay does not require identical new timings.
- Full suite: **586 passed in218.59seconds**. Collection preceded addition of two
  final failure-retention cases; both pass in the final focused run.
- Final focused run: **29 passed in1.09seconds**, including all15 new budget checks.
- Ruff, compileall and `git diff --check` pass.
- Logs under `reports/`: `candidate-original-audit-2026-10-13.log`,
  `candidate-budget-development-2026-10-13.log`, `candidate-budget-audit-2026-10-13.log`,
  `candidate-budget-focused-2026-10-13.log`, `candidate-budget-full-suite-2026-10-13.log`.

## Pending work

Next declare a development-only matched experiment targeting scoring competition
and false positives among retained contacts. Freeze the training/validation cohort,
all compared settings and complete outcome accounting before scoring or fitting.
Do not assume that larger candidate budgets improve accuracy or change defaults
based on retention alone. Reserve a newly screened annotated source panel before
subsequent independent testing. Previously consumed prospective families remain
exposed and must not be reused as fresh tests. Training/tool provenance, long
biological annotations, experimental stability/function and validated release
remain pending. No user terminal commands are required to finish this milestone.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/candidate_budget_development_review_2026-10-13.md
cat docs/CANDIDATE_BUDGET_DEVELOPMENT.md
.venv/bin/python scripts/compare_candidate_budgets.py --verify
.venv/bin/python scripts/analyze_candidate_development.py --verify
.venv/bin/python -m pytest -q tests/test_candidate_budgets.py tests/test_candidate_diagnostics.py tests/test_development_slices.py
.venv/bin/python -m pytest -q
```

Read this versioned handoff and the review before implementing the next declared
experiment. All earlier handoffs and immutable runs are preserved.
