# RNA-StableAI handoff — 2026-10-15 V4

Project: RNA-StableAI. Date: 2026-10-15 (America/Los_Angeles). Version: V4.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
State: active development. The matched pair-set model study is complete, but
independent biological structure validation and a validated release remain open.

## Completed work

Added `scripts/audit_fresh_structure_inventory.py`, its focused regression
test, and a replayable metadata-only artifact at
`results/fresh_structure_inventory_2026-10-15.json`. The audit combines the
retained Rfam 3D seed PDB/chain mapping, all known exposure events, the 16
development-source families plus RF00022, and cached Rfam 15.1 clan metadata.
It records source, metadata, development-selection and exposure hashes. No new
structure labels, candidate sequences, contacts, predictions or model inference
were read or run.

Of 142 mapped families (19,193 mapping rows), 38 are already family/PDB-exposed,
one more was development-source-screened, six have an exposed clan, and 92 lack
retained clan metadata. Five pass the known metadata screen, but only RF00015
and RF00044 have at least three distinct unexposed PDB accessions (13 and three).
These are mapping possibilities, not supported biological references. The new
panel has zero sequence-bound supported references and cannot meet the declared
three-family/12-reference readiness gate yet. Added the finding to the README,
roadmap and `reports/fresh_structure_inventory_review_2026-10-15.md`. The README
picture remains present. No publication occurred.

## Verification

- Inventory replay passed.
- Focused inventory test: **1 passed**.
- Python compilation and `git diff --check` passed.
- Prior full suite remains **828 passed** for the completed model study; this
  turn did not rerun it because this change adds only a metadata audit.
- Ruff is not installed in the project virtual environment.

## Pending work

Freeze a bounded Rfam 15.1 metadata acquisition for the 92 unresolved mapped
families, acquire and replay it, then repeat clan/family/PDB screening. Choose
and freeze a candidate panel from metadata before reading structure/contact
labels. Bind sequences and raw annotations without replacing unsupported
records; audit per-sequence annotation lineage, overlap and tool-training
provenance. Require at least 12 supported references and three families with
three each before any new model inference. PDB-derived FR3D annotations are
computational and do not alone establish experimental truth. Long biological
RNA, causal stability, mutation effects and retained function remain open.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-15_V4.md
cat reports/fresh_structure_inventory_review_2026-10-15.md
.venv/bin/python scripts/audit_fresh_structure_inventory.py --verify results/fresh_structure_inventory_2026-10-15.json
.venv/bin/python -m pytest -q tests/test_fresh_structure_inventory.py
cat configs/reference_readiness.json
cat docs/REFERENCE_READINESS.md
```

Before future publication, inspect the live GitHub README and merge upstream
edits while preserving the user's picture HTML and any repository image assets.
