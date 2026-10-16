# RNA-StableAI family-provenance source review — 2026-10-15

The previously frozen metadata plan selected 12 training and four validation
family/clan groups before sequence or structure labels were read. The source
builder retained the exact Rfam Stockholm responses for all 16 selected families,
verified their family/clan identity, screened sequences against the frozen prior
exposure ledger and each other at the declared 0.8 similarity threshold, then
mapped every WUSS consensus contact for each fixed selected sequence. No selected
record was replaced after pair parsing. Crossing and noncanonical contacts were
retained wherever a complete reference could be mapped.

The fixed screen selected **140** sequences. **81** have complete computational
pair sets: **59 training** and **22 validation**. The other **59** remain marked
unsupported because a selected sequence lacks at least one annotated paired
column. RF00024 has **zero** supported references. Its consensus has 106 pairs;
each of its 12 selected sequences lacks 2–22 paired columns. The predeclared minimum of one
supported record per selected family therefore fails, despite the aggregate
48/16 training/validation thresholds passing. `dataset_ready` is false; there
is no training, inference, checkpoint selection or independent-test claim.

The successful source run is
`results/family_provenance_dataset_source_runs/20261016T004840.252786Z/`.
Its `binding.json` includes every selected record, screening decision, status,
complete pair set where supported, and per-family accounting. Its manifest fixes
the response and binding hashes. The first acquisition attempt failed on sandbox
DNS; an approved retry downloaded all 16 sources into
`results/family_provenance_dataset_source_runs/20261016T004500.107067Z/`.
After the session interrupted processing, the final run reused those exact
hash-checked bytes. Directory timestamps are UTC; this review date is local
America/Los_Angeles.

This is development material. Comparative consensus references are computational,
not independent measured structures. Family/clan and sequence screening does not
certify complete evolutionary or tool-training independence. A new plan would
have to disclose that RF00024's failed annotation binding has now been seen;
simply replacing it within this frozen plan would break the declared selection.

Verification:

The focused source and binding tests passed (26 tests). The full suite passed
**823 tests in 219.32 seconds**; see
[`family-provenance-source-full-suite-2026-10-15.log`](family-provenance-source-full-suite-2026-10-15.log).

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/plan_family_provenance_dataset.py --verify results/family_provenance_dataset_metadata_summary.json
.venv/bin/python scripts/prepare_family_provenance_dataset.py --verify results/family_provenance_dataset_source_summary.json
.venv/bin/python -m pytest -q tests/test_family_provenance_dataset.py tests/test_family_provenance_source.py tests/test_prospective_pair_integration.py
```
