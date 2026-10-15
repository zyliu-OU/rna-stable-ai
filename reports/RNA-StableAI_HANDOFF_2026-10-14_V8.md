# RNA-StableAI handoff — 2026-10-14 V8

Project: RNA-StableAI. Date: 2026-10-14 (America/Los_Angeles). Version: V8.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
State: active autonomous development until the available GPT-6 usage limit.
This is an interim checkpoint; no pause or new user command is required.

## Completed since V7

1. Implemented/tested/frozen `scripts/evaluate_raw_structure_feasibility.py`.
   Completed all **60/60** planned model/control outcomes on 10 raw PDB-derived
   references across six families. All **20/20** native requests complete,
   **zero unknown**, 1.740145475 known native wall seconds. Original three
   seed-20261006 models, exact top-16 decoder, zero penalty, 37 C / beam 100 /
   30-second / 4-GiB native settings remained fixed. Durable test exposure precedes
   model loading and native calls. Unknown interrupted native requests are never
   retried. Replay uses frozen weights and retained native journals.
2. Descriptive mean pair F1: baseline 0.123592, stack 0.140203, helix 0.325531,
   all-unpaired 0.0, ViennaRNA 0.626116, LinearFold 0.626116. The native tools
   return identical structures on all ten inputs; this is not two independent
   replications. Gold retains 271 cWW contacts, seven noncanonical combinations,
   and nine crossing-reference records. No model/default selection from outcomes.
3. Exported/visually inspected source-bound PNG/SVG via
   `scripts/plot_raw_structure_feasibility.py`. Figure binds exact scores and
   source/code hashes; no added native calls or fitting.
4. Implemented and replayed `scripts/audit_checkpoint_lineage.py` with nine checks.
   All three models use identical frozen corpus bytes, 89 training / 47 validation
   records, matched to historical exposure events and checkpoint bytes. Across
   each 136 records: 47 supplied family IDs, six whole-PDB candidate family
   mappings, 83 family-unresolved. Candidates are not sequence/chain assignments.
   Project training uses source train 65 / holdout 24; project validation uses
   source train 8 / holdout 29 / test 10. Source-test records are already
   development exposure, not fresh independent tests.
5. Added `reports/raw_structure_feasibility_review_2026-10-14.md`,
   `docs/CHECKPOINT_LINEAGE.md`, and refreshed concise README/roadmap/current status.
   The exact user README picture is retained. Current milestone publication is
   being prepared from an isolated export after inspecting upstream.

## Verification

- **803 passed in 216.32 seconds**, full suite in
  `reports/checkpoint-lineage-full-suite-2026-10-14.log`.
- Fourteen evaluator checks include exposure ordering, live-source gates,
  failed/null outcomes, runtime/weight/code tampering, orphan outputs, interrupted
  native non-retry and replay without callbacks. Nine lineage checks bind metadata
  to datasets/exposures/weights. All related Ruff checks pass.
- Source/identity/feasibility/lineage replays pass without new native calls or
  exposure. Figure inspected at full readable resolution.
- Exact-source archive: **270/280** recorded Python bindings; ten historical
  versions remain explicitly missing. Captured current bundle: 173 Python files.
- All computational jobs are complete at this checkpoint.

## Canonical run paths

- Metadata protocol: `results/raw_structure_panel_protocol_runs/20261015T024603.141857Z`.
- Metadata: `results/raw_structure_panel_metadata_runs/20261015T024650.695305Z`.
- Raw protocol: `results/raw_structure_references_protocol_runs/20261015T025018.239045Z`.
- Raw references: `results/raw_structure_references_runs/20261015T025107.807266Z`.
- Identity: `results/raw_structure_identity_runs/20261015T025342.239699Z`.
- Evaluation: `results/raw_structure_feasibility_runs/20261015T025936.192087Z`.
- Figure: `results/raw_structure_feasibility_figures/20261015T030234.188591Z`.
- Lineage: `results/checkpoint_lineage_runs/20261015T030800.142018Z`.

## Pending work

Publish this verified milestone while preserving current GitHub history, upstream
edits, all previous artifacts and the user's README picture. Previous published
commit: `ec77cc062481ca03900ef0651d3dd43574ab4eaf`. Do not force-push or change the
original workspace index/placeholder origin. Record the actual publication commit
in a new handoff after remote verification.

Continue with an explicitly source-labelled, family/clan-aware training/validation
data-development plan. The 83 unresolved development-family assignments motivate
that work; do not fabricate assignments from organism or RNA-type text. Design
metadata/provenance and split rules before new labels. Exclude all consumed
test/assay/raw-source families from new model-selection evidence. No reuse of
the present cohort as a fresh test, or tuning/calibration on these outcomes.

The six-family feasibility minimum passed, but broad biological validation did
not: fewer than 12 references, only two families with three references each,
unknown training/tool provenance, derived rather than direct assay references.
Long biological accuracy, controlled mutation effects, retained function and a
validated release remain pending. Current learned checkpoints are unchanged.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-14_V8.md
cat reports/raw_structure_feasibility_review_2026-10-14.md
cat docs/CHECKPOINT_LINEAGE.md
.venv/bin/python scripts/evaluate_raw_structure_feasibility.py --verify results/raw_structure_feasibility_summary.json
.venv/bin/python scripts/audit_checkpoint_lineage.py --verify results/checkpoint_lineage_summary.json
.venv/bin/python scripts/archive_replay_sources.py --verify
gh api repos/zyliu-OU/rna-stable-ai/readme --jq .content | base64 --decode
.venv/bin/python scripts/prepare_github_snapshot.py
```

Use a new isolated export with latest GitHub main as parent. Continue under the
active goal after publication; the user requested work until the usage limit.
