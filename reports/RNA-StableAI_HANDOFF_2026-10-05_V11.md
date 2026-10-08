# RNA-StableAI handoff — 2026-10-05 — V11

Project: RNA-StableAI
Date: 2026-10-05 (America/Los_Angeles)
Version: V11
Absolute workspace: `/home/zyliu/Documents/rna-stable-ai`

Continuous development remains authorized. Save handoff+stop if GPT-6 usage exhausts.
No observable usage-limit signal received; available tools expose no account quota.
This is a proactive checkpoint during ongoing development.

Completed training-only structured hinge plus0.1 weighted BCE on SAME89/47 snapshots,
fresh model,10epochs, exact sparse validation. Gold retained in pruned training graphs;
full unaugmented validation BCE, unaugmented top16 prediction. Selectedepoch2,
development F1 .31288613175669067, below exact-selected BCE .3884985411.
Run:`results/structured_comparative_development_runs/20261006T032540.594773Z`.
Audit verified890 training decision/order/target/loss ledger rows, exact initial
loss/graph anchor, random initialization, checkpoint/selection/full validation loss,
94 reference predictions and exposure binding. It does not replay every optimizer step.

Reusable trainer now supports an optional training-only loss callback; default BCE
behavior preserved. Validation never invokes custom loss. Seven prototype/callback
tests passed;20 combined structured/inference tests passed including measured audit.
Structured checkpoint inference is supported and named`trained_structured_sparse`;
source exact decoder honored,1024 nt cap; no labels at prediction time.

Consolidated report extended to376 predictions/8 methods on47 identical exposed
references, including structured model. Composition/reference/subgroup/export audit
and2 focused report tests passed. All older report runs preserved.
`reports/expanded_checkpoint_selection_report.md` is the current convenience report.
Native baselines remain .717773/.719387; neural models remain below them. No new test.

Full suite after callbacks/structured additions is running:
`reports/tests-structured-selection-checkpoint.log`/XML. Last complete suite341 passed
in131.58 s. Do not report the running suite passed before inspecting completion.
Source backups:`reports/source_backups/20261006T032539.080192Z`,
`20261006T032710.013841Z`, `20261006T032737.351221Z`.

Next active prototype:`src/rnastable/stack_pairs.py` with2 sequence-only adjacent
stackability indicators, learned weights initializedzero,2 extra parameters.
Outside(i-1,j+1)/inside(i+1,j-1) canonical compatibility respects boundaries/minloop4.
Base logits/weights identical at initialization; feature/gradient/broadcast tests pass.
Not integrated into tiled inference or measured training yet. Integrate optional pair
context logits in tiled scorer AFTER running suite completes, preserve old scorer;
add checkpoint factory dispatch; train on SAME89/47 with full BCE/exact validation,
fixed10epochs/seed, audit/model comparisons. No CRW recuration or fresh test.

Exact continuation commands:

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/verify_structured_comparative_development.py
.venv/bin/python scripts/report_expanded_checkpoint_selection.py
.venv/bin/python scripts/predict_context.py --source-summary results/structured_comparative_development_summary.json --fasta configs/context_inference_demo.fasta
.venv/bin/python scripts/verify_context_inference.py
.venv/bin/python -m pytest -q tests/test_stack_pairs.py
.venv/bin/python -m pytest -q
```

RF00008/RF00017 consumed. Comparative annotations are not assays; family/clan/tool
training overlap unresolved; no long labelled accuracy/biological-stability claim.
Canonical prior checkpointsV8–V10 preserve detailed histories. No installs, deployments,
Git writes or external messaging. Continuous work should resume at next prototype.
