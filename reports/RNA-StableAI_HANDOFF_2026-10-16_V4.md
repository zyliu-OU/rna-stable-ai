# RNA-StableAI handoff — 2026-10-16 V4

Project: RNA-StableAI. Date: 2026-10-16 (America/Los_Angeles). Version: V4.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
State: the under-5,000-nt project focus and preserved longer-sequence policy
were published to GitHub. There is no validated release.

## Completed work

Published the V2/V3 work to `https://github.com/zyliu-OU/rna-stable-ai` as
commit `53ac396` on `main` from the isolated checkout
`/tmp/rna-stable-ai-publish-20261016`. The original workspace, its unrelated
staged state and its placeholder origin were not used for GitHub operations.

The update makes 1–4,999 nt the active development scope and places exactly
5,000 nt and longer in preserved, deferred scope. It includes the
machine-readable policy, policy helper, regression tests, length-scope
documentation, updated README/DEVELOPMENT pages and the 2026-10-16 roadmap.
Historical longer-sequence code, data, configurations, results, reports and
provenance remain in place.

The publication also includes the clearly documented second fresh-structure
panel draft and V2 handoff. Publication verification ran its focused tests, so
the draft's pure metadata-selection behavior now has passing unit coverage.
The protocol remains unfrozen: no source acquisition or model inference ran.

Before publication, fetched GitHub `main`, confirmed no upstream divergence,
inspected the live README and preserved the user's image HTML and attachment URL
exactly.

## Verification

- Focused publication tests: **9 passed in 0.13 seconds**.
- Both new Python modules compiled successfully.
- Staged `git diff --check` passed.
- The staged update contained 12 intended files, 661 insertions and five
  deletions, with no file deletions.
- Push succeeded: `2958767..53ac396 main -> main`.
- The README image remains
  `https://github.com/user-attachments/assets/4da2605a-3a6d-4130-9014-950dc75bd34d`.
- The full suite was not rerun; the prior published development snapshot retains
  its 831-passing-test verification.

## Pending work

Use 1–4,999 nt as the default active range for new work while retaining stricter
method limits where applicable. Do not delete or rewrite historical
5,000/10,000-nt evidence. Any resumed long-sequence work requires a new,
explicitly versioned protocol.

The second fresh-structure panel has focused unit coverage but still requires
scientific review before it may be frozen. No acquisition or inference is
authorized. Independent biological validation below 5,000 nt remains the
current gate.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-16_V4.md
cat configs/project_scope_2026-10-16.json
cat docs/LENGTH_SCOPE.md
.venv/bin/python -m pytest -q tests/test_project_scope.py tests/test_sequence_diverse_structure_panel.py
gh api repos/zyliu-OU/rna-stable-ai/git/ref/heads/main --jq .object.sha
```

Before future GitHub publication, inspect the live README again and preserve the
user's picture and any repository image assets.

