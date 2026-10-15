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

This session has no accessible downloads, Python 3.12 or working CUDA device. To reproduce
the recorded fallback CPU encoder measurements without modifying the existing environment:

```bash
./scripts/rnastable benchmark --config configs/benchmark.json --gpu-python /home/zyliu/anaconda3/envs/vllm-lab/bin/python
```

Read reports/installation_summary.md, reports/system_info.txt and
reports/commands.jsonl for exact constraints and failures. Results are at:

- results/folding_benchmark.csv
- results/gpu_benchmark.csv
- results/benchmark_summary.json
- reports/benchmark_report.md

Tests validate generation, FASTA preservation, input and length handling, descriptive
scores, real subprocess failure/timeout handling, output parsing, CLI behavior, and
archival of prior results. They do not claim real folding integrations passed when
tools are absent. No neural-network training is started.

Next, make Python 3.12 and folding tools available, lock the successful environment,
then assess approximate folds against ViennaRNA at smaller lengths and real reference
structures before implementing mutation proposals and optimization.
