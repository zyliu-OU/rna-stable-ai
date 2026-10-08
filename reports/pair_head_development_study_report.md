# Matched-seed pair-head development study

Same exposed development snapshots and matched base initializations; compare zero-initialized sequence-only feature heads. No fresh test.

Three matched initialization seeds share the same 89 training and 47 reused validation records; not independent biological replication.
Validation selects checkpoints and supports development comparison only. Consumed test sets are not read or evaluated.
All heads retain identical base initialization, full pair BCE, optimizer, ten epochs and exact top-16 sparse decoder. Feature parameter counts differ.
Interrupted fits are not retried; any recovered completed fit retains unknown parent-process cost.
Component wall times are bounded process measurements, not isolated throughput benchmarks.

| Seed | Head | Status | Selected epoch | Development pair F1 | Parameters |
|---:|---|---|---:|---:|---:|
| 20261006 | baseline | ok | 3 | 0.38849854106861975 | 25874 |
| 20261006 | stack | ok | 5 | 0.423379568067344 | 25876 |
| 20261006 | helix | ok | 5 | 0.5244233333981245 | 25882 |
| 20261007 | baseline | ok | 3 | 0.37627740637695983 | 25874 |
| 20261007 | stack | ok | 3 | 0.40101251568271834 | 25876 |
| 20261007 | helix | ok | 4 | 0.4950770012765886 | 25882 |
| 20261008 | baseline | ok | 4 | 0.3932529810620267 | 25874 |
| 20261008 | stack | ok | 4 | 0.4055479388678194 | 25876 |
| 20261008 | helix | ok | 3 | 0.49106862354687564 | 25882 |

Paired differences from the matched-seed baseline:
- {'seed': 20261006, 'head': 'stack', 'paired_development_f1_delta_vs_baseline': 0.03488102699872425}
- {'seed': 20261006, 'head': 'helix', 'paired_development_f1_delta_vs_baseline': 0.13592479232950477}
- {'seed': 20261007, 'head': 'stack', 'paired_development_f1_delta_vs_baseline': 0.024735109305758507}
- {'seed': 20261007, 'head': 'helix', 'paired_development_f1_delta_vs_baseline': 0.11879959489962877}
- {'seed': 20261008, 'head': 'stack', 'paired_development_f1_delta_vs_baseline': 0.012294957805792706}
- {'seed': 20261008, 'head': 'helix', 'paired_development_f1_delta_vs_baseline': 0.09781564248484892}
