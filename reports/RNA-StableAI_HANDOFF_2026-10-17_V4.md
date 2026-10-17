# RNA-StableAI handoff — 2026-10-17 V4

Project: RNA-StableAI  
Date: 2026-10-17 (America/Los_Angeles)  
Version: V4  
Workspace: `/home/zyliu/Documents/rna-stable-ai`

## Completed work

- Audited local bpRNA training additions and primary bpRNA/Rfam sources for the unresolved family-separation gate. The 17 additions have seven CRW and ten RFAM source-group labels, but no family IDs or accessions in their selected records or DBN headers.
- Confirmed the 11 development references fall in Rfam SSU clan CL00111 (RF00177, RF02542) or LSU clan CL00112 (RF02540, RF02541). Wrote the evidence and proposed gate in `reports/bprna_long_family_provenance_audit_2026-10-17.md`.
- Inspected the small official bpRNA database-construction archive. Its published RNA schema does not contain an explicit Rfam family-accession field. No family mapping was inferred from numeric bpRNA IDs. No model code, default, README, or GitHub publication changed.

## Verification

- Recounted the selected training records from the frozen `selection.json` (7 CRW, 10 RFAM) and inspected representative DBN headers in the pinned source ZIP.
- Verified the official database-construction ZIP inventory and SHA-256 `3ebc6e1b2f52556d964c50b83070b2484eaa7f5f61162e26a0bcb0ea1dcc2cc9`; read its SQL schema for family/source fields. Checked current Rfam clan pages for the four development families.
- The preceding score-offset run replay and six focused tests remain passed; no executable code was changed in this audit.

## Pending work

- Obtain record-level bpRNA origin metadata or run a pinned Rfam covariance-model mapping for all 17 additions, preserving ambiguous assignments. Freeze this before selecting an independent family-separated long-reference panel.
- Continue development-only ranking and objective work using the existing 11-reference panel. Do not claim independent validation, promote a checkpoint, or choose a production calibration from it.
- Preserve the user-added GitHub README picture and upstream edits before any future publication.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/bprna_long_family_provenance_audit_2026-10-17.md
.venv/bin/python -c 'import json,collections; r=json.load(open("results/bprna_long_training_smoke_runs/20261017T033749.792816Z/selection.json"))["selected"]; print(len(r),collections.Counter(x["source_group"] for x in r))'
.venv/bin/python scripts/study_long_score_offset.py --verify-run results/long_score_offset_runs/20261017T184134.981159Z/summary.json
cat reports/long_candidate_budget_matched_2026-10-17.md
```
