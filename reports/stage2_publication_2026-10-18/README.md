# October 18 Stage 2 publication evidence

These concise JSON files are byte-identical copies of the local study-level
summaries and selected protocol manifests. MANIFEST.json records exact local
source paths and SHA-256. All studies use exposed development references;
Stage 2 remains open and Stage 3 cell-free expression remains queued.

Full source archives, sequence/structure inventories, predictions, candidate
arrays and model checkpoints remain local. Protocol manifests retain original
host paths and hashes for provenance; this directory is not a complete portable
replay bundle. Do not pass these concise copies to runners expecting complete
local artifacts. Reproduction requires the exact referenced sources and runs.

The original 103-record weighted-BCE study remains the comparison baseline.
Assignment supervision is a development variant; negative/mixed ranking and
hard-negative outcomes are preserved. Gold-label recovery oracles are bounds,
not model predictions. See the [scientific review](../stage2_recovery_ceiling_and_assignment_review_2026-10-18.md)
and [V7 handoff](../RNA-StableAI_HANDOFF_2026-10-18_V7.md).

Publication verification: 51 focused tests passed in the clean checkout. The
retained official RCSB schema is included under tests/fixtures; the original
ignored results copy remains local. See the [test log](../stage2-publication-focused-tests-2026-10-18.log).
