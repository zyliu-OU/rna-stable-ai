# RNA-StableAI handoff — 2026-10-17 V5

Project: RNA-StableAI  
Date: 2026-10-17 (America/Los_Angeles)  
Version: V5  
Workspace: `/home/zyliu/Documents/rna-stable-ai`

## Completed work

- Added a frozen, replayable exact-segment audit for the 17 selected long bpRNA training additions versus the 11 longer-RNA development references. The per-record evidence and interpretation are in `reports/long_training_reference_segment_audit_2026-10-17.md`.
- Fourteen of 17 additions share at least one exact 30-nt segment with a development reference; ten share at least one 40-nt segment. Twelve share at least ten distinct 30-mers with their best matching reference. All 544 deterministic mononucleotide-shuffled controls had zero 30-nt overlap.
- The finding strengthens the development-only classification of the 11-reference cohort. Exact segments are evidence of sequence overlap, not a complete family assignment. No model default, README, or GitHub publication changed.

## Verification

- Frozen protocol and deterministic run replay passed, including source/driver hashes, per-record counts, and shuffle controls.
- `py_compile` passed for the new driver. Three focused tests passed (`test_bprna_training_subset_v2.py`, `test_long_validation_family.py`).
- Canonical result: `results/long_training_reference_segment_audit_runs/20261017T185041.371852Z/summary.json`.

## Pending work

- Obtain source-level family/clan provenance or version-pinned Rfam covariance-model assignments for the 17 bpRNA additions. Treat ambiguous and multiple hits explicitly.
- Freeze a genuinely independent long-reference panel after family/clan and regional sequence-overlap checks; seek complete labels in the 4,000–4,999-nt active range. The existing 11-reference panel remains development only.
- Continue candidate-ranking/objective work using development evidence, with native controls. Do not promote a checkpoint or production calibration based on this cohort. Preserve the GitHub README picture before any future publication.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/long_training_reference_segment_audit_2026-10-17.md
.venv/bin/python scripts/audit_long_training_reference_segments.py --verify-protocol results/long_training_reference_segment_audit_protocol_runs/20261017T185039.732720Z/manifest.json
.venv/bin/python scripts/audit_long_training_reference_segments.py --verify-run results/long_training_reference_segment_audit_runs/20261017T185041.371852Z/summary.json
.venv/bin/python -m pytest -q tests/test_bprna_training_subset_v2.py tests/test_long_validation_family.py
cat reports/bprna_long_family_provenance_audit_2026-10-17.md
```
