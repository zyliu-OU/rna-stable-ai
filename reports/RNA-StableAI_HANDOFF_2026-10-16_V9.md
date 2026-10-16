# RNA-StableAI handoff — 2026-10-16 V9

Project: RNA-StableAI. Date: 2026-10-16 (America/Los_Angeles). Version: V9.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Active project focus: 1–4,999 nt; retain all historical work at 5,000 nt and above. The prospective structure-reference method retains a stricter 20–512-nt sequence-screen limit.

## Completed work

- Recorded the user's local results: both BGSU metadata tests passed in 0.12 seconds; BGSU acquisition replay passed; and the metadata inventory was generated successfully.
- The inventory has 17,217 data rows, 215 row-level metadata candidates, 44 candidate families, and four families with at least three deduplicated metadata candidates. The four are RF00386 (10), RF01684 (4), RF02348 (6), and RF03072 (5), totaling 25 candidate PDB/class representatives. These are metadata counts, not independent sequence or validated reference counts.
- Added `configs/bgsu_sequence_pool_2026-10-16.json` and `scripts/freeze_bgsu_sequence_pool.py` to freeze exactly those four families and their candidate order. The protocol snapshots the source inventory, exposure ledger, configuration, selected PDB/auth-chain identifiers, and driver hash. Replay checks the acquired source and snapshot bytes. It authorizes no contact acquisition or inference.
- Added focused fixture test `tests/test_bgsu_sequence_pool.py`. No GitHub upload occurred; README and picture were untouched.

## Verification

- User terminal: `2 passed in 0.12s`; BGSU metadata acquisition replay passed.
- User terminal inventory result: 44 candidate families; four with at least three metadata candidates. Row dispositions: 6,945 exposed-family, 1,605 exposed-clan, 4,950 unresolved/proposed Rfam, 3,398 non-RNA, 104 outside observed-length proxy, and 215 metadata-candidate rows (plus one header).
- Read-only inspection identified the four families and confirmed no duplicate PDB accession among their 25 selected metadata rows.
- The newly added freeze test and freeze/replay have **not** been run by the assistant, per the user's terminal-testing preference.

## Pending work

User runs the focused freeze test, freezes the pool, and replays it locally. Inspect the resulting counts and manifest. Then build/freeze a separate sequence-only RCSB acquisition protocol before any sequence fetch; exact full-chain length, sequence overlap with prior exposures, and within-panel diversity must be screened and all read sequences durably exposed. Do not infer sequence independence from NR class or taxon alone. Contact labels, structural identity and tool-training provenance remain unaudited. No model inference or release is authorized.

Before any future GitHub publication, inspect the live README and preserve the user's picture markup and image assets.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python -m pytest -q tests/test_bgsu_nr_metadata.py tests/test_bgsu_sequence_pool.py
.venv/bin/python scripts/plan_bgsu_nr_metadata.py --verify results/bgsu_nr_metadata_inventory_2026-10-16.json
.venv/bin/python scripts/freeze_bgsu_sequence_pool.py
.venv/bin/python scripts/freeze_bgsu_sequence_pool.py --verify results/bgsu_sequence_pool_protocol.json
jq '.candidate_counts' "$(jq -r '.run_dir' results/bgsu_sequence_pool_protocol.json)/selection.json"
```

The freeze command refuses to overwrite an existing protocol pointer. If it already exists, use the `--verify` command rather than deleting any protocol artifacts. Return the terminal output before sequence acquisition.
