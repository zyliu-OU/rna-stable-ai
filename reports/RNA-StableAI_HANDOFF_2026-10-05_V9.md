# RNA-StableAI handoff — 2026-10-05 — V9

Project: RNA-StableAI
Date: 2026-10-05 (America/Los_Angeles)
Version: V9
Absolute workspace: `/home/zyliu/Documents/rna-stable-ai`

Proactive checkpoint during authorized continuous development; no GPT-6 usage-limit
signal received. If a usage-limit signal arrives while execution remains possible,
save a final versioned handoff and stop. Account quota cannot be read by available tools.

Completed sinceV8: exact sparse maximum-logit noncrossing dynamic programming,
O(n*m)work/O(n²)storage, strictly bounded to1024 nt and64 positive candidates per right
endpoint. Random/tied dense-DP equivalence and greedy counterexamples passed.
Exact measured comparison contains282 predictions (2 models ×47 ×3 decoders).
All282 checkpoint/candidate/structure/objective/metric rows replayed successfully.
Full-label checkpoint mean development F1:greedy .1407018642,refined .2085785072,
exact sparse .342535080846632. Sampled checkpoint exact sparse .23460531347731278.
These are the same exposed development records; maximum logits is not maximum label
agreement. Native baselines remain .717773/.719387 (seeV8), no new test claim.
Report:`reports/exact_sparse_development_report.md`.

FASTA inference now has explicit`--decoder exact_sparse`, requires a global sparse
checkpoint and<=1024 nt, rejects invalid requests before output, freezes decoder
identity, and audits exact exports. Synthetic demo and10 inference tests passed.
Default retained decoder behavior and old runs remain replayable. Exact source backup:
`reports/source_backups/20261006T031504.388976Z`.

Active: fresh full-label training on the SAME89/47 snapshots selecting checkpoints
with exact sparse validation (instead of refinement);10 fixed epochs, same architecture,
optimizer and seed. Script/config/auditor implemented; wait for completion and audit.
No fresh data curation, negative sampling or test inference in this run.
Training log:`reports/exact-comparative-training.log`.
Need integrate the frozen`inference_decoder=exact_sparse` source config into FASTA
loader after training; current explicit override already works for earlier checkpoints.

Verification:last complete full suite324 passed in122.08 s plus later focused
comparison/diagnostic/exact/inference checks. New full suite is running:
`reports/tests-exact-sparse-checkpoint.log` and XML. Do not report it passed until finished.
V8 retains detailed CRW/native/candidate results and commands; earlier handoffs preserved.

Exact continuation commands:

```bash
cd /home/zyliu/Documents/rna-stable-ai
tail -n 10 reports/exact-comparative-training.log
.venv/bin/python scripts/verify_exact_comparative_development.py
.venv/bin/python scripts/verify_exact_sparse_development.py
.venv/bin/python scripts/predict_context.py --source-summary results/long_comparative_development_summary.json --decoder exact_sparse --fasta configs/context_inference_demo.fasta
.venv/bin/python scripts/verify_context_inference.py
.venv/bin/python -m pytest -q tests/test_exact_sparse_pairs.py tests/test_context_inference.py
```

Then inspect full-suite result, updateREADME/status and versioned handoff, continue
next development stage automatically. Do not rerun CRW selection after exposure;
reuse retained89/47 snapshots. RF00008/RF00017 tests consumed. No long experimental
cohort/family independence/stability claims. No deployments, installs or Git writes.
