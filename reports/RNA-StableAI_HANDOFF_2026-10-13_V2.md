# RNA-StableAI handoff

Project: RNA-StableAI. Date: 2026-10-13 (America/Los_Angeles). Version: V2.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Status: **Ongoing autonomous build; development objective comparison complete,
third-panel metadata screening running. This checkpoint does not end the work.**

## Completed work

Implemented `scripts/run_helix_objective_development.py`, 14 new tests,
`docs/HELIX_OBJECTIVE_DEVELOPMENT.md` and README instructions. Declared and
completed three fresh helix structured-hinge-plus-0.1-BCE fits against the original
matched BCE fits: same 89 training/47 validation records, initial state, ten epochs,
optimizer and exact top16 decoder. All 141 paired outcomes and 30 slices remain
reported. Each new fit retains 890 loss decisions; all initial states/predictions,
training ledgers, gold retention, selected checkpoint outputs and full validation
BCE replay. New structured F1 is0.429375/0.417392/0.446825 versus
BCE0.524423/0.495077/0.491069. False positives improve but F1 falls for every
seed. Existing model pointers and defaults remain unchanged. No native folds or
prospective inference occurred in this experiment.

Run: `results/helix_objective_development_runs/20261014T002930.596309Z`.
Review: `reports/helix_objective_development_review_2026-10-13.md`.

Frozen third prospective source proposal RF00010/RF00023/RF00168 in
`configs/prospective_pair_family_panel_2026-10-13.json` using original seed20261006
baseline/stack/helix models and `pair_set_zero_based_v1`.
Protocol: `results/prospective_family_protocol_runs/20261014T003018.640568Z/manifest.json`.
Sandbox DNS-failed acquisition retained at
`results/prospective_family_acquisition_runs/20261014T003036.122470Z`.
Approved outside-sandbox retry downloaded all6 metadata files, 982 total seed
sequences, at `results/prospective_family_acquisition_runs/20261014T003052.784986Z`.
It is still screening prior exposure/redundancy; raw successful downloads are not
a completed screened cohort. Existing evidence pointer remains historical.
An early evidence invocation safely rejected the incomplete acquisition pointer.
Use the exact retry run after its summary exists.

## Verification

Full suite: **602 passed in219.41seconds**.
Focused new objective tests:14 passed; broader objective/structured/budget/
prospective integration set:53 passed. Complete objective replay:3/3 fits and
141 planned paired outcomes pass. Ruff, compileall and whitespace checks pass.
Logs: `reports/helix-objective-development-2026-10-13.log`,
`reports/helix-objective-audit-2026-10-13.log`,
`reports/helix-objective-focused-2026-10-13.log`,
`reports/helix-objective-integration-focused-2026-10-13.log`,
`reports/helix-objective-full-suite-2026-10-13.log`.
No Git index change, commit, push or publication.

## Pending work

Wait for metadata screening to complete, audit the immutable acquisition summary,
download hash-bound annotation/provenance evidence outside the sandbox, verify it,
and bind exact full contacts/known overlap before preparing any evaluation. Never
use a historical evidence pointer with the new protocol. Failed/unsupported outcomes
retain denominators. Named unexposed family IDs do not certify unknown training/
tool provenance;3104 of3202 known exposure records have no family ID.

User requested continued autonomous work until a terminal command is necessary.
The approved network retry works; no user terminal command is currently required.
Active goal remains running. Current shell sessions at save: metadata acquisition
2820 (outside sandbox). Finished full suite17881, training33108 and objective
replay90391 need no further work. If resuming after session loss, inspect the unique
acquisition directory before creating another retained attempt; do not overwrite it.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
tail -5 reports/prospective-third-family-acquisition-retry-2026-10-13.log
test -f results/prospective_family_acquisition_runs/20261014T003052.784986Z/summary.json
.venv/bin/python scripts/run_helix_objective_development.py --verify
```

Only after the successful acquisition summary exists and passes its audit:

```bash
.venv/bin/python scripts/download_prospective_evidence.py --acquisition results/prospective_family_acquisition_runs/20261014T003052.784986Z/summary.json
.venv/bin/python scripts/download_prospective_evidence.py --verify
.venv/bin/python scripts/evaluate_prospective_panel.py --reference-format pair_set_zero_based_v1
```

Network commands require outside-sandbox execution here. Preparation must clear
known source overlap, reference binding and current exposure gates before running
`--evaluate`. Preserve previously consumed panels; do not tune on their scores.
