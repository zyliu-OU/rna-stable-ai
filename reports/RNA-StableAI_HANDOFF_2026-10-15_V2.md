# RNA-StableAI handoff — 2026-10-15 V2

Project: RNA-StableAI. Date: 2026-10-15 (America/Los_Angeles). Version: V2.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
State: provenance-controlled development data are ready for a new training
study. Overall development and independent biological validation are unfinished.
No validated release.

## Completed work

Continued from V1 without changing its frozen run or 59 unsupported records.
Implemented `scripts/extend_family_provenance_dataset.py` to select the first
unused metadata-ranked group, RF00022, as a declared development-only training
replacement for RF00024. Its source was frozen before download. The sandbox DNS
attempt failed; an approved retry downloaded the source. Sequence-first
selection fixed seven RF00022 candidates, all with incomplete paired-column
coverage. That failed extension and its denominator remain retained at
`results/family_provenance_extension_runs/20261016T011329.080000Z/`.

Implemented `scripts/derive_coverage_development_dataset.py` as a separate,
explicitly label-informed development protocol. It reuses the hash-bound RF00022
source and records paired-column coverage for every candidate, then selects
complete, nonredundant records. The prior 15 family selections remain fixed.
The new protocol selected two complete RF00022 references. Its final dataset
contains **130 selected records**, including **61 complete training** and
**22 complete validation** pair references across 12 and four families.
The other 47 selected records retain unsupported status. All declared aggregate
and per-family data gates now pass. `train.json` and `validation.json` are at
`results/family_coverage_development_runs/20261016T011555.025711Z/`, with a
hash-bound `binding.json`, manifest and replay audit. Directory stamps are UTC.

The README, roadmap and development review reflect the new dataset. The user's
README picture HTML and attachment URL are preserved. No model fitting,
inference, checkpoint selection or GitHub publication occurred.

## Verification

- Frozen extension source and coverage dataset replay passed. The final
  summary reports `dataset_ready: true` and `model_training_performed: false`.
- Focused extension and coverage tests: **3 passed**.
- Full suite: **826 passed in 216.40 seconds**; log
  `reports/family-coverage-full-suite-2026-10-15.log`.
- `git diff --check` passed and both new scripts compile.

## Pending work

Build a fresh pair-set training adapter and frozen training protocol for
baseline, stack and helix heads under the previously declared three random
seeds, ten epochs, CPU bounds and validation-only checkpoint selection. Existing
training scripts expect dot-bracket structures; the new dataset preserves
explicit pair sets, including crossing contacts, so conversion must not silently
drop gold pairs. Record exposure events before fitting. Keep the prior failed
runs and the label-informed selection disclosure visible. The new validation
split is development data, not an independent test. Independent biological
structure validation, long biological RNA, causal stability and retained
function remain open.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-15_V2.md
cat reports/family_coverage_development_review_2026-10-15.md
cat results/family_coverage_development_summary.json
.venv/bin/python scripts/extend_family_provenance_dataset.py --verify results/family_provenance_extension_summary.json
.venv/bin/python scripts/derive_coverage_development_dataset.py --verify results/family_coverage_development_summary.json
.venv/bin/python -m pytest -q tests/test_family_provenance_extension.py tests/test_family_coverage_development.py
```

Before a training protocol, inspect
`configs/family_provenance_dataset_2026-10-14.json` and the `train.json`,
`validation.json`, `binding.json` files in the final run above. No fresh
pair-set training command exists yet. Before future publication, inspect the
live GitHub README and merge upstream edits while preserving the user's picture.
