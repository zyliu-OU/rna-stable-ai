# RNA-StableAI handoff — 2026-10-15 V3

Project: RNA-StableAI. Date: 2026-10-15 (America/Los_Angeles). Version: V3.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
State: the new development dataset and matched pair-set model study are complete.
Independent biological structure validation remains the current scientific
gate; overall development is unfinished and there is no validated release.

## Completed work

Continued from V2's ready 61-training/22-validation computational pair-set
dataset. Added `src/rnastable/pair_set_training.py` and
`scripts/run_family_pair_set_training.py` to freeze and run baseline, stack and
helix heads under the previously declared three seeds, ten epochs, CPU bounds,
random initialization and exact sparse decoder. Explicit pairs remain in the
input snapshots. Full-reference validation scores include contacts outside the
model's legal pair space; training reports 116 unlearnable contacts from 1,351
train gold pairs and 53 from 632 validation gold pairs. Training and validation
exposure events were recorded before fitting.

All nine components completed. Added
`scripts/summarize_family_pair_set_training.py` to replay component inputs,
exposure events, initial and selected checkpoints, predictions, full-reference
scores, epoch selection and matched initial weights. Across three seeds, mean
selected development validation pair F1 was **0.3219 baseline**, **0.3907
stack** and **0.4817 helix**. These values were selected on development
validation records; they are not independent biological accuracy. The study is
at `results/family_pair_set_training_runs/20261016T012741.486402Z/` and its
pointer is `results/family_pair_set_training_summary.json`. Run timestamps are
UTC, while this handoff date is local.

Updated the README, roadmap and
`reports/family_pair_set_training_review_2026-10-15.md`. The user's README
picture HTML and attachment URL remain present. Model inference defaults and
older checkpoints were not changed. No GitHub publication occurred.

## Verification

- All nine component audits and the matched-initialization study audit passed.
- Focused pair-set tests: **2 passed**.
- Full suite: **828 passed in 216.11 seconds**; log
  `reports/family-pair-set-training-full-suite-2026-10-15.log`.
- `git diff --check` passed; new scripts and module compile.
- Study summary declares `test_evaluated: false` and no independent-test claim.

## Pending work

Design and freeze a fresh independently annotated biological structure panel
with adequate supported references and documented family, sequence, annotation
and tool-training provenance before further model inference. The current
training and validation records have exposure events and cannot be fresh tests.
The earlier raw-contact comparison remains a small feasibility study. Long
biological RNA, causal stability, mutation effects and retained function also
remain open. Do not promote development validation scores as release evidence.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-15_V3.md
cat reports/family_pair_set_training_review_2026-10-15.md
cat results/family_pair_set_training_summary.json
.venv/bin/python scripts/run_family_pair_set_training.py --verify-protocol results/family_pair_set_training_protocol.json
.venv/bin/python scripts/summarize_family_pair_set_training.py --verify results/family_pair_set_training_summary.json
.venv/bin/python -m pytest -q tests/test_family_pair_set_training.py
cat docs/REFERENCE_READINESS.md
```

Before any future publication, inspect the live GitHub README and merge
upstream edits while preserving the user's picture and any image assets.
