# RNA-StableAI handoff — 2026-10-16 V1

Project: RNA-StableAI. Date: 2026-10-16 (America/Los_Angeles). Version: V1.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
State: yesterday's interrupted publication tail was resumed and completed. The
scientific project remains in development; there is no validated release.

## Completed work

Read the latest 2026-10-15 V7 handoff and checked GitHub directly. GitHub
`main` already contained the development snapshot at
`1a4b14cde0d3c4bd6dce88eef93f5402f30ab9b7`, but the V7 handoff itself
returned HTTP 404 and had not been uploaded before the prior session stopped.

Created a fresh isolated publication checkout at
`/tmp/rna-stable-ai-publish-20261016`, confirmed it began clean at the GitHub
commit, and published the byte-identical missing V7 handoff as commit
`4ee104c` on `main`. The original workspace, its staged state, and its
placeholder `origin` were not used for GitHub operations.

Before publishing, inspected the live GitHub README and its image reference.
The checkout README and workspace README had the same SHA-256 hash, and the
user's image HTML and attachment URL remained unchanged. No README or image
asset was modified by this continuation.

## Verification

- GitHub authentication succeeded through the configured keyring.
- GitHub `main` initially resolved to `1a4b14cde0d3c4bd6dce88eef93f5402f30ab9b7`.
- GitHub confirmed V6 existed and V7 was absent before the continuation.
- The local and publication-checkout V7 files had identical SHA-256
  `08a89e556c25585d554e35b7aafd0155d03a2edbef30d4e6ce967b11f1517240`.
- `git diff --check` passed before the documentation-only commit.
- Push succeeded: `1a4b14c..4ee104c main -> main`.
- No test suite was rerun because the resumed upload changed documentation only;
  the published development snapshot retains yesterday's 831-passing-test
  verification.

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
cat reports/RNA-StableAI_HANDOFF_2026-10-16_V1.md
cat reports/fresh_structure_reference_review_2026-10-15.md
.venv/bin/python scripts/prepare_fresh_structure_references.py --verify results/fresh_structure_references_summary.json
.venv/bin/python scripts/audit_fresh_structure_readiness.py --verify results/fresh_structure_readiness_summary.json
git -C /tmp/rna-stable-ai-publish-20261016 status --short
gh api repos/zyliu-OU/rna-stable-ai/git/ref/heads/main --jq .object.sha
```

Before future publication, inspect the live GitHub README again and merge
upstream edits while preserving the user's picture and any repository image
assets.

