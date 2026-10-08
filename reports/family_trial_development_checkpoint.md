# RNA-StableAI family-trial development checkpoint

Workspace: `/home/zyliu/Documents/rna-stable-ai`
Run: `/home/zyliu/Documents/rna-stable-ai/results/family_trial_runs/20261006T020448.519769Z`

## Completed

- Exact Rfam accession/sequence/BPSEQ binding from the local legacy EternaFold archive.
- Frozen within-trial family separation: train RF00001 (24), validation RF00169 (23), test RF00008 (9).
- Fresh pair model, 10 CPU epochs, 11,697 parameters; selected epoch 9 with validation F1 0.03432242044067323.
- 736 positive / 56,646 negative training legal pairs; training-only loss weight 8.772951265853669. No unrepresentable train or validation reference contacts.
- Test exposure recorded before inference; all 45 planned predictions measured and 18 native folds succeeded.
- Registry includes incomplete starts, prior pilot snapshots and custom development snapshots. 125 distinct exposures now known.
- No previous study summaries or historical long-study manifest changed (hashes checked against prior status).

## Results

| Method | Mean test pair F1 |
|---|---:|
| LinearFold | 0.8793522785458269 |
| ViennaRNA | 0.8793522785458269 |
| all_unpaired | 0.0 |
| trained_pair | 0.091157185894028 |
| untrained_pair | 0.03735359290914846 |

## Interpretation and pending work

Processed comparative annotations are not new experimental measurements. Only one
family occurs per split; prior PDB family assignments, clan independence and legacy
folding-tool training overlap are unresolved. The neural model transfers poorly.
RF00008 is consumed: future improvements must use development data and a newly
frozen test family. The quadratic-score/cubic-decoder architecture stays bounded
to 256 nt. Actual test lengths were 40–58 nt. No long-RNA accuracy or biological
stability claim follows from this trial.

Next work: develop richer pair/context features and scalable inference using
train/validation data only; source a larger family/clan-labelled cohort with verified
experimental provenance before a fresh evaluation. No new package/system installs
or remote Git writes were performed.

## Verification and continuation

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/verify_family_trial.py
.venv/bin/python scripts/verify_family_plan.py --run results/family_trial_runs/20261006T020448.519769Z/family_plan
.venv/bin/python scripts/verify_pair_development.py
.venv/bin/python scripts/verify_experimental_pilot.py
.venv/bin/python scripts/verify_equal_budget.py --summary results/equal_budget_long_summary.json
.venv/bin/python -m pytest -q
```

The full suite passed: **265 tests**, XML `reports/tests-family-trial-checkpoint.xml`.
The family trial, existing pair-development, experimental-pilot and long equal-budget
audits passed. Source backup before this stage:
`reports/source_backups/20261006T020004.653204Z/`.

To prepare a future fresh trial, copy `configs/family_trial.json`, supply new
sequence-bound families and source evidence, and validate the proposed config with
` .venv/bin/python scripts/run_family_trial.py --config configs/new_family_trial.json --dry-run `.
Do not reinterpret the already observed RF00008 test as fresh.
