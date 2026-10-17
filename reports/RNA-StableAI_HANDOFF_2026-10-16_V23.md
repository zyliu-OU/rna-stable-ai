# RNA-StableAI handoff — 2026-10-16 V23

Project: RNA-StableAI  
Date: 2026-10-16 (America/Los_Angeles)  
Version: V23  
Workspace: `/home/zyliu/Documents/rna-stable-ai`

## Completed work

- Published the curated Step 2 longer-RNA development update to `zyliu-OU/rna-stable-ai` on `main` in commit `f4b0da0744d8361737066b7402af95f15f649a45` (`Publish longer RNA Step 2 development study`). The publication contains code, four configuration files, three focused test files, the development review, V21/V22 handoffs, and concise run summaries. Upstream bpRNA archives, raw Rfam source files, checkpoints, and full frozen run artifacts remain local.
- Updated the public README with the three-seed 11-reference development result and its limitations. The live README's user-added image tag was preserved exactly; no repository image asset was involved because the picture uses a GitHub attachment URL.
- Kept the active scope at 1–4,999 nt and described the result as development evidence. Independent structure validation and bpRNA training-family provenance remain open. No model inference default or release gate changed.

## Verification

- The clean publication checkout passed 34 focused tests: sampled-pair supervision, bounded exact decoder, longer Rfam panel, and pair-reference tests.
- The clean publication checkout had no uncommitted changes after the push. GitHub reported `main` at `f4b0da0744d8361737066b7402af95f15f649a45`.
- A post-push GitHub README read confirmed the exact image tag, the new longer-length result, and the handoff link. The earlier development run replays and evidence are documented in V22 and `reports/long_length_step2_review_2026-10-16.md`.

## Pending work

- Resolve bpRNA family provenance and obtain an independent family-separated validation panel with complete long-RNA references, including 4,000–4,999 nt if feasible.
- Improve sparse candidate recall and decoded pair recovery using frozen development comparisons. The current learned model still trails LinearFold and ViennaRNA on the selected 11-reference panel.
- Keep full source archives and frozen run artifacts local until redistribution rights and artifact scope are explicitly reviewed. Preserve the README picture in future updates.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/RNA-StableAI_HANDOFF_2026-10-16_V23.md
cat reports/long_length_step2_review_2026-10-16.md
.venv/bin/python -m pytest -q tests/test_sampled_pair_supervision.py tests/test_long_exact_sparse_pairs.py tests/test_long_validation_family.py tests/test_pair_reference.py
gh api repos/zyliu-OU/rna-stable-ai/commits/main --jq .sha
gh api repos/zyliu-OU/rna-stable-ai/contents/README.md?ref=main --jq .content | base64 -d | rg -n '<img|Longer-length development|Latest development handoff'
```
