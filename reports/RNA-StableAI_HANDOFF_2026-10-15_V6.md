# RNA-StableAI handoff — 2026-10-15 V6

Project: RNA-StableAI. Date: 2026-10-15 (America/Los_Angeles). Version: V6.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
State: active research development. The new biological contact panel was
acquired and audited, but reference readiness failed. Independent biological
validation and a validated release remain unfinished.

## Completed work

Continued from V5's frozen eight-family/56-candidate protocol. Added
`scripts/prepare_fresh_structure_references.py`, froze exact BGSU RNA 3D Hub
requests, and acquired all **56/56** responses. Durable request journals,
response hashes, source-first sequence screening, exposure events, full raw cWW
contact binding and a replay audit are retained at
`results/fresh_structure_references_summary.json`. Three response sequences
were unsupported and 40 were within-panel redundant. Thirteen records were
selected before contact parsing; all 13 raw graphs bound to their sequences.
Valid source sequences were recorded as validation exposure before contact
binding. No model inference was run.

Added `scripts/audit_fresh_structure_readiness.py` and
`results/fresh_structure_readiness_summary.json`. One accepted raw graph has
zero cWW contacts, so the positive-contact audit counts **12 informative
references**, with **zero families** reaching three informative references.
The declared threshold is 12 total and three families with at least three
each; the coverage gate therefore fails. Rfam family-level structure-source
text was retained and classified, but no per-sequence experimental annotation
or tool-training independence was certified. The full account is
`reports/fresh_structure_reference_review_2026-10-15.md`. Updated README and
roadmap; the user's README picture is preserved. No GitHub publication occurred.

## Verification

- Frozen panel, reference binding and post-binding readiness replays passed.
- Focused tests: **15 passed**.
- Full suite: **831 passed in 216.01 seconds**.
- Python compilation and `git diff --check` passed.
- No model inference or independent accuracy claim was made.

## Pending work

Design a new sequence-diverse source plan using families, clans and PDBs outside
this now-exposed panel, freeze it before reading labels, and retain all source
failures and unsupported records. Seek at least 12 informative references with
three families contributing at least three each, then assess per-sequence
annotation truth and complete tool-training provenance. Do not rerun the new
panel as a fresh test. Long biological RNA, causal stability, mutation effects
and retained function also remain open.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-15_V6.md
cat reports/fresh_structure_reference_review_2026-10-15.md
.venv/bin/python scripts/freeze_fresh_structure_panel.py --verify results/fresh_structure_panel_protocol.json
.venv/bin/python scripts/prepare_fresh_structure_references.py --verify results/fresh_structure_references_summary.json
.venv/bin/python scripts/audit_fresh_structure_readiness.py --verify results/fresh_structure_readiness_summary.json
.venv/bin/python -m pytest -q tests/test_fresh_structure_readiness.py tests/test_raw_structure_references.py
cat configs/reference_readiness.json
```

Before future publication, inspect the live GitHub README and merge upstream
edits while preserving the user's picture HTML and any repository image assets.
