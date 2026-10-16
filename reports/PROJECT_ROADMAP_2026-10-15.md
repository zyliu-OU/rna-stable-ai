# RNA-StableAI development roadmap — 2026-10-15

Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Status: active research development; no validated release.

The seven-stage scientific plan remains as described in the
[previous roadmap](PROJECT_ROADMAP_2026-10-14.md). Independent biological
structure validation is still the current gate. The earlier ten-reference raw
contact comparison remains a small feasibility study.

The user resumed development. The frozen sequence-first source builder acquired
all 16 Rfam sources and fixed 140 candidates before contact parsing. Of those,
81 have complete pair references (59 training, 22 validation). RF00024 has no
supported reference among its 12 selected candidates. That original run remains
failed and retained. A declared RF00022 extension also failed under the same
selection rule. A second, explicitly label-informed development protocol now
derives **61 training and 22 validation** complete pair references across all
12/4 groups, passing the dataset gate. A frozen, matched three-head/three-seed
study then trained on those explicit pair sets. Mean selected development
validation pair F1 was 0.322 baseline, 0.391 stack and 0.482 helix. These are
validation-selected development results, not independent accuracy. See the
[source review](family_provenance_source_review_2026-10-15.md) and
[coverage dataset review](family_coverage_development_review_2026-10-15.md),
plus the [training review](family_pair_set_training_review_2026-10-15.md).

Next work is independently annotated biological structure validation with
adequate supported coverage and explicit family, sequence and tool-training
provenance. Keep the earlier failed selections and their unsupported denominators
intact. The new training/validation records are now exposure-ledger inputs and
cannot be reused as fresh tests. A metadata-only [inventory audit](fresh_structure_inventory_review_2026-10-15.md)
screened 142 mapped families. Ninety-two still lack retained Rfam clan metadata,
and only two currently clear exposure screening with at least three distinct
PDB accessions. A subsequent [metadata acquisition and panel freeze](fresh_structure_metadata_and_panel_review_2026-10-15.md)
resolved 91 of 92 missing descriptions and froze eight families/56 candidate
PDB chains without contact labels. RF04222 returned 404. Next acquire and
bind those fixed candidates, then audit readiness before any model inference.
Long biological RNA, measured mutation effects and retained function remain open.

The [contact panel review](fresh_structure_reference_review_2026-10-15.md)
records the outcome: all 56 requests succeeded, but sequence redundancy left
12 informative cWW references and zero families meeting the three-reference
minimum. The gate failed, and the source cohort is now exposed. Future source
plans must exclude these families/PDBs and freeze a new selection before labels.
