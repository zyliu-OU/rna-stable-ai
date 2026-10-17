# RNA-StableAI handoff — 2026-10-16 V24

Project: RNA-StableAI  
Date: 2026-10-16 (America/Los_Angeles)  
Version: V24  
Workspace: `/home/zyliu/Documents/rna-stable-ai`

## Completed work

- Updated the GitHub README Step 3 entry to include RNA sequence optimization for measured protein expression efficiency, alongside stability. The goal retains the intended encoded protein and required RNA features and remains within the current 1–4,999-nt development scope.
- Added a Step 3 plan: define the target expression system, editable regions, constraints, controls, and measurements; generate valid synonymous and permitted UTR variants; compare fixed baselines and multi-objective candidates on held-out genes/families; then test prioritized variants with biological replicates and time-matched protein and RNA measurements. Total protein output, protein output relative to RNA abundance, RNA persistence, and protein function remain distinct outcomes.
- Kept expression improvement explicitly unverified. Current Step 2 structure-model development and the independent validation gate remain open. Preserved the user-added GitHub README image tag exactly.
- Published the README change and this handoff from a clean checkout of `zyliu-OU/rna-stable-ai`. The local workspace README was not overwritten because the workspace has unrelated staged changes; the live GitHub README is the publication source.

## Verification

- Before editing, fetched `origin/main` in the clean checkout and confirmed it matched the prior published commit `aff053660eb79b9c4b7f75c5bb5811b72451fbbe`. Read the live GitHub README and confirmed its image markup and V23 handoff link.
- Verified the updated README retains the exact image tag once, includes the new Step 3 goal and plan, and links this V24 handoff. Confirmed the publication checkout is clean after pushing. No model code or tests changed in this README-only update.

## Pending work

- Complete the Step 2 longer-sequence validation and bpRNA family-provenance work before using structure predictions as trusted Step 3 design inputs.
- Before an expression study, choose the target protein, host or cell system, editable RNA regions, assay, control sequences, and success thresholds. Then freeze the experimental and analysis protocol.
- Keep expression and stability claims tied to measured outcomes; do not infer improved protein production from predicted folding or sequence proxies alone. Preserve the README picture in future publications.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/RNA-StableAI_HANDOFF_2026-10-16_V24.md
cat reports/long_length_step2_review_2026-10-16.md
gh api repos/zyliu-OU/rna-stable-ai/commits/main --jq .sha
gh api repos/zyliu-OU/rna-stable-ai/contents/README.md?ref=main --jq .content | base64 -d | rg -n '<img|Step 3 goal|protein expression|Latest development handoff'
```
