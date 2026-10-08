# Checkpoint proposal-prior pilot

Previously exposed synthetic1000 nt input, no accuracy labels or model fitting. Native strict energy acceptance and ViennaRNA final selection. Random-pool/compatibility-only controls; equal planned native fold budgets, added neural proxy costs reported separately.

Run: `/home/zyliu/Documents/rna-stable-ai/results/checkpoint_prior_pilot_runs/20261006T035130.449329Z`

| Policy | Native proposals | Proxy calls | Accepted | Selected Vienna delta | Selected mutations |
|---|---:|---:|---:|---:|---:|
| random_pool | 8 | 0 | 6 | -11.0 | 12 |
| compatibility_only | 8 | 0 | 4 | -8.400000000000034 | 8 |
| checkpoint_prior | 8 | 128 | 7 | -18.5 | 14 |

One exposed synthetic input/one search seed; no fresh test, generalization or biological stability claim.
Pair logits are proposal-ranking proxies, not folding energy; native tools decide acceptance/selection.
Neural arm adds128 potential proxy calls beyond matched native requests; wall/costs are not assumed equal.
Original-template compatibility is a control/prior, not proof of retained biological function.
