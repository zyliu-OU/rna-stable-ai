# RNA-StableAI handoff — 2026-10-16 V21

Project: RNA-StableAI  
Date: 2026-10-16 (America/Los_Angeles)  
Version: V21  
Workspace: `/home/zyliu/Documents/rna-stable-ai`

## Completed work

- Resumed Step 2 core-model development within the active 1–4,999 nt scope. The prior 27-record bpRNA extension trained through 1,014 nt, while its reused validation cohort ends at 387 nt; no longer-sequence accuracy claim follows from it.
- Added `src/rnastable/sampled_pair_supervision.py`. It accepts complete pair references up to 4,999 nt, retains every legal canonical reference pair, counts unsupported reference pairs, and samples a bounded number of legal negatives using a reproducible seed. It avoids building a quadratic all-pairs label tensor. This is a development labeler; sampled loss is not equivalent to the existing full-pair objective.
- Added `tests/test_sampled_pair_supervision.py` covering a 4,999-nt record, exact gold retention, deterministic sampling, legal pair chemistry, unsupported contacts, scope rejection, and agreement with full-pair labels when the short-record sample is exhaustive.
- No long-sequence source record was selected or read for this change. No training, inference, default change, README edit, or publication occurred. The independent structure-validation gate remains open.

## Verification

- Focused suite: 34 passed (`test_sampled_pair_supervision.py`, `test_bprna_training_subset_v2.py`, `test_bprna_length_pilot.py`, `test_pair_reference.py`).
- Python compilation and whitespace checks passed for the new module and tests.
- A synthetic 4,999-nt run returned 100 legal positives and 400 sampled negatives with zero excluded gold pairs in 1.09 s wall time; process peak RSS was 620,036 KiB, including Python/PyTorch startup. This is a label-generation smoke check, not a training-memory result.

## Pending work

- Freeze a family- and sequence-separated longer development-validation cohort with complete pair labels before further model tuning. The bpRNA source-group labels alone do not establish family separation. Previously exposed bpRNA pool sequences must not be presented as independent tests.
- Integrate sampled supervision into a separately versioned, resource-bounded training protocol for 1,025–4,999 nt. Compare it with full-pair training on short sequences, then run matched seeds and length-band validation. Record negative-sampling limits and measure actual training memory/time.
- Preserve all historical 5,000-nt-and-longer assets while keeping them outside active development. Keep independent biological structure validation separate. Before any GitHub publication, inspect the live README and preserve the user's picture markup and image assets.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/RNA-StableAI_HANDOFF_2026-10-16_V21.md
.venv/bin/python -m pytest -q tests/test_sampled_pair_supervision.py tests/test_bprna_training_subset_v2.py tests/test_bprna_length_pilot.py tests/test_pair_reference.py
.venv/bin/python -m py_compile src/rnastable/sampled_pair_supervision.py tests/test_sampled_pair_supervision.py
git diff --check -- src/rnastable/sampled_pair_supervision.py tests/test_sampled_pair_supervision.py reports/RNA-StableAI_HANDOFF_2026-10-16_V21.md
sed -n '1,220p' src/rnastable/sampled_pair_supervision.py
sed -n '1,170p' src/rnastable/pair_set_training.py
```
