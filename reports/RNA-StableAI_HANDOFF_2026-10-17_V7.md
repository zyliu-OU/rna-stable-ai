# RNA-StableAI handoff — 2026-10-17 V7

Project: RNA-StableAI  
Date: 2026-10-17 (America/Los_Angeles)  
Version: V7  
Workspace: `/home/zyliu/Documents/rna-stable-ai`

## Completed work

- Submitted one public bpRNA CRW training sequence (`bpRNA_CRW_13049`) to [Rfam's documented batch sequence-search endpoint](https://docs.rfam.org/en/latest/api.html#sequence-searches) as an exploratory check for a direct family hit. The service returned job `infernal_cmscan-R20261017-195709-0511-4231837-p1m`.
- Saved the job URL and last observed empty result in `results/crw_rfam_search_attempt_2026-10-17.json`. The endpoint still showed blank opened/started/closed fields and no search sequence or hits after repeated checks, so no family was assigned from it.
- The preceding sequence-bound SQL origin result for all 17 training additions remains canonical in `reports/bprna_long_origin_binding_2026-10-17.md` and `results/bprna_long_origin_binding_v2_runs/20261017T185531.913009Z/summary.json`. No model default, README, or GitHub publication changed.

## Verification

- Rfam POST returned a job ID; subsequent GET responses did not yet contain a completed search sequence or result. The job is pending or unavailable, not a verified zero-hit outcome.
- The local V2 SQL origin-binding replay passed; three focused bpRNA source/subset tests passed earlier in this continuation.

## Pending work

- Recheck the Rfam job within the provider's result-retention window. Accept a result only if its returned sequence matches the submitted record and it has completion metadata; preserve all hits and ambiguity. If it remains empty, use a different version-pinned mapping path for the seven CRW records.
- Freeze a new independent family-separated long-reference panel only after the CRW lineage and regional sequence-overlap checks are resolved. The existing 11-reference cohort remains development-only.
- Preserve the user-added GitHub README picture and upstream edits before any future publication.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/bprna_long_origin_binding_2026-10-17.md
.venv/bin/python scripts/bind_bprna_long_origin_metadata.py --verify-run results/bprna_long_origin_binding_v2_runs/20261017T185531.913009Z/summary.json
cat results/crw_rfam_search_attempt_2026-10-17.json
curl -L --fail --silent --show-error --max-time 30 https://batch.rfam.org/result/infernal_cmscan-R20261017-195709-0511-4231837-p1m -H accept:application/json
```
