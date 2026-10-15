# RNA-StableAI handoff — 2026-10-14 V10

Project: RNA-StableAI. Date: 2026-10-14 (America/Los_Angeles). Version: V10.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
State: **development paused at the user's explicit request**. This supersedes
V9's instruction to continue until the usage limit. Publish the checkpoint only;
do not resume development until the user requests it. No development jobs remain.

## Completed work

The prior feasibility/lineage milestone is on GitHub at
`9a68f6dbd4a5958947d4b5826cb7622e653e9152`. Its ten supported raw references,
60 model/control outcomes, source-identity checks, figure and lineage audit remain
unchanged. Step 4, independent biological validation, remains the scientific gate.
Original model checkpoints and defaults are unchanged.

Added `scripts/plan_family_provenance_dataset.py`, its config and 18 tests.
The frozen metadata-only protocol screens previously exposed families/clans and
ranks eligible groups deterministically before any new sequence/structure labels.
All 72 metadata requests verified (30 reused, 42 newly downloaded). From 29
eligible groups the plan fixes 12 training and four validation groups, without
model metrics. This is a development-data plan, not an independent test or a new
trained model. No new sequence/structure labels, inference, fitting or exposure.

Protocol: `results/family_provenance_dataset_protocol_runs/20261015T033100.546708Z/manifest.json`.
Successful metadata run: `results/family_provenance_dataset_metadata_runs/20261015T033435.517946Z`.
Pointer: `results/family_provenance_dataset_metadata_summary.json`.
Initial sandbox DNS failures and the successful approved retry remain recorded.

The README and roadmap now show the paused state and deferred next task. The
user's README picture HTML and attachment URL are preserved exactly. GitHub main
was inspected before publication: no upstream changes since the prior milestone.
Publish from a fresh isolated export; preserve the original workspace Git index.

## Verification

- Full suite: **821 passed in 219.50 seconds**; log
  `reports/family-provenance-dataset-full-suite-2026-10-14.log`.
- Metadata accounting, response hashes and deterministic selection replay passed.
- Source archive: **271/281** recorded Python bindings, 174 current Python files;
  ten historical versions remain explicitly unavailable. Archive replay passed.
- The broad biological gate remains unmet. Legacy model lineage still leaves
  83/136 records without confirmed family assignments. No causal mutation,
  cellular half-life, long biological accuracy or retained-function claim.

## Pending work

After an explicit user resume, implement provenance-controlled development-data
preparation under the frozen source/selection rules, retaining complete supported
pair sets and fixed exclusions. No pretrained inheritance from unresolved old
data is planned. Training requires a separate deliberate continuation; this
metadata phase does not authorize training. Fresh independent biological testing,
long biological RNA, stability/function evidence and validated release remain open.

## Exact continuation commands

Read-only checks, safe while paused:

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-14_V10.md
cat reports/current_work_status.md
.venv/bin/python scripts/plan_family_provenance_dataset.py --verify results/family_provenance_dataset_metadata_summary.json
.venv/bin/python scripts/archive_replay_sources.py --verify
gh api repos/zyliu-OU/rna-stable-ai/commits/main --jq '{sha: .sha, message: .commit.message}'
```

Optional full verification, not development:

```bash
.venv/bin/python -m pytest -q
```

For an authorized later implementation, first inspect the immutable protocol and
metadata summary above. No dataset-builder/training command exists yet; do not
invent one or silently acquire new labels while development is paused. Preserve
the live README picture and merge upstream edits before every publication.
