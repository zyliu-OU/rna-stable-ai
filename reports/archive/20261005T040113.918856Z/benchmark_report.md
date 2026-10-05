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


## Reproduce

```bash
cd /home/zyliu/Documents/rna-stable-ai
./scripts/rnastable benchmark --config configs/benchmark.json --gpu-python /home/zyliu/Documents/rna-stable-ai/.venv/bin/python
```

Next: compare computational structures with `rnastable compare-folds` and test constrained CPU mutation search with `rnastable optimize`. Training remains deferred.

## Subsequent folding-quality assessment

8/8 reference comparisons completed. See [folding_quality_report.md](folding_quality_report.md). The original benchmark measurements above remain unchanged.

- structured: pair F1 range 0.940–0.999 against ViennaRNA computed structures.
- mixed: pair F1 range 0.450–0.546 against ViennaRNA computed structures.
- Successful longer-timeout reference retries: mixed_10000_seed1729.

## Subsequent constrained search

1000 nt; 3 accepted proposals; 6 changed positions. LinearFold energy change: -2.8000000000000114 kcal/mol; ViennaRNA change: -2.8000000000000114 kcal/mol. Constraints passed: True.

See [optimization_history_report.md](optimization_history_report.md). This is one synthetic example of computed-energy optimization, with no training or biological validation.


## Supplemental CPU seed/beam evaluation

16/16 runs; statuses: {'validated': 16}. Lengths: [5000, 10000]; proposal budget: 8.

See [evaluation_sweep_report.md](evaluation_sweep_report.md) for per-beam quality, independent ViennaRNA energy validation, timing, and paired-sample limitations. The original benchmark remains unchanged.

