# RNA-StableAI handoff — 2026-10-17 V2

Project: RNA-StableAI  
Date: 2026-10-17 (America/Los_Angeles)  
Version: V2  
Workspace: `/home/zyliu/Documents/rna-stable-ai`

## Completed work

- Extended the frozen top-16/32/64 candidate-budget study from one checkpoint to all three matched seeds and both sampled-pair training arms. Results and interpretation are in `reports/long_candidate_budget_matched_2026-10-17.md`.
- Mean pair F1 across seeds rose from 0.2605 to 0.2889 in the 88-record arm and from 0.2960 to 0.3123 in the 105-record arm between top 16 and top 64. The extended arm stayed ahead at every budget, with a smaller mean advantage at top 64 (+0.0234) than top 16 (+0.0355).
- Inspected the 17 added bpRNA training records and their source archive. They comprise 7 CRW and 10 RFAM source-group records; the local DBN headers have no family IDs. Family separation from the development references remains unresolved.
- Kept the work local. No README, GitHub publication, model inference default, or release gate changed.

## Verification

- Frozen matched protocol and run replay passed. All six top-16 prediction sets matched the prior saved outputs exactly; per-record scores, candidate counts and recall, and paired differences were checked.
- Six focused tests passed (`test_long_exact_sparse_pairs.py`, `test_sampled_pair_supervision.py`); the new driver compiled.
- Peak process RSS for the sequential study was 738,124 KiB. Decoder times exclude candidate scoring.

## Pending work

- Resolve source-level family provenance for the added bpRNA records and obtain independent, family-separated long references, preferably including the 4,000–4,999-nt active range.
- Use development-only comparisons to improve score calibration or decoded pair recovery. Keep native controls and the independent structure-validation gate; the current label-informed 11-reference panel does not justify promotion.
- Preserve the user-added GitHub README picture and upstream edits before any future publication.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/long_candidate_budget_matched_2026-10-17.md
.venv/bin/python scripts/study_long_candidate_budget_matched.py --verify-protocol results/long_candidate_budget_matched_protocol_runs/20261017T183354.499840Z/manifest.json
.venv/bin/python scripts/study_long_candidate_budget_matched.py --verify-run results/long_candidate_budget_matched_runs/20261017T183356.669629Z/summary.json
.venv/bin/python -m pytest -q tests/test_long_exact_sparse_pairs.py tests/test_sampled_pair_supervision.py
cat reports/long_length_step2_review_2026-10-16.md
```
