# RNA-StableAI handoff — 2026-10-14 V4

Project: RNA-StableAI. Date: 2026-10-14 (America/Los_Angeles). Version: V4.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
State: active autonomous development at the user's request; continue until the
available GPT-6 usage limit. No new token budget was specified. This is an interim
checkpoint, not a request to stop. Later versioned handoffs supersede this state.

## Completed work

1. Preserved the user's live GitHub picture in the local README using the exact
   attachment markup recorded in V3. No GitHub write during this development.
2. Implemented `scripts/audit_reference_readiness.py` and a declared coverage
   policy: 12 supported references, at least three families with three each.
   It retains denominators, distinguishes annotation-source claims from verified
   experimental truth, excludes consumed families, ignores model metrics, and
   freezes/replays source, code, policy, and exposure inventories.
   Run: `results/reference_readiness_runs/20261015T020727.857457Z`.
   Historical panels support 9, 8, and 4 references; none meets the new coverage
   minimum. RF00174 explicitly declares `Predicted; PFOLD`. Published citations
   do not certify experimental per-sequence annotations. Added 28 checks and
   `docs/REFERENCE_READINESS.md`.
3. Implemented and tested `scripts/prepare_structure_derived_source.py` and
   `configs/structure_derived_source_2026-10-14.json`. Pinned official Rfam 3D source
   commit `a22cc827b5b99a3e97935384cc0812b73bc49668`, nine exact Git blob identities,
   original seed-20261006 baseline/stack/helix checkpoints, selection rules,
   exposure inventory, and readiness minima before new annotation downloads.
   Families: RF00504 glycine, RF00522 preQ1-I, RF01051 c-di-GMP-I. These were
   unconsumed at freeze. Initial sandbox DNS failure retained; approved retry
   downloaded all nine files with exact Git/SHA-256/size bindings, including the
   Apache-2.0 license, source pipeline, mappings, and three alignments.
   Protocol: `results/structure_derived_source_protocol_runs/20261015T021405.263740Z`.
   Acquisition: `results/structure_derived_source_runs/20261015T021501.529110Z`.
4. Implemented `scripts/prepare_structure_derived_binding.py` and 14 checks.
   Selects by fixed family/PDB/chain/sequence order before contact parsing,
   deduplicates repeated sequences, screens exact mapped PDB/family and heuristic
   prior sequence overlap, and infers additional conservative exposed families
   from retained global PDB mappings. Uses per-sequence `_SS` annotations only,
   never consensus fallback. Different bracket stacks preserve crossing contacts;
   unsupported annotations are not replaced. Durable source exposure precedes
   contact mapping. Derived records retain computational status and explicitly
   do not certify completeness against raw FR3D contacts.

## Verification

- Readiness full suite: **700 passed in 225.31 seconds**;
  `reports/reference-readiness-full-suite-2026-10-14.log`.
- Readiness + source + binding focused checks: **56 passed in 0.30 seconds**.
  Initial constructed binding fixtures had mismatched sequence/annotation widths;
  corrected fixtures now test the intended crossing/gap cases and all pass.
- Ruff formatting/checks pass for the three new scripts and tests.
- Readiness final replay and source acquisition replay pass. No model inference
  or native requests have been issued during this continuation.
- Source archive expanded to **261/271** recorded versions in the completed
  readiness checkpoint. Ten historical versions remain unavailable. Exact initial
  readiness script bytes were preserved before its final revision.

## Pending / running work at checkpoint

The real-source binding is running under the frozen protocol and current prior
exposure inventory. Full regression including the two source-import stages is
also running. Inspect logs before starting duplicate work:
`reports/structure-derived-binding-2026-10-14.log` and
`reports/structure-derived-full-suite-2026-10-14.log`.

Do not edit frozen source/readiness scripts. Preserve binder source bytes before
changing its code after a binding manifest exists. The official upstream writer
assigns cWW brackets positionally; overwrites and raw multiple-partner contacts
are not ruled out. Inspect complete-contact provenance before promoting this
source to independent experimental evidence or running predictions. RF00522 has
only one annotated source structure, so the broad coverage gate may fail.

Continue with binding/replay verification, complete-contact source engineering,
and a more adequate independently annotated panel. No assay-driven model tuning.
Long biological accuracy, controlled mutation effects/function, and validated
release remain pending. Preserve the README picture on every future publication.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-14_V4.md
tail -20 reports/structure-derived-binding-2026-10-14.log
tail -5 reports/structure-derived-full-suite-2026-10-14.log
ps -C python,python3 -o pid,etime,pcpu,comm
.venv/bin/python scripts/prepare_structure_derived_source.py --verify results/structure_derived_source_runs/20261015T021501.529110Z/summary.json
.venv/bin/python scripts/audit_reference_readiness.py --verify results/reference_readiness_summary.json
.venv/bin/python -m pytest -q tests/test_reference_readiness.py tests/test_structure_derived_source.py tests/test_structure_derived_binding.py
```

After successful binding completes:

```bash
.venv/bin/python scripts/prepare_structure_derived_binding.py --verify results/structure_derived_binding_summary.json
.venv/bin/python scripts/archive_replay_sources.py
.venv/bin/python scripts/archive_replay_sources.py --verify
```

Scientific source references: https://docs.rfam.org/en/latest/building-families.html,
https://github.com/Rfam/rfam-3d-seed-alignments, and the pinned source README/code
retained in the acquisition directory. New code/evidence remain local and unpublished.
