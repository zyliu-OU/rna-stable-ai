# RNA-StableAI handoff — 2026-10-16 V3

Project: RNA-StableAI. Date: 2026-10-16 (America/Los_Angeles). Version: V3.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
State: the project-wide active length focus is now sequences shorter than 5,000
nt. Existing longer-sequence work is preserved as deferred evidence. There is
no validated release.

## Completed work

Formalized the user's exclusive length boundary: 1–4,999 nt is active scope;
exactly 5,000 nt and longer is preserved, deferred scope. Added the
machine-readable policy `configs/project_scope_2026-10-16.json`, the policy
helper `src/rnastable/project_scope.py`, focused regression tests and
`docs/LENGTH_SCOPE.md`.

The helper validates the fixed boundary, rejects invalid lengths, enforces the
active range when requested, and partitions records without dropping or
truncating deferred sequences. The policy explicitly keeps historical
protocols immutable and prevents deferred evidence from being counted as
active-scope validation.

Updated README, DEVELOPMENT and the new dated roadmap
`reports/PROJECT_ROADMAP_2026-10-16.md`. Existing method-specific bounds remain
in force when stricter than 5,000 nt. The historical 5,000/10,000-nt studies,
commands, code, data, results, reports and provenance remain in place. No old
configuration or artifact was rewritten or deleted.

The second fresh-structure panel files described in V2 remain unverified drafts;
this scope update did not resume or freeze that development.

## Verification

- Focused policy tests: **6 passed in 0.02 seconds**.
- `src/rnastable/project_scope.py` compiled successfully.
- Scoped `git diff --check` passed.
- Existing mixed and structured 5,000/10,000-nt FASTA assets were confirmed
  present.
- The README still contains the user's original image HTML and attachment URL.
- The full suite was not rerun because this change added an isolated policy
  helper, tests and documentation; the focused test covers the boundary and
  preservation behavior.

## Pending work

Apply the policy to each new protocol as it is created. Do not alter historical
protocol bounds or remove longer-sequence evidence. Any future work at 5,000 nt
or above must use a new explicitly versioned protocol and an explicit scope
decision.

Independent biological structure validation below 5,000 nt remains the current
scientific gate. If development resumes, first review and validate the V2 draft
second-panel planner. No model inference is authorized until coverage,
annotation lineage and tool-training provenance gates pass.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-16_V3.md
cat configs/project_scope_2026-10-16.json
cat docs/LENGTH_SCOPE.md
.venv/bin/python -m pytest -q tests/test_project_scope.py
.venv/bin/python -m py_compile src/rnastable/project_scope.py
```

To review, but not automatically freeze, the paused second-panel draft:

```bash
sed -n '1,260p' scripts/plan_sequence_diverse_structure_panel.py
cat configs/fresh_structure_panel_2026-10-16.json
.venv/bin/python -m pytest -q tests/test_sequence_diverse_structure_panel.py
```

Before any future GitHub publication, inspect the live README and preserve the
user's picture and any repository image assets.
