# RNA-StableAI handoff — 2026-10-16 V15

Project: RNA-StableAI. Date: 2026-10-16 (America/Los_Angeles). Version: V15.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Active scope: 1–4,999 nt; retain all historical data and information for 5,000 nt and above. The assistant runs local commands and tests for the user.

## Completed work

- Advanced core-model length development separately from the unresolved independent-structure validation gate.
- Froze a 60-record, metadata-selected bpRNA-1m training-only pool at stated lengths 400–1,024 nt. The first sequence screen was interrupted during slow overlap checking after its exposure event was durably recorded; its artifacts remain intact. A v2 screen used an exact bit-parallel LCS upper-bound prefilter before the unchanged overlap rule. The v2 run screened all 60 records and retained 27 training-only examples (16 CRW, 11 RFAM; actual lengths 400–1,014 nt). Of the other 33, six had unsupported source records, five overlapped prior exposures, and 22 were redundant within the pool. All 54 valid sequences were recorded as exposed.
- Added a frozen, matched single-seed helix training pilot: the previous 61 training records plus the 27 longer records (88 total), the same 22 development-validation records, the same seed/configuration, ten epochs, and unchanged exact top-16 decoder. Initial weights were bitwise equal to the prior control. No inference default changed.
- The selected pilot checkpoint reached mean validation full-pair F1 **0.491062** versus **0.489149** for the prior control, a development difference of **+0.001913**. This is a small single-seed result on reused validation, not an independent accuracy gain. Training length reaches 1,014 nt, but validation length reaches only 387 nt; longer-RNA generalization remains unmeasured.
- The pilot protocol is `results/bprna_length_pilot_protocol_runs/20261016T174446.305367Z/manifest.json`; completed result is `results/bprna_length_pilot_runs/20261016T174449.083968Z/summary.json`. The screened cohort is `results/bprna_training_subset_v2_runs/20261016T174219.360435Z/summary.json`.
- No GitHub upload, README edit, independent test evaluation, or structure-contact acquisition occurred. Preserve the user's GitHub README picture before any publication.

## Verification

- Thirty-five focused tests passed in 1.12 seconds, covering subset selection, v2 overlap filtering, pilot configuration, pair-reference rules, and family-pair-set training.
- The frozen subset v2 and pilot both completed self-audits. An independent replay of the pilot summary/checkpoints/predictions passed.
- The pilot summary confirms 88 training records, 22 reused validation records, 27 longer additions, selected epoch 10, no test evaluation, no independent-accuracy claim, and no default change.

## Pending work

- Freeze a genuinely held-out **longer** development-validation cohort before any further model tuning, with family/sequence/exposure separation and complete pair labels. Do not reuse the already-exposed 54 pool sequences as an independent test. Evaluate per-length-band behavior and at least multiple seeds before deciding whether the longer training extension is useful.
- The current full-pair trainer is capped at 1,024 nt. Design and test bounded sparse training before using the preserved 1,025–4,999 nt bpRNA inventory. Keep the 5,000+ nt historical work intact but outside active development.
- Independent structure validation remains a separate unresolved gate. Do not turn training-only bpRNA structures into independent test evidence.
- Before any GitHub publication, inspect the latest live README and merge/preserve the user's picture markup and image assets.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python -m pytest -q tests/test_bprna_training_subset.py tests/test_bprna_training_subset_v2.py tests/test_bprna_length_pilot.py tests/test_family_pair_set_training.py tests/test_pair_reference.py
.venv/bin/python scripts/prepare_bprna_training_subset_v2.py --verify results/bprna_training_subset_v2_runs/20261016T174219.360435Z/summary.json
.venv/bin/python scripts/run_bprna_length_pilot.py --verify results/bprna_length_pilot_runs/20261016T174449.083968Z/summary.json
jq '{candidate_count,valid_sequence_count,selected_training_only_count,reason_counts}' results/bprna_training_subset_v2_runs/20261016T174219.360435Z/summary.json
jq '{train_records,validation_records,new_longer_train_records,train_max_length_nt,validation_max_length_nt,extended_validation_full_pair_f1,control_validation_full_pair_f1,development_f1_difference,test_evaluated,independent_accuracy_claim}' results/bprna_length_pilot_runs/20261016T174449.083968Z/summary.json
```

These are assistant-run replay commands. The next development implementation is the separated longer validation cohort; no such cohort or independent long-length score exists yet.
