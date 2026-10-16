# RNA-StableAI handoff — 2026-10-16 V7

Project: RNA-StableAI. Date: 2026-10-16 (America/Los_Angeles). Version: V7.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
State: the user completed the requested local checks. The second reference
pool is verified but fails the sequence-selected family-coverage upper bound.
There is no validated release.

## Completed work

Recorded the user's terminal results: 13 focused tests passed in 0.10 seconds;
the metadata-only pool replay passed; and the sequence-only acquisition replay
passed. The repeated metadata-pool success line comes from the acquisition
audit replaying its parent protocol.

Refreshed the metadata-only family/PDB inventory using the completed screen's
exposure ledger. It now counts 5,061 exposed sequence records, 72 exposed
families and 241 exposed PDBs. Fifty-four mapped families remain unexposed
metadata candidates; only 16 have at least three distinct unexposed mapped
PDBs. These are not sequence-diversity or reference-readiness counts. Recorded
the implication in
`reports/source_feasibility_after_sequence_screen_2026-10-16.md`.

No additional source panel was frozen or acquired. No contacts or model
predictions were requested. No GitHub upload occurred. Historical work at
5,000 nt and above remains preserved.

## Verification

- User terminal: **13 passed in 0.10s**.
- User terminal: metadata-only pool replay passed.
- User terminal: sequence-only acquisition replay passed.
- Read-only metadata inventory recomputation completed for planning; no local
  computing tests were launched by the assistant after the user's preference.

## Pending work

Broaden sequence-aware source discovery beyond the retained Rfam 3D mapping
and consumed families/PDBs. Freeze the next source and selection protocol
before reading contact labels. Continue exact source-sequence binding,
annotation-lineage and tool-training provenance audits. Do not infer reference
coverage from PDB counts. The active project scope is 1–4,999 nt; individual
methods may require stricter limits.

The user prefers to run local computing tests in their own terminal. Provide
commands and interpret returned output rather than launching tests.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-16_V7.md
cat reports/source_feasibility_after_sequence_screen_2026-10-16.md
cat reports/sequence_screening_pool_review_2026-10-16.md
jq '{candidate_count,source_sequences_bound,selected_before_contacts,selection_reason_counts}' results/structure_pool_sequence_summary.json
```

If local regression tests are needed after new edits, ask the user to run:

```bash
.venv/bin/python -m pytest -q tests/test_project_scope.py tests/test_sequence_diverse_structure_panel.py tests/test_structure_pool_sequences.py
```

Before any future GitHub publication, inspect the live README and preserve the
user's picture and any repository image assets.
