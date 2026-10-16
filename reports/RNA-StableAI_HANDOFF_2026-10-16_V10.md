# RNA-StableAI handoff — 2026-10-16 V10

Project: RNA-StableAI. Date: 2026-10-16 (America/Los_Angeles). Version: V10.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Active scope: 1–4,999 nt; historical 5,000-nt-and-longer data remains retained. This prospective structure-reference method has a stricter 20–512-nt sequence screen.

## Completed work

- Recorded the user's local results: one BGSU pool test passed in 0.07 seconds; the parent acquisition/pool replays passed; and the frozen metadata-only pool is `results/bgsu_sequence_pool_protocol_runs/20261016T170641.329923Z/manifest.json`.
- Frozen pool counts are RF00386: 10, RF01684: 4, RF02348: 6, RF03072: 5 (25 metadata candidates total). These are not sequence-independent or contact-supported counts.
- Added `scripts/screen_bgsu_pool_sequences.py` to freeze an exact three-batch RCSB sequence request plan, acquire canonical RNA sequences, screen exact 20–512-nt length and overlap against prior exposure and the selected panel, and journal every valid sequence read as an exposure event. Each run is independently auditable. Contact requests and model inference remain disabled.
- Added `tests/test_bgsu_pool_sequences.py` for request batching and the closed contact/inference policy. Existing `screen_structure_pool_sequences.py` remains unchanged so prior frozen replays retain their driver identity.
- No GitHub upload occurred; README and its picture were untouched.

## Verification

- User terminal: `1 passed in 0.07s`; BGSU source acquisition replay passed; BGSU metadata-only pool replay passed; frozen counts 10/4/6/5; repeat replay passed.
- Code was inspected for frozen request identity, exposure-ledger consistency, per-run response hashing, selection replay, and exposure-event replay.
- The new sequence-only test, protocol freeze, acquisition, and replay have **not** been run by the assistant, per the user's terminal-testing preference.

## Pending work

Run the focused test, freeze/replay the sequence-only request protocol, then perform the fixed sequence acquisition locally and return its summary. There are no contact requests in this step. A selected total below 12, fewer than three families with at least three supported candidates, or insufficient sequence independence blocks the later contact phase. Even if those numeric gates appear to pass, exact structure identity, contact provenance, Rfam annotation lineage, and training provenance remain unresolved. No model inference or release is authorized.

Before any future GitHub publication, inspect the live README and preserve the user's picture markup and image assets.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python -m pytest -q tests/test_bgsu_pool_sequences.py tests/test_structure_pool_sequences.py
.venv/bin/python scripts/screen_bgsu_pool_sequences.py
.venv/bin/python scripts/screen_bgsu_pool_sequences.py --verify results/bgsu_pool_sequence_protocol.json
.venv/bin/python scripts/screen_bgsu_pool_sequences.py --acquire
for f in results/bgsu_pool_sequence_runs/*/summary.json; do .venv/bin/python scripts/screen_bgsu_pool_sequences.py --verify "$f"; done
jq '{candidate_count,successful_batches,failed_batches,source_sequences_bound,selected_before_contacts,selected_family_counts,selection_reason_counts}' results/bgsu_pool_sequence_runs/*/summary.json
```

The protocol freeze refuses to overwrite an existing pointer; if the protocol already exists, skip that command and replay it. Acquisition creates a new timestamped run each time and preserves any failed attempts. Return the output before any contact acquisition.
