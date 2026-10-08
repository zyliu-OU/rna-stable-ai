# Helix checkpoint-prior synthetic replication

Frozen code and model, fixed exposed synthetic input/seed plan, serial bounded native requests. No test accuracy or model fitting.

Previously exposed synthetic sequences and two search seeds; no fresh accuracy test, biological assay or generalization claim.
Helix checkpoint replaces the prior; the other proposal-ranking and mutation settings remain fixed. Vienna final validation is explicitly extended from30 to300 seconds for every arm.
The earlier stack replication used30-second finalist validation; compare the separately extended10k stack selections with this study, not its original timeouts.
Code is frozen for all components. Native requests run serially within the study, but other development checks may overlap; timings are observations, not isolated speed benchmarks.
Unknown or interrupted native requests are retained in denominators and never automatically retried. Deadline may leave a partial study.

| Input | Seed | Policy | Proposals | Proxy calls | Selected Vienna delta | Reason |
|---|---:|---|---:|---:|---:|---|
| synthetic_1000 | 20261006 | random_pool | 8 | 0 | -11.0 | confirmed_improvement |
| synthetic_1000 | 20261006 | compatibility_only | 8 | 0 | -8.400000000000034 | confirmed_improvement |
| synthetic_1000 | 20261006 | checkpoint_prior | 8 | 128 | -21.0 | confirmed_improvement |
| synthetic_1000 | 20261007 | random_pool | 8 | 0 | -5.400000000000034 | confirmed_improvement |
| synthetic_1000 | 20261007 | compatibility_only | 8 | 0 | -12.0 | confirmed_improvement |
| synthetic_1000 | 20261007 | checkpoint_prior | 8 | 128 | -17.30000000000001 | confirmed_improvement |
| synthetic_5000 | 20261006 | random_pool | 8 | 0 | 0.0 | no_reference_improvement |
| synthetic_5000 | 20261006 | compatibility_only | 8 | 0 | -2.7000000000000455 | confirmed_improvement |
| synthetic_5000 | 20261006 | checkpoint_prior | 8 | 128 | -2.800000000000182 | confirmed_improvement |
| synthetic_5000 | 20261007 | random_pool | 8 | 0 | 0.0 | no_reference_improvement |
| synthetic_5000 | 20261007 | compatibility_only | 8 | 0 | -5.900000000000091 | confirmed_improvement |
| synthetic_5000 | 20261007 | checkpoint_prior | 8 | 128 | -13.600000000000136 | confirmed_improvement |
| synthetic_10000 | 20261006 | random_pool | 8 | 0 | 0.0 | no_reference_improvement |
| synthetic_10000 | 20261006 | compatibility_only | 8 | 0 | -6.099999999999909 | confirmed_improvement |
| synthetic_10000 | 20261006 | checkpoint_prior | 8 | 128 | -5.899999999999636 | confirmed_improvement |
| synthetic_10000 | 20261007 | random_pool | 8 | 0 | 0.0 | no_reference_improvement |
| synthetic_10000 | 20261007 | compatibility_only | 8 | 0 | -5.299999999999727 | confirmed_improvement |
| synthetic_10000 | 20261007 | checkpoint_prior | 8 | 128 | -17.899999999999636 | confirmed_improvement |
