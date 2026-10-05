# Selection review of saved CPU folding evidence

Source: `/home/zyliu/Documents/rna-stable-ai/results/evaluation_replication_summary.json`; output: `/home/zyliu/Documents/rna-stable-ai/results/selection_reviews/20261004T232639.585011Z`.

This review reuses previously audited input/finalist folds. No folding, benchmarking or training was rerun. Original sweep evidence remains unchanged.

Selected sources: {'finalist': 14, 'input': 4}; reasons: {'confirmed_improvement': 14, 'no_reference_improvement': 4}.

| Job | Selected source | Reason | Candidate Vienna change | Selected Vienna change |
|---|---|---|---:|---:|
| mixed_2000_seq1729_search2718_beam200 | finalist | confirmed_improvement | -10.100000000000023 | -10.100000000000023 |
| mixed_2000_seq1729_search2718_beam400 | finalist | confirmed_improvement | -11.100000000000023 | -11.100000000000023 |
| mixed_2000_seq1730_search2718_beam200 | finalist | confirmed_improvement | -8.200000000000045 | -8.200000000000045 |
| mixed_2000_seq1730_search2718_beam400 | finalist | confirmed_improvement | -8.200000000000045 | -8.200000000000045 |
| mixed_2000_seq1731_search2718_beam200 | finalist | confirmed_improvement | -14.100000000000023 | -14.100000000000023 |
| mixed_2000_seq1731_search2718_beam400 | finalist | confirmed_improvement | -12.800000000000068 | -12.800000000000068 |
| mixed_5000_seq1729_search2718_beam200 | finalist | confirmed_improvement | -2.400000000000091 | -2.400000000000091 |
| mixed_5000_seq1729_search2718_beam400 | finalist | confirmed_improvement | -3.0 | -3.0 |
| mixed_5000_seq1730_search2718_beam200 | input | no_reference_improvement | 1.7999999999999545 | 0.0 |
| mixed_5000_seq1730_search2718_beam400 | finalist | confirmed_improvement | -2.2000000000000455 | -2.2000000000000455 |
| mixed_5000_seq1731_search2718_beam200 | input | no_reference_improvement | 8.799999999999955 | 0.0 |
| mixed_5000_seq1731_search2718_beam400 | finalist | confirmed_improvement | -2.0 | -2.0 |
| mixed_10000_seq1729_search2718_beam200 | finalist | confirmed_improvement | -5.199999999999818 | -5.199999999999818 |
| mixed_10000_seq1729_search2718_beam400 | finalist | confirmed_improvement | -0.09999999999990905 | -0.09999999999990905 |
| mixed_10000_seq1730_search2718_beam200 | finalist | confirmed_improvement | -4.230000000000018 | -4.230000000000018 |
| mixed_10000_seq1730_search2718_beam400 | finalist | confirmed_improvement | -1.400000000000091 | -1.400000000000091 |
| mixed_10000_seq1731_search2718_beam200 | input | no_reference_improvement | 0.20000000000027285 | 0.0 |
| mixed_10000_seq1731_search2718_beam400 | input | no_reference_improvement | 0.0 | 0.0 |

Only confirmed lower ViennaRNA energy selects a finalist. Otherwise the selected FASTA contains the input; its change is zero only if input reference energy is known. Rejected finalists remain in their source runs. This is computed energy, not experimental biological stability.
