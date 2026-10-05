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
