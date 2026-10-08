# RNA-StableAI handoff — 2026-10-05 — V5

Project: RNA-StableAI
Date: 2026-10-05 (America/Los_Angeles)
Version: V5
Absolute workspace: `/home/zyliu/Documents/rna-stable-ai`

## Completed work

Implemented exact legacy Rfam FASTA/BPSEQ binding, deterministic cohort selection,
a comparative family-trial runner, a durable exposure registry and a comprehensive
trial auditor. The general family planner now incorporates the live project registry,
including custom historical development snapshots and incomplete trial starts.
Exposure events are flushed/fsynced before training/validation/test use; test-start
is written before inference or folding. Corrupt exposure events fail closed.

Completed fixed trial: `results/family_trial_runs/20261006T020448.519769Z`.
Train RF00001: 24 sequences (27–121 nt); validation RF00169: 23 (77–104 nt);
test RF00008: 9 (40–58 nt). These IDs come from exact legacy `EXT_ID` metadata;
broad RNA types were not used as family assignments. Labels are processed
comparative annotations, recorded as computational references, not new experimental
measurements. Original archive split tags remain in record provenance; trial splits
use frozen family IDs.

Fresh pair model: 11,697 parameters, 10 CPU epochs, seed 20261006, fixed zero logit
threshold. Validation selected epoch 9, F1 0.03432242044067323. Training-only pair
counts: 736 positive / 56,646 negative; positive weight 8.772951265853669.
No excluded train/validation reference contacts. All 45 predictions measured and
18 native folds succeeded. Test mean pair F1:

| Method | Mean pair F1 |
|---|---:|
| Trained pair | 0.091157185894028 |
| Initial pair | 0.03735359290914846 |
| ViennaRNA | 0.8793522785458269 |
| LinearFold | 0.8793522785458269 |
| All unpaired | 0 |

The model transfers poorly across these families. RF00008 is now consumed as test;
it must not be used for tuning or described as fresh in future evaluations. The
registry now contains 125 distinct exposure records. One family per split, unresolved
prior PDB family assignments, clan independence and legacy folding-tool training
overlap constrain interpretation. Scores do not establish long-RNA performance or
biological stability. Current pair matrices/decoder remain quadratic/cubic, max256 nt.

## Verification

- Full suite: 265 passed; `reports/tests-family-trial-checkpoint.xml`.
- Real family plan audit: 24/23/9 records; frozen pretrial ledger checks69 prior exposures.
- Family trial audit: exact source binding, cohort selection, frozen split/ledger,
  durable event inventory, validation checkpoint choice, loaded-checkpoint inference,
  native command and raw sequence/structure/energy checks, all retained evaluation exports.
- Earlier pair-development, experimental-pilot and long equal-budget audits passed.
- Default trial `--dry-run` now exits2 before output: empty RF00008 family after
  exposure filtering (expected rejection). No new trial directory was created.
- Prior long-summary, long-manifest, pilot-summary and pair-development-summary hashes
  match the preceding status. Previous measured artifacts remain preserved.

Before-edit backup: `reports/source_backups/20261006T020004.653204Z/`.
Current files/hashes and retained prior studies: `reports/current_work_status.json`.
Detailed stage report: `reports/family_trial_development_checkpoint.md`.
Latest trial artifacts: `results/family_trial_summary.json`, `results/family_trial.csv`,
`reports/family_trial_report.md`. The per-run summary and frozen artifacts are canonical
for auditing if future latest pointers change.

## Pending work

Improve richer sequence/pair context and scalable scoring/decoding using development
data only. Obtain a larger verified family/clan-labelled cohort with experimental
source/condition metadata before freezing another fresh test. Resolve prior PDB family
assignments and folding-tool training provenance if making cross-study independence
claims. No model or hyperparameter changes were selected using this test result.

No Git push, package install or system change performed. Workspace Git metadata remains
protected; prepare an export checkout only when remote Git work is requested.
User authorization: continue development autonomously; no routine confirmation needed.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/current_work_status.md
cat reports/family_trial_development_checkpoint.md
.venv/bin/python scripts/verify_family_trial.py --summary results/family_trial_runs/20261006T020448.519769Z/summary.json
.venv/bin/python scripts/verify_family_plan.py --run results/family_trial_runs/20261006T020448.519769Z/family_plan
.venv/bin/python scripts/verify_pair_development.py
.venv/bin/python scripts/verify_experimental_pilot.py
.venv/bin/python scripts/verify_equal_budget.py --summary results/equal_budget_long_summary.json
.venv/bin/python -m pytest -q
```

For a future trial, first supply new family/source evidence in the importer and an
explicit config. Once `configs/new_family_trial.json` exists:

```bash
.venv/bin/python scripts/run_family_trial.py --config configs/new_family_trial.json --dry-run
.venv/bin/python scripts/log_command.py .venv/bin/python scripts/run_family_trial.py --config configs/new_family_trial.json
.venv/bin/python scripts/verify_family_trial.py
```

The default completed RF00008 plan is intentionally rejected on rerun. Existing
checkpoint inference inside the auditor is integrity replay, not fresh test selection.
