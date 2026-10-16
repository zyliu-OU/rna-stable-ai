# RNA-StableAI handoff — 2026-10-16 V5

Project: RNA-StableAI. Date: 2026-10-16 (America/Los_Angeles). Version: V5.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
State: development stopped at the user's request. No new protocol was frozen,
no data was acquired, and no model inference or GitHub upload occurred in this
development turn.

## Completed work

Reviewed the existing second-panel draft in
`configs/fresh_structure_panel_2026-10-16.json`,
`scripts/plan_sequence_diverse_structure_panel.py`, and
`tests/test_sequence_diverse_structure_panel.py`. The draft chooses spaced PDB
accession identifiers. That spacing does not demonstrate diversity of RNA
sequences, so its current “sequence-diverse” claim needs correction before the
panel is frozen. The existing 512 nt candidate cap lies within the project's
active range of 1–4,999 nt.

Read the official RCSB PDB Data API documentation for a possible future
sequence-metadata screening stage. No API requests for candidates were made.
The three draft files were not edited during this turn.

## Verification

Confirmed the local date is 2026-10-16 PDT and V4 was the latest existing
handoff. Confirmed the three draft files still exist in the workspace. No
tests or scientific audits were run in this turn.

## Pending work

Development is stopped. If resumed, revise the draft to distinguish a
predeclared PDB candidate pool from a sequence-diversity screen. Verify the
chain-identifier mapping and sequence source before acquiring any contact
labels. Review and test the revised protocol, then freeze it before fetching
candidate labels. Keep exposure and unsupported-record accounting intact.
The independent biological reference gate remains closed. Historical work at
5,000 nt and above remains preserved and deferred.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-16_V5.md
cat docs/LENGTH_SCOPE.md
cat configs/fresh_structure_panel_2026-10-16.json
sed -n '1,260p' scripts/plan_sequence_diverse_structure_panel.py
.venv/bin/python -m pytest -q tests/test_sequence_diverse_structure_panel.py
```

Before any future GitHub publication, inspect the live README and preserve
the user's picture and any repository image assets.
