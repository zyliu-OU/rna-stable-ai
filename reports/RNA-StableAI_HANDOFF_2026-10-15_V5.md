# RNA-StableAI handoff — 2026-10-15 V5

Project: RNA-StableAI. Date: 2026-10-15 (America/Los_Angeles). Version: V5.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
State: active development. A new biological structure candidate panel is
frozen, but independent biological validation and a validated release remain
unfinished.

## Completed work

Continued from V4's metadata-only inventory. Added
`scripts/acquire_fresh_structure_metadata.py` and froze 92 missing Rfam 15.1
family-description requests. The initial sandbox attempt failed on DNS and is
retained. The approved network acquisition validated **91/92** responses;
RF04222 returned **HTTP 404** and remains unresolved. The successful acquisition
and its response hashes replay from
`results/fresh_structure_metadata_summary.json`.

Updated `scripts/audit_fresh_structure_inventory.py` so V4's historical audit
can still replay against its frozen metadata paths after new descriptions
arrived. The refreshed inventory,
`results/fresh_structure_inventory_after_metadata_2026-10-15.json`, finds 81
metadata candidate families, 38 family/PDB-exposed, 21 exposed-clan, one
development-source-screened and one unresolved.

Added `configs/fresh_structure_panel_2026-10-15.json` and
`scripts/freeze_fresh_structure_panel.py`. The replayable protocol at
`results/fresh_structure_panel_protocol.json` fixes eight families and **56
distinct PDB-chain candidates** before reading contact labels: RF00015,
RF00080, RF00100, RF01734, RF01763, RF01831, RF02977 and RF03013. All pass
the current family/clan/PDB metadata screen. Selection order, family caps,
future binding rules and no-replacement policy are frozen. Updated the README,
roadmap and `reports/fresh_structure_metadata_and_panel_review_2026-10-15.md`.
The user's README picture is preserved. No GitHub publication occurred.

## Verification

- Frozen metadata acquisition replay passed; 91 successes and one explicit
  404 failure.
- Both V4 and refreshed inventory replays passed.
- Panel freeze replay passed; eight families and 56 candidate requests.
- Focused tests: **2 passed**; Python compilation and `git diff --check` passed.
- No new structure labels, candidate sequences, contacts or model predictions
  were read. No independent accuracy claim was made.

## Pending work

Acquire exactly the 56 frozen BGSU RNA 3D Hub contact responses with bounded
requests and durable journals. Bind source sequences first, screen overlap
against the exposure ledger and within the panel, retain source failures and
unsupported records without replacement, then parse full raw cWW contacts.
Audit annotation lineage and tool-training provenance. Run the declared
reference-readiness gate: at least 12 supported references and three families
with at least three each. Only if the gate passes should new model inference
be considered. RF04222 remains an unresolved metadata 404; it is not in the
frozen panel. Long biological RNA, causal stability, mutation effects and
retained function remain open.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-15_V5.md
cat reports/fresh_structure_metadata_and_panel_review_2026-10-15.md
.venv/bin/python scripts/acquire_fresh_structure_metadata.py --verify results/fresh_structure_metadata_summary.json
.venv/bin/python scripts/audit_fresh_structure_inventory.py --verify results/fresh_structure_inventory_2026-10-15.json
.venv/bin/python scripts/audit_fresh_structure_inventory.py --verify results/fresh_structure_inventory_after_metadata_2026-10-15.json
.venv/bin/python scripts/freeze_fresh_structure_panel.py --verify results/fresh_structure_panel_protocol.json
.venv/bin/python -m pytest -q tests/test_fresh_structure_inventory.py tests/test_fresh_structure_metadata.py
sed -n '1,320p' scripts/prepare_raw_structure_references.py
```

Before any future publication, inspect the live GitHub README and merge
upstream edits while preserving the user's picture HTML and any repository
image assets.
