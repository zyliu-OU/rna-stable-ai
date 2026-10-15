# Supplied pair-set reference evaluation

Dataset: reused_47_record_pair_score_equivalence

Exact zero-based contacts; crossing reference/predicted pairs are scored without removal, flattening or replacement.
Each nucleotide has at most one partner. Reference pair chemistry and minimum loop size are not inferred or filtered.
Missing/failed predictions retain unknown metrics. Means describe measured inputs only, with one vote per reference.
Source labels/provenance are supplied annotations, not independent biological evidence. Pair agreement does not establish stability or retained function.
This evaluator performs no inference, native folding, training or checkpoint selection; supplied records are conservatively registered as validation exposure.

| Method | Kind | Planned | Measured | Mean pair F1 |
|---|---|---:|---:|---:|
| baseline_seed20261006 | computational | 35 | 35 | 0.28398885222358006 |
| baseline_seed20261006 | experimental | 12 | 12 | 0.6933184668666521 |
| baseline_seed20261007 | computational | 35 | 35 | 0.27851638971926945 |
| baseline_seed20261007 | experimental | 12 | 12 | 0.6614137049618901 |
| baseline_seed20261008 | computational | 35 | 35 | 0.305883590010645 |
| baseline_seed20261008 | experimental | 12 | 12 | 0.6480803716285569 |
| helix_seed20261006 | computational | 35 | 35 | 0.46199566048449764 |
| helix_seed20261006 | experimental | 12 | 12 | 0.7065040460628697 |
| helix_seed20261007 | computational | 35 | 35 | 0.42037756811842647 |
| helix_seed20261007 | experimental | 12 | 12 | 0.7129503479878948 |
| helix_seed20261008 | computational | 35 | 35 | 0.40820953701396406 |
| helix_seed20261008 | experimental | 12 | 12 | 0.7327409592678679 |
| stack_seed20261006 | computational | 35 | 35 | 0.3354511756117352 |
| stack_seed20261006 | experimental | 12 | 12 | 0.6798373793962029 |
| stack_seed20261007 | computational | 35 | 35 | 0.3117321079298595 |
| stack_seed20261007 | experimental | 12 | 12 | 0.6614137049618901 |
| stack_seed20261008 | computational | 35 | 35 | 0.3223939619212809 |
| stack_seed20261008 | experimental | 12 | 12 | 0.6480803716285569 |
