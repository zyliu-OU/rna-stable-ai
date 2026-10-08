# Checkpoint proposal-prior pilot

Previously exposed synthetic resource input, no accuracy labels or model fitting. Native strict energy acceptance and ViennaRNA final selection. Random-pool/compatibility-only controls; equal planned native fold budgets, added neural proxy costs reported separately.

Run: `/home/zyliu/Documents/rna-stable-ai/results/helix_prior_replication_runs/20261007T015942.325358Z/snapshot/results/checkpoint_prior_pilot_runs/20261007T020400.749199Z`

| Policy | Native proposals | Proxy calls | Accepted | Selected Vienna delta | Selected mutations |
|---|---:|---:|---:|---:|---:|
| random_pool | 8 | 0 | 4 | 0.0 | 0 |
| compatibility_only | 8 | 0 | 6 | -5.900000000000091 | 12 |
| checkpoint_prior | 8 | 128 | 5 | -13.600000000000136 | 10 |

Cost accounting: `{"completed_proxy_calls_across_attempts": 128, "incomplete_attempts": 0, "known_proxy_wall_seconds_across_attempts": 0.7450829320068806, "native": {"completed_requests": 33, "current_invocation_cache_hits": 0, "current_invocation_callbacks": 33, "known_native_wall_seconds": 212.5531098010033, "total_cost_known": true, "unique_requests": 33, "unknown_requests": 0}, "proxy_cost_policy": "Completed scorer calls across all attempts; incomplete attempts may have additional unknown work. Pool ranking wall includes scoring and journal writes; audit replay costs excluded."}`

One exposed synthetic input/one search seed per component; no fresh test, generalization or biological stability claim.
Pair logits are proposal-ranking proxies, not folding energy; native tools decide acceptance/selection.
Neural arm adds128 potential proxy calls beyond matched native requests; wall/costs are not assumed equal.
Original-template compatibility is a control/prior, not proof of retained biological function.
