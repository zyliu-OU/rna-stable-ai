# Command and environment record

`commands.jsonl` records installation attempts, system probes, tests, CLI calls and
encoder worker arguments with exit codes and captured output. `system_info.txt`
contains the full system probe. `runtime_versions.json` records available default
interpreter packages; the benchmark CSV records the separate encoder interpreter.
No successful Python 3.12 environment exists, so no reproducibility lock is claimed.

Initial read-only inspection, before the logger was created:

```bash
pwd
ls -la
rg --files -g AGENTS.md -g '!external/**' -g '!.venv/**' /home/zyliu/Documents
find .. -maxdepth 2 -name AGENTS.md -print
ls -la .agents .codex
command -v uv python3.12 python3 python gcc g++ make git RNAfold
cat /etc/os-release
lscpu
free -h
nvidia-smi
nvcc --version
df -h . /tmp
python3 --version
```

Project files were authored using shell heredocs and Python text edits, with
`mkdir -p` for the requested directories and `chmod +x scripts/rnastable` for the
local launcher. Existing protected directories were not written. Upstream web
documentation was checked for installation and LinearPartition partition-only flags.

Repeatable commands:

```bash
python3 scripts/setup.py
python3 scripts/log_command.py env PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider --junitxml=reports/tests.xml
python3 scripts/log_command.py ./scripts/rnastable benchmark --config configs/benchmark.json --gpu-python /home/zyliu/anaconda3/envs/vllm-lab/bin/python
python3 scripts/log_command.py python3 scripts/verify_results.py
```

After Python 3.12 installation succeeds, use `.venv/bin/python` for tests and omit
`--gpu-python` to benchmark the isolated environment. All external interpreter access
in this session was read-only, with bytecode writes disabled for encoder runs.

## Folding-quality and constrained optimization extension

The host successfully installed Python 3.12 and all dependencies. Installation versions and tool commits are now summarized from successful logged commands, while initial failures remain historical.

Executed and logged:

```bash
./scripts/rnastable compare-folds --retry-timeout 300
./scripts/rnastable optimize --config configs/optimization.json
.venv/bin/python -m pytest -q -p no:cacheprovider --junitxml=reports/tests-v2-final.xml
.venv/bin/python scripts/refresh_reports.py
.venv/bin/python scripts/verify_quality.py
.venv/bin/python scripts/verify_optimization.py
.venv/bin/python scripts/verify_results.py
./scripts/rnastable report
```

The real optimization was repeated and yielded the same finalist and decisions. Detailed outcomes are in optimization_reproducibility.txt. All tests and artifact audits passed after fixing a report-refactor error found by the CLI test. Neural-network training remains deferred.

## CPU seed/beam evaluation extension

New files: configs/evaluation_sweep.json, src/rnastable/sweep.py, tests/test_sweep.py, and scripts/verify_sweep.py. Modified source files were backed up under reports/source_backups before edits. Source and tool fingerprints are captured in every sweep manifest.

Executed and logged:

```bash
./scripts/rnastable evaluate --config configs/evaluation_sweep.json
.venv/bin/python -m pytest -q -p no:cacheprovider --junitxml=reports/tests-evaluation-final.xml
.venv/bin/python scripts/verify_sweep.py
./scripts/rnastable report
env XDG_CACHE_HOME="$PWD/external/cache" ./scripts/rnastable evaluate --config configs/evaluation_sweep.json --resume results/sweep_runs/20261004T205442.491896Z
```

36/36 runs validated successfully at 1,000 nt. The initial figure render emitted fontconfig cache warnings in the restricted session; its PNG was produced and visually checked. Resume used a project-local XDG cache, reused all cells, and retained all measured rows and aggregates. No dependencies, drivers, system CUDA, other environments or system files were changed. Training remains deferred.

## Bounded long-RNA pilot

Added configs/evaluation_long.json and scripts/summarize_long.py. No folding/search core changes were required. The configuration covers 2,000/5,000/10,000 nt, both sequence types, beam 200, one input/search seed, eight proposals, 60-second LF timeout and 600-second ViennaRNA timeout.

Executed and logged:

```bash
env XDG_CACHE_HOME="$PWD/external/cache" ./scripts/rnastable evaluate --config configs/evaluation_long.json
.venv/bin/python -m pytest -q -p no:cacheprovider --junitxml=reports/tests-long.xml
.venv/bin/python scripts/verify_sweep.py
.venv/bin/python scripts/summarize_long.py
.venv/bin/python scripts/verify_sweep.py --summary results/evaluation_long_summary.json
./scripts/rnastable report
```

6/6 runs validated, 48 proposal folds audited, 59 tests passed. Five finalists lowered ViennaRNA MFE and one was unchanged. No failures or worsened finalists were recorded. The standalone long-scaling figure was visually inspected. Prior generic sweep results remain archived and in their immutable run directories. No training, dependency changes or system modifications were performed.

20261004T223204.815793Z: Added mixed long-RNA replication (18 searches; 3 seeds, 3 lengths, paired beams200/400; 8 proposals;120s LinearFold/600s ViennaRNA;8GiB/process). No training or system changes. Commands and output recorded via scripts/log_command.py. Earlier README/notes backed up under reports/source_backups/20261004T223204.815793Z. Separate paired analysis rejects missing/duplicate/different-input pairs; unavailable energies stay missing.

20261004T231536.970657Z: Replication completed /home/zyliu/Documents/rna-stable-ai/results/sweep_runs/20261004T223012.118701Z;18 validated/no failures;144 proposal folds audited;9 paired CSV calculations audited;64 tests passed. Vienna outcomes {'improved': 14, 'unchanged': 1, 'worsened': 3}. Added separate replication report/CSV/JSON and standalone replication_tradeoffs.png. No neural training or system modifications.
