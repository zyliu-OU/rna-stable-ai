# RNA-StableAI current work status

Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Canonical handoff: `RNA-StableAI_HANDOFF_2026-10-11_V3.md`.
Current step: 4 — independent biological validation.

Prospective source screening freezes the baseline/stack/helix model-seed-20261006
checkpoints, exact sparse decoder and zero penalty before new metadata outcomes.
Protocol: `/home/zyliu/Documents/rna-stable-ai/results/prospective_family_protocol_runs/20261012T023120.466587Z/manifest.json`.

All three Rfam description downloads failed with workspace DNS errors. Their
sequence requests remain unstarted; no new files, labels or inference were
produced. A completed attempt ledger does not mean successful data acquisition.
Full suite: 508 passed in216.24seconds; focused source/readiness tests:20 passed.

Next: retry acquisition with this frozen protocol when source access is available,
then verify family/clan and training-overlap provenance, bind exact annotations
and freeze the final evaluation plan before predictions. All changes are local.
Previous status files are preserved under `/home/zyliu/Documents/rna-stable-ai/reports/archive/20261012T023735.102545Z`.
