# RNA-StableAI handoff — 2026-10-16 V14

Project: RNA-StableAI. Date: 2026-10-16 (America/Los_Angeles). Version: V14.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Active scope: 1–4,999 nt; preserve historical data at 5,000 nt and above. The user prefers the assistant to run local commands and tests directly.

## Completed work

- Continued the core-model length-coverage pivot rather than independent structure validation. Confirmed that the current family-pair-set training cohort is only 61–360 nt, validation 46–387 nt, and the retained CRW longer-training attempt had no records at 1,025–4,096 nt.
- Located the official bpRNA-1m dot-bracket-only archive as a training-only candidate. Its ZIP is 45,237,373 bytes; the 4,023,074,135-byte bpRNA-1m(90) full archive was not downloaded. Added fixed source config and `scripts/acquire_bprna_training_source.py`; froze the source, preserved an initial sandbox-network failure, then acquired and replayed the successful run `results/bprna_training_source_runs/20261016T173354.858608Z/`.
- Added header-only length inventory code and a v2 recovery pass for 538 comma-wrapped length headers. All 102,318 DBN files now have a parsed *stated* length: 83,448 at 1–399 nt; 4,772 at 400–1,024 nt; 14,098 at 1,025–4,999 nt; none at 5,000 nt or longer. No candidate sequence or structure string was read during these inventories.
- Added focused tests and `reports/bprna_training_length_review_2026-10-16.md`. The official bpRNA [download page](https://bprna.cgrb.oregonstate.edu/download.php) and [about page](https://bprna.cgrb.oregonstate.edu/about.php) identify the dataset and its multi-source origins. This is a training-source candidate, not an independent test panel.
- No model fit, inference-default change, contact acquisition, GitHub upload, or README edit occurred. All historical long-size work remains retained.

## Verification

- Four focused bpRNA source/inventory tests passed in 0.05 seconds.
- Acquired ZIP source replay passed. Original and recovered inventories were created; recovered v2 inventory replay passed separately.
- Read-only ZIP inspection confirmed the DBN layout and the malformed comma-wrapped header format. All 538 were recovered by v2; zero unresolved headers remain.
- These are header-length counts only. Actual sequence/structure lengths, valid pair labels, source overlaps, and family/validation leakage remain unverified.

## Pending work

Freeze a small, declared **training-only** subset from the 4,772 header candidates at 400–1,024 nt, then read and validate only those selected sequences/structures. Record every read sequence in a durable exposure event, screen overlap with existing validation/test/exposure ledgers, and retain all exclusions before fitting. Use the existing model and validation baseline for a matched development-only comparison; do not claim independent accuracy. The 14,098 records at 1,025–4,999 nt need a bounded sparse-training method before fitting, because the current full-pair trainer caps at 1,024 nt. Keep the independent structure-reference work separately unresolved.

Before any future GitHub publication, inspect the latest live README and preserve the user's picture markup and image assets.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/acquire_bprna_training_source.py --verify results/bprna_training_source_runs/20261016T173354.858608Z/summary.json
.venv/bin/python scripts/inventory_bprna_training_lengths_v2.py --verify results/bprna_training_length_inventory_2026-10-16_v2.json
.venv/bin/python -m pytest -q tests/test_bprna_training_source.py tests/test_bprna_training_lengths.py tests/test_bprna_training_lengths_v2.py
jq '{length_band_counts,source_group_length_band_counts,recovered_comma_length_header_count,unresolved_header_count,candidate_sequences_read,structure_labels_read}' results/bprna_training_length_inventory_2026-10-16_v2.json
cat reports/bprna_training_length_review_2026-10-16.md
```

These local commands are for the assistant to run as needed, not routine work to hand back to the user.
