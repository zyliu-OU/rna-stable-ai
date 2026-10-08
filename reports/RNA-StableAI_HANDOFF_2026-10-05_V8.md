# RNA-StableAI handoff — 2026-10-05 — V8

Project: RNA-StableAI
Date: 2026-10-05 (America/Los_Angeles)
Version: V8
Absolute workspace: `/home/zyliu/Documents/rna-stable-ai`

Continuous development is authorized. After verified stages automatically continue.
User requests handoff+stop if GPT-6 usage finishes. No limit signal received; quota
telemetry is unavailable. Saved proactively so abrupt cutoff does not lose progress.

Completed: all-distance tiled sparse scorer and approximate refinement; longer source-bound
CRW development import; full-label training on89 train/47 validation; deterministic
training-only negative sampling on the exact same snapshots; native baseline comparison
and label-informed candidate diagnostics. Historical V7 and earlier are preserved.

Full-label:4,462 positives/1,180,545 negatives, selectedepoch10, mean development
F1 .20857850721519425. Sampled:all4,462 positives retained,70,013 negatives,
weight15.690945764231287, selectedepoch9, F1 .20172616105030025. Sampling did not
improve the overall development score. Full validation labels/loss audited.
Source runs: `results/long_comparative_development_runs/20261006T025852.417408Z`
and`results/sampled_comparative_development_runs/20261006T030802.214027Z`.

Same47 records:ViennaRNA F1 .7177733468424221,LinearFold .7193873774786459.
All235 predictions and94 successful raw native folds audited. Per-source rows:
`reports/expanded_development_comparison_report.md`.

Candidate diagnostics:94 checkpoint/validation rows audited. CRW full-label model:
1,042 reference contacts nonpositive,192 removed bytop-k,325 retained contacts omitted
bydecoder; oracle candidate F1 bound .377805 versus decoded .048387. These oracle
bounds use labels, are not predictions, and cannot be promoted as model accuracy.
`reports/expanded_candidate_diagnostics_report.md` contains other groups.

Verification:full suite324 passed in122.08 s
(`reports/tests-sampled-comparative-checkpoint.xml`);7 subsequently added focused
candidate/comparison tests passed. All full/sample checkpoint, source, exposure,
reference and native fold audits passed. Exposure registry174 unique records.
FASTA supports retained context/global/expanded/sampled checkpoints with frozen bytes,
exact sequence binding, exposure-before-inference, JSON/DBN/reference exports.

Next:implement exact sparse dynamic programming bounded to1024 nt to diagnose decoding
loss without fitting. Keep tiled approximate inference for synthetic10,000 nt.
Do not rerun CRW curation blindly after36 newly selected records became exposed; reuse
retained89/47 snapshots. No fresh test planned. New longer experimental sources and
family/clan independence remain unresolved. RF00008/RF00017 tests already consumed.
Comparative annotations are not experimental assays; no stability/generalization claim.

Exact verification/continuation commands:

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/verify_sampled_comparative_development.py
.venv/bin/python scripts/verify_expanded_development_comparison.py
.venv/bin/python scripts/verify_expanded_candidate_diagnostics.py
.venv/bin/python scripts/predict_context.py --source-summary results/sampled_comparative_development_summary.json --fasta configs/context_inference_demo.fasta
.venv/bin/python scripts/verify_context_inference.py
.venv/bin/python -m pytest -q tests/test_candidate_diagnostics.py tests/test_expanded_comparison.py
.venv/bin/python -m pytest -q
```

Latest measured inference source backup:`reports/source_backups/20261006T030833.014002Z`.
Older source backups under`reports/source_backups/` preserve prior measured implementations.
Prior pilot/pair/family/equal-budget summaries remain retained. No Git writes, system
installation, deployment or external messages. Mutable status convenience files are
current; this versioned handoff is canonical.
