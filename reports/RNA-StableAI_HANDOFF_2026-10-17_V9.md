# RNA-StableAI handoff — 2026-10-17 V9

Project: RNA-StableAI
Date: 2026-10-17 (America/Los_Angeles)
Version: V9
Workspace: `/home/zyliu/Documents/rna-stable-ai`

## Completed work

- Stopped Stage 2 development at the user's request and published the October 17 code, reports, eight earlier handoffs, and 13 concise result summaries to GitHub `main` in commit [`7cd20e18513cc1d230f6085a195b11faacf803db`](https://github.com/zyliu-OU/rna-stable-ai/commit/7cd20e18513cc1d230f6085a195b11faacf803db).
- Updated the GitHub README from the live `main` copy, preserving the user's image markup and the upstream Step 3 protein-expression plan. Added the 13-reference, five-clan, 400–535 nt feasibility result and linked the [Stage 2 progress review](stage2_family_validation_progress_2026-10-17.md). The workspace README now matches the published README.
- Kept upstream bpRNA/Rfam archives, full run artifacts, predictions, and checkpoints local. No model default or checkpoint was promoted.

## Verification

- `git ls-remote origin refs/heads/main` returned the published commit; the publication checkout is clean.
- The README image markup is present, all 14 README report links resolve in the publication checkout, and all 15 added Python scripts passed `py_compile`.
- `git diff --cached --check` reported only intentional Markdown hard-break spaces in dated reports and earlier handoffs. No code or README whitespace errors were reported.
- The Stage 2 study's prior frozen replays passed. No full test suite was rerun solely for publication.

## Pending work

- Six submitted Rfam batch searches for CRW training sequences remained pending at the last saved audit; their empty interim responses must not be interpreted as zero hits. One completed CRW record has multiple SSU-family hits within clan CL00111, so a unique family is not established.
- The five-clan panel is small and uses computational structure labels. Its mean pair F1 was 0.1669 for the extension versus 0.1413 for the control across three seeds; it does not establish independent accuracy.
- Find complete, family/clan-separated structure references at 1,000–4,999 nt. The screened bpRNA RFAM and Rfam 15.1 seed sources yielded no surviving candidates in that interval. Preserve the active scope below 5,000 nt.
- This V9 handoff was saved locally after the GitHub push and is the canonical resume note; the published README links to V8, the last handoff present in that push.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/stage2_family_validation_progress_2026-10-17.md
cat results/crw_rfam_batch_protocol_runs/20261017T190950.011534Z/jobs.json
.venv/bin/python scripts/audit_crw_rfam_batch_results.py --verify-run results/crw_rfam_batch_result_audit_runs/20261017T191101.601086Z/summary.json
curl -L --fail --silent --show-error --max-time 30 https://batch.rfam.org/result/infernal_cmscan-R20261017-200953-0824-56794459-p1m -H accept:application/json
cat results/rfam_seed_long_candidate_audit_runs/20261017T191603.870444Z/summary.json
```
