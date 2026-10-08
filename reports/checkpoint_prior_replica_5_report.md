# Checkpoint proposal-prior pilot

Previously exposed synthetic resource input, no accuracy labels or model fitting. Native strict energy acceptance and ViennaRNA final selection. Random-pool/compatibility-only controls; equal planned native fold budgets, added neural proxy costs reported separately.

Run: `/home/zyliu/Documents/rna-stable-ai/results/checkpoint_prior_pilot_runs/20261007T010937.627482Z`

| Policy | Native proposals | Proxy calls | Accepted | Selected Vienna delta | Selected mutations |
|---|---:|---:|---:|---:|---:|
| random_pool | 8 | 0 | 4 | None | 0 |
| compatibility_only | 8 | 0 | 5 | None | 0 |
| checkpoint_prior | 8 | 128 | 5 | None | 0 |

Cost accounting: `{"completed_proxy_calls_across_attempts": 128, "incomplete_attempts": 0, "known_proxy_wall_seconds_across_attempts": 1.1179117400004088, "native": {"completed_requests": 33, "current_invocation_cache_hits": 0, "current_invocation_callbacks": 33, "known_native_wall_seconds": 295.54970241700016, "total_cost_known": true, "unique_requests": 33, "unknown_requests": 0}, "proxy_cost_policy": "Completed scorer calls across all attempts; incomplete attempts may have additional unknown work. Pool ranking wall includes scoring and journal writes; audit replay costs excluded."}`

One exposed synthetic input/one search seed per component; no fresh test, generalization or biological stability claim.
Pair logits are proposal-ranking proxies, not folding energy; native tools decide acceptance/selection.
Neural arm adds128 potential proxy calls beyond matched native requests; wall/costs are not assumed equal.
Original-template compatibility is a control/prior, not proof of retained biological function.
