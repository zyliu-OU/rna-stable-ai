# RNA-StableAI handoff — 2026-10-18 V2

Project: RNA-StableAI
Date: 2026-10-18 (America/Los_Angeles)
Version: V2
Workspace: `/home/zyliu/Documents/rna-stable-ai`

## Completed work

- Continued V1 by investigating original provenance of CRW 54679 and 54684.
- Retrieved and hash-pinned GenBank Z48620.1 and V00694.1. Replayed the archived exact-sequence SQL origin binding before connecting these accessions to training records.
- Added `scripts/audit_crw_original_provenance.py` with a version-pinned, replayable local alignment audit. CRW 54679 matches 2,473 query bases exactly, with one clipped leading base, over the entire annotated intron 2 in Z48620.1. CRW 54684 aligns over the entire annotated intron 1 in V00694.1 with 2,503 identities, three mismatches, one insertion and 13 clipped leading bases.
- Archived CRW I2 names plus the accession intron context support broad group II intron provenance. The short Rfam domain hits are consistent with this architecture; no exact full-query accession identity or formal whole-record Rfam assignment was claimed.
- Saved `quarantine.json` beside the audit summary for future independent-panel planning: retain both records, RF00029/RF02012, CL00102 and broad group II architecture as exposures. Future panel drivers must explicitly incorporate this planning artifact; older frozen protocols were not changed.
- Wrote `reports/crw_group_ii_provenance_2026-10-18.md`. All changes remain local; model defaults, training sequences, README and GitHub were unchanged.

## Verification

- Six focused tests passed: `tests/test_crw_original_provenance.py` and `tests/test_crw_panel_exposure.py`.
- Original SQL origin-binding replay passed.
- Frozen provenance audit replay passed against pinned accession files, selected sequences, driver and Biopython version.
- CRW diagram downloads failed TLS verification and were not used as retrieved evidence. GenBank records were retrieved successfully with normal certificate verification.

## Pending work

- Next research step: inventory another source of complete 1,000–4,999 nt reference structures outside exposed families/clans and group II intron homologs. The existing bpRNA RFAM and Rfam 15.1 seed screens yielded no surviving candidates.
- Before freezing any new independent panel, incorporate the quarantine artifact together with existing family/clan, exact-sequence, shared-segment and near-duplicate exclusions. Group II architecture is a conservative planning exclusion, not a newly verified Rfam family crosswalk.
- Formal whole-record family assignments and terminal differences for the two records remain unresolved. Do not reclassify existing feasibility evidence as independent validation.
- Keep active model/reference scope below 5,000 nt. Before publishing, inspect the live GitHub README and preserve the user's image and upstream edits.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/crw_group_ii_provenance_2026-10-18.md
.venv/bin/python -m pytest -q tests/test_crw_original_provenance.py tests/test_crw_panel_exposure.py
.venv/bin/python scripts/audit_crw_original_provenance.py --verify-run results/crw_original_provenance_audit_runs/20261018T222023.684010Z/summary.json
cat results/crw_original_provenance_audit_runs/20261018T222023.684010Z/quarantine.json
cat reports/stage2_family_validation_progress_2026-10-17.md
rg --files scripts | rg 'raw_structure|fresh_structure|bgsu|reference_readiness|sequence_diverse'
```
