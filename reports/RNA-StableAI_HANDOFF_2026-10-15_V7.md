# RNA-StableAI handoff — 2026-10-15 V7

Project: RNA-StableAI. Date: 2026-10-15 (America/Los_Angeles). Version: V7.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
State: the current development snapshot was published to GitHub main. The
scientific project remains in development; there is no validated release.

## Completed work

Published the V6 development and structure-readiness work to
`https://github.com/zyliu-OU/rna-stable-ai` as commit
`1a4b14cde0d3c4bd6dce88eef93f5402f30ab9b7` on `main`. The isolated
publication checkout is `/tmp/rna-stable-ai-publish-20261015`; the original
workspace, its unrelated staged state, and its placeholder `origin` were not
used for the push. The update added or modified 470 files without deleting
upstream files, including model-study code and evidence, the 56-request contact
panel, readiness audit, reports and prior handoffs. The export manifest records
the 12,933-file source snapshot and credential/file-size scan.

Before publication, read the live GitHub README and verified its picture HTML
and attachment URL. The published README preserves that picture exactly.
GitHub main and the live README blob were checked after the push.

## Verification

- Original workspace full suite: **831 passed in 216.01 seconds**.
- Clean publication checkout focused tests: **5 passed**.
- Export snapshot: all **12,933** file hashes verified after copying into the
  publication checkout; no credential pattern or GitHub file-size violation.
- Staged `git diff --check` passed; no deletions were staged.
- GitHub main resolved to the published commit above. README blob hash matched
  the publication checkout, including the user's image HTML.

## Pending work

The independent biological reference gate remains closed: the published
contact panel has 12 informative references and zero families with three.
Design and freeze a new sequence-diverse source plan outside the exposed
families/PDBs, then audit annotation truth and tool-training provenance before
any model inference. Long biological RNA, causal stability, mutation effects
and retained function remain open. No release was created.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-15_V7.md
cat reports/fresh_structure_reference_review_2026-10-15.md
.venv/bin/python scripts/prepare_fresh_structure_references.py --verify results/fresh_structure_references_summary.json
.venv/bin/python scripts/audit_fresh_structure_readiness.py --verify results/fresh_structure_readiness_summary.json
git -C /tmp/rna-stable-ai-publish-20261015 status --short
gh api repos/zyliu-OU/rna-stable-ai/git/ref/heads/main --jq .object.sha
```

Before future publication, inspect the live GitHub README again and merge
upstream edits while preserving the user's picture and any repository image
assets.
