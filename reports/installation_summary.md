## Installation status from recorded evidence

Setup UTC: 2026-10-04T20:21:13.229714+00:00; status: **complete**.

Benchmark UTC: 20261004T202224.300862Z. Interpreter: `/home/zyliu/Documents/rna-stable-ai/.venv/bin/python`.

| Package | Recorded version |
|---|---|
| python | 3.12.14 |
| RNA-StableAI | 0.1.0 |
| numpy | 2.5.3 |
| scipy | 1.18.1 |
| pandas | 3.0.6 |
| biopython | 1.88 |
| psutil | 7.2.2 |
| tqdm | 4.70.1 |
| pyyaml | 6.0.3 |
| pytest | 9.1.1 |
| matplotlib | 3.11.2 |
| torch | 2.14.1+cu130 |
| ViennaRNA | 2.7.2 |

### CPU tool builds

- LinearFold: latest recorded build exit code 0; Git commit `c3ee9bd80c06c2fc39a7bb7ae5e77b9566227cac`.
- LinearPartition: latest recorded build exit code 0; Git commit `b450fb3e63189073b68d385589035f992080aa3a`.
- EternaFold: latest recorded build exit code 0; Git commit `87b9aac55cee14fd562049d08f7b92d3131f10ce`.

Folding status counts: {'ok': 23, 'timeout': 1}. GPU encoder status counts: {'ok': 4}.

The saved encoder run reports CUDA available: True; GPU: NVIDIA GeForce RTX 4080 SUPER. This describes that run, not a fresh device probe in the restricted session.

ViennaRNA was benchmarked through its CPU Python bindings; a standalone RNAfold binary was not used in this run. EternaFold was built but not benchmarked.

Earlier session DNS/device failures are historical. Their exact outputs remain in commands.jsonl, and prior prose is archived before replacement. The original system_info.txt is the initial system snapshot.

Successful package freeze: `environment-20261004T202045.lock.txt`.

No driver, system CUDA, kernel/boot, system Python or other-project changes were made by these scripts. No training was performed.
