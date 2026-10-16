# RNA-StableAI pair-set training review — 2026-10-15

The ready, label-informed development dataset contains 61 training and 22
validation complete computational pair references across 12 and four groups.
The frozen study trained baseline, stack and helix heads with the same three
random seeds, ten epochs, optimizer settings and exact sparse decoder. All nine
runs began from declared random initialization; matched base weights and zero
initial feature-head weights were audited. Training and validation exposure
events were written before fitting. No test cohort was read or scored.

The trainer uses explicit pair sets. It retains all 1,351 training and 632
validation gold contacts in source snapshots and validation scoring. Of these,
116 training and 53 validation contacts are outside the model's legal canonical
pair space and are counted as unlearnable, without deleting them from the full
reference. Epoch selection used full-reference validation pair F1, then lower
validation BCE, then earliest epoch.

| Head | Seed 20261015 | Seed 7 | Seed 1729 | Mean selected validation pair F1 |
|---|---:|---:|---:|---:|
| Baseline | 0.2845 | 0.3154 | 0.3658 | **0.3219** |
| Stack | 0.3708 | 0.4096 | 0.3918 | **0.3907** |
| Helix | 0.4688 | 0.4871 | 0.4891 | **0.4817** |

The untrained models scored 0.0 on this validation set under the fixed sparse
decoder. The table is **development performance selected on these same
validation records**. It is not independent biological accuracy. The data
protocol used observed label coverage to repair an earlier failed development
selection, and comparative consensus labels are computational. These scores do
not establish long biological RNA accuracy, stability, mutation benefit or
retained function. Model inference defaults and the earlier checkpoints remain
unchanged.

Study:
`results/family_pair_set_training_runs/20261016T012741.486402Z/`.
Each component retains input snapshots, exposure events, initial and selected
checkpoints, epoch history, predictions and a replayable summary. The top-level
summary audits all nine components and matched initial weights.

The focused pair-set tests passed (two tests). The full suite passed **828 tests
in 216.11 seconds**; see
[`family-pair-set-training-full-suite-2026-10-15.log`](family-pair-set-training-full-suite-2026-10-15.log).

Verification:

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/run_family_pair_set_training.py --verify-protocol results/family_pair_set_training_protocol.json
.venv/bin/python scripts/summarize_family_pair_set_training.py --verify results/family_pair_set_training_summary.json
.venv/bin/python -m pytest -q tests/test_family_pair_set_training.py
```
