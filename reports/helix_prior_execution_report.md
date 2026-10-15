# Full native study execution accounting

Every fixed planned component, including unstarted and incomplete components; started/interrupted native entries and orphan raw requests retain unknown outcome/cost. Proxy known costs count completed calls across attempts; incomplete attempts can have additional unknown work. Read-only inspection under stopped parent driver lock.

Totals: `{"completed_native_requests": 197, "completed_proxy_calls": 768, "incomplete_proxy_attempts": 1, "journal_recorded_native_requests": 198, "known_native_wall_seconds": 2008.9399087069967, "known_proxy_wall_seconds": 4.308983139987504, "not_started_native_requests": 0, "orphan_raw_native_requests": 0, "planned_native_requests": 198, "started_native_requests": 198, "unknown_native_requests": 1}`

| Component | Input index | Seed | Planned | Started | Complete | Unknown | Not started |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 20261006 | 33 | 33 | 33 | 0 | 0 |
| 1 | 0 | 20261007 | 33 | 33 | 33 | 0 | 0 |
| 2 | 1 | 20261006 | 33 | 33 | 33 | 0 | 0 |
| 3 | 1 | 20261007 | 33 | 33 | 33 | 0 | 0 |
| 4 | 2 | 20261006 | 33 | 33 | 33 | 0 | 0 |
| 5 | 2 | 20261007 | 33 | 33 | 32 | 1 | 0 |
