# Synthetic sampled-training resource steps

Constructed nested reverse-complement labels; one sampled gradient/Adam step per length in separate bounded processes. No all-pair label enumeration, model checkpoint selection, biological accuracy or stability.

Synthetic nested annotations only; one update demonstrates feasibility, not long biological accuracy.
Retained label tensor bytes exclude model/optimizer/Python allocations; theoretical full tensor bytes describe the avoided index/label layout, not measured savings.
Whole-process GNUtime peak RSS includes Python/Torch startup and excludes guard supervisor; per-process memory cap is not a tree-wide RSS cap.
Other development tasks may overlap; timings are observations, not isolated speed benchmarks.

| Length | Status | Wall seconds | Process peak RSS MiB | Sample label bytes | Full label layout bytes (theoretical) |
|---:|---|---:|---:|---:|---:|
| 1000 | ok | 2.3704371979993084 | 784.1875 | 328680 | 3732620 |
| 5000 | ok | 2.6219320420004806 | 801.98828125 | 1648680 | 93593100 |
| 10000 | ok | 3.2710411399993973 | 813.92578125 | 3298680 | 374711560 |
