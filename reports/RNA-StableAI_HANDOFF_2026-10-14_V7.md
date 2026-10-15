# RNA-StableAI handoff — 2026-10-14 V7

Project: RNA-StableAI. Date: 2026-10-14 (America/Los_Angeles). Version: V7.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
State: active autonomous development until the available GPT-6 usage limit.
Interim checkpoint; the user has not requested a pause.

## Completed work since V6

- Declared a separate six-family raw structure-derived feasibility study in
  `configs/raw_structure_panel_2026-10-14.json`. Families RF00379, RF00380,
  RF00442, RF01054, RF01750, RF01786 were unconsumed at metadata/request freeze.
  Its minimum is one supported reference in each of all six families, at least
  six total. This is explicitly a narrow feasibility question; the broader
  12-reference / three sufficiently represented family gate stays open.
- Implemented `scripts/plan_raw_structure_panel.py` with 15 focused checks.
  Frozen all three original model checkpoints and exact selection policy before
  downloads. Acquired/audited all 30 family/clan metadata files, conservatively
  inferring prior exposed families from retained PDB mappings. Fixed 21 candidate
  PDB-chain requests before opening new sequence/contact bytes.
- Implemented `scripts/prepare_raw_structure_references.py` with 12 checks.
  All 21 raw source requests completed. Three responses had unusable sequences;
  seven candidates were redundant and one exceeded the declared final family cap.
  Selected 10 records, all supported single-partner cWW graphs. Family counts:
  c-di-AMP 1, Mbox 1, guanidine-I 3, preQ1-II 1, ZMP/ZTP 3, c-di-GMP-II 1.
  All returned cWW contacts, including crossings and noncanonical chemistry,
  remain in gold sets. Multiple-partner graphs would remain unsupported, never
  projected. Durable validation exposure precedes contact parsing. No replacement.
- Implemented `scripts/verify_raw_structure_identity.py` with 10 checks.
  All 10 selected records match returned PDB/chain IDs and every returned
  contact nucleotide matches its sequence coordinate, including non-cWW rows.
  The three unusable source responses remain explicit rejections. This additional
  audit closes an identity-checking gap without changing frozen raw-source code
  or substituting reference contacts.

## Verification

- Full suite through raw acquisition/binding: **770 passed in 225.84 seconds**,
  `reports/raw-structure-references-full-suite-2026-10-14.log`.
- New metadata/raw acquisition checks: 27 passed. Identity-stage checks: 10 pass;
  combined new focused set: 37 passed in 0.28 seconds.
- Ruff formatting/checks pass for the three new scripts and their tests.
- Metadata/source/identity replays pass without new network requests, exposure,
  model predictions or native folds. Sandbox DNS failures and successful approved
  retries remain separate retained runs.
- A new exact-source archival pass is running/finishing at checkpoint:
  `reports/raw-structure-source-archive-2026-10-14.log`. Prior verified count was
  264/274; do not assume its updated count until reading the result.

## Frozen artifacts

- Metadata protocol: `results/raw_structure_panel_protocol_runs/20261015T024603.141857Z`.
- Metadata: `results/raw_structure_panel_metadata_runs/20261015T024650.695305Z`.
- Raw request protocol: `results/raw_structure_references_protocol_runs/20261015T025018.239045Z`.
- Raw responses/binding: `results/raw_structure_references_runs/20261015T025107.807266Z`.
- Identity audit: `results/raw_structure_identity_runs/20261015T025342.239699Z`.

Models remain original seed-20261006 baseline/stack/helix with exact top-16 sparse
decoder and zero penalty, copied in the metadata protocol. Source families are
now consumed for future independent-test planning. The current study can still
perform its explicitly predeclared feasibility comparison with those frozen
models, but cannot be relabelled as another fresh independent test or close the
broad validation gate. No model/native prediction has run in this continuation.

## Pending work

Implement/test a frozen feasibility evaluator using the existing tested model
loader, exact pair-set scorer, NativeJournal and native controls. Preserve all
10 selected records × six methods (60 planned outcomes) and all failed/null
predictions. Source-level denominator remains 21 requests with every exclusion.
Use 37 C, LinearFold beam 100, 30 seconds / 4 GiB per native request. Plan 20
native requests if all references remain supported. Record test exposure before
loading/invoking models or native tools. Unknown interrupted native requests
must not be retried; audit reads retained journals without native calls.

Freeze native/runtime/model/code inputs, exact identity audit and source binding
before predictions. Check live prior exposure excluding only this source's own
declared exposure; reject external changes before first test start. No fitting,
checkpoint selection or default change based on this pilot. Retain per-family
and per-record descriptive scores; no independent confidence or stability claims.

Latest published GitHub commit remains `ec77cc062481ca03900ef0651d3dd43574ab4eaf`
with the user's picture and its parent commit preserved. V6/V7 status and these
new source-planning stages remain local until a future verified publication.
Keep the active goal running. No user terminal command is required.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-14_V7.md
cat configs/raw_structure_panel_2026-10-14.json
tail -2 reports/raw-structure-source-archive-2026-10-14.log
.venv/bin/python scripts/plan_raw_structure_panel.py --verify results/raw_structure_panel_metadata_summary.json
.venv/bin/python scripts/prepare_raw_structure_references.py --verify results/raw_structure_references_summary.json
.venv/bin/python scripts/verify_raw_structure_identity.py --verify results/raw_structure_identity_summary.json
.venv/bin/python -m pytest -q tests/test_raw_structure_panel.py tests/test_raw_structure_references.py tests/test_raw_structure_identity.py
.venv/bin/python scripts/archive_replay_sources.py --verify
```

Do not edit frozen source drivers or raw data. Create a separate evaluator and
its own immutable run. Inspect current source/identity pointers before starting
duplicate work, and preserve the README picture in all future publications.
