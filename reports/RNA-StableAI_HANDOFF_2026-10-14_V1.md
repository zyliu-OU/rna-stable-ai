# RNA-StableAI handoff — 2026-10-14 V1

Project: RNA-StableAI. Date: 2026-10-14 (America/Los_Angeles). Version: V1.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Repository: https://github.com/zyliu-OU/rna-stable-ai (public, `main`).

## Completed work

- Checked actual development beyond the stale October 13 V3 handoff: candidate
  budgets, matched helix objectives, the third prospective panel, the measured
  assay pilot, and exact-source archival were already complete.
- Finished the interrupted GitHub update. Published code, tests, protocols,
  experimental checkpoints, retained data/results, and source archives in commit
  `d0dd8fb72fadf80875fd5859caf15d7640a6930e`, preserving existing history from
  `e63d4f4461bb6ec13bbcedd9d07c13eb93b7aca9` without force-pushing or deleting files.
- Replaced the long front page with a compact overview showing all seven stages,
  current step 4, latest evidence, next research task, quick start, and project
  links. Detailed commands and study history remain in `DEVELOPMENT.md`.
- Added `reports/PROJECT_ROADMAP_2026-10-14.md`, refreshed both current-status
  files, and updated the GitHub repository description to name the current step.
- Updated the snapshot exporter to include the detailed guide and keep host-path
  notes in the documentation. No model, decoder, experiment, or default changed.

## Verification

- Final development suite from October 13: **672 passed in 216.49 seconds**,
  `reports/github-update-full-suite-2026-10-13.log`. Reviewed the saved result;
  no full rerun was needed for the documentation/export change.
- Repeated assay-pilot replay and prospective pair-evaluation replay successfully
  on October 14 without new native requests or test exposure. All 384 assay-pilot
  predictions / 2,880 comparisons remain retained; latest structure panel keeps
  all 90 outcomes, including 66 unsupported/null outcomes.
- Repeated source-archive audit: **257/267** recorded Python versions recovered;
  ten remain explicitly missing. Nine archive regression checks passed.
- Exporter compiled and ran successfully. Verified all **11,931** exported source
  file hashes, front-page/roadmap links, size limits, whitespace, and publication
  scope before the development push. Credential-pattern scan passed.
- GitHub API confirmed the published main commit and the exact README blob hash
  `1abb17e8b15818e2754ee4a765d19a7c667a32b1`; repository description also verified.
- The development push used isolated export
  `/home/zyliu/Documents/rna-stable-ai/exports/20261015T015551.374700Z/rna-stable-ai`.
  The original workspace Git index and placeholder remote were preserved. This
  handoff and completed status are included in a follow-up documentation update.

## Pending work

Current scientific gate: **step 4 — independent biological structure validation**.
Next research task is to design a screened independently annotated panel with
adequate supported references and documented training/tool provenance. Previously
consumed prospective families and the measured-assay source are not fresh tests.
Long biological RNA accuracy, causal mutation benefits, cellular stability,
retained function, and a validated release remain unresolved. The completed
64-construct assay pilot is descriptive and all selected quality flags are 1.
No new experiment was run during this publication task.

## Exact continuation commands

Inspect the current plan and local evidence:

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/RNA-StableAI_HANDOFF_2026-10-14_V1.md
cat reports/PROJECT_ROADMAP_2026-10-14.md
cat reports/current_work_status.md
.venv/bin/python scripts/archive_replay_sources.py --verify
.venv/bin/python scripts/evaluate_degradation_pilot.py --verify
.venv/bin/python scripts/evaluate_prospective_panel.py --verify --reference-format pair_set_zero_based_v1
```

Check GitHub without using the workspace's placeholder origin:

```bash
gh repo view zyliu-OU/rna-stable-ai --json url,description,pushedAt
gh api repos/zyliu-OU/rna-stable-ai/commits/main --jq '{sha: .sha, message: .commit.message}'
```

For a future authorized publication, create a fresh export rather than changing
immutable evidence or force-pushing:

```bash
.venv/bin/python scripts/prepare_github_snapshot.py
```

Attach the returned snapshot to the latest GitHub history in an isolated checkout;
`scripts/publish_github.sh` is for initial repository creation, not updates.
Do not push the original workspace's placeholder remote.
