# Measured degradation source preparation

The [OpenVaccine study](https://www.nature.com/articles/s42256-022-00571-8)
reports chemical-degradation measurements on short RNA constructs and provides
public data through its [author repository](https://github.com/eternagame/KaggleOpenVaccine).
This is a possible empirical check of computational proxies. It does not supply
experimental outcomes for RNA-StableAI's proposed mutations, long biological
RNAs or retained cellular function. Supplied predicted structures must not be
scored as experimental structural truth.

The initial source-only protocol pins author commit
`b95af835cc38bd7dc55ed6e7397d124787f86996` and
`data/Kaggle_RYOS_data/Kaggle_RYOS_trainset.json`. It preserves the three original
seed-20261006 models, exact top-16 inference and zero penalty. It also declares
a possible 64-record pilot in lexicographic sequence-ID order with no selection
by quality or measurement value. These are preliminary rules; this source-only
stage does not authorize predictions or native folds.

```bash
.venv/bin/python scripts/prepare_degradation_source.py
.venv/bin/python scripts/prepare_degradation_source.py --acquire
.venv/bin/python scripts/prepare_degradation_source.py --verify
```

A unique source protocol retains model weights, summaries, code and exposure
hashes before downloading assay bytes. Acquisition first requests the pinned
raw author file, with a declared Git-LFS media fallback. Requests have a
30-second socket timeout and a 64-MiB response cap. Failed requests retain an
explicit ledger; absent data does not mean an empty measured cohort. Successful
acquisition binds original bytes without parsing assay labels or selecting
sequences. Offline verification checks exact bytes, the request ledger and
frozen source/model/code bindings, with no network or inference.

Next implement and verify an exact assay-schema binding step before predictions.
Retain all selected identities and all five declared assay fields; keep missing,
invalid or unsupported outcomes visible. Negative normalized measurements should
not be silently clipped. Scored positions, assay errors and quality metadata
need exact length/value validation. Scoring should distinguish chemical-reactivity
measurements from degradation measurements, preserve assay conditions and avoid
calling computational free energy a measured degradation rate.

Freeze the final descriptive analysis, input/reference mapping, current exposure
screen and native resource plan before prediction. Report condition-specific
results and missing denominators; do not tune the model on this pilot. This
benchmark would be an external empirical proxy assessment, not proof of causal
mutation stabilization, independent biological replication or validated function.

The acquired author file uses Pandas column-mapped JSON and contains1,589 rows.
The binding parser checks matching source-row indices across every column before
reconstructing records; NDJSON and record-array fixtures are also supported.
This representation change preserves source IDs, selection and assay coordinates.
The initial strict NDJSON-only attempt failed before exposure or assay binding;
its incomplete run is preserved.

```bash
.venv/bin/python scripts/prepare_degradation_binding.py
.venv/bin/python scripts/prepare_degradation_binding.py --verify
```

The first binding freezes the source, prior exposures, implementation and analysis
plan before inspecting assay vectors. All source sequences are conservatively
registered as validation exposure before binding measurements. Exact target/error
vectors must cover the complete `seq_scored` prefix. Invalid conditions retain
unsupported outcomes and null means; other conditions on that record remain
available. All values and errors are retained, including negative normalized
measurements. Source predicted structures and derived half-life fields are ignored.

The64-record pilot retains320 supported assay outcomes, zero prior sequence
overlaps, and only `SN_filter=1` records. Future analysis must retain empty quality
slices and disclose this source/pilot restriction. The mean of a normalized assay
vector is not a measured whole-RNA half-life. The frozen descriptive plan specifies
Spearman correlations, a minimum of three complete records, and model/native
unpaired fraction, scored-prefix GC fraction and native energy-per-nt proxies.
Native folding is at37C; chemical assay conditions differ. No causal mutation,
independent uncertainty or retained-function claim is supported by this pilot.
Binding replay verifies all source values/errors, coordinates, selection, prior
overlap decisions, code and exposure; it performs no model predictions or folds.
