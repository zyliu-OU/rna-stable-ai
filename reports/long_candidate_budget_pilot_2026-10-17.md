# RNA-StableAI Step 2: bounded candidate-budget pilot

Date: 2026-10-17 (America/Los_Angeles)  
Workspace: `/home/zyliu/Documents/rna-stable-ai`

The frozen final checkpoint from the 105-record, seed-1729 sampled-pair arm was evaluated on the existing 11-reference, four-family, label-informed longer-RNA development cohort. All budgets used the same model scores and bounded exact sparse decoder. The 16, 32, and 64 positive legal partners per right endpoint were declared before the run. Top-16 structures matched the earlier saved predictions exactly.

| Candidate limit | Mean record pair F1 | Legal gold candidate recall | Total retained candidates | Total decoder time |
| ---: | ---: | ---: | ---: | ---: |
| 16 | 0.2869 | 62.31% | 354,876 | 3.15 s |
| 32 | 0.2897 | 72.33% | 626,556 | 5.27 s |
| 64 | 0.3014 | 79.47% | 1,004,014 | 8.41 s |

The top-64 F1 difference from top-16 is +0.0145. Seven of 11 records improved and four worsened. Peak process RSS for the sequential three-budget run was 735,924 KiB; this is a process peak, not a per-budget memory measurement. Candidate scoring was done once at top 64 and subsets were decoded separately, so the decoder times exclude candidate scoring and are not full inference latencies.

This shows that candidate retention is a real bottleneck for this checkpoint, while more candidates alone recover only a small fraction of the gap to the native controls (0.4742 LinearFold and 0.4499 ViennaRNA mean pair F1 on this panel). The panel is small, contains related records, and was selected using label completeness. Training-family lineage is unresolved. No independent validation or production default change follows from this result.

The first frozen pilot at `results/long_candidate_budget_pilot_runs/20261017T182924.151816Z` completed prediction but its summary writer used the `budgets` key twice, leaving only the budget list in the summary. Those artifacts were preserved. The corrected V2 protocol and result are canonical for this pilot:

- Protocol: `results/long_candidate_budget_pilot_v2_protocol_runs/20261017T183019.984723Z/manifest.json`
- Result: `results/long_candidate_budget_pilot_v2_runs/20261017T183020.985904Z/summary.json`
- Script: `scripts/study_long_candidate_budget.py`

Verification: the V2 run replay passed, including source and code hashes, the saved top-16 prediction match, per-record pair scores, and aggregate candidate counts and recall. The focused exact-decoder tests passed (2 tests), and the script compiled.

Next: repeat a predeclared budget comparison across all three seeds and both training arms, then investigate score calibration and decoding methods on development data. Resolve bpRNA training-family provenance and obtain a truly independent long-reference panel before making a generalization claim.
