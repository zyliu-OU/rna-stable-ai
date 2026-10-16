# RNA-StableAI handoff — 2026-10-16 V11

Project: RNA-StableAI. Date: 2026-10-16 (America/Los_Angeles). Version: V11.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Active project scope: 1–4,999 nt; retain all historical data at 5,000 nt and above. This prospective reference method screens 20–512 nt.

## Completed work

- Recorded the user's terminal results: three focused tests passed in 0.08 seconds. The 25-chain BGSU sequence-only protocol was frozen in `results/bgsu_pool_sequence_protocol_runs/20261016T170829.244881Z/`, and all three RCSB sequence batches succeeded.
- The acquisition run `results/bgsu_pool_sequence_runs/20261016T170830.465622Z/` bound all 25 sequences, selected 13 before contact acquisition, and passed its replay audit. Selected family counts: RF00386 4, RF01684 3, RF02348 2, RF03072 4. One candidate exceeded the 20–512-nt method limit; ten overlapped selected panel sequences; one overlapped prior exposure.
- The sequence-count gate is met numerically: 13 selected total, with three families at or above three selected sequences. This is **not** contact-supported reference coverage. The run's exposure event journals all 25 valid sequences read, including rejected ones.
- Corrected a bad command from V10: `screen_bgsu_pool_sequences.py --verify` expects an **acquisition summary**, not the protocol pointer. The user's traceback was from that command mismatch; the acquisition and its replay succeeded. Added `scripts/audit_bgsu_sequence_protocol.py` for direct protocol replay without changing the frozen driver.
- Added `scripts/audit_bgsu_sequence_readiness.py` and `tests/test_bgsu_sequence_readiness.py` to report the numeric sequence gate separately from still-unaudited structure identity, Rfam lineage, contact provenance, and tool-training provenance. No contact acquisition, model inference, or GitHub upload occurred; README picture remains untouched.

## Verification

- User terminal: `3 passed in 0.08s`; 3/3 sequence batches okay; acquisition replay passed twice (automatic and explicit).
- Read-only inspection of selected records confirmed 13 exact sequence lengths and family counts 4/3/2/4. The numeric 12-total and three-families-with-three gate is met.
- New protocol-replay wrapper, readiness audit, and focused readiness test have **not** been run by the assistant, per the user's terminal-testing preference.

## Pending work

Run the new focused test and replay/audit commands locally. Next development should resolve exact PDB author-chain/polymer identity and family annotation lineage before freezing any contact acquisition. NR class membership and 0.8 sequence-overlap screening are not proof of biological independence. Do not treat the 13 sequences as validated references; supported-reference count remains zero pending contact/identity/provenance checks. No model inference or release is authorized.

Before any future GitHub publication, inspect the live README and preserve the user's picture markup and image assets.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python -m pytest -q tests/test_bgsu_sequence_readiness.py
.venv/bin/python scripts/audit_bgsu_sequence_protocol.py results/bgsu_pool_sequence_protocol.json
.venv/bin/python scripts/screen_bgsu_pool_sequences.py --verify results/bgsu_pool_sequence_runs/20261016T170830.465622Z/summary.json
.venv/bin/python scripts/audit_bgsu_sequence_readiness.py --output results/bgsu_sequence_readiness_2026-10-16.json
.venv/bin/python scripts/audit_bgsu_sequence_readiness.py --verify results/bgsu_sequence_readiness_2026-10-16.json
jq '{selected_sequence_count,selected_family_counts,families_meeting_sequence_count_minimum,sequence_count_gate_met,supported_reference_count,contact_acquisition_authorized}' results/bgsu_sequence_readiness_2026-10-16.json
```

If the readiness output file already exists, do not delete or overwrite it; use `--verify` and inspect the existing result. Return the output before any contact acquisition.
