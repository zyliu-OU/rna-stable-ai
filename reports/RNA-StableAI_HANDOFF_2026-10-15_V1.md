# RNA-StableAI handoff — 2026-10-15 V1

Project: RNA-StableAI. Date: 2026-10-15 (America/Los_Angeles). Version: V1.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
State: development resumed; independent biological validation remains the
scientific gate. No validated release.

## Completed work

Implemented `scripts/prepare_family_provenance_dataset.py` against the frozen
metadata selection from the 2026-10-14 V10 handoff. The builder freezes 16
Stockholm requests for 12 training and four validation family/clan groups,
checks the prior exposure ledger, screens sequences at the declared similarity
threshold before parsing pairs, retains every selected outcome without
replacement, maps complete WUSS contacts into explicit pair sets, and replays
the source and result hashes. A safe bitset LCS upper bound makes the existing
sequence-overlap rule practical without changing its result. Added focused tests.

All 16 sources were downloaded. The fixed screen selected 140 records; 81 have
complete computational pair references (59 training, 22 validation). The other
59 have missing annotated paired columns. RF00024 has zero supported records
among 12 selected. This fails the declared one-supported-record-per-family gate,
so `dataset_ready` is false. No training, inference or checkpoint selection took
place. The source review explains the failure and its limits.

The first sandbox acquisition attempt failed DNS. The approved retry obtained
all 16 sources in
`results/family_provenance_dataset_source_runs/20261016T004500.107067Z/`.
After an interrupted processing run, the final run reused those exact
hash-checked bytes:
`results/family_provenance_dataset_source_runs/20261016T004840.252786Z/`.
The final `binding.json` records selections, exclusions, complete pair sets,
unsupported statuses and per-family counts. Run directory stamps are UTC.

Updated the README, development command reference, current roadmap and source
review. The README picture HTML and attachment URL remain present. No GitHub
publication was attempted; the original workspace has a large pre-existing
staged/untracked state, which was left intact.

## Verification

- Source acquisition replay and frozen metadata replay passed.
- Focused source, metadata and pair integration tests: **26 passed**.
- Full suite: **823 passed in 219.32 seconds**; log
  `reports/family-provenance-source-full-suite-2026-10-15.log`.
- `git diff --check` passed. The new builder compiles.
- No source response or selected unsupported record was silently replaced.

## Pending work

Design a new, explicitly versioned development-data protocol that acknowledges
the observed RF00024 binding failure before further label acquisition. Preserve
this frozen run and its 59 unsupported denominators. Training remains gated by
the declared per-family condition; do not lower the threshold or inherit old
checkpoints silently. Independent biological structures with broad coverage,
long biological RNA, measured mutation effects, function and release validation
remain open. Comparative consensus labels are computational, and screening does
not certify evolutionary or tool-training independence.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-15_V1.md
cat reports/family_provenance_source_review_2026-10-15.md
cat results/family_provenance_dataset_source_summary.json
.venv/bin/python scripts/plan_family_provenance_dataset.py --verify results/family_provenance_dataset_metadata_summary.json
.venv/bin/python scripts/prepare_family_provenance_dataset.py --verify results/family_provenance_dataset_source_summary.json
.venv/bin/python -m pytest -q tests/test_family_provenance_dataset.py tests/test_family_provenance_source.py tests/test_prospective_pair_integration.py
```

For the next protocol, inspect
`results/family_provenance_dataset_source_runs/20261016T004840.252786Z/binding.json`
and `configs/family_provenance_dataset_2026-10-14.json` first. No new protocol
or training command exists yet. Before any future publication, inspect the live
GitHub README and merge upstream edits while preserving the user's picture.
