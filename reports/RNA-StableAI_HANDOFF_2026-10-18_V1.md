# RNA-StableAI handoff — 2026-10-18 V1

Project: RNA-StableAI
Date: 2026-10-18 (America/Los_Angeles)
Version: V1
Workspace: `/home/zyliu/Documents/rna-stable-ai`

## Completed work

- Resumed from October 17 V9 and replayed its frozen CRW audit.
- Retrieved all six outstanding Rfam results into a new directory; all seven CRW records now have completed, exact-full-query-verified responses. Original responses and frozen protocols remain intact.
- Added `scripts/audit_crw_panel_exposure.py` and three focused tests. The supplementary audit pins its inputs and records inclusive hit coverage, all significant possible family/clan exposures, and overlap with the frozen panel and candidate inventory.
- Found no returned-hit family/clan overlap with the 13-reference panel. RF02545/RF02546 overlap the CRW SSU/LSU hits but were already excluded by the prior clan screen.
- Documented that CRW 54679 and 54684 have only short local hits (3.0–6.4% of query length), leaving whole-record lineage unresolved. A sole non-null clan in the older summary does not rule out unclanned hits or establish whole-RNA lineage.
- Wrote `reports/crw_rfam_completed_lineage_audit_2026-10-18.md`. No training, model promotion, README edits or publication occurred. Existing staged and unstaged work was preserved.

## Verification

- `tests/test_crw_panel_exposure.py`: 3 passed.
- New completed CRW result audit replay passed through the supplementary audit.
- Supplementary coverage/exposure replay passed, including pinned Rfam 15.1 clan annotations and all response hashes.
- Previous 1,000–4,999 nt Rfam seed candidate audit replay passed; zero surviving candidates remains the result.

## Pending work

- Investigate original source provenance and full-length family/clan lineage for `bpRNA_CRW_54679` and `bpRNA_CRW_54684`; conservative quarantine remains an option for future panel design. Do not treat local hits or lack of returned overlap as independence proof.
- Obtain a separate source of complete, family/clan-separated 1,000–4,999 nt references. Existing seed and bpRNA RFAM screens did not fill this gap. Keep active scope below 5,000 nt.
- The five-clan feasibility study remains development evidence with computational labels; do not retroactively reclassify it as independent validation.
- Changes are local. Before any future publication, inspect the live GitHub README and preserve the user's picture and upstream edits.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/crw_rfam_completed_lineage_audit_2026-10-18.md
.venv/bin/python -m pytest -q tests/test_crw_panel_exposure.py
.venv/bin/python scripts/audit_crw_rfam_batch_results.py --verify-run results/crw_rfam_batch_result_audit_runs/20261018T221637.760541Z/summary.json
.venv/bin/python scripts/audit_crw_panel_exposure.py --verify-run results/crw_panel_exposure_runs/20261018T221708.139284Z/summary.json
.venv/bin/python scripts/audit_rfam_seed_long_candidates.py --verify-run results/rfam_seed_long_candidate_audit_runs/20261017T191603.870444Z/summary.json
cat reports/bprna_long_origin_binding_2026-10-17.md
rg -n '54679|54684' scripts/bind_bprna_long_origin_metadata.py results/bprna_long_training_smoke_runs/20261017T033749.792816Z/selection.json
```
