# RNA-StableAI handoff — 2026-10-16 V12

Project: RNA-StableAI. Date: 2026-10-16 (America/Los_Angeles). Version: V12.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Active project scope: 1–4,999 nt; preserve historical data at 5,000 nt and above. This prospective structure-reference method screens 20–512 nt.

## Completed work

- Recorded the user's readiness output: focused test passed (1 in 0.07 seconds), protocol and acquisition replays passed, and the sequence-count gate is true for 13 selected sequences (RF00386 4, RF01684 3, RF02348 2, RF03072 4). Supported-reference count remains zero and contact acquisition is not authorized.
- The user changed the local-computing preference: **run future local commands and tests as the assistant**, rather than asking the user to run them. This preference supersedes prior V7–V11 handoff notes.
- Added `scripts/audit_bgsu_family_lineage.py` and focused tests in `tests/test_bgsu_family_lineage.py`. The audit cross-checks each selected BGSU family/PDB/author-chain claim against the retained Rfam 15.1 PDB mapping, while separately marking unresolved exact sequence-to-coordinate identity.
- Created and replayed `results/bgsu_family_lineage_2026-10-16.json`. Results: **1 unambiguous cross-source family/chain match** (`RF00386:8dp3_R`), **1 ambiguous Rfam chain assignment** (`RF00386:8s95_C` maps to both RF00005 and RF00386), and **11 BGSU-only family/chain claims** with no match in the retained Rfam mapping. The initial quick text search suggested two corroborations, but detailed family/chain parsing corrected that to one; absence in Rfam 15.1 is not itself a disproof, including for newer PDBs.
- No contacts or model predictions were requested. No GitHub upload occurred; README picture was untouched.

## Verification

- Assistant local focused tests: `3 passed in 0.09s` for lineage/readiness tests.
- Assistant local expanded focused tests: `9 passed in 0.13s` across BGSU and prior sequence-screen tests.
- Family-lineage audit generated and its replay passed; parent BGSU source, pool, protocol, and sequence acquisition replays all passed during each audit.
- Read-only inspection confirmed the exact one-match/one-ambiguity/eleven-BGSU-only breakdown and retained PDB release dates. One BGSU-only record is from 2017, so missing Rfam mapping cannot be explained solely as a newer-PDB effect.

## Pending work

Resolve source annotation lineage and exact PDB author-chain/polymer-to-coordinate identity for selected sequences before any contact acquisition. The two Rfam hits on `8s95_C` may refer to overlapping regions on one chain; inspect region coordinates before interpreting the ambiguity. Consider a newer independently pinned family-mapping source for the 11 BGSU-only claims, with all source reads and exclusions journaled. Do not promote the numeric sequence gate to validated reference coverage. Contact provenance, tool-training provenance, and model inference remain closed.

Before any future GitHub publication, inspect the live README and preserve the user's picture markup and image assets.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/audit_bgsu_family_lineage.py --verify results/bgsu_family_lineage_2026-10-16.json
jq '{selected_sequence_count,status_counts,contact_acquisition_authorized}' results/bgsu_family_lineage_2026-10-16.json
jq -r '.records[] | [.id,.status,(.rfam_15_1_chain_families|join(",")),.pdb_release_date] | @tsv' results/bgsu_family_lineage_2026-10-16.json
rg -n -i '8s95' results/structure_derived_source_runs/20261015T021501.529110Z/source/pdb_full_region.txt results/structure_derived_source_runs/20261015T021501.529110Z/source/pdb_full_region_curated.txt
.venv/bin/python -m pytest -q tests/test_bgsu_*.py tests/test_structure_pool_sequences.py
```

These local commands are for the assistant to run as needed; do not send routine test execution back to the user.
