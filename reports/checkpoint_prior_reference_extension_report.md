# Extended native validation of checkpoint-prior finalists

Frozen exposed synthetic finalists, separate longer native validation budget. No new search, model fitting, accuracy labels, test-set or biological stability claim.

Run: `/home/zyliu/Documents/rna-stable-ai/results/checkpoint_prior_reference_extension_runs/20261007T012318.389726Z`
Separate planned budget: 12 requests at 300 seconds each.

| Seed | Policy | Input status | Finalist status | Selected Vienna delta | Selection reason |
|---:|---|---|---|---:|---|
| 20261006 | random_pool | ok | ok | 0.0 | no_reference_improvement |
| 20261006 | compatibility_only | ok | ok | -6.099999999999909 | confirmed_improvement |
| 20261006 | checkpoint_prior | ok | ok | -2.399999999999636 | confirmed_improvement |
| 20261007 | random_pool | ok | ok | 0.0 | no_reference_improvement |
| 20261007 | compatibility_only | ok | ok | -5.299999999999727 | confirmed_improvement |
| 20261007 | checkpoint_prior | ok | ok | -6.599999999999909 | confirmed_improvement |

Separate increased validation budget on frozen previously exposed synthetic finalists; original 30-second results remain unchanged.
Descriptive native-energy validation only, no new search, fitting, accuracy test or biological stability claim.
Six arms share one synthetic sequence and two search seeds; no independent biological replication.
Unknown interruption costs stay unknown; timeouts are completed failed outcomes with measured cost. Wall times are not isolated throughput comparisons.
