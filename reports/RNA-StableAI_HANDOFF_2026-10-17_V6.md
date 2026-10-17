# RNA-StableAI handoff — 2026-10-17 V6

Project: RNA-StableAI  
Date: 2026-10-17 (America/Los_Angeles)  
Version: V6  
Workspace: `/home/zyliu/Documents/rna-stable-ai`

## Completed work

- Acquired and pinned the official bpRNA-1m SQL RNA-table archive locally. Added `scripts/bind_bprna_long_origin_metadata.py` and a frozen V2 run that binds all 17 selected training additions to archived origins by source group and exact uppercase-normalized sequence. See `reports/bprna_long_origin_binding_2026-10-17.md`.
- Resolved archived Rfam labels for ten RFAM additions: nine have one family and one has two possible SSU families. Nine of ten fall in the SSU or LSU rRNA clans represented by the development panel; one is RF01050 telomerase. Bound all seven CRW records to original names/accessions but did not infer their Rfam families.
- Found that numeric bpRNA IDs cannot safely join the selected dot-bracket archive to the SQL dump: three same-numbered RFAM SQL rows refer to different sequences, while seven selected RFAM IDs have no same-numbered SQL row. Preserved a first binding attempt that stopped on duplicate CRW sequence rows; V2 handles and retains them.
- Kept the source archive and all results local. No README, GitHub publication, model default, or checkpoint gate changed.

## Verification

- V2 frozen protocol and deterministic run replay passed, rescanning the 39,672,063-byte official ZIP and reproducing every sequence-bound origin and ambiguity.
- The driver compiled; three focused bpRNA source/subset tests passed.
- Canonical result: `results/bprna_long_origin_binding_v2_runs/20261017T185531.913009Z/summary.json`.

## Pending work

- Obtain direct curated family assignments or version-pinned Rfam covariance-model hits for the seven CRW additions. Preserve ambiguous and overlapping family hits.
- Freeze a genuinely independent longer-RNA panel outside exposed families/clans after regional sequence-overlap and near-duplicate checks; seek complete 4,000–4,999-nt labels. The existing 11-reference cohort remains development-only.
- Continue model scoring/decoding work on development data without checkpoint promotion. Preserve the user-added GitHub README picture before any future publication.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/bprna_long_origin_binding_2026-10-17.md
.venv/bin/python scripts/bind_bprna_long_origin_metadata.py --verify-protocol results/bprna_long_origin_binding_v2_protocol_runs/20261017T185531.683657Z/manifest.json
.venv/bin/python scripts/bind_bprna_long_origin_metadata.py --verify-run results/bprna_long_origin_binding_v2_runs/20261017T185531.913009Z/summary.json
.venv/bin/python -m pytest -q tests/test_bprna_training_source.py tests/test_bprna_training_subset_v2.py
cat reports/long_training_reference_segment_audit_2026-10-17.md
```
