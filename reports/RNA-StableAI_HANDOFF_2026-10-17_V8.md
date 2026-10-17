# RNA-StableAI handoff — 2026-10-17 V8

Project: RNA-StableAI  
Date: 2026-10-17 (America/Los_Angeles)  
Version: V8  
Workspace: `/home/zyliu/Documents/rna-stable-ai`

## Completed work

- Rechecked Rfam batch job `infernal_cmscan-R20261017-195709-0511-4231837-p1m`. It still has empty `searchSequence`, `opened`, `started`, and `closed` fields. No family was assigned and zero hits were not inferred.
- Added `scripts/plan_bprna_family_separated_candidates.py` to inventory archived bpRNA RFAM sequences within 400–4,999 nt against all known training and development family exposures, exact sequence identities, and exact 30-nt training segments. Structure labels were not used; no model predictions were made.
- Frozen and replayed the corrected V3 result at `results/bprna_family_separated_candidates_v3_runs/20261017T190513.066933Z/summary.json`. It found 433 provisional sequences in 39 families; all are 400–999 nt. There were no surviving 1,000–4,999 nt candidates in this source.
- Wrote `reports/bprna_family_separated_candidate_inventory_2026-10-17.md`. V1 excluded only the 11 selected development references; V2 corrected this to all 338 development candidates; V3 removed an unused reference-label input and clarified the policy. All frozen runs are retained.
- No model defaults, README, or GitHub publication changed.

## Verification

- V3 candidate-inventory replay passed against pinned source and driver hashes.
- `python -m py_compile` and `git diff --check` passed for the new driver.
- The four mutually exclusive V3 decisions sum to 1,166 eligible unique sequence-family entries: 589 known-family, 11 exact exposed, 133 shared 30-nt segment, 433 provisional.
- The Rfam response remains incomplete; no negative family result was claimed.

## Pending work

- Resolve or conservatively quarantine the seven CRW training records' family/clan lineage. Do not interpret the empty Rfam batch response as a zero-hit result.
- Audit clan membership and complete reference structures for the 39 medium-length candidate families before any validation freeze. These are metadata-only planning candidates and are not independent tests.
- Acquire a separate source of complete, family-separated 1,000–4,999 nt references; the screened bpRNA RFAM source has no surviving candidates in that range.
- Preserve the user-added GitHub README picture and upstream edits before any future publication.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/bprna_family_separated_candidate_inventory_2026-10-17.md
.venv/bin/python scripts/plan_bprna_family_separated_candidates.py --verify-run results/bprna_family_separated_candidates_v3_runs/20261017T190513.066933Z/summary.json
cat results/crw_rfam_search_attempt_2026-10-17.json
curl -L --fail --silent --show-error --max-time 30 https://batch.rfam.org/result/infernal_cmscan-R20261017-195709-0511-4231837-p1m -H accept:application/json
```
