# RNA-StableAI handoff

- Project: RNA-StableAI
- Date: 2026-10-05 (America/Los_Angeles)
- Version: V15
- Workspace: `/home/zyliu/Documents/rna-stable-ai`
- State: stopped at the user's request after the latest verified development stage.

## Completed work

- Added `src/rnastable/native_journal.py`, an atomic JSON journal with fsync/replace, file locking, request binding checks, completed-result reuse, interrupted-request recovery, and invalid-energy rejection.
- Added five focused journal tests in `tests/test_native_journal.py`.
- Added checkpoint-prior proposal selection and the three-arm native pilot:
  `random_pool`, `compatibility_only`, and `checkpoint_prior`.
- Pilot artifacts:
  - `results/checkpoint_prior_pilot_runs/20261006T035130.449329Z`
  - `results/checkpoint_prior_pilot_summary.json`
  - `reports/checkpoint_prior_pilot_report.md`
- Pilot audit passed: 3 exact constrained trajectories, 33 raw native folds, pool/checkpoint logits, selections, exposure records, and budget denominators verified. No accuracy test or fitting claim was made.

## Verification

- Full suite before the journal addition: `363 passed in 166.80s`.
- Native-journal focused tests: `5 passed`.
- Checkpoint-prior/core focused tests: `14 passed`.
- Pilot audit log: `reports/checkpoint-prior-pilot-audit.log`.

## Pending work

- Integrate `NativeJournal` into the pooled native runner, including request-key source/checkpoint/config binding and resume semantics.
- Replicate the three-arm prior pilot across additional synthetic inputs and seeds with the same native budget and cost accounting.
- Run the full suite after journal integration.
- Independent longer experimental/family-data evaluation remains pending; no new test-set or generalization claim is authorized.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/verify_checkpoint_prior_pilot.py
.venv/bin/python -m pytest -q tests/test_native_journal.py tests/test_checkpoint_prior.py tests/test_pooled_proposals.py
.venv/bin/python scripts/verify_stack_comparative_development.py
.venv/bin/python scripts/run_stack_scalability.py --verify
.venv/bin/python -m pytest -q
```
