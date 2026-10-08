# RNA-StableAI handoff — 2026-10-05 — V12

Project: RNA-StableAI
Date: 2026-10-05 (America/Los_Angeles)
Version: V12
Absolute workspace: `/home/zyliu/Documents/rna-stable-ai`

Continuous development authorized. User requests handoff+stop if GPT-6 usage finishes.
No observable usage-limit signal; no account-quota telemetry. Proactive checkpoint.

Completed2 sequence-only adjacent canonical stackability indicators, respecting sequence
boundaries/minloop4; learned weights startzero and base parameters/logits match prior
initialization. Wrapped global scorer adds2 parameters,25,876 total. Tiled scorer calls
optional pair-context head; prior models/outputs preserved and focused audits passed.
Fixed10epoch training on SAME89/47 development records with full BCE/exact validation:
selectedepoch5/F1 .423379568067344 (previous exact-selected BCE .3884985411).
Weights outside .0950167775,inside .0903997421. Run:
`results/stack_comparative_development_runs/20261006T033137.606696Z`.
Full source/base initialization/zero feature weights/checkpoints/full-label loss/exposure/
94 predictions audit passed. One seed/reused development; no independent test gain.

Consolidated report now423 predictions/9 methods on47 exact same references:
`reports/expanded_checkpoint_selection_report.md`. Native tools still .717773/.719387,
substantially above neural models. Old report runs preserved.
Stack checkpoint supported in FASTA inference with frozen exact decoder/1024 nt cap;
demo/export audit passed. Default earlier context source remains unchanged.

Synthetic resource run:`results/stack_scalability_runs/20261006T033347.600122Z`.
Explicit greedy/refinement substitution for benchmark ONLY, not silent FASTA fallback.
10,000 nt:scoring4.3954s,greedy.4251s,refinement6.0189s;159,461 candidates/2,551,376bytes;
score tile640,000 elements,head feature tile1,280,000 elements,cumulative processpeak
828,956KiB includingTorch. One observation; no speedup/long labelled accuracy/stability
claim. Exact candidate/score/greedy/refiner/exposure replay audit passed. Synthetic
inputs have no labels; marker uses validation_started for resource exposure.

Verification:last complete full suite352 passed in133.96s
(`reports/tests-structured-selection-checkpoint.xml`). Subsequent focused24 scorer/
inference checks,6 stack/report checks and resource replay passed. Stack full suite
currently running:`reports/tests-stack-checkpoint.log`/XML. Inspect before claimingpass.

Next:add explicit`--decoder greedy|refined` for global checkpoints to enable long FASTA
prediction with deliberate approximate decoder substitution. Keepsource exact default
and1024 nt cap; override supports existing10000 nt/10record/20000total limits. Freeze
method+decoder settings in manifest/summary and exact replay. Preserve measured inference
module/CLI before edit. Then full appropriate checks/docs/status/versioned checkpoint.

Exact commands:

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/verify_stack_comparative_development.py
.venv/bin/python scripts/run_stack_scalability.py --verify
.venv/bin/python scripts/report_expanded_checkpoint_selection.py
.venv/bin/python scripts/predict_context.py --source-summary results/stack_comparative_development_summary.json --fasta configs/context_inference_demo.fasta
.venv/bin/python scripts/verify_context_inference.py
.venv/bin/python -m pytest -q tests/test_stack_pairs.py tests/test_context_inference.py
```

Current-source backups:`reports/source_backups/20261006T033118.643301Z`,
`20261006T033414.062281Z`. Initial stack runner had a source-path preflight error before
output; fixed to frozen exact development summary, rejected log retained in
`reports/stack-comparative-preflight-rejected.log`. No rejected trial or exposure created.
RF00008/RF00017 consumed; reuse89/47 snapshots, no CRW recuration. No fresh assay/family
independence/biological stability claim. No install/deployment/Git write/messages.
