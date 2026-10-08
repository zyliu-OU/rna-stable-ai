# RNA-StableAI — handoff 2026-10-05 V4

Project: **RNA-StableAI**
Date: **2026-10-05** (America/Los_Angeles)
Version: **V4**
Absolute workspace: `/home/zyliu/Documents/rna-stable-ai`

## Completed work

- Added direct symmetric pair scoring and optimal noncrossing/canonical decoding
  under the learned-logit objective. No physical-energy interpretation; bounded to
  256 nt (quadratic memory, cubic decoding).
- Added training-only masked-pair supervision and loss weighting, unsupported-contact
  counts, immutable input/config/code snapshots and validation-only model selection.
- Trained 10 CPU epochs on the existing **41 train / 12 validation** development records;
  selected epoch **10**. Validation pair F1 **0.5411435**, initial model **0.1487671**.
  These are reused development-validation scores, not independent test accuracy.
- The new model has **no test input or test evaluation**. No native folds were rerun.
- Added family-plan creation/replay tools requiring explicit source-backed,
  sequence-hash-bound family IDs. Family/accession/sequence separation and prior-test
  exposure checks occur before outputs. CLI adds all 69 known pilot exposures;
  broad RNA-type metadata is never inferred as family IDs.
- No real family-separated plan created; verified assignments/fresh data are still
  needed. Synthetic tests establish planner behavior only.
- Updated README and status, preserved edited files before development under
  `reports/source_backups/20261006T013114.578273Z/`. No GitHub push or system changes.

## Evidence and verification

Pair development run: `/home/zyliu/Documents/rna-stable-ai/results/pair_development_runs/20261006T013412.256466Z`
Latest summary: `results/pair_development_summary.json`
Detailed report: `reports/pair_development_checkpoint.md`

**257 tests passed**, `reports/tests-pair-development-checkpoint.xml`.
24 added tests cover decoder optimality/exhaustive search, global-vs-greedy choices,
score symmetry/gradients/bounds, pair supervision, weight changes, family and exposure
rejections, frozen-plan/ledger replay and corruption guards, and saved-checkpoint audit.
Pair audit passed: data hashes, train/validation separation, training-only weights,
epoch history, validation selection, all loaded-checkpoint predictions and score exports.

The original experimental pilot summary and long-study summary/manifest hashes remain
unchanged. Their evidence is preserved. Existing regression tests may replay old
checkpoints for integrity; they do not score the new model on that old test set.
Commands/output are in `reports/commands.jsonl`.

## Pending work

Acquire a fresh cohort with verified sequence-bound family IDs and source/measurement
metadata. Use the planner and full prior-exposure ledger to freeze disjoint families
and reserve a new independent test before training/tuning. Current local metadata
has only broad RNA types, which cannot substantiate a family-separated study.

Run a family-separated training study and then evaluate the new reserved test once.
The prior 16-record test has already been observed; do not reuse it as fresh evidence.
Develop a scalable model/decoder before addressing long RNA. No energy surrogate
or biological-stability measurement has been implemented.

Development remains local. Push when requested using the existing export checkout
and preserving its history; workspace-root `.git` is a protected placeholder.
Repository: https://github.com/zyliu-OU/rna-stable-ai
Export: `/home/zyliu/Documents/rna-stable-ai/exports/20261005T040714.078931Z/rna-stable-ai`.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/current_work_status.json
.venv/bin/python scripts/log_command.py .venv/bin/python scripts/verify_pair_development.py
.venv/bin/python scripts/log_command.py .venv/bin/python -m pytest -q
```

Once the four new data/metadata files exist (README documents their schemas):

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/plan_family_study.py --references data/new_references.json --assignments data/verified_families.json --plan configs/new_family_plan.json --exposure data/exposure.json
.venv/bin/python scripts/verify_family_plan.py --run results/family_plans/<printed-UTC>
```

Those input paths are future inputs, not files already created. Do not manufacture
family annotations or call an empty exposure ledger evidence of an untouched test.

For an explicitly requested development replication, this creates a fresh run and
still performs validation only:

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/log_command.py .venv/bin/python scripts/train_pair_development.py
```

Use `.venv`. Preserve environments, tools, raw evidence, checkpoints, manifests and
prior reports. No active development process remains. Do not modify system Python,
NVIDIA drivers, CUDA, kernel or boot files. Historical batch execution resumes still
require exact frozen provenance; audit completed historical runs without refolding.
