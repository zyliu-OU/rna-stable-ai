# RNA-StableAI handoff — 2026-10-18 V3

Project: RNA-StableAI
Date: 2026-10-18 (America/Los_Angeles)
Version: V3
Workspace: `/home/zyliu/Documents/rna-stable-ai`

## Completed work

- Continued V2 by surveying a separate direct RCSB source for experimental RNA entities of 1,000–4,999 nt, without the earlier 3.5 Å resolution cutoff.
- Frozen search found 4,498 entities; a description-based heuristic shortlisted 161. Acquired all shortlisted entity metadata plus modeled-residue counts for 173 instances, without sequences or contacts.
- Added frozen acquisition/replay drivers: `survey_rcsb_long_rna_metadata.py`, `inspect_rcsb_long_shortlist.py`, and `inspect_rcsb_long_coverage_v2.py`; original rejected coverage driver/protocol remain preserved.
- Added `audit_rcsb_long_source_leads.py`, consuming frozen exposures, known bpRNA families, Rfam 15.1 clans, BGSU mappings and the group II quarantine. Its replayable summary has 3 exposed PDBs, 55 exposed-family entities, 93 without a full model by count, 8 remaining ribosomal-description/context cases and 2 source leads (sum 161).
- Identified Qβ `7LHD_1` (4,217 nt) and AP205 `8TOC_1` (4,269 nt) as metadata source leads with equal deposited/model-residue counts. MS2 `5TC1_3` models only 242 of 3,569 residues; the two 1,157-nt TLC1 entities model only 98/232 residues.
- Wrote `reports/rcsb_long_rna_source_survey_2026-10-18.md`. Zero independent pair references have been qualified. No new sequences, contact labels, predictions, README edits or GitHub publication occurred.

## Verification

- 12 focused tests passed across `test_rcsb_long_source_survey.py`, `test_crw_original_provenance.py`, and `test_crw_panel_exposure.py`.
- Source-lead audit replay passed, including all parent RCSB survey/entity/coverage and BGSU saved-response hash/identity checks.
- First coverage attempt was rejected for an incorrect GraphQL field. The corrected V2 field was checked against the retained official RCSB schema; failed artifacts remain intact.

## Pending work

- Next: freeze a sequence-only acquisition plan for exactly `7LHD_1` and `8TOC_1`. Their label/auth chains are A/A and A/R respectively. Validate canonical full sequences and declared lengths, journal valid read sequences as exposures, then apply exact, shared-30-nt and near-duplicate checks against all training/development exposures. Retain both candidates and any failures without replacement.
- Resolve family/clan and group II architecture exclusions; no annotation means unresolved, never independent. The metadata filter was heuristic and is not an exhaustive independence screen over all 4,498 entities.
- Audit model/contact annotation lineage and complete pair-reference feasibility before an independent panel freeze. Qβ's primary paper describes computational structural modeling based on cryo-EM density. Equal modeled/deposited counts alone do not establish reliable nucleotide identities or complete pair labels.
- The existing metadata protocols authorize no sequence/contact fetch or inference; create a separate frozen protocol for each next stage. No additional user confirmation is needed for ordinary authorized continuation.
- Active model/reference scope remains below 5,000 nt. Preserve the live README image and upstream edits before any future publication.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/rcsb_long_rna_source_survey_2026-10-18.md
.venv/bin/python -m pytest -q tests/test_rcsb_long_source_survey.py tests/test_crw_original_provenance.py tests/test_crw_panel_exposure.py
.venv/bin/python scripts/audit_rcsb_long_source_leads.py --verify-run results/rcsb_long_source_lead_audit_runs/20261018T223215.383558Z/summary.json
cat results/rcsb_long_source_lead_audit_runs/20261018T223215.383558Z/summary.json
sed -n '1,240p' scripts/screen_bgsu_pool_sequences.py
sed -n '1,220p' scripts/screen_structure_pool_sequences.py
```
