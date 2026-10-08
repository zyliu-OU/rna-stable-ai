# RNA-StableAI — handoff 2026-10-05 V3

Project: **RNA-StableAI**
Date: **2026-10-05** (America/Los_Angeles)
Version: **V3**
Absolute workspace: `/home/zyliu/Documents/rna-stable-ai`

## Completed work

- User authorized starting experimental evaluation and training, superseding the
  previous handoffs' training deferral. Completed a separate first CPU
  secondary-structure pilot; no energy surrogate or GPU training.
- Imported the locally available PDB-source subset of RNA STRAND S-Processed
  BPSEQ records distributed by EternaFold, with exact metadata/sequence binding.
  Preserved every processed pair and recorded all exclusions/source hashes.
- Frozen prospective configuration and split snapshots; filtered PDB accessions,
  exact duplicates and symmetric SequenceMatcher similarity >=0.8 conflicts.
  Retained **41 train / 12 validation / 16 test**, lengths actually 20–159 nt.
- Trained a separate 10,979-parameter three-state Conv1d baseline for **20 epochs**
  on CPU/two threads. Validation selected **epoch 6**; test is absent from fitting
  and checkpoint-selection APIs. Initial and selected checkpoints are saved.
- Evaluated 16 test records against ViennaRNA, LinearFold, initial/trained CNN and
  all-unpaired baselines: all 32 native folds succeeded; all 80 predictions scored.
- Test pair F1: trained **0.0674603**, untrained **0.0131579**, all-unpaired **0**,
  ViennaRNA/LinearFold both **0.9437730**. The learned baseline is weak and
  overfits; no long-RNA or biological-stability conclusion.
- Added data/training/pilot/audit/plot modules, configuration and 23 tests.
  README and current JSON/Markdown status updated. No GitHub push or system changes.

## Evidence and verification

Pilot run: `/home/zyliu/Documents/rna-stable-ai/results/experimental_pilot_runs/20261006T010347.964097Z`

Latest summary: `results/experimental_pilot_summary.json`
Report: `reports/experimental_pilot_report.md`
Detailed checkpoint: `reports/experimental_training_checkpoint.md`
Diagnostics: `/home/zyliu/Documents/rna-stable-ai/results/experimental_pilot_runs/20261006T010347.964097Z/figures/20261006T010807.239562Z/diagnostics.png`

Full suite: **233 passed**, `reports/tests-experimental-checkpoint.xml`.
Pilot audit passed: raw input/source reconstruction and isolated splits, training-only
label weights, epoch events, validation selection, loaded-checkpoint inference,
raw fold sequence/structure/energy binding and exact scores/coverage/exports.
A negative checkpoint-integrity test rejects corrupted bytes without modifying the run.

The prior equal-budget long study independently re-audited successfully. Its summary
and manifest hashes match the previous recorded values; measured artifacts remain
preserved. Commands and output are in `reports/commands.jsonl`.
Pre-edit backups: `reports/source_backups/20261006T010000.120440Z/`.

## Pending work and limits

This uses processed PDB-derived annotations, not raw experimental pair measurements.
The sequence heuristic is not a family split. Training records are 20–76 nt; no
long-RNA model was trained. Legacy folding-tool parameter overlap is unknown.
A newer DMS dataset was investigated but downloads failed (shell DNS, web HTTP 403);
it was not evaluated. No biological stability measurement or energy surrogate training.

Next, plan a larger RNA-family-separated study and a model that scores global pairs.
Reserve a new independent test cohort before tuning: the current 16-record test has
already been observed. Preserve this first pilot unchanged. Do not retune it against
the reported test scores or overwrite its checkpoints/manifest.

Development changes remain local. Prepare/push when requested using the existing
export checkout and preserving its history. Workspace-root `.git` is a protected
placeholder. Public WIP repository: https://github.com/zyliu-OU/rna-stable-ai
Existing export: `/home/zyliu/Documents/rna-stable-ai/exports/20261005T040714.078931Z/rna-stable-ai`.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/current_work_status.json
.venv/bin/python scripts/log_command.py .venv/bin/python scripts/verify_experimental_pilot.py
.venv/bin/python scripts/log_command.py .venv/bin/python scripts/verify_equal_budget.py --summary results/equal_budget_long_summary.json
.venv/bin/python scripts/log_command.py .venv/bin/python -m pytest -q
```

Import/configuration inspection without a new training run:

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/run_experimental_pilot.py --dry-run
```

Regenerate a standalone diagnostic figure from audited evidence, without training:

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/plot_experimental_pilot.py
```

An explicitly requested replication creates a fresh run (never overwrites this pilot):

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/log_command.py .venv/bin/python scripts/run_experimental_pilot.py
```

Use `.venv`. Preserve tools, raw data, checkpoints, measurements and archives.
No active pilot process remains. Do not modify system Python, NVIDIA drivers, CUDA,
kernel or boot files. Strict historical batch execution-resume provenance guards
remain in effect; completed historical studies should be audited without refolding.
