# RNA-StableAI handoff — 2026-10-05 — V13

Project: RNA-StableAI
Date: 2026-10-05 (America/Los_Angeles)
Version: V13
Absolute workspace: `/home/zyliu/Documents/rna-stable-ai`

Continuous development authorized. Handoff+stop requested if GPT-6 usage finishes.
No observable limit signal; account quota unavailable through tools. Proactive checkpoint.

Completed explicit`--decoder source|exact_sparse|greedy|refined` for checkpoint FASTA.
Source honors frozen settings; exact sparse<=1024 nt; explicit approximate overrides
for global checkpoints permit<=10000 nt/10records/20000total. Context checkpoint sparse
requests reject before output. Methods have override suffixes; refinement settings frozen
and checked; auditor validates input limits/decoder/config/export/exposure binding.
18 focused inference tests passed including long override and tamper/reject checks.

Measured10,000 nt synthetic stack checkpoint with`--decoder refined`; immutable run:
`results/context_inference_runs/20261006T033827.304596Z`.
Convenience`results/stack_long_inference_summary.json` binds this specific run independently
of mutablelatestcontext inference. Structure/objective exactly match synthetic resource
refinement; exact checkpoint/export/exposure audit passed. No labels/accuracy evaluation.
FASTA:`configs/stack_long_inference_demo.fasta` (from resource benchmark's synthetic10k).

Preceding fullsuite358 passed in153.65s (`reports/tests-stack-checkpoint.xml`).
New fullsuite for overrides is running:`reports/tests-long-override-checkpoint.log`/XML.
Inspect before claiming completion. Source backup:
`reports/source_backups/20261006T033748.591015Z`.

V12 preserves measured stackability F1 .4233795681 on SAME89/47 development and
synthetic resource details. Native47-record baselines .717773/.719387 remain higher.
Consolidated423 predictions/9methods in`reports/expanded_checkpoint_selection_report.md`.
No independent test gain, long labelled accuracy or biological-stability claim.

Next active stage:checkpoint-guided proposal ranking within constrained native-energy
search. Implement independent target-template sparse scoring and pool ranking, without
changing historical`optimization.py` or budget provenance. Score compatible original
LinearFold template pairs directly (no quadratic all-pair inference/decoding); compatible
contact count first, mean learned logits second. Compare random-pool, compatibility-only
and checkpoint-guided arms with equal native fold budgets and identical frozen input.
NativeLinearFold strict improvements and ViennaRNA selection remain final acceptance
rules. Freeze source/target/pools/scores/folds/provenance; no labels/model refitting or new
test claims. Start unit tests/plan before measured pilot. All old results retained.

Exact continuation commands:

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/predict_context.py --source-summary results/stack_comparative_development_summary.json --decoder refined --fasta configs/stack_long_inference_demo.fasta
.venv/bin/python scripts/verify_context_inference.py
.venv/bin/python -m pytest -q tests/test_context_inference.py
.venv/bin/python scripts/run_stack_scalability.py --verify
.venv/bin/python scripts/verify_stack_comparative_development.py
.venv/bin/python -m pytest -q
```

Reusing the retained long-demo FASTA is not a fresh accuracy test. Input records are
conservatively exposed before prediction. RF00008/RF00017 consumed; no CRW recuration.
Longer independent experimental/family data remains pending. No installs/deployments/
Git writes/external messages. Continue stages automatically while execution permits.
