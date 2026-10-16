# RNA-StableAI handoff — 2026-10-16 V8

Project: RNA-StableAI. Date: 2026-10-16 (America/Los_Angeles). Version: V8.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Active development scope: 1–4,999 nt; preserve all historical work at 5,000 nt and above.

## Completed work

- Froze a metadata-only BGSU RNA 3D Hub nonredundant-set source protocol for release 4.61 at 3.5 Å in `configs/bgsu_nr_source_2026-10-16.json` and `scripts/acquire_bgsu_nr_source.py`. No candidate sequences, contact labels, or model predictions were requested.
- Acquired the fixed JSON export (16,338,632 bytes) in `results/bgsu_nr_source_runs/20261016T170022.196778Z/`. Its acquisition self-audit passed. An earlier sandbox network failure remains separately journaled; the convenience pointer `results/bgsu_nr_source_summary.json` now references the successful run.
- Added `scripts/plan_bgsu_nr_metadata.py` to screen that export against the durable exposure ledger and retained clan metadata. It excludes proposed/unresolved Rfam mappings, exposed families/clans/PDBs, non-RNA and multichain IFEs, and structures outside the observed-length proxy of 20–4,999 nt. It reports one candidate per PDB and NR equivalence class, but does not assert sequence independence or validated reference coverage.
- Added focused fixture tests in `tests/test_bgsu_nr_metadata.py`. No GitHub upload occurred and the README picture was not touched.

## Verification

- BGSU source acquisition self-audit passed immediately after download. The successful `source.json` exists and its recorded size is 16,338,632 bytes.
- The earlier failed acquisition remains auditable. The source pointer was corrected to the successful summary without changing either run.
- The metadata inventory and new focused tests have **not** been run by the assistant, in accordance with the user's preference to run local computing tests in their terminal. Counts of newly eligible families are therefore pending.
- Prior user terminal results: 13 focused tests passed; metadata-only pool replay and sequence-only acquisition replay passed (see V7).

## Pending work

Run the focused tests and generate/verify the BGSU metadata inventory locally. Review the resulting eligible-family and class counts before freezing a new sequence-only selection protocol. Exact full-chain length <5,000 nt, sequence independence, structure identity, contact provenance, and reference readiness all remain unverified. Do not download contacts or perform model inference based on metadata counts alone.

If a later GitHub publication is requested, first inspect the live README and preserve the user's picture markup and image assets; do not publish an older README snapshot.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python -m pytest -q tests/test_bgsu_nr_metadata.py
.venv/bin/python scripts/acquire_bgsu_nr_source.py --verify results/bgsu_nr_source_runs/20261016T170022.196778Z/summary.json
.venv/bin/python scripts/plan_bgsu_nr_metadata.py --output results/bgsu_nr_metadata_inventory_2026-10-16.json
.venv/bin/python scripts/plan_bgsu_nr_metadata.py --verify results/bgsu_nr_metadata_inventory_2026-10-16.json
jq '{row_dispositions,candidate_family_count,families_with_three_metadata_candidates}' results/bgsu_nr_metadata_inventory_2026-10-16.json
```

Return the command output for review before any sequence acquisition. The `--output` command uses exclusive creation and will refuse to overwrite an existing inventory; if it already exists, use `--verify` and inspect it rather than deleting it.
