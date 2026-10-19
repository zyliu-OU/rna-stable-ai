# RNAfold + STRAND + RiboNN + BoTorch: first integration build

This Stage 2 build runs fixed-input folding and mathematical optimizer checks.
The complete four-component stability/translation pipeline is still being built.
Expression candidate generation remains gated by `configs/stage2_to_stage3_gate_2026-10-18.json`.

## Run the milestone

From `/home/zyliu/Documents/rna-stable-ai`:

```bash
PYTHONPATH=external/four_component_deps:src .venv/bin/python scripts/build_four_component_integration.py
PYTHONPATH=external/four_component_deps:src .venv/bin/python -m pytest -q tests/test_component_integration.py tests/test_discrete_bo.py tests/test_project_scope.py tests/test_stage2_scope_audit.py
```

Each new run creates a unique `results/four_component_build_runs/` directory with
the exact config, source hashes and copies, runtime versions, fixed synthetic
transcripts, RiboNN input TSV and exclusions, positional RNAfold probabilities,
folding settings and parameter-file hash, worker wall time and peak RSS,
per-seed toy optimization histories/checkpoints, comparison to matched-budget
random evaluation, summary and artifact checksums. No model is promoted.

Verify completed artifacts with:

```bash
PYTHONPATH=src .venv/bin/python scripts/verify_four_component_build.py results/four_component_build_runs/RUN_ID
```

The driver accepts `--resume RUN_DIRECTORY` with an identical config,
implementation and recorded core runtime versions. Completed folding outputs
are cached; toy observations are saved atomically after each evaluation.
Resume updates that directory's summaries: use an explicit copied run directory
when checking resume on a completed historical run. Verify completed artifacts
before resuming. Incomplete runs that predate an artifact manifest require
inspection of their cached outputs before resuming.

## Dependencies and pinned sources

BoTorch dependencies live in `external/four_component_deps`, which must be on
`PYTHONPATH` explicitly; the scientific `.venv` dependencies were not replaced.
Exact added versions are in `configs/four_component_optimizer_requirements_2026-10-18.txt`.
Installation into a fresh target (network access required):

```bash
/home/zyliu/anaconda3/bin/python -m pip --python .venv/bin/python install --target external/four_component_deps --no-deps -r configs/four_component_optimizer_requirements_2026-10-18.txt
```

This lock describes added packages and uses existing Python 3.12, torch, NumPy,
SciPy, typing_extensions and packaging from the project environment. Inspect
run `runtime.json` and `identity.json` for the measured runtime. It is not a
complete independent environment export or a wheel hash lock.

The config pins a source manifest under `results/four_component_source_runs/`.
`scripts/inventory_four_component_sources.py` can create a fresh snapshot of the
same upstream commits; it never executes downloaded code. Large data files use
Git blob retrieval. Source files and raw reference data stay local and ignored.
Do not overwrite existing source manifests or substitute a new snapshot in a
completed protocol. Weight metadata can be refreshed separately using
`scripts/inventory_ribonn_weights.py`; that command does not download weights.

## Contracts and remaining integration

`src/rnastable/component_integration.py` defines explicit full-transcript CDS
boundaries, sequence and annotation/context hashes, canonical RNA validation,
standard-code complete-CDS checks, pairwise supplied-edit checks, and RiboNN
input/export and output identity matching. All supplied nucleotides, including
any explicitly supplied poly(A), count toward the 1–2,999 nt cap. No implicit
cap, tail, modification, truncation or normalization is applied.

RiboNN exports full-transcript TSV fields to avoid upstream missing-value
handling of empty UTR columns. The join function consumes **raw per-fold output
from `predict_using_nested_cross_validation_models`**, before `src/main.py`
averages folds and tissue scores. Require a named task and complete expected
fold inventory; join by transcript ID plus sequence, never row order. The
upstream final `prediction_output.txt` has already averaged folds and does not
satisfy this raw output contract. Weight hashes, isolated inference environment,
task units and biological calibration remain pending. The separate weight
license restricts use to academic research and noncommercial purposes.

`ensemble_worker.py` runs MFE plus partition-function calculations in a fresh
CPU process. It reports both MFE and ensemble energy per nucleotide; neither is
silently assigned to STRAND's released `energy` column before extraction audit.
GC is reported as a fraction by the folding adapter; STRAND reference data use
percent units. AUP is mean unpaired probability; ALO reproduces the released R
bounding/log-odds arithmetic. Original reference positional values above one
are preserved and counted. New folding probabilities are validated separately.
No fitted STRAND stability score is returned in this build. An R reference fit,
component-selection policy and original extraction compatibility remain pending.

`discrete_bo.py` fits a double-precision CPU SingleTaskGP and uses analytic
LogExpectedImprovement on a finite mathematical pool. It excludes infeasible
and previously evaluated choices, caches observations, and records selections.
The fixed synthetic transcripts are not optimized. Toy results establish
software mechanics only; they cannot establish biological model accuracy or
that Bayesian optimization improves RNA candidates.

## STRAND reference milestone, October 18

The released-reference regression has now been reproduced under isolated
R 4.5.3 / pls 2.8.5. Training-only LOO PRESS selects two components for the
four-feature model. The reference-only Python export and saved R model replay
match native R predictions within 6e-15. Details, metrics and artifact identities
are in [the reproduction review](../reports/strand_reference_reproduction_review_2026-10-18.md).

The archived paper methods identify **LinearPartition** as the original feature
engine; RNAfold was used for visualization. Six fixed reference-sequence checks
suggest ensemble energy is closer to the released energy column than MFE, but
do not establish unrestricted substitution compatibility. Original extraction
version, beam and parameters remain unpinned. New-sequence stability scoring
and expression candidate design remain disabled. The reference adapter accepts
only frozen released-reference feature identities.

```bash
# Replay saved artifacts without refitting or folding:
PYTHONPATH=src .venv/bin/python scripts/reproduce_strand_reference.py --verify-run results/strand_reference_reproduction_runs/20261019T042427.196161Z

# Create a fresh reproduction run, with two R fits and six fixed-input folds:
PYTHONPATH=src .venv/bin/python scripts/reproduce_strand_reference.py
```

The explicit R environment package lock and archive metadata are retained inside
the run. This is a source-code numerical reproduction under recorded versions;
the paper reports R 4.4.0, and its exact historical pls package build is unknown.
RiboNN pretrained inference was subsequent work at that milestone; its completed
software replay is recorded below. Biological calibration remains pending.

## RiboNN pretrained inference milestone, October 18

Human inference now runs in `external/ribonn-inference`, with released Python
3.10.13, PyTorch 1.13.1 CPU, pytorch-lightning 1.8.5 and NumPy 1.22.4. MKL is
pinned to 2023.2.0 to avoid an observed import failure with the newer library.
The exact 75-package environment lock is retained in the run.

The 207 MB Zenodo weight archive was downloaded and verified. Its original weight
license is retained; it restricts use to academic research and noncommercial
purposes. No weights are published by this work. The source model/data/predict
files remain byte-identical to the pinned author commit. The runtime wrapper
maps tensor-only checkpoint loading to CPU and audits every requested weight
hash; it does not change model layers or preprocessing.

The released top-five-per-fold selection loaded 50 human checkpoints over ten
folds. Two fresh processes produced identical values for all 78 task outputs
on seven accepted fixed inputs; the eighth input was the explicit over-limit
UTR control. The named HEK293T output is a software probe on its released model
scale, not a physical protein-yield estimate or selected cell-free objective.

```bash
# Verify cached artifacts without loading checkpoints:
PYTHONPATH=src .venv/bin/python scripts/run_ribonn_fixed_inference.py --verify-run results/ribonn_fixed_inference_runs/20261019T045101.117038Z

# Fresh two-process pretrained inference replay; no training or candidate design:
PYTHONPATH=src .venv/bin/python scripts/run_ribonn_fixed_inference.py
```

Details: [RiboNN inference review](../reports/ribonn_fixed_inference_review_2026-10-18.md).
The original default output filename is avoided. Raw per-fold outputs, explicit
exclusions, sequence identities, checkpoint order/hashes and resource measurements
remain in the versioned run. Mouse weights were inventoried but not executed.
Unrestricted RNAfold-to-STRAND feature substitution, independent validation and
cell-free calibration remain pending; Stage 2 stays open.
