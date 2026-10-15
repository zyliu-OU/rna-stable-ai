# RNA-StableAI handoff

Project: RNA-StableAI. Date: 2026-10-11 (America/Los_Angeles). Version: V8.
Workspace: `/home/zyliu/Documents/rna-stable-ai`. Saved UTC: 2026-10-12T03:51:29.732525+00:00.
Current roadmap step: 4 — next prospective pair-set source panel frozen; external acquisition required.

## Completed work

Created `configs/prospective_pair_family_panel.json` for RF00050 (FMN), RF00174
(Cobalamin), RF00234 (glmS), explicitly declaring `pair_set_zero_based_v1`.
Official family descriptions: https://rfam.org/family/RF00050,
https://rfam.org/family/RF00174, https://rfam.org/family/RF00234.
These are proposed source families, not certified independent test cohorts.
No new sequence or annotation outcomes were read before freezing.

Frozen protocol: `results/prospective_family_protocol_runs/20261012T035016.976142Z/manifest.json`. Config, exposure registry, all three development
checkpoint weights and summaries are retained and hash-verified. Seed 20261006,
exact_sparse decoder, maximum length 512, and maximum five records per family
remain fixed. No model tuning or inference occurred. The known named exposure
families exclude this panel; 3104 of 3187 exposure records have unknown family
identity, so full independence is unresolved.

Attempted acquisition run:
`results/prospective_family_acquisition_runs/20261012T035028.548636Z`.
All three descriptions failed with temporary DNS resolution errors; sequence
requests were not started. Sources complete: false. Selected records: zero.
Offline verification validates the failed ledger, not successful data acquisition.
Previously completed biological evaluation and immutable source runs are retained.
The convenience protocol/acquisition pointers now identify this new panel.
The evidence pointer still identifies the historical completed batch until a new
evidence download succeeds; do not prepare or infer against that old pointer.

## Verification

Protocol freezing passed checkpoint identity, seed/decoder, family exposure and
snapshot hash checks. New acquisition audit passed without network or inference.
Focused prospective-data and pair integration tests: **18 passed in 0.14s**.
The previously completed full suite remains **569 passed in 215.97s**;
this continuation changes only configuration and documentation, not pipeline code.
Changes remain local; no Git index changes, commit, push or publication.

## Pending work and terminal commands

Run the following in the user's normal terminal. The workspace cannot resolve
rfam.org. The evidence downloader requires a successful nonempty acquisition and
rejects incomplete metadata; never infer success merely from a zero exit status.
Both reports must say acquisition complete: True. Send the output for continuation.
The evidence command uses the newly generated acquisition convenience summary.

```bash
cd /home/zyliu/Documents/rna-stable-ai

.venv/bin/python scripts/prepare_prospective_family_panel.py \
  --acquire \
  --protocol results/prospective_family_protocol_runs/20261012T035016.976142Z/manifest.json

.venv/bin/python scripts/prepare_prospective_family_panel.py --verify
cat reports/prospective_family_acquisition_report.md

.venv/bin/python scripts/download_prospective_evidence.py \
  --acquisition results/prospective_family_acquisition_summary.json

.venv/bin/python scripts/download_prospective_evidence.py --verify
cat reports/prospective_evidence_report.md
```

After successful source and evidence downloads, continue offline provenance,
complete WUSS annotation binding and exposure screening before final evaluation.
Do not run inference yet. Once the new complete panel and final plan are validated:

```bash
.venv/bin/python scripts/evaluate_prospective_panel.py --reference-format pair_set_zero_based_v1
.venv/bin/python scripts/evaluate_prospective_panel.py --evaluate --reference-format pair_set_zero_based_v1
.venv/bin/python scripts/evaluate_prospective_panel.py --verify --reference-format pair_set_zero_based_v1
```

Consumed RF00059/RF00162/RF00167 cannot become fresh tests. Full training/tool
provenance, long biological annotations, experimental stability/function and
validated release remain pending. Pair-set scoring preserves crossing reference
contacts; existing predictors remain nested structure predictors.

Previous current status files archived at `/home/zyliu/Documents/rna-stable-ai/reports/archive/20261012T035129.732525Z`.
