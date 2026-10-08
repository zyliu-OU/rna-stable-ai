# RNA-StableAI handoff — 2026-10-05 — V10

Project: RNA-StableAI
Date: 2026-10-05 (America/Los_Angeles)
Version: V10
Absolute workspace: `/home/zyliu/Documents/rna-stable-ai`

Continuous development authorized. User requests handoff+stop if GPT-6 usage finishes.
No observable usage-limit signal received; no account-quota telemetry is available.
This checkpoint is saved proactively while development continues.

Completed exact-decoder checkpoint selection on SAME89 train/47 validation, full labels,
architecture, optimizer and seed as expanded training. All10 mean training losses and
random initialization exactly match prior full-label training. Selection decoder alone
changed: exact sparse selectedepoch3/F1 .38849854106861975 versus refinement-selected
checkpoint epoch10/F1 .2085785072; posthoc exact onepoch10 F1 .3425350808.
Run:`results/exact_comparative_development_runs/20261006T031734.025839Z`.
Source/full-label/random-init/checkpoint/selection/reference audit passed; no test inference.

FASTA loader now honors frozen`inference_decoder=exact_sparse` by default for the new
checkpoint, with1024 nt bound before output. Explicit exact override works for older
global checkpoints. Existing defaults remain for other retained source configurations.
Demo and exact exports audited;16 focused exact/inference checks passed.
Source backup:`reports/source_backups/20261006T031859.027902Z`.

Consolidated report on47 identical exposed references/329 predictions,7 methods:
`reports/expanded_checkpoint_selection_report.md`; figure in
`results/expanded_selection_report_runs/20261006T032011.409305Z/development_selection.png`.
Native baselines remain .717773/.719387, substantially above neural models. Selection
figure inspected and exact composition/reference/denominator/export audit passed.
All scores are development-only; oracle candidate bounds fromV8/V9 are not predictions.

Verification:full suite341 passed in131.58 s
(`reports/tests-exact-selection-checkpoint.xml`);2 later report tests passed.
Structured training-loss prototype subsequently added:5 focused tests passed, including
brute-force noncrossing loss-augmented oracle/gradient/gold-retention checks. This prototype
is NOT a measured trained experiment yet. It uses pruned top16 loss-augmented candidates
plus every supported gold pair; exact decode within that graph, not full-graph SVM.
Reference:https://www.jmlr.org/papers/v6/tsochantaridis05a.html.

Next active stage: integrate training-only structured hinge with fixed small BCE term,
full unchanged validation labels/loss and exact checkpoint selection. Preserve measured
`context_training.py` before optional loss callback. Reuse frozen89/47 snapshots, fresh
random model, fixed10epochs, no test/family selection or CRW recuration. Run/audit loss,
checkpoints, exact prediction exports; update README/status/full tests, continue.

Exact continuation commands:

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/verify_exact_comparative_development.py
.venv/bin/python scripts/verify_exact_sparse_development.py
.venv/bin/python scripts/report_expanded_checkpoint_selection.py
.venv/bin/python scripts/predict_context.py --source-summary results/exact_comparative_development_summary.json --fasta configs/context_inference_demo.fasta
.venv/bin/python scripts/verify_context_inference.py
.venv/bin/python -m pytest -q tests/test_structured_pair_loss.py tests/test_expanded_selection_report.py
.venv/bin/python -m pytest -q
```

PriorV8/V9 retain global/CRW/sampling/candidate/native details. RF00008/RF00017 tests
consumed. No new assay, longer experimental cohort, family independence, long labelled
accuracy or biological-stability claim. No installs, deployments, Git writes or messages.
