# RNA-StableAI handoff — 2026-10-14 V5

Project: RNA-StableAI. Date: 2026-10-14 (America/Los_Angeles). Version: V5.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
State: active autonomous development until the available GPT-6 usage limit, as
requested. This checkpoint does not pause the goal. No explicit token budget.

## Completed work

- Completed all V4 pending binding and regression work. Added four new drivers:
  `audit_reference_readiness.py`, `prepare_structure_derived_source.py`,
  `prepare_structure_derived_binding.py`, `audit_structure_contact_provenance.py`.
- Audited all three historical panels without model metrics. Supported counts
  9/8/4 fail the declared broad coverage minimum. Cobalamin explicitly uses PFOLD;
  a published citation is not automatically experimental per-sequence truth.
- Acquired nine pinned official Rfam 3D source files from commit
  `a22cc827b5b99a3e97935384cc0812b73bc49668`, preserving license and source code.
  Bound six exact per-sequence annotations from 41 candidates (35 redundant):
  glycine 3, preQ1-I 1, c-di-GMP-I 2. No consensus fallback, contact deletion,
  unsupported replacement, or model/default change. Durable validation exposure
  preceded contact mapping. New source families are consumed for future planning.
- Frozen and completed a distinct raw FR3D source-integrity audit for six PDB
  chains. All six raw sequences match; only 6WLT/A, 2L1V/A and 3IRW/R have identical
  supplied/current contact sets. 3OWI/A, 3P49/A and 4YAZ/A differ. All raw graph
  edges and set differences are retained; original references were not replaced.
  Differences may reflect versions or representation; no causal attribution.
- Retained the user's picture in local README. Checked live GitHub edits since
  `45d3d4c7fe9fb75415f57381ad5996a3dfda7b78`: the sole upstream change is that
  picture, committed at `5a2c05dd90b7ee28aa334f9fcb9046a23e7a5be6`.
- Updated concise README, roadmap, source attribution, and methods. See
  `reports/development_2026-10-14_review.md` for evidence and limitations.

## Verification

- Full suite: **743 passed in 217.45 seconds**, recorded in
  `reports/structure-contact-provenance-full-suite-2026-10-14.log`.
- 71 new focused checks cover coverage/source claims, source/model freeze-before-
  network, coordinate/crossing preservation, non-replacement, exposure ordering,
  missing sources, complete raw graphs/multiple partners, and hash-bound replay.
- All four scripts/tests pass Ruff. Source/readiness/binding/raw-contact replays
  pass. Replays create no new exposure, network requests, predictions or native folds.
- Exact-source archive: **264/274** recorded Python bindings; ten historical
  versions remain explicitly unavailable. Captured current bundle has 167 files.
- Known exposure inventory now has 4,835 records. Models and native defaults
  remain unchanged. No model prediction or native folding during this continuation.

## Retained run directories

- Readiness: `results/reference_readiness_runs/20261015T020727.857457Z`.
- Source protocol: `results/structure_derived_source_protocol_runs/20261015T021405.263740Z`.
- Source: `results/structure_derived_source_runs/20261015T021501.529110Z`.
- Binding: `results/structure_derived_binding_runs/20261015T021934.814458Z`.
- Raw protocol: `results/structure_contact_provenance_protocol_runs/20261015T022345.539073Z`.
- Raw responses: `results/structure_contact_provenance_runs/20261015T022710.758207Z`.

Sandbox DNS failures and successful approved retries remain separate immutable
runs. Source-derived records remain conservatively computational; exact raw
contact completeness, source versions, and training/tool independence are not
automatically certified by a PDB-derived string or a citation.

## Pending work

Publish this verified milestone from an isolated export, based on the latest
GitHub main history including the user's picture. Inspect upstream again before
pushing; do not force-push, delete prior artifacts, or overwrite upstream edits.
Original workspace index/placeholder remote remain untouched.

Continue development by freezing raw contact graphs directly for a separate
unconsumed-family source panel, with exact PDB/chain/sequence mapping and explicit
single-partner/contact-completeness gates. Broader coverage remains open; six
source references do not meet the 12-reference / three represented-family minimum.
Do not promote the current six into a new independent test or tune models on
source-quality findings. Long biological accuracy, controlled mutation benefits,
retained function, and validated release remain pending.

Do not edit frozen drivers after their manifests without preserving exact prior
source bytes. No user terminal action is required at this checkpoint.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-14_V5.md
cat reports/development_2026-10-14_review.md
.venv/bin/python scripts/audit_reference_readiness.py --verify results/reference_readiness_summary.json
.venv/bin/python scripts/prepare_structure_derived_source.py --verify results/structure_derived_source_runs/20261015T021501.529110Z/summary.json
.venv/bin/python scripts/prepare_structure_derived_binding.py --verify results/structure_derived_binding_summary.json
.venv/bin/python scripts/audit_structure_contact_provenance.py --verify results/structure_contact_provenance_summary.json
.venv/bin/python scripts/archive_replay_sources.py --verify
gh api repos/zyliu-OU/rna-stable-ai/readme --jq .content | base64 --decode
.venv/bin/python scripts/prepare_github_snapshot.py
```

Use the export's own Git checkout with current upstream main as parent;
`scripts/publish_github.sh` is initial-create only. Never push the workspace's
placeholder origin. Keep the goal active after this milestone and continue.
