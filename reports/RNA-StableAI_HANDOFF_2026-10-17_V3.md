# RNA-StableAI handoff — 2026-10-17 V3

Project: RNA-StableAI  
Date: 2026-10-17 (America/Los_Angeles)  
Version: V3  
Workspace: `/home/zyliu/Documents/rna-stable-ai`

## Completed work

- Continued Step 2 with a frozen additive score-offset diagnostic across all six fixed-final checkpoints at top-64 candidate retention. See `reports/long_score_offset_study_2026-10-17.md`.
- Across three seeds, the control arm's mean pair F1 was 0.2889 at zero offset and 0.2967 at +0.5. The extended arm's was 0.3123 at zero and 0.3189 at +1.0. Best offsets varied by checkpoint and gains were small. Positive offsets only rescored already retained positive candidates.
- Kept all work local; no README, GitHub publication, checkpoint promotion, or inference default changed.

## Verification

- Frozen protocol and run replay passed, including source/code hashes, all six exact zero-offset matches to the prior top-64 outputs, per-record pair scores, and aggregate pair counts.
- Six focused tests passed (`test_long_exact_sparse_pairs.py`, `test_sampled_pair_supervision.py`); the new script compiled.
- Peak process RSS for the sequential study was 721,024 KiB. Canonical result: `results/long_score_offset_runs/20261017T184134.981159Z/summary.json`.

## Pending work

- Investigate candidate ranking and learned objectives using development data, keeping native controls as reference baselines.
- Resolve bpRNA training-family provenance and freeze a genuinely independent family-separated long validation panel, including 4,000–4,999 nt if feasible. This label-informed 11-reference cohort cannot establish generalization or a production calibration.
- Preserve the user-added GitHub README picture and upstream edits before any future publication.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/long_score_offset_study_2026-10-17.md
.venv/bin/python scripts/study_long_score_offset.py --verify-protocol results/long_score_offset_protocol_runs/20261017T184132.522583Z/manifest.json
.venv/bin/python scripts/study_long_score_offset.py --verify-run results/long_score_offset_runs/20261017T184134.981159Z/summary.json
.venv/bin/python -m pytest -q tests/test_long_exact_sparse_pairs.py tests/test_sampled_pair_supervision.py
cat reports/long_candidate_budget_matched_2026-10-17.md
```
