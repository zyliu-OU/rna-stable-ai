# RNA-StableAI V1 benchmark report

Run UTC: 20261004T202224.300862Z

## CPU folding benchmarks

Status counts: {'ok': 23, 'timeout': 1}. Timeout: 120 s/tool/sequence; address-space cap: 8 GiB/process.

| Tool | Sequence | Status | Wall seconds | Peak RSS MiB | MFE kcal/mol | Ensemble energy kcal/mol |
|---|---|---|---:|---:|---:|---:|
| ViennaRNA | structured_1000_seed1729 | ok | 0.6662840940002752 | 39.265625 | -788.4 |  |
| LinearFold | structured_1000_seed1729 | ok | 0.36606820999986667 | 31.47265625 | -788.4 |  |
| LinearPartition | structured_1000_seed1729 | ok | 0.6665828870000041 | 26.1796875 |  | -795.94932 |
| ViennaRNA | mixed_1000_seed1729 | ok | 0.71629790399993 | 38.9921875 | -429.2 |  |
| LinearFold | mixed_1000_seed1729 | ok | 0.3662080839999362 | 32.50390625 | -421.5 |  |
| LinearPartition | mixed_1000_seed1729 | ok | 0.7164120190000176 | 26.484375 |  | -440.89972 |
| ViennaRNA | structured_2000_seed1729 | ok | 2.7206920240000727 | 55.44921875 | -1531.7 |  |
| LinearFold | structured_2000_seed1729 | ok | 0.8669781200001125 | 64.2734375 | -1531.7 |  |
| LinearPartition | structured_2000_seed1729 | ok | 1.668383470000208 | 54.4140625 |  | -1541.94009 |
| ViennaRNA | mixed_2000_seed1729 | ok | 2.769739441999718 | 56.203125 | -710.5 |  |
| LinearFold | mixed_2000_seed1729 | ok | 0.7676963159997285 | 64.02734375 | -691.5 |  |
| LinearPartition | mixed_2000_seed1729 | ok | 1.5176103189996866 | 52.796875 |  | -737.99951 |
| ViennaRNA | structured_5000_seed1729 | ok | 22.068530598000052 | 165.69140625 | -3949.6 |  |
| LinearFold | structured_5000_seed1729 | ok | 2.4191996439999457 | 172.2109375 | -3948.4 |  |
| LinearPartition | structured_5000_seed1729 | ok | 4.723401017000015 | 149.796875 |  | -3980.21943 |
| ViennaRNA | mixed_5000_seed1729 | ok | 22.270400302000326 | 165.75390625 | -1804.3 |  |
| LinearFold | mixed_5000_seed1729 | ok | 2.222752536000371 | 168.45703125 | -1756.8 |  |
| LinearPartition | mixed_5000_seed1729 | ok | 4.473942225999963 | 149.30859375 |  | -1849.18622 |
| ViennaRNA | structured_10000_seed1729 | ok | 119.97354898899994 | 560.25 | -7809.5 |  |
| LinearFold | structured_10000_seed1729 | ok | 5.277918532000058 | 356.51953125 | -7789.2 |  |
| LinearPartition | structured_10000_seed1729 | ok | 10.243415327999628 | 314.05859375 |  | -7849.15263 |
| ViennaRNA | mixed_10000_seed1729 | timeout | 120.00258469399978 |  |  |  |
| LinearFold | mixed_10000_seed1729 | ok | 4.529373847999977 | 343.46875 | -3680.5 |  |
| LinearPartition | mixed_10000_seed1729 | ok | 9.2808 | 319.953125 |  | -3829.67195 |

## Separate PyTorch encoder baseline

Median forward times after warmup. CPU wall time excludes tokenization; GPU CUDA event time excludes H2D transfer. Transfer measures pinned-memory H2D copy into a preallocated tensor. GPU memory includes model, inputs and inference activations; reserved memory is reported separately. Batch size is fixed by configuration.

Interpreter: `/home/zyliu/Documents/rna-stable-ai/.venv/bin/python`

| Length | Batch | Status | CPU seconds | GPU seconds | Transfer seconds | Peak GPU MiB |
|---:|---:|---|---:|---:|---:|---:|
| 1000 | 1 | ok | 0.0002729945001647138 | 0.0001233919970691204 | 1.484800036996603e-05 | 8.7998046875 |
| 2000 | 1 | ok | 0.0004061810000166588 | 0.0001231839992105961 | 1.527999993413687e-05 | 9.41796875 |
| 5000 | 1 | ok | 0.0010077850001835031 | 0.00013603200018405914 | 1.4992000069469214e-05 | 11.3271484375 |
| 10000 | 1 | ok | 0.0022977710000304796 | 0.00013907199352979663 | 1.5792000107467174e-05 | 14.4169921875 |

## Errors and limitations

- CPU folding tools do not use GPU.
- LinearFold-V energy is an approximate minimum; LinearPartition ensemble free energy is not MFE.
- Synthetic structured controls contain designed stems, not verified secondary structures.
- Encoder uses random fixed weights; inference throughput does not measure RNA stability.
- No training performed; single folding replicate per sequence; no statistical speedup claim.
- 
Exceeded 120s; killed process group
- /home/zyliu/Documents/rna-stable-ai/external/LinearFold/gflags.py:584: SyntaxWarning: invalid escape sequence '\S'
  doc = re.sub('(?<=\S)\n(?=\S)', ' ', doc, re.M)

- /home/zyliu/Documents/rna-stable-ai/external/LinearPartition/gflags.py:584: SyntaxWarning: invalid escape sequence '\S'
  doc = re.sub('(?<=\S)\n(?=\S)', ' ', doc, re.M)
Free Energy of Ensemble: -1541.94009 kcal/mol

- /home/zyliu/Documents/rna-stable-ai/external/LinearPartition/gflags.py:584: SyntaxWarning: invalid escape sequence '\S'
  doc = re.sub('(?<=\S)\n(?=\S)', ' ', doc, re.M)
Free Energy of Ensemble: -1849.18622 kcal/mol

- /home/zyliu/Documents/rna-stable-ai/external/LinearPartition/gflags.py:584: SyntaxWarning: invalid escape sequence '\S'
  doc = re.sub('(?<=\S)\n(?=\S)', ' ', doc, re.M)
Free Energy of Ensemble: -3829.67195 kcal/mol

- /home/zyliu/Documents/rna-stable-ai/external/LinearPartition/gflags.py:584: SyntaxWarning: invalid escape sequence '\S'
  doc = re.sub('(?<=\S)\n(?=\S)', ' ', doc, re.M)
Free Energy of Ensemble: -3980.21943 kcal/mol

- /home/zyliu/Documents/rna-stable-ai/external/LinearPartition/gflags.py:584: SyntaxWarning: invalid escape sequence '\S'
  doc = re.sub('(?<=\S)\n(?=\S)', ' ', doc, re.M)
Free Energy of Ensemble: -440.89972 kcal/mol

- /home/zyliu/Documents/rna-stable-ai/external/LinearPartition/gflags.py:584: SyntaxWarning: invalid escape sequence '\S'
  doc = re.sub('(?<=\S)\n(?=\S)', ' ', doc, re.M)
Free Energy of Ensemble: -737.99951 kcal/mol

- /home/zyliu/Documents/rna-stable-ai/external/LinearPartition/gflags.py:584: SyntaxWarning: invalid escape sequence '\S'
  doc = re.sub('(?<=\S)\n(?=\S)', ' ', doc, re.M)
Free Energy of Ensemble: -7849.15263 kcal/mol

- /home/zyliu/Documents/rna-stable-ai/external/LinearPartition/gflags.py:584: SyntaxWarning: invalid escape sequence '\S'
  doc = re.sub('(?<=\S)\n(?=\S)', ' ', doc, re.M)
Free Energy of Ensemble: -795.94932 kcal/mol


## Installation status for this session

- Directory initially contained only protected `.git`, `.agents`, `.codex`, and `.aws` directories. No existing project files were deleted or reset.
- Ubuntu 26.04 LTS, Ryzen 9 5950X (16 cores / 32 threads), approximately 30 GiB RAM, approximately 1.3 TiB available disk space.
- PCI identifies NVIDIA RTX 4080 SUPER. Loaded module reports driver 595.91.07. CUDA toolkit reports 13.3.73. `nvidia-smi` fails: `NVIDIA-SMI has failed because it couldn't communicate with the NVIDIA driver.` Visible `/dev/nvidia*` listing is empty. VRAM could not be measured, so no VRAM capacity is asserted.
- System Python remains 3.14.4; default Anaconda Python remains 3.14.6.
- Discovered read-only uv 0.12.5 in an existing environment. Project-local Python 3.12 download failed: `failed to lookup address information: Temporary failure in name resolution` for github.com. No `.venv` was created with a substitute interpreter.
- Dependency installation attempted with project-local target: `ERROR: Could not find a version that satisfies the requirement numpy (from versions: none)`. PyPI hostname resolution failed on the uv bootstrap attempt. No new core Python dependencies were successfully installed.
- LinearFold, LinearPartition, and optional EternaFold clones failed: `Could not resolve host: github.com`. ViennaRNA installation was attempted separately; exact output is in commands.jsonl. No folding tool performance or MFE results are available.
- Read-only fallback encoder baseline uses existing Python 3.13.14 and PyTorch 2.11.0+cu130 (CUDA wheel runtime 13.0). `torch.cuda.is_available()` is false and device count is zero. This is an external fallback measurement, not the requested Python 3.12 environment.
- Tests and dependency-independent pipeline run using existing Python 3.14.6 and pytest 9.0.3. Other available packages are inventoried in reports/runtime_versions.json; they are not claimed as isolated installations.
- No sudo, driver changes, system CUDA changes, kernel/boot changes, package upgrades in other environments, or neural-network training were performed.


## Reproduce

```bash
cd /home/zyliu/Documents/rna-stable-ai
./scripts/rnastable benchmark --config configs/benchmark.json
```

Next: install the missing folding tools and Python 3.12 once downloads are accessible, then rerun and assess approximate fold quality against ViennaRNA at shorter lengths before adding optimization.
