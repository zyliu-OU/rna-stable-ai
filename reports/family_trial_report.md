# Family-disjoint comparative trial

Run: `/home/zyliu/Documents/rna-stable-ai/results/family_trial_runs/20261006T020448.519769Z`

Families: {'train': ['RF00001'], 'validation': ['RF00169'], 'test': ['RF00008']}
Counts: {'train': 24, 'validation': 23, 'test': 9}

| Method | Planned | Measured | Mean pair F1 |
|---|---:|---:|---:|
| LinearFold | 9 | 9 | 0.8793522785458269 |
| ViennaRNA | 9 | 9 | 0.8793522785458269 |
| all_unpaired | 9 | 9 | 0.0 |
| trained_pair | 9 | 9 | 0.091157185894028 |
| untrained_pair | 9 | 9 | 0.03735359290914846 |

Processed comparative annotations; not a new experimental measurement. Legacy tool-training overlap and clan independence are unestablished.
Only one family per split; no population-wide family generalization claim.
Prior PDB family assignments are unresolved; prior sequence exposure is filtered, but complete cross-study family independence is unestablished.
Quadratic scores and cubic decoding remain limited to 256 nt. No long-RNA accuracy or biological stability measurement.
