# RNA-StableAI current work status

Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Canonical handoff: `RNA-StableAI_HANDOFF_2026-10-11_V6.md`.
Current step: 4 — biological validation tooling.

Complete pair-set reference evaluation now preserves crossing contacts and
accepts nested or pair-list supplied predictions. Strict coordinate/partner and
sequence validation, frozen inputs, exposure events and output replay are
implemented. WUSS pair mapping still rejects missing annotated paired columns.

All seven metrics match legacy scoring for 423 stored development predictions.
No new model, accuracy experiment or fresh test was produced. The previous
prospective results and checkpoints remain unchanged; their historical model
replay is included in the tests. The decoder still predicts nested structures.
Full suite: 562 passed in 227.14 seconds; focused checks: 46 passed.

Next: integrate complete pair references into new frozen prospective protocols,
reserve new unexposed families, and continue source/provenance and long-RNA
validation. Changes remain local. Previous status files are preserved under
`/home/zyliu/Documents/rna-stable-ai/reports/archive/20261012T033007.260233Z`.
