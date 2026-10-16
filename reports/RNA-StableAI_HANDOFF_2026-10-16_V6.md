# RNA-StableAI handoff — 2026-10-16 V6

Project: RNA-StableAI. Date: 2026-10-16 (America/Los_Angeles). Version: V6.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
State: development continued through a frozen metadata pool and a completed
sequence-only screen. Independent biological validation remains blocked; there
is no validated release. The user requested that future local computing tests
be given as terminal commands rather than run by the assistant.

## Completed work

Corrected the published draft's unsupported claim that spaced PDB IDs imply
sequence diversity. Revised `configs/fresh_structure_panel_2026-10-16.json`,
`scripts/plan_sequence_diverse_structure_panel.py` and their focused tests to
describe a metadata-only sequence-screening pool. Replaced the typically
~1,534-nt bacterial SSU rRNA family with an unexposed shorter family under the
panel's 512-nt method cap. Froze and replayed a 77-chain/eight-family pool at
`results/sequence_screening_pool_protocol.json`.

Added `scripts/screen_structure_pool_sequences.py` and focused tests. Froze
eight exact RCSB GraphQL sequence-only batches before acquisition at
`results/structure_pool_sequence_protocol.json`. The sandbox-only attempt
failed network access and remains retained. An approved network retry returned
all eight batches. The acquisition code audited its result and published
`results/structure_pool_sequence_summary.json`. All 76 valid source sequences
were recorded as validation exposure before any contact acquisition.

The screen selected 12 candidates from 77. Only RF02340 reached three selected
sequences. Thus the panel cannot meet the declared three-family/three-per-family
coverage threshold even if every selected contact graph succeeds. No contacts
were requested and no model inference ran. See
`reports/sequence_screening_pool_review_2026-10-16.md`.

## Verification

- Before the user's testing preference, focused tests passed: **13 passed**.
- Both new Python modules compiled before protocol freeze.
- Metadata-pool freeze replay passed.
- Sequence-only protocol audit passed.
- The successful sequence acquisition completed its built-in replay audit.
- Read-only inspection of the summary showed 77 candidates, eight successful
  batches, 76 valid source sequences, 62 redundant, two outside 20–512 nt, one
  unsupported, and 12 selected. Only one family has three selected.
- A separate, compute-heavy replay was stopped when the user requested terminal
  commands instead of assistant-run local tests. No further tests were run.
- No GitHub upload occurred in this development turn.

## Pending work

Do not acquire contacts for this cohort as a route to the current coverage
gate: the sequence-selected upper bound already fails. Plan a fresh family/PDB
cohort outside all recorded exposures, ideally with independent sequence
metadata before contact labels. Validate exact RCSB-to-BGSU sequence binding
before any reference claim. Audit per-sequence annotation truth and tool
training provenance. Preserve the failed cohort and all historical longer
sequence evidence.

The user will run local computing tests in their own terminal. Provide exact
commands and interpret their returned logs when shared; do not launch another
local test unless they ask.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-16_V6.md
cat reports/sequence_screening_pool_review_2026-10-16.md
.venv/bin/python -m pytest -q tests/test_project_scope.py tests/test_sequence_diverse_structure_panel.py tests/test_structure_pool_sequences.py
.venv/bin/python scripts/plan_sequence_diverse_structure_panel.py --verify results/sequence_screening_pool_protocol.json
.venv/bin/python scripts/screen_structure_pool_sequences.py --verify results/structure_pool_sequence_summary.json
```

The last replay may take several minutes because it compares candidate
sequences against the retained exposure ledger. Before any future GitHub
publication, inspect the live README and preserve the user's picture and any
repository image assets.
