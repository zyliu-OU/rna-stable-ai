# Checkpoint prior synthetic replication

Run: `/home/zyliu/Documents/rna-stable-ai/results/checkpoint_prior_replication_runs/20261007T005714.695875Z`

Three previously exposed synthetic inputs and two search seeds; repeated seeds share inputs and are not independent biological samples.
Descriptive native-energy/proposal-ranking comparison only; no accuracy evaluation, fitting, generalization or biological stability claim.
Equal planned native requests do not imply equal wall time or proxy costs. Failed and timeout folds retain their request denominator.
Audit proxy replay costs are excluded from experimental search cost; incomplete attempts may add unknown proxy work.

| Input | Seed | Policy | Native proposals | Proxy calls | Selected Vienna delta | Selection reason |
|---|---:|---|---:|---:|---:|---|
| synthetic_1000 | 20261006 | random_pool | 8 | 0 | -11.0 | confirmed_improvement |
| synthetic_1000 | 20261006 | compatibility_only | 8 | 0 | -8.400000000000034 | confirmed_improvement |
| synthetic_1000 | 20261006 | checkpoint_prior | 8 | 128 | -18.5 | confirmed_improvement |
| synthetic_1000 | 20261007 | random_pool | 8 | 0 | -5.400000000000034 | confirmed_improvement |
| synthetic_1000 | 20261007 | compatibility_only | 8 | 0 | -12.0 | confirmed_improvement |
| synthetic_1000 | 20261007 | checkpoint_prior | 8 | 128 | -15.800000000000011 | confirmed_improvement |
| synthetic_5000 | 20261006 | random_pool | 8 | 0 | 0.0 | no_reference_improvement |
| synthetic_5000 | 20261006 | compatibility_only | 8 | 0 | -2.7000000000000455 | confirmed_improvement |
| synthetic_5000 | 20261006 | checkpoint_prior | 8 | 128 | -6.900000000000091 | confirmed_improvement |
| synthetic_5000 | 20261007 | random_pool | 8 | 0 | 0.0 | no_reference_improvement |
| synthetic_5000 | 20261007 | compatibility_only | 8 | 0 | -5.900000000000091 | confirmed_improvement |
| synthetic_5000 | 20261007 | checkpoint_prior | 8 | 128 | -7.0 | confirmed_improvement |
| synthetic_10000 | 20261006 | random_pool | 8 | 0 | None | validation_failed |
| synthetic_10000 | 20261006 | compatibility_only | 8 | 0 | None | validation_failed |
| synthetic_10000 | 20261006 | checkpoint_prior | 8 | 128 | None | validation_failed |
| synthetic_10000 | 20261007 | random_pool | 8 | 0 | None | validation_failed |
| synthetic_10000 | 20261007 | compatibility_only | 8 | 0 | None | validation_failed |
| synthetic_10000 | 20261007 | checkpoint_prior | 8 | 128 | None | validation_failed |

Unique native requests: 198; unknown requests: 0; completed experimental proxy calls: 768.
Known native wall seconds: 1002.799; known scorer wall seconds: 4.171.
