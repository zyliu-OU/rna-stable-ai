# RNA-StableAI handoff

- Project: RNA-StableAI
- Date: 2026-10-07 (America/Los_Angeles)
- Version: V1
- Workspace: `/home/zyliu/Documents/rna-stable-ai`
- Publication checkout: `/home/zyliu/Documents/rna-stable-ai/exports/20261008T024420.311901Z/rna-stable-ai`
- Repository: https://github.com/zyliu-OU/rna-stable-ai
- Development commit: `607cdf7e8fb3a985ecce456d91dad109cb8775d9`

## Completed work

Reviewed current development and pushed it to the existing GitHub `main` branch, preserving commit `9169b03895074637b320db3090c4495cbab22120` and its history. The update contains helix prediction, matched head studies, decoder penalties, population-sampled training, native journaling/resume protections, development diagnostics and scientific figures, plus retained result evidence. The workspace's original Git index and placeholder remote remain untouched; use the publication checkout for GitHub operations.

Review: `reports/github_update_review_2026-10-07.md`. External dependencies, virtual environment, credentials and top-level trained checkpoints are excluded.

## Verification

- Full suite: **481 passed in 219.21 seconds**.
- Completed first helix replication, nine matched head fits, penalties, population training/resource steps, development slices, figures, extended native references and longer-training availability audits passed.
- Export hashes verified; credential-pattern scan passed; no exported file exceeds 100 MiB. Source/config/test/document whitespace checks passed. Historical logs and generated SVG preserve original bytes.
- Git push succeeded: `9169b03..607cdf7 main -> main`. This handoff is saved after that development push and will also be published.

## Pending work

The second helix study `results/helix_prior_replication_runs/20261007T023827.967339Z` remains incomplete: ten saved component pointers, no aggregate `summary.json`. It was not resumed for publication. Independent family evaluation, longer biological annotations and generalization remain pending. Reused development metrics and native energies do not establish biological stability. Historical paths require local reruns on another machine.

## Exact continuation commands

Verify publication:

```bash
cd /home/zyliu/Documents/rna-stable-ai/exports/20261008T024420.311901Z/rna-stable-ai
git status --short
git log -2 --oneline
git ls-remote origin refs/heads/main
```

Resume the separate incomplete study only from its frozen runner:

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/run_helix_prior_replication.py --resume results/helix_prior_replication_runs/20261007T023827.967339Z --publish-name helix_prior_seed7_replication
.venv/bin/python scripts/run_helix_prior_replication.py --verify --publish-name helix_prior_seed7_replication
.venv/bin/python -m pytest -q
```

If the final handoff push needs to be retried:

```bash
git -C /home/zyliu/Documents/rna-stable-ai/exports/20261008T024420.311901Z/rna-stable-ai push origin main
```
