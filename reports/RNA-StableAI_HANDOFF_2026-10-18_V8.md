# RNA-StableAI handoff — 2026-10-18 V8

Project: RNA-StableAI
Date: 2026-10-18 (America/Los_Angeles)
Version: V8
Workspace: `/home/zyliu/Documents/rna-stable-ai`
Previous scientific handoff: [V7](RNA-StableAI_HANDOFF_2026-10-18_V7.md).

## Completed publication

Published the October 18 Stage 2 update to [zyliu-OU/rna-stable-ai main](https://github.com/zyliu-OU/rna-stable-ai) in commit [`e1758333075e1c7eaaeea3d22c55d79d1d462c59`](https://github.com/zyliu-OU/rna-stable-ai/commit/e1758333075e1c7eaaeea3d22c55d79d1d462c59), titled `Publish under-3000 nt Stage 2 studies and recovery diagnosis`.

Publication used the isolated checkout `/tmp/rna-stable-ai-publish-20261018-stage2`, based on live main `7cd20e18513cc1d230f6085a195b11faacf803db`. The original workspace retains its placeholder origin and pre-existing staged/unstaged/untracked state; no original index staging, commit or push was performed. The checkout is clean after pushing. GitHub's main commit API returned the exact new commit.

The commit changes 66 files (5,703 insertions, 31 deletions; no deleted files), including:

- Scope policy/config/helper/test and length documentation for **1–2,999 nt**, with historical 3,000+ nt work preserved. Historical October 16 scope remains explicitly loadable.
- Stage 2 gate/roadmap, original scoped BCE training runner, endpoint-ranking and hard-negative studies, gold recovery ceiling diagnostic and endpoint partner/null assignment experiment, associated new modules and tests.
- CRW exposure/original provenance and historical RCSB metadata survey/audit code and reviews. Added BGSU metadata acquisition/config dependency used by the RCSB audit. RCSB 3,000+ nt leads remain historical deferred evidence, not active validation.
- October 18 reviews and handoffs V1–V7, plus October 17 V9, preserving all prior published handoffs and studies.
- Nine byte-identical concise JSON summary/protocol copies, their source/hash manifest and explanation under `reports/stage2_publication_2026-10-18/`. These are provenance/results summaries, **not a complete portable replay bundle**. Exact artifact names and original local paths are listed in that directory's MANIFEST.json.
- Official RCSB instance schema fixture/provenance plus the publication focused-test log.

Full upstream bpRNA/Rfam/GenBank run-source archives, full sequence/reference inventories, gold oracle structures, prediction/candidate arrays and model checkpoints were **not uploaded** by this update. They remain local in the exact paths pinned by V7. No training, native folding, model default or checkpoint promotion occurred for publication.

## README and user picture preservation

Inspected the latest cloned GitHub README before preparing the update, then compared its text against the working README. Differences were the authorized scope, Stage 2/3 plan and handoff/roadmap edits. The exact upstream picture HTML is retained once:

```html
<img width="1774" height="887" alt="image" src="https://github.com/user-attachments/assets/4da2605a-3a6d-4130-9014-950dc75bd34d" />
```

The picture uses a GitHub attachment URL and references no repository image asset. Existing repository image assets were not deleted. The protein-expression plan and unrelated upstream README content remain. README now reports the scoped baseline, assignment variant, oracle diagnostic, negative/mixed studies, Stage 2's open gate and cell-free Stage 3 target. Native-control gaps and one short-seed regression are explicit. Old test totals are labeled historical; new focused results are dated.

After push, fetched GitHub's live README content and verified exact byte equality with the publication checkout and exact image-tag preservation. All 33 local README links resolve in the checkout. The README's latest development handoff links **V7**, which is included in this publication. This V8 publication record is created after push and remains local, not in the commit. The working README was synchronized to the verified published README; no staged index was changed.

Published README SHA-256: `06cfa0cfee6a31937ba0b417c922863beaf343f9ba95c7566152e8f2b9b686c7`.

## Verification and routine issues resolved

- First clean-checkout targeted run: **50 passed, 1 failed in 4.54 s**. The failure was `test_corrected_instance_fields_exist_in_official_schema` reading an ignored local results schema.
- Made the test portable by copying the **exact existing official schema bytes** into `tests/fixtures/rcsb_instance_schema_2026-10-18.json` and changing that one test path. No schema content, scientific assertions, frozen model or study runner changed. Fixture provenance: `tests/fixtures/rcsb_instance_schema_2026-10-18_PROVENANCE.md`; original source URL `https://data.rcsb.org/rest/v1/schema/polymer_entity_instance`; SHA-256 `5fab5922db0ddc09ebf26f592f17009b95f8b04ff4270c395e32ab32cd98c915`.
- Corrected publication run: **51 passed in 4.38 s** across the 11 focused test files listed below. Log: `reports/stage2-publication-focused-tests-2026-10-18.log`.
- Parsed all 30 curated Python source/test files with `ast.parse`; initial 34 README/evidence links passed before adding the test-log links. Final live README's 33 local links passed after push.
- Nine copied summary/protocol files exactly match local SHA-256, checked against the publication MANIFEST.json. No raw results/checkpoint/data paths were staged. All changed files are below 500 KB; before adding the small final test log the total changed-file content was 443,510 bytes.
- `git diff --cached --check` passed before commit. No full repository suite or frozen-study inference replay was rerun solely for publication. V7 retains prior 18-test and full baseline/oracle/assignment replay evidence and all runtime/resource limits.
- First commit attempt found no Git author configured in the fresh checkout. Resolved using command-local identity matching recent upstream commits and authenticated account: Zongyuan Liu, `74483335+zyliu-OU@users.noreply.github.com`. No global identity configuration changed.
- Post-push README fetch initially failed within the network sandbox. Retried with approved escalation and fetched successfully. No publication step remains pending.
- No study/fit/replay process was started this publication turn; push and verification commands finished. Some Git commands emitted environment `Failed to create stream fd` notices but completed successfully; their successful exit codes and remote API verification establish publication outcome.

## Scientific state and pending work

Keep Stage 2 open for **1–2,999 nt**, with cell-free expression Stage 3 queued. Original 103-record BCE remains the comparison baseline. Longer/shorter mean pair F1 are 0.3173511819/0.1560640870; endpoint partner/null auxiliary variant reaches 0.3261881307/0.1606458705. Longer gains occur in all three seeds; short seed20261015 regresses. Native longer LinearFold/ViennaRNA are 0.4381334451/0.4214700331; shorter 0.3301074317/0.3346291106. No independent validation or quantitative acceptance gate has been satisfied.

The baseline full/retained-candidate gold oracle F1 is 0.9606455787/0.8256698667 for long and 0.9027071479/0.7059245554 for short. These label-informed bounds are not model predictions and were not measured on the new assignment checkpoints. Full-reference unsupported/crossing pairs remain in all scoring denominators. Longer candidate and score-selection gaps dominate missed gold counts; this is not a decoder implementation bug finding.

Next priority: audit original sequence/reference chemistry/provenance for `bpRNA_RFAM_5479` (417 nt, 75 noncanonical annotated pairs) without deleting labels or changing the frozen benchmark. Then select one fixed matched follow-up informed by the residual pair-selection gap. Avoid broad sweeps reported as independent validation. Quantitative application-specific criteria, genuinely independent sequence/family/clan-separated evidence, and 2,000–2,999 nt coverage remain unresolved (only one current longer reference). V7 contains complete inventories, exact run/checkpoint/hash paths, losses, per-seed scores, algorithm definitions and scientific limitations; continue from that record plus this publication update.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-18_V8.md
cat reports/RNA-StableAI_HANDOFF_2026-10-18_V7.md
cat reports/stage2_recovery_ceiling_and_assignment_review_2026-10-18.md
cat reports/stage2_publication_2026-10-18/README.md
cat reports/stage2-publication-focused-tests-2026-10-18.log

# Verify live publication head, without using the workspace placeholder origin:
gh api repos/zyliu-OU/rna-stable-ai/commits/main --jq .sha

# Same focused tests, in the retained publication checkout; no fitting:
cd /tmp/rna-stable-ai-publish-20261018-stage2
PYTHONPATH=src:scripts /home/zyliu/Documents/rna-stable-ai/.venv/bin/python -m pytest -q tests/test_crw_panel_exposure.py tests/test_crw_original_provenance.py tests/test_rcsb_long_source_survey.py tests/test_project_scope.py tests/test_stage2_scope_audit.py tests/test_endpoint_ranking.py tests/test_hard_negative_supervision.py tests/test_recovery_ceiling.py tests/test_endpoint_assignment.py tests/test_sampled_pair_supervision.py tests/test_long_exact_sparse_pairs.py
git -c core.fsmonitor=false status --short

# Resume local science / inspect outlier labels without a new fit:
cd /home/zyliu/Documents/rna-stable-ai
rg -n 'bpRNA_RFAM_5479' results/under3000_endpoint_assignment_protocol_runs/20261018T234607.509040Z/validation.json
sed -n '100,180p' scripts/prepare_bprna_training_subset.py
cat configs/stage2_to_stage3_gate_2026-10-18.json
```

For future publication, fetch/inspect the latest upstream README and preserve the user's picture and upstream edits again. Do not publish from the original workspace's unrelated staged files. Do not overwrite earlier handoffs or manifest-pinned sources. This V8 file is the canonical local publication resume note; V7 remains the published scientific detail record.
