# RNA-StableAI

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
cd /home/zyliu/Documents/rna-stable-ai
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
successful installation produces a lock; this offline session did not produce a lock.

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
directories containing input/finalist FASTA, raw folds and complete summaries.
All replaced reports have archived copies. Successful search demonstrates optimization
of computed energy, not biological stability. No training is included.

Next, repeat the search across independent seeds and sequence types, then assess against
experimental reference structures and application-specific constraints before expanding
the objective or considering a learned surrogate.
