# RNA-StableAI — handoff 2026-10-05 V2

Project: **RNA-StableAI**
Date: **2026-10-05** (America/Los_Angeles)
Version: **V2**
Absolute workspace: `/home/zyliu/Documents/rna-stable-ai`

## Completed work

- Continued local development after the archive-safe batch progress fix.
- Added `rnastable evaluate-reference` for scoring supplied full dot-bracket
  references and saved predictions on exactly matching sequences, with dry-run validation.
- Added explicit method/reference planning, missing/failed denominators, per-method
  and per-reference-kind aggregates, exact-pair metrics and retained input metadata.
- Added frozen input/provenance evidence and latest/per-run CSV/JSON/report exports;
  `scripts/verify_reference.py` audits identity, scores, coverage and all exports.
- Added two clearly labeled synthetic format-demo configurations and 33 tests.
- Documented the schema, supported structures and score conventions in README.
- Preserved modified files before editing under
  `reports/source_backups/20261006T004822.149269Z/`.
- Saved `reports/reference_development_checkpoint.md` and updated JSON/Markdown status.
- Prior batch counter work remains complete. Strict historical resume rejection is
  unchanged: do not rewrite historical manifests or override recorded provenance.
- No new folds, neural training, installations, system changes or GitHub push.

## Verification

- Final full suite: **210 passed**, `reports/tests-reference-final.xml`.
- New reference-evaluation tests include numerical scores, empty structures,
  reference-kind separation, missing/failure outcomes, invalid plans, CLI behavior,
  changed evidence rejection and preserved-run audits after live input removal.
- CLI demonstration and full reference audit passed: four planned predictions,
  two scored, two missing; handwritten synthetic controls only.
- Demo run: `/home/zyliu/Documents/rna-stable-ai/results/reference_runs/20261006T005240.380877Z`.
- Existing long-study full audit passed: four exact paired inputs, 20 searches,
  256 proposal folds, peak owned concurrency two. Its summary/manifest hashes
  match the previous recorded values. Measured artifacts are preserved.
- Commands and output: `reports/commands.jsonl`.

## Pending work

Select an experimental reference dataset and record source/measurement conditions,
then evaluate independent saved predictions. No experimental dataset has been selected,
downloaded or evaluated; caller reference labels are not source verification. The
current demo establishes software behavior, not experimental accuracy or stability.

Development changes remain local. Prepare/push to the existing public WIP repository
when requested, preserving existing history. Repository:
https://github.com/zyliu-OU/rna-stable-ai

Workspace-root `.git` is a protected placeholder. Existing export checkout:
`/home/zyliu/Documents/rna-stable-ai/exports/20261005T040714.078931Z/rna-stable-ai`.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/current_work_status.json
.venv/bin/python scripts/log_command.py .venv/bin/python scripts/verify_reference.py
.venv/bin/python scripts/log_command.py .venv/bin/python scripts/verify_equal_budget.py --summary results/equal_budget_long_summary.json
.venv/bin/python scripts/log_command.py .venv/bin/python -m pytest -q
```

To audit the retained demonstration independently of the latest publication:

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/verify_reference.py --summary results/reference_runs/20261006T005240.380877Z/results/reference_evaluation_summary.json
```

To exercise the documented input validation without writing a new study:

```bash
cd /home/zyliu/Documents/rna-stable-ai
./scripts/rnastable evaluate-reference --references configs/reference_demo.json --predictions configs/reference_predictions_demo.json --dry-run
```

Use `.venv` and `./scripts/rnastable`. Preserve environments, tools, measured results,
raw evidence and archives. Do not modify system Python, NVIDIA drivers, CUDA, kernel
or boot files. No neural training is authorized by this continuation.
