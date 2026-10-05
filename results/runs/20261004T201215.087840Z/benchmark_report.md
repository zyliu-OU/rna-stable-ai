# RNA-StableAI V1 benchmark report

Run UTC: 20261004T201101.111884Z

## CPU folding benchmarks

Status counts: {'unavailable': 24}. Timeout: 120 s/tool/sequence; address-space cap: 8 GiB/process.

| Tool | Sequence | Status | Wall seconds | Peak RSS MiB | MFE kcal/mol | Ensemble energy kcal/mol |
|---|---|---|---:|---:|---:|---:|
| ViennaRNA | structured_1000_seed1729 | unavailable |  |  |  |  |
| LinearFold | structured_1000_seed1729 | unavailable |  |  |  |  |
| LinearPartition | structured_1000_seed1729 | unavailable |  |  |  |  |
| ViennaRNA | mixed_1000_seed1729 | unavailable |  |  |  |  |
| LinearFold | mixed_1000_seed1729 | unavailable |  |  |  |  |
| LinearPartition | mixed_1000_seed1729 | unavailable |  |  |  |  |
| ViennaRNA | structured_2000_seed1729 | unavailable |  |  |  |  |
| LinearFold | structured_2000_seed1729 | unavailable |  |  |  |  |
| LinearPartition | structured_2000_seed1729 | unavailable |  |  |  |  |
| ViennaRNA | mixed_2000_seed1729 | unavailable |  |  |  |  |
| LinearFold | mixed_2000_seed1729 | unavailable |  |  |  |  |
| LinearPartition | mixed_2000_seed1729 | unavailable |  |  |  |  |
| ViennaRNA | structured_5000_seed1729 | unavailable |  |  |  |  |
| LinearFold | structured_5000_seed1729 | unavailable |  |  |  |  |
| LinearPartition | structured_5000_seed1729 | unavailable |  |  |  |  |
| ViennaRNA | mixed_5000_seed1729 | unavailable |  |  |  |  |
| LinearFold | mixed_5000_seed1729 | unavailable |  |  |  |  |
| LinearPartition | mixed_5000_seed1729 | unavailable |  |  |  |  |
| ViennaRNA | structured_10000_seed1729 | unavailable |  |  |  |  |
| LinearFold | structured_10000_seed1729 | unavailable |  |  |  |  |
| LinearPartition | structured_10000_seed1729 | unavailable |  |  |  |  |
| ViennaRNA | mixed_10000_seed1729 | unavailable |  |  |  |  |
| LinearFold | mixed_10000_seed1729 | unavailable |  |  |  |  |
| LinearPartition | mixed_10000_seed1729 | unavailable |  |  |  |  |

## Separate PyTorch encoder baseline

Median forward times after warmup. CPU wall time excludes tokenization; GPU CUDA event time excludes H2D transfer. Transfer measures pinned-memory H2D copy into a preallocated tensor. GPU memory includes model, inputs and inference activations; reserved memory is reported separately. Batch size is fixed by configuration.

Interpreter: `/home/zyliu/anaconda3/envs/vllm-lab/bin/python`

| Length | Batch | Status | CPU seconds | GPU seconds | Transfer seconds | Peak GPU MiB |
|---:|---:|---|---:|---:|---:|---:|
| 1000 | 1 | skipped | 0.0003200684999455916 |  |  |  |
| 2000 | 1 | skipped | 0.0005055205000417118 |  |  |  |
| 5000 | 1 | skipped | 0.0012065105000829135 |  |  |  |
| 10000 | 1 | skipped | 0.0024545850001231884 |  |  |  |

## Errors and limitations

- CPU folding tools do not use GPU.
- LinearFold-V energy is an approximate minimum; LinearPartition ensemble free energy is not MFE.
- Synthetic structured controls contain designed stems, not verified secondary structures.
- Encoder uses random fixed weights; inference throughput does not measure RNA stability.
- No training performed; single folding replicate per sequence; no statistical speedup claim.
- CUDA unavailable; GPU timing, transfer and memory left blank
- Tool not installed or not discoverable

## Installation status for this session

- Directory initially contained only protected `.git`, `.agents`, `.codex`, and `.aws` directories. No existing project files were deleted or reset.
- Ubuntu 26.04 LTS, Ryzen 9 5950X (16 cores / 32 threads), approximately 30 GiB RAM, approximately 1.3 TiB available disk space.
- PCI identifies NVIDIA RTX 4080 SUPER. Loaded module reports driver 595.91.07. CUDA toolkit reports 13.3.73. `nvidia-smi` fails: `NVIDIA-SMI has failed because it couldn't communicate with the NVIDIA driver.` Visible `/dev/nvidia*` listing is empty. VRAM could not be measured, so no VRAM capacity is asserted.
- System Python remains 3.14.4; default Anaconda Python remains 3.14.6.
- Discovered read-only uv 0.12.5 in an existing environment. Project-local Python 3.12 download failed: `failed to lookup address information: Temporary failure in name resolution` for github.com. No `.venv` was created with a substitute interpreter.
- Dependency installation attempted with project-local target: `ERROR: Could not find a version that satisfies the requirement numpy (from versions: none)`. PyPI hostname resolution failed on the uv bootstrap attempt. No new core Python dependencies were successfully installed.
- LinearFold, LinearPartition, and optional EternaFold clones failed: `Could not resolve host: github.com`. ViennaRNA installation was attempted separately; exact output is in commands.jsonl. No folding tool performance or MFE results are available.
- Read-only fallback encoder baseline uses existing Python 3.13.13 and PyTorch 2.11.0+cu130 (CUDA wheel runtime 13.0). `torch.cuda.is_available()` is false and device count is zero. This is an external fallback measurement, not the requested Python 3.12 environment.
- Tests and dependency-independent pipeline run using existing Python 3.14.6 and pytest 9.0.3. Other available packages are inventoried in reports/runtime_versions.json; they are not claimed as isolated installations.
- No sudo, driver changes, system CUDA changes, kernel/boot changes, package upgrades in other environments, or neural-network training were performed.


## Reproduce

```bash
cd /home/zyliu/Documents/rna-stable-ai
./scripts/rnastable benchmark --config configs/benchmark.json --gpu-python /home/zyliu/anaconda3/envs/vllm-lab/bin/python
```

Next: install the missing folding tools and Python 3.12 once downloads are accessible, then rerun and assess approximate fold quality against ViennaRNA at shorter lengths before adding optimization.
