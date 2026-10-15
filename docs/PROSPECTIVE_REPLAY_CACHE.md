# Verified metadata replay cache

Large Rfam seed families can make symmetric sequence-overlap screening expensive.
The first acquisition audit fully recomputes the retained screening and panel
selection. Only a successful comparison writes a cache outside immutable source
runs under `results/prospective_acquisition_replay_cache/`.

The key includes original summary bytes, source manifest bytes and current
screening implementation hashes. On every audit, source snapshots, frozen model
protocol, request identities and file hashes are checked before cache lookup.
A cached result must match the retained summary and its full expected inventory.
Changed inputs, outcomes or implementation require a new full replay; malformed
cache bindings/results reject verification. Existing caches are preserved.

To force the computation even when a matching cache exists:

```bash
.venv/bin/python scripts/prepare_prospective_family_panel.py --verify --recompute-screening
```

A cache is a local memo of a verified deterministic calculation, not independent
biological evidence or a cryptographic attestation. It does not bypass current
exposure or annotation checks at binding and final planning, and it does not
perform network requests, create test exposure or permit inference. Its purpose
is to avoid repeating the identical historical screen at every evidence step.
