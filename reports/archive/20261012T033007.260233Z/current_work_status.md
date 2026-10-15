# RNA-StableAI current work status

Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Canonical handoff: `RNA-StableAI_HANDOFF_2026-10-11_V5.md`.
Current step: 4 — limited prospective comparison complete; broader biological
validation remains ongoing.

All 15 records and six methods retain 90 planned outcomes. Nine references are
supported; six remain unsupported with unknown metrics (SAM pseudoknots and one
Purine missing paired column). Means on the nine supported references: baseline
0.1396, stack 0.2319, helix 0.3561, ViennaRNA/LinearFold 0.6065, all-unpaired 0.
All 18 native requests completed. Frozen-model, metric and request replay passed.
Final full suite: 535 passed in 221.95 seconds; focused checks: 33 passed.

RF00059/RF00162/RF00167 are now consumed. Use `--verify` for historical replay;
fresh reuse is rejected. No new training or model/decoder selection occurred.
Next model work must use development cohorts with new reserved families for
future evaluation. Unknown provenance, long biological accuracy and experimental
stability/function remain unresolved. No more downloads are required for this
completed panel. Changes remain local; earlier status files are preserved under
`/home/zyliu/Documents/rna-stable-ai/reports/archive/20261012T031415.693210Z`.
