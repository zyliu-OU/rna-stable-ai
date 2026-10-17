# RNA-StableAI handoff — 2026-10-16 V22

Project: RNA-StableAI  
Date: 2026-10-16 (America/Los_Angeles)  
Version: V22  
Workspace: `/home/zyliu/Documents/rna-stable-ai`

## Completed work

- Continued Step 2 core structure-model development in the active 1–4,999-nt scope. Added bounded exact sparse-pair decoding (`src/rnastable/long_exact_sparse_pairs.py`) and a synthetic 4,999-nt sampled training smoke (`scripts/smoke_sampled_pair_training.py`). No production inference default changed.
- Froze and acquired two preselected Rfam longer-reference panels; both failed their predeclared completeness gates (2 and 1 complete references). Preserved all attempts. Screened an already acquired larger Rfam pool to create an 11-record, four-family, 1,399–3,100-nt development panel. Selection used reference completeness, so this is not an independent test.
- Screened a 24-record bpRNA metadata pool and selected 17 training-only RNAs of 1,158–3,995 nt. A real 3,995-nt record completed a sampled-pair optimizer step with peak process RSS 683,184 KiB.
- Evaluated two older frozen checkpoints with the same bounded exact top-16 decoder on the 11-reference development panel: pair F1 0.0817 control and 0.1901 extended. Native baselines reached 0.4742 LinearFold and 0.4499 ViennaRNA, with all 11 folds successful in each arm. Candidate coverage remains limited.
- Ran a matched three-seed comparison with 88 prior training records versus the same 88 plus 17 longer records. Both arms used sampled-pair loss and identical initial weights for each seed. Mean development pair F1 increased from 0.2605 to 0.2960; paired gain was +0.0355, positive in all three seeds. These are development results, not generalization evidence.
- Wrote the detailed review at `reports/long_length_step2_review_2026-10-16.md`. Did not edit or publish the README; its user-added picture remains untouched.

## Verification

- Focused suite: 34 passed (`test_sampled_pair_supervision.py`, `test_long_exact_sparse_pairs.py`, `test_long_validation_family.py`, `test_pair_reference.py`). Python compilation passed for all new longer-length scripts and decoder.
- The two Rfam panels, bpRNA training-only screen, development reference screen, frozen checkpoint predictions, native controls, and all six matched fits have deterministic replay verifiers. The six-fit replay rechecked saved checkpoint states and predictions.
- Canonical evidence: `results/sampled_long_development_runs/20261017T034847.147062Z/summary.json`; `results/long_validation_coverage_runs/20261017T033935.363253Z/summary.json`; `results/long_native_controls_runs/20261017T034318.804594Z/summary.json`. Protocols and full run locations are listed in the review.

## Pending work and interpretation

- Resolve family provenance of the 17 bpRNA additions. The current 11-record panel was selected using reference completeness and is related within families; no independent family-separated structure-validation claim is supported. Coverage also stops at 3,100 nt.
- Improve candidate recall and decoding under a frozen comparison. The older checkpoint diagnostic retained 25.9% and 40.5% of legal gold pairs in top-16 candidates.
- Obtain a frozen independent long validation panel, ideally including 4,000–4,999 nt with complete labels. Keep native controls and the independent structure gate. Do not promote a checkpoint or start expression optimization from these development results.
- Preserve historical >=5,000-nt assets outside active Step 2 work. Before any GitHub publication, inspect the latest live README, merge upstream edits, and preserve its picture markup and image assets.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/RNA-StableAI_HANDOFF_2026-10-16_V22.md
cat reports/long_length_step2_review_2026-10-16.md
.venv/bin/python -m pytest -q tests/test_sampled_pair_supervision.py tests/test_long_exact_sparse_pairs.py tests/test_long_validation_family.py tests/test_pair_reference.py
.venv/bin/python scripts/verify_long_validation_family.py results/long_validation_family_runs/20261017T033513.077462Z/summary.json
.venv/bin/python scripts/verify_long_validation_family.py results/long_validation_family_v2_runs/20261017T033627.321212Z/summary.json
.venv/bin/python scripts/verify_bprna_long_training_smoke.py results/bprna_long_training_smoke_runs/20261017T033749.792816Z/summary.json
.venv/bin/python scripts/verify_long_validation_coverage.py results/long_validation_coverage_runs/20261017T033935.363253Z/summary.json
.venv/bin/python scripts/verify_long_length_checkpoints_v3.py results/long_length_checkpoint_evaluation_v3_runs/20261017T034635.042291Z/summary.json
.venv/bin/python scripts/verify_long_native_controls.py results/long_native_controls_runs/20261017T034318.804594Z/summary.json
.venv/bin/python scripts/verify_sampled_long_development.py results/sampled_long_development_runs/20261017T034847.147062Z/summary.json
git status --short -- reports scripts configs src/rnastable tests results
```
