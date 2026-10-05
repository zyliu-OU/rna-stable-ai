#!/usr/bin/env bash
# Publish the prepared development snapshot; do not touch the working project's Git state.
set -euo pipefail
snapshot=${1:?Usage: scripts/publish_github.sh /absolute/path/to/prepared/rna-stable-ai}
snapshot=$(realpath "$snapshot")
repo=zyliu-OU/rna-stable-ai
test -f "$snapshot/EXPORT_MANIFEST.json"
test -d "$snapshot/.git"
gh auth status
login=$(gh api user --jq .login)
if [[ "$login" != zyliu-OU ]]; then
    echo 'Use the zyliu-OU GitHub account before publishing.' >&2
    exit 1
fi
if gh repo view "$repo" >/dev/null 2>&1; then
    echo "Repository already exists: $repo; inspect it before attaching this snapshot." >&2
    exit 1
fi
gh repo create "$repo" --private \
    --description 'RNA-StableAI: work-in-progress research prototype for reproducible long-RNA folding and constrained optimization benchmarks' \
    --source "$snapshot" --remote origin --push
gh repo view "$repo" --json url,isPrivate --jq '{url: .url, private: .isPrivate}'
git -C "$snapshot" ls-remote --heads origin main
