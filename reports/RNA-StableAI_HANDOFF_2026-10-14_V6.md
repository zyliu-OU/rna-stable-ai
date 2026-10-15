# RNA-StableAI handoff — 2026-10-14 V6

Project: RNA-StableAI. Date: 2026-10-14 (America/Los_Angeles). Version: V6.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
State: active autonomous development until the available GPT-6 usage limit.
This is an interim checkpoint; do not pause or complete the active goal.

## Completed work

All V5 development and evidence are published on public GitHub main in
`ec77cc062481ca03900ef0651d3dd43574ab4eaf`:
https://github.com/zyliu-OU/rna-stable-ai/commit/ec77cc062481ca03900ef0651d3dd43574ab4eaf.
Preserved the user's picture and their own preceding commit
`5a2c05dd90b7ee28aa334f9fcb9046a23e7a5be6` as the new commit's parent.
No force push or file deletions. Original workspace Git index and placeholder
remote were untouched.

Publication checkout:
`/home/zyliu/Documents/rna-stable-ai/exports/20261015T023211.529798Z/rna-stable-ai`.
Verified all 12,070 exported source-file hashes, size bounds, credential-pattern
scan, local README/roadmap links, and picture presence. GitHub main equals the
local commit. Live README blob `3d82b59fea76f67b0aca885f5dab89845ffdc00c` exactly
matches the local export. The current-status refresh and this V6 are local.

## Verification and scientific state

Full suite: **743 passed in 217.45 seconds**. Source archive: **264/274** recorded
Python versions, ten historical versions explicitly unavailable. All four new
source/readiness/provenance drivers and 71 focused checks are included.

Broad validation remains at step 4. Six new PDB-derived source references do not
meet the broad supported-coverage minimum. All six raw FR3D sequences match,
but only three current raw contact sets match their historical supplied strings.
All graph/set differences are retained; no original references were replaced.
No new model prediction, native fold, training, or default change was performed.
See V5 and `reports/development_2026-10-14_review.md` for exact run paths.

## Pending work

Continue source engineering with metadata-only planning of a separately frozen
raw-contact panel. Candidate families under consideration: RF00379 (c-di-AMP),
RF00380 (Mbox/ykoK), RF00442 (guanidine-I), RF01054 (preQ1-II), RF01750 (ZMP/ZTP),
and RF01786 (c-di-GMP-II). Only metadata/mapping counts were inspected for these;
no sequence, contact, or model outcome was opened. The frozen retained Rfam PDB
mapping contains 16/3/10/1/12/2 distinct PDB-chain entries for these families.
Do not treat those counts as supported or independent references.

A new protocol must freeze exact candidate PDB chains, models, raw-contact target,
source limits, selection/redundancy rules and exposure inventory before new source
responses. It must retain all failures and prevent projection of multiple-partner
graphs into unsupported one-partner references. Known family/PDB/clan provenance,
exact sequence identity, unsupported outcomes and current exposure gates remain
required. Any narrow feasibility pilot is separate from the broader validation
gate and must not be presented as closing it. No inference is authorized merely
by metadata availability.

All original, assay, prospective, and newly read source families remain consumed
for fresh-test planning. No tuning on them. Long biological accuracy, causal
mutation benefits/function, complete tool-training provenance, and release remain
pending. Keep the user's picture in every future publication; inspect upstream
before constructing each new export.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-14_V6.md
cat docs/STRUCTURE_DERIVED_REFERENCES.md
cat reports/PROJECT_ROADMAP_2026-10-14.md
.venv/bin/python scripts/audit_structure_contact_provenance.py --verify results/structure_contact_provenance_summary.json
.venv/bin/python scripts/archive_replay_sources.py --verify
gh api repos/zyliu-OU/rna-stable-ai/commits/main --jq '{sha: .sha, message: .commit.message}'
git -C exports/20261015T023211.529798Z/rna-stable-ai status --short
```

All computational and publication commands are finished at this checkpoint;
there are no outstanding native requests or test processes. Continue development
under the active goal. No user terminal command is needed.
