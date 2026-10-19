# RiboNN fixed-input pretrained inference — 2026-10-18

Human pretrained inference is working in an isolated CPU environment. Two fresh
processes loaded the same 50 checkpoints and produced byte-identical raw output
files: **70 transcript/fold rows × 78 task outputs**. This establishes software
replay, not translation accuracy or cell-free validity.

Canonical run: `results/ribonn_fixed_inference_runs/20261019T045101.117038Z/`.
[Protocol](../configs/ribonn_fixed_inference_v1_2026-10-18.json),
[driver](../scripts/run_ribonn_fixed_inference.py),
[isolated worker](../scripts/ribonn_inference_worker.py),
[checkpoint inventory](ribonn_checkpoint_inventory_2026-10-18.json).

## Source, weights and environment

The pinned author source is Sanofi-Public/RiboNN commit
`dc896e1d1f78bf6b4e9bb7525c7852fcf25532e8`. Model, preprocessing and prediction
source bytes are unchanged. The adapter invokes the released raw per-fold
inference function. Its only loading adjustment sets
`torch.load(map_location="cpu", weights_only=True)`, while checking each requested
checkpoint hash and requiring a tensor-only state dictionary. Strict model state
loading and original forward/ensemble operations are retained.

Zenodo record 17258709 `weights.zip`: **207,395,960 bytes**,
MD5 **dd088ee2feffcda6ce26124a471a140f**, SHA-256
**2ce3bc1adb38ec6752c79147241a4fb2664e9804e806b3eab1287489a15d8b64**.
Acquisition manifest:
`results/ribonn_weight_acquisition_runs/20261019T044334.430330Z/manifest.json`.
All **182 extracted files** were length/hash-verified, including 90 human and
90 mouse state dictionaries plus two run tables. Mouse inference was not run.
The original academic research/noncommercial weight license is retained next
to the archive and in the upstream workspace. No weights are published.

`external/ribonn-inference`: Python **3.10.13**, PyTorch **1.13.1 CPU**, NumPy
**1.22.4**, pandas **2.2.3**, pytorch-lightning **1.8.5**, torchmetrics **1.3.1**,
lightning-utilities **0.10.1**, scikit-learn **1.0.2**, SciPy **1.13.1**,
setuptools **81.0.0**. MKL is **2023.2.0**: initial MKL 2026.1.0 caused a verified
`iJIT_NotifyEvent` import error. The **75-package** explicit URL/build lock and
full archive metadata are saved in `conda_explicit.txt` and
`conda_package_metadata.json`. The original project .venv is unchanged.
This CPU inference environment intentionally omits the released CUDA stack and
unused MLflow training dependency; no training or transfer learning was invoked.

## Protocol and actual results

Select the five largest released validation R² values **within each of ten
folds**, with no tuning on these fixed inputs. Ambiguous ties are rejected.
All 50 model IDs, scores and hashes are frozen in `checkpoint_inventory.json`;
actual loading order/hashes are recorded in each worker summary. Architecture
compatibility is checked across selected checkpoints. Named task
**predicted_TE_HEK293T** was chosen as a software probe, not a cell-free assay
objective. All 78 original tasks are retained; no tissue average is substituted.

Inputs reuse V10's five fixed synthetic annotated transcripts, then add an empty
UTR control and 1,381/1,382-nt 5′ UTR controls. Complete sequence/CDS/context hashes
are in `input_inventory.json`. `validated_input.tsv` contains seven accepted
inputs; `upstream_input.tsv` also includes the excluded control so upstream's
actual length filter is exercised. Full supplied lengths remain below 3,000 nt.
No candidate was generated, optimized or experimentally measured.

The encoder's released channel order is **A,T,C,G plus CDS codon markers**,
start-codon aligned in a **5 × 13,318** tensor. An independent explicit encoder
matches every accepted input exactly. The first implementation's independent
check assumed a different channel order and failed before any model inference;
that check was corrected to match the inspected upstream source, which remained
unchanged. Exact encoded tensor hashes and CDS marker counts are saved in
`inference_*/encoding_audit.json`.

Each process uses two CPU threads, one interop thread, deterministic algorithms,
batch size two, no DataLoader workers, eval mode and no gradients. Recorded
max_shift is zero. Per-fold checkpoint means use the released routine; the
adapter then averages the ten verified fold values for the named task only.
Inputs are joined by ID and sequence, with complete expected fold sets. Reversing
the raw row order preserves fold values and means within floating summation
precision. Missing, duplicate, unexpected, nonfinite or wrong-sequence outputs
are rejected. The over-limit control returns an explicit exclusion.

| Input | Full length nt | 5′ UTR nt | Status | Mean released-task score / reason |
| --- | ---: | ---: | --- | --- |
| fixed_synthetic_64 | 64 | 12 | ok | 1.691883635520935 |
| fixed_synthetic_400 | 400 | 12 | ok | 1.0533050537109374 |
| fixed_synthetic_1000 | 1000 | 12 | ok | 0.34637500792741777 |
| fixed_synthetic_2000 | 2000 | 12 | ok | 0.02124803075566888 |
| fixed_synthetic_2999 | 2999 | 12 | ok | -0.14130756631493568 |
| ribonn_empty_UTRs | 9 | 0 | ok | 1.692789363861084 |
| ribonn_utr5_1381 | 1390 | 1381 | ok | 1.4407749772071838 |
| ribonn_utr5_1382 | 1391 | 1382 | excluded | utr5_exceeds_1381_nt |

These scores are on the **released model target scale**. No inverse transform,
physical unit, protein yield, calibrated biological confidence or validated
cell-free interpretation is asserted. Short/empty-UTR and synthetic inputs are
software controls; successful execution does not establish in-domain accuracy.
No source/training overlap audit or labeled validation was performed.

| Process | Upstream inference s | Full subprocess wall s | Peak VmHWM KiB |
| ---: | ---: | ---: | ---: |
| 0 | 12.992448 | 16.263913 | 382704 |
| 1 | 12.641503 | 14.945671 | 377160 |

Memory is worker Linux post-exec VmHWM, not GPU memory or a worst-case guarantee.
The wall limit is 1,800 seconds per process; no OS memory cap was imposed.

## Verification and artifacts

**50 focused tests passed in 3.38 s.**
[Test record](ribonn-fixed-inference-focused-tests-2026-10-18.log),
[artifact/replay check log](ribonn-fixed-inference-replay-checks-2026-10-18.log).
The run's **49 inventoried artifacts**, eight transcript identities, seven joined
scores and one explicit exclusion verify. Modified joined output in a temporary
copy was rejected by checksum verification; canonical files were untouched.

Raw arrays: `inference_0/raw_fold_predictions.tsv` and
`inference_1/raw_fold_predictions.tsv`. Joined output:
`joined_predictions.json`. Worker summaries/configs/encoding audits, actual model
loads, input and checkpoint inventories, exact source copies, environment lock,
identity and checksums remain local in the canonical run. The upstream workspace
uses a symlink to the retained archive extraction; raw weights are not duplicated
inside the inference run or included in its 49-artifact count.

Summary SHA-256: **deca964a5d5ba53d85a989067ef484d2775cb55502c2d62b540b22699ca6306c**.
No full repository test suite, neural retraining, transfer learning, mouse
inference, RNA candidate optimization, assay or combined-pipeline biological
validation was run. Current output replay compares two executions of the same
pinned implementation/runtime; no external published golden prediction file was
available for comparison.

```bash
cd /home/zyliu/Documents/rna-stable-ai
# Cached artifact/output verification; no weight loading or inference:
PYTHONPATH=src .venv/bin/python scripts/run_ribonn_fixed_inference.py --verify-run results/ribonn_fixed_inference_runs/20261019T045101.117038Z
# Fresh two-process fixed-input inference replay:
PYTHONPATH=src .venv/bin/python scripts/run_ribonn_fixed_inference.py
```

Remaining work: decide and validate the RNAfold-to-STRAND feature mapping or
separately named calibration, connect versioned score records, and complete the
independent Stage 2 gates. Cell-free calibration and expression candidate design
remain queued. No publication or README edit was made.
