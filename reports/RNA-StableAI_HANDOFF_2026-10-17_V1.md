# RNA-StableAI handoff — 2026-10-17 V1

Project: RNA-StableAI  
Date: 2026-10-17 (America/Los_Angeles)  
Version: V1  
Workspace: `/home/zyliu/Documents/rna-stable-ai`

## Completed work

- Continued Step 2 structure-model development with a frozen, replayable candidate-budget pilot in `scripts/study_long_candidate_budget.py` and `reports/long_candidate_budget_pilot_2026-10-17.md`.
- Evaluated the fixed final seed-1729 checkpoint from the 105-record sampled-pair arm on the existing 11-reference development cohort. The same model scores and exact decoder were used at 16, 32, and 64 retained candidates per endpoint.
- Mean pair F1 was 0.2869, 0.2897, and 0.3014, respectively. Legal gold candidate recall was 62.31%, 72.33%, and 79.47%. Top 64 improved 7 records and worsened 4 relative to top 16. No inference default or release gate changed.
- Preserved an initial run whose summary had a key collision; its predictions remain available. Corrected the writer and froze a new V2 protocol. Canonical result: `results/long_candidate_budget_pilot_v2_runs/20261017T183020.985904Z/summary.json`.

## Verification

- V2 replay verified frozen source/code hashes, candidate counts and recall, per-record pair F1, and an exact top-16 structure match to the prior saved predictions.
- `tests/test_long_exact_sparse_pairs.py`: 2 passed. `py_compile` passed for the new script.
- Peak process RSS was 735,924 KiB. The 64-candidate decoder took 8.41 s across 11 RNAs versus 3.15 s at 16 candidates, excluding shared candidate scoring.

## Pending work

- Repeat the predeclared budget study across all three matched seeds and both training arms; consider score calibration or decoder alternatives using development data only.
- Resolve family provenance for the 17 added bpRNA training records. Obtain an independent family-separated long validation panel, including 4,000–4,999 nt if feasible.
- Keep the native controls and independent validation gate. The current label-informed 11-reference panel does not support a generalization claim or checkpoint promotion. Preserve the user-added GitHub README picture before any future publication; no README or GitHub publication occurred in this handoff.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/long_candidate_budget_pilot_2026-10-17.md
.venv/bin/python scripts/study_long_candidate_budget.py --verify-protocol results/long_candidate_budget_pilot_v2_protocol_runs/20261017T183019.984723Z/manifest.json
.venv/bin/python scripts/study_long_candidate_budget.py --verify-run results/long_candidate_budget_pilot_v2_runs/20261017T183020.985904Z/summary.json
.venv/bin/python -m pytest -q tests/test_long_exact_sparse_pairs.py
cat reports/long_length_step2_review_2026-10-16.md
```
