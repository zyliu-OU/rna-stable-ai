# RNA-StableAI handoff — 2026-10-14 V9

Project: RNA-StableAI. Date: 2026-10-14 (America/Los_Angeles). Version: V9.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
State: active autonomous development until the available GPT-6 usage limit.
This checkpoint is not a pause. No new user terminal action is required.

## Completed work

Published the full V8 feasibility/identity/lineage milestone at
`9a68f6dbd4a5958947d4b5826cb7622e653e9152`:
https://github.com/zyliu-OU/rna-stable-ai/commit/9a68f6dbd4a5958947d4b5826cb7622e653e9152.
The existing parent is `ec77cc062481ca03900ef0651d3dd43574ab4eaf`; the user's
picture commit remains in history and its exact HTML remains at the README top.
No force push, file deletions, or original workspace index changes.

Publication checkout:
`/home/zyliu/Documents/rna-stable-ai/exports/20261015T031547.490147Z/rna-stable-ai`.
Verified all **12,304** exported source-file hashes, links, limits, credential
pattern scan, and picture presence. The live main commit matches local HEAD.
Live README blob `8d7de321c28c67849366c744b60deb350e924aa4` matches the export.

## Verification and scientific state

**803 tests pass** in 216.32 seconds. Archive **270/280** recorded source versions;
ten historical versions remain unavailable. The six-family raw-contact comparison
retains 60/60 measured outcomes and 20/20 completed native requests, zero unknown.
Helix mean pair F1 0.325531; both native controls 0.626116, with identical native
structures on all ten inputs. No tuning, model/default change, or broad validation
claim. Per-family PNG/SVG and all raw/source/native journals are published.

Checkpoint lineage binds identical 89-training/47-validation corpora across all
three models. 83/136 records lack confirmed family assignment; PDB-level candidates
are not exact sequence assignments. Ten upstream source-test rows are already
project development validation. Details and exact run paths are in V8 and
`reports/raw_structure_feasibility_review_2026-10-14.md`.

## Pending work

Continue with a metadata-only, source-labelled training/validation data plan.
Suggested design: fixed candidate Rfam family pool, exclude consumed families,
known PDB-derived family candidates and exposed clans, group by clan/family before
splitting, and select train/validation groups deterministically without model
metrics. Declare source support, annotation, length, overlap, caps and failure
handling before new sequences/structure labels. New development checkpoints
should start from declared random initialization, with explicit data provenance,
rather than inherit unresolved old training inputs. Do not train or select models
on any completed test/assay/raw-source cohort.

Use new standalone dataset/training drivers and existing frozen model factories
where practical so historical source/evaluation code stays auditable. Preserve
exact source bytes before any future core-code changes. The broader biological
gate remains open; long RNA, mutation/function evidence, and complete legacy tool
training provenance remain pending. The original checkpoints remain unchanged.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-14_V9.md
cat docs/CHECKPOINT_LINEAGE.md
cat reports/raw_structure_feasibility_review_2026-10-14.md
.venv/bin/python scripts/audit_checkpoint_lineage.py --verify results/checkpoint_lineage_summary.json
.venv/bin/python scripts/evaluate_raw_structure_feasibility.py --verify results/raw_structure_feasibility_summary.json
.venv/bin/python scripts/archive_replay_sources.py --verify
gh api repos/zyliu-OU/rna-stable-ai/commits/main --jq '{sha: .sha, message: .commit.message}'
git -C exports/20261015T031547.490147Z/rna-stable-ai status --short
```

All computation and publication jobs are finished at save. V9/current-status
refresh is local; later development publication can include it. Continue under
the active goal and preserve the user's picture in every future update.
