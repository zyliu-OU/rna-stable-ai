# RNA-StableAI

**Status: work in progress — research prototype.** This repository records ongoing
development and measured experiments; no release or trained model is published.

The saved evidence retains its original host paths and timestamps. On another
machine, rerun the pipeline to produce local artifacts; historical audit scripts
may require those original paths. External tools and environments are installed
locally by setup and are not vendored in this repository.

V1 research pipeline for deterministic 1,000–10,000 nt RNA controls, CPU folding
benchmarks, and a separate untrained PyTorch encoder throughput baseline.

Eight FASTA controls cover four lengths and two sequence types. Structured controls
repeat designed reverse-complement stems and loops; mixed controls alternate GC-rich,
AU-rich and balanced blocks. Seeds, sequence hashes and configuration accompany every run.

CPU folding uses RNAfold when available or ViennaRNA Python bindings in a subprocess.
LinearFold-V uses beam 100 and reports approximate minimum energy in kcal/mol;
LinearPartition-V uses partition-only mode and reports ensemble free energy, not MFE.
These tools are benchmarked on CPU. Each invocation has a 120-second timeout and an
8 GiB per-process address-space cap. Wall time includes startup. GNU time reports
maximum RSS when available; failed/timeout/unavailable values remain blank.

The separate encoder embeds A/C/G/U tokens and uses Conv1d, GELU and mean pooling.
It has no attention matrix, uses fixed random weights, and performs inference only.
CPU median wall time, GPU median CUDA event time, pinned H2D transfer time, batch size
and peak allocated/reserved GPU memory are distinct fields. CUDA failures are explicit
skips. A CPU encoder measurement is not an RNA folding measurement.

## Install locally

```bash
cd rna-stable-ai
python3 scripts/setup.py
.venv/bin/python -m rnastable doctor
.venv/bin/python -m pytest -q
```

Setup prefers uv and installs Python 3.12 and packages into project-local locations.
It preserves existing environments, records commands, and attempts each C++ tool even
when Python setup fails. The CUDA 13.0 PyTorch wheel requires an operational compatible
driver; it does not alter the installed toolkit. Select another official wheel index
if deploying on a different driver. Inspect upstream sources and installed versions
before assuming the setup succeeded. Successful environment freezes and tool Git hashes
are logged for pinning subsequent runs. Package specifications are unpinned until a
successful installation produces a lock. The recorded host freeze is included in reports/.

ViennaRNA pip installation supplies CPU bindings; a separately installed RNAfold is
preferred if discovered on PATH or under external/vienna/bin. Upstream references:
[ViennaRNA](https://www.tbi.univie.ac.at/RNA/documentation.html),
[LinearFold](https://github.com/LinearFold/LinearFold),
[LinearPartition](https://github.com/LinearFold/LinearPartition),
[EternaFold](https://github.com/WaymentSteeleLab/EternaFold),
[PyTorch](https://pytorch.org/get-started/locally/).
EternaFold is an optional source-build attempt, not part of the V1 timing comparison.

## Run

```bash
./scripts/rnastable generate --config configs/benchmark.json
./scripts/rnastable benchmark --config configs/benchmark.json
```

`rnastable` is installed as a console entry point when setup succeeds. The executable
`scripts/rnastable` also works directly from any directory, selecting .venv if present
and otherwise the existing python3. `--output-root` supports isolated result directories.
Existing FASTA files are accepted only if identical; differing content is preserved and
rejected. Prior benchmark CSV/JSON/report files are copied to results/runs before new
results are written. Every folding subprocess stores raw stdout/stderr under results/raw.

The host setup has succeeded with Python 3.12.14 and the project-local dependencies.
The saved benchmark has 23 successful CPU folds, one 120-second ViennaRNA timeout,
and four successful GPU encoder runs. The original restricted-session failures are
retained as historical command records. See reports/installation_summary.md for the
recorded versions and tool Git hashes, and reports/environment-*.lock.txt for the
successful package freeze.

Results are at results/folding_benchmark.csv, results/gpu_benchmark.csv,
results/benchmark_summary.json and reports/benchmark_report.md.

Tests validate generation, FASTA preservation, input and length handling, descriptive
scores, real subprocess failure/timeout handling, output parsing, CLI behavior, and
archival of prior results. They do not claim real folding integrations passed when
tools are absent. No neural-network training is started.

## Compare folds and optimize

```bash
./scripts/rnastable report
./scripts/rnastable compare-folds --retry-timeout 300
./scripts/rnastable optimize --config configs/optimization.json
.venv/bin/python scripts/verify_optimization.py
```

Comparison reuses existing raw folds after validating the exact input sequence hash.
The optional longer timeout retries missing ViennaRNA references without changing the
original benchmark. Pair precision/recall/F1, Jaccard agreement and base-pair distance
use ViennaRNA as a computational reference. LinearFold structures are independently
reevaluated with current ViennaRNA parameters to distinguish parameter differences from
search approximation. Outputs: results/folding_quality.csv,
results/folding_quality_summary.json and reports/folding_quality_report.md.

The default optimization is a 48-proposal CPU hill climb on the mixed 1,000-nt control,
with fixed seed 2718, beam 100 and at most 40 changed positions relative to input.
It accepts energy improvements of at least 0.1 kcal/mol. Swapping different nucleotides
preserves length, GC count and every nucleotide count. Configured protected positions
use one-based coordinates. Each proposal is bounded by time and memory limits; failures
are logged and do not prevent later proposals. The input and finalist receive separate
ViennaRNA CPU validation, with a 300-second timeout. A lower surrogate score can fail
independent validation; that outcome is reported explicitly.

For a full coding sequence, `--coding --input path/to/cds.fasta` uses synonymous codon
substitutions, preserves GC count, and checks the translated sequence. This mode requires
full codons in frame 0, genetic code 1, and 1,000–10,000 nt; it does not infer CDS/UTR
boundaries. Stop codons are fixed. Noncoding mode is the default for synthetic controls.

Outputs: results/optimization_history.csv, results/optimization_history_summary.json,
reports/optimization_history_report.md, and immutable results/optimization_runs/<UTC>/
directories containing input/finalist/selected FASTA, raw folds and complete summaries.
All replaced reports have archived copies. Successful search demonstrates optimization
of computed energy, not biological stability. No training is included.

Next, repeat the search across independent seeds and sequence types, then assess against
experimental reference structures and application-specific constraints before expanding
the objective or considering a learned surrogate.

## Evaluate consistency across seeds and beams

```bash
./scripts/rnastable evaluate --config configs/evaluation_sweep.json
.venv/bin/python scripts/verify_sweep.py
```

The default CPU pilot contains 36 runs: 1,000 nt, structured and mixed controls,
three sequence seeds, two search seeds and beams 50/100/200. Each search receives
24 proposals and a 40-position mutation budget. Lengths up to 10,000 nt are supported
by the configuration, but the default pilot only establishes behavior at 1,000 nt.
Larger grids can take substantially longer because every finalist is folded with
ViennaRNA on CPU. There is no GPU folding or training in this evaluation.

Beam comparisons share input sequences and search seeds, with equal proposal budgets.
Their accepted mutations and later trajectories can differ. Input ViennaRNA references
are cached once per exact sequence within the run. Shared reference timings are not
independent timing measurements. Each row retains the search status, failed proposals,
input/finalist agreement, energy changes, runtime, input/finalist hashes, and raw evidence.

Outputs:

- results/evaluation_sweep.csv: individual runs
- results/evaluation_sweep_aggregate.csv: kind/length/beam summaries
- results/evaluation_sweep_summary.json: complete run metadata and evidence paths
- reports/evaluation_sweep_report.md: results, limitations and CPU tradeoff figure
- results/sweep_runs/<UTC>/: input/finalist FASTA, raw folds, cell summaries and checkpoint

Failed validations stay missing and are reported separately from unchanged/worsened
scores. Search repeats share inputs and are not independent biological samples; the
small pilot does not support population-level or statistical-significance claims.

To resume an interrupted grid, use the same configuration and the run directory printed
in the progress/report, for example:

```bash
./scripts/rnastable evaluate --config configs/evaluation_sweep.json --resume results/sweep_runs/<UTC>
```

Resume verifies configuration, code, tool binary and environment version fingerprints,
input identity, and finalist constraints before reusing completed cells. Interrupted
attempts are retained; a cell without a saved summary is rerun in a new attempt directory.
Completed failures remain explicit failures when resumed. Ctrl-C kills the active folding
process group. Existing reports and summaries are archived before replacement.

## Bounded long-sequence scaling pilot

```bash
./scripts/rnastable evaluate --config configs/evaluation_long.json
.venv/bin/python scripts/verify_sweep.py
.venv/bin/python scripts/summarize_long.py
```

This pilot covers 2,000/5,000/10,000 nt, both synthetic sequence types, beam 200,
sequence seed 1729 and search seed 2718. Each search has eight proposals, a 40-position
mutation limit, a 60-second LinearFold timeout, and a 600-second ViennaRNA validation
timeout. Per-process address space remains capped at 8 GiB. Reference and finalist
energy/structure comparisons are performed on CPU; there is no training.

This is a scaling check with one input/search seed per kind and length, not an
independent replication study. Its proposal budget is smaller than the 1,000-nt sweep's
24 steps; absolute improvements must not be compared as though budgets were equal.
One timing per fold includes process startup and is not a statistical timing estimate.

Latest generic results are published as evaluation_sweep.* with archived prior copies.
The long-pilot summary script also saves results/evaluation_long_summary.json,
results/evaluation_long.csv, results/evaluation_long_aggregate.csv,
reports/long_sequence_report.md and a length-scaling figure within the immutable run
directory. Every raw fold and finalist remains in results/sweep_runs/<UTC>/.

Resume with the original configuration and run directory:

```bash
./scripts/rnastable evaluate --config configs/evaluation_long.json --resume results/sweep_runs/<UTC>
```

## Long mixed-RNA replication and paired beams

```bash
./scripts/rnastable evaluate --config configs/evaluation_replication.json
.venv/bin/python scripts/summarize_replication.py
.venv/bin/python scripts/verify_sweep.py --summary results/evaluation_replication_summary.json
.venv/bin/python scripts/verify_replication.py
```

This 18-search study pairs beams 200/400 on mixed RNA at 2,000, 5,000 and
10,000 nt with input seeds 1729/1730/1731 and search seed 2718. Each search
uses eight proposals, at most 40 changed positions, a 120-second LinearFold
timeout, 600-second ViennaRNA timeout, and 8 GiB per-process address-space cap.
All folds run on CPU. No training occurs. Three synthetic inputs per length
are a small replication check; search-seed and timing variability remain unmeasured.

The reporter saves separate evaluation_replication CSV, aggregate CSV, paired
CSV and summary JSON plus reports/replication_report.md. Original long-pilot
artifacts stay preserved. The sweep retains raw evidence and checkpoints.
Resume with the identical configuration and recorded directory:

```bash
./scripts/rnastable evaluate --config configs/evaluation_replication.json --resume results/sweep_runs/<UTC>
```

## Reference-confirmed output selection

Use `selected.fasta` as the optimization output. `finalist.fasta` retains the
LinearFold search candidate for research and audit. Both `optimize` and `evaluate`
select the finalist only if search completed and both ViennaRNA folds succeeded
with finite energies, with the finalist lower by more than 1e-9 kcal/mol.
Equal/worse energy, unchanged sequence, failed search or failed validation returns
the original input. Missing input reference energy remains unknown; returning the
input does not claim a measured energy or biological stability.

Summaries include selection source/reason, selected FASTA/hash, changed positions
and selected reference-energy change. Existing candidate mutation counts, scores,
validation statuses and sweep improvement/worsening aggregates retain their original
meaning, before output selection. Every proposed finalist and raw fold is retained.

```bash
./scripts/rnastable optimize --config configs/optimization.json
.venv/bin/python scripts/verify_optimization.py
./scripts/rnastable evaluate --config configs/evaluation_selection_smoke.json
.venv/bin/python scripts/verify_sweep.py
```

Review the completed long replication without rerunning its folds:

```bash
.venv/bin/python scripts/review_selection.py --summary results/evaluation_replication_summary.json
.venv/bin/python scripts/verify_selection_review.py
```

The review creates new selected FASTAs under results/selection_reviews/<UTC>/ and
separate selection_review CSV/JSON/report artifacts. It audits saved raw evidence
first and records source hashes; it is not a new folding benchmark. Previously
completed runs remain auditable. Resume requires the code/tool/environment
fingerprint from the run's manifest, now including selection.py.

## Search-seed robustness

```bash
./scripts/rnastable evaluate --config configs/evaluation_robustness.json
.venv/bin/python scripts/summarize_robustness.py
.venv/bin/python scripts/verify_robustness.py
```

This 36-search CPU study uses mixed inputs at 1,000/2,000 nt, three input
seeds, three search seeds and paired beams 200/400, with eight proposals each.
Per-input CSVs report search variability, selected output diversity and candidate
worsenings. Across-input summaries average search repeats within each input first,
then give inputs equal weight. Failures and unknown selections stay explicit.
Three synthetic inputs per length support descriptive results, not population
claims or generalization of search variability to 5,000/10,000 nt.

Outputs: results/evaluation_robustness{,_inputs,_groups,_pairs}.csv,
results/evaluation_robustness_summary.json, reports/search_robustness_report.md
and a standalone search_variability.png in the recorded sweep directory.

## Explicit protected intervals

Constraint schema version 1 requires input_sha256 matching the uppercase RNA
sequence (not the FASTA file bytes). protected_positions are one-based coordinates;
protected_regions contain one-based inclusive start/end and an optional label.
Intervals may overlap; protection is their union plus configured protected positions.
Region labels are user-supplied descriptions; no biological annotation is inferred.
Each optimization summary records the constraint file path/hash, coordinate system,
regions and complete merged position list. Protein preservation remains the existing
full-codon frame-0/code-1 mode; interval protection applies in both modes.

The example below protects two synthetic 24-nt intervals and position 1000 on
mixed_1000_seed1729. It is a demonstration, not a biological annotation.

```bash
./scripts/rnastable optimize --config configs/optimization_protected_demo.json --constraints configs/constraints_synthetic_example.json --dry-run
./scripts/rnastable optimize --config configs/optimization_protected_demo.json --constraints configs/constraints_synthetic_example.json
.venv/bin/python scripts/verify_optimization.py
```

Dry-run validates a single input, length, sequence identity, coordinate bounds and
protein mode without calling fold tools or creating optimization outputs.

## Live command logging

```bash
.venv/bin/python scripts/log_command.py ./scripts/rnastable evaluate --config configs/evaluation_robustness.json
```

New logged commands stream progress directly, save a durable start event in
reports/command_starts.jsonl, and append completion/output/exit code to
reports/commands.jsonl with a matching command ID. Ctrl-C is forwarded to the
owned child and recorded as an interruption. Existing completed records remain
compatible. The logger accepts --log-dir before its command for isolated runs.

## Long search-seed robustness with bounded CPU batches

```bash
.venv/bin/python scripts/run_robustness_batches.py --config configs/evaluation_robustness_long.json --workers 2
.venv/bin/python scripts/summarize_robustness.py --config configs/evaluation_robustness_long.json --name robustness_long
.venv/bin/python scripts/verify_robustness.py --summary results/evaluation_robustness_long_summary.json
.venv/bin/python scripts/verify_batch_study.py
```

This bounded study covers mixed RNA at 5,000/10,000 nt, two input seeds
1729/1730, two search seeds 2718/2719 and beams 200/400: 16 searches,
eight proposals each. Each independent input runs its beam/search cases serially
with shared input references. At most two input batches run concurrently.
Concurrent wall times include contention and are not isolated folding benchmarks.
The original CPU/GPU benchmark measurements remain preserved.

Each component has separate logs, raw fold evidence and checkpoints. The parent
merges actual rows in planned order and records concurrency/provenance. A child
failure does not stop other batches; an incomplete parent is recorded explicitly.
No aggregate completion is published until all component commands succeed.
Interrupted attempts are retained; Ctrl-C is forwarded to owned child processes.

Resume using the batch runner and the parent directory printed at startup:

```bash
.venv/bin/python scripts/run_robustness_batches.py --config configs/evaluation_robustness_long.json --workers 2 --resume results/sweep_runs/<UTC>
```

Configuration, worker count, driver/logger code, core code, binaries and
environment fingerprints must match. Completed cells are reused by their component
sweeps. Use the batch runner to resume a batched parent rather than the serial
evaluate command, since parent evidence is stored in component directories.

Reporting accepts --config and --name; long results are published separately as
evaluation_robustness_long CSV/JSON artifacts and search_robustness_long_report.md.
Short-study results remain separately saved. Only two inputs per long length are
replicated; these descriptive results do not establish population performance.

### Batch audit evidence

The batch runner saves native, durable events for each driver attempt under
results/sweep_runs/<UTC>/driver_events/<attempt>/events.jsonl. Its final status
references the event log, so verify_batch_study works for direct invocations
without an outer log_command wrapper. Incomplete or over-limit native traces
fail verification; they do not silently fall back to other evidence.

Older completed runs use saved outer command output when available. Direct older
runs can instead audit the latest successful per-component CLI intervals from
their existing command logs. The audit labels this narrower evidence explicitly:
parent startup/teardown concurrency is unavailable for those old runs. Original
folds and historical driver records are retained; no events are reconstructed.
