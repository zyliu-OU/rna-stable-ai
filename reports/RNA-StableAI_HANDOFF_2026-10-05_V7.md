# RNA-StableAI handoff — 2026-10-05 — V7

Project: RNA-StableAI
Date: 2026-10-05 (America/Los_Angeles)
Version: V7
Absolute workspace: `/home/zyliu/Documents/rna-stable-ai`

Continuous development is authorized. Automatically continue after verified stages.
User requests saving a handoff and stopping if GPT-6 usage is exhausted. No usage-limit
signal has been received, and no remaining-account-quota tool is available. Checkpoints
are saved proactively because an abrupt cutoff may prevent a final write.

Completed since V6:
- Global sparse all-distance pair scorer, fixed top-16 candidates per right endpoint,
  bounded-memory greedy decoding, and exact short-input decoder diagnostics.
  Development run `results/global_sparse_development_runs/20261006T024235.048398Z`:
  same 65 train/35 validation, selected epoch6, validation F1 .1621174685121644.
- Synthetic 10,000 nt global inference: scoring4.38 s, greedy0.20 s, 97,271 candidates
  (1.56 MB), score tile640,000 elements. Scores quadratic; stable top-k sorting adds
  sorting work. No long labelled accuracy or speedup claim.
- Sparse local refinement improves logit objective while preserving noncrossing pairs.
  Original validation F1 .2004820941 versus greedy .1621174685 and sparse exact .3082245715.
  Subset-conflict variant was also measured/audited. Both are approximate.
- Imported only legacy CRW train/holdout FASTA+BPSEQ annotations with exact source
  binding, prior-sequence and within-study external-ID/sequence filtering; never test.
  Selected24 new train317–552 nt and12 validation319–543 nt, comparative annotations.
- Expanded fresh training on89 train/47 validation,10 epochs, selected10:
  validation F1 .20857850721519425, 4,462 positive/1,180,545 negative training pairs,
  weight264.57754370237564. Run `results/long_comparative_development_runs/20261006T025852.417408Z`.
  Full source/label/checkpoint/exposure/reference audit passed. Different denominator
  from short studies; scores cannot establish improvement. No test inference.
- FASTA checkpoint inference now supports retained global/expanded checkpoints and
  exact exported prediction replay. Latest expanded-model demo passed.
- Deterministic training-only negative sampler retains all representable positives;
  5 focused tests passed. Sampled training driver/auditor remain to implement.

Verification: last full suite306 passed (`reports/tests-global-sparse-checkpoint.xml`).
Subsequent focused CRW/refinement/inference/sampling tests and expanded training audits
passed. Full suite after those additions is pending. V6's running suite actually
finished290 passed; V6 is preserved unchanged. Historic pilot/pair/family/budget results
are retained. RF00008/RF00017 test families are already consumed; do not reuse them for
fresh claims. All new model comparisons use development data. Comparative annotations
are not experimental assays. New longer experimental/family-independent data pending.

Next work: fixed negative-sampling comparison on the SAME retained89/47 snapshots;
full validation labels, new random model, no fresh curation or test evaluation. Do not
rerun CRW selection blindly after its36 records have entered the exposure registry.
Then audit checkpoint, compare identical-development per-source scores, update docs/status,
and run full suite. Incomplete samples are not a measured experiment.

Exact continuation/verification commands:

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/verify_global_sparse_development.py
.venv/bin/python scripts/verify_global_sparse_scalability.py
.venv/bin/python scripts/verify_sparse_refinement.py
.venv/bin/python scripts/verify_long_comparative_development.py
.venv/bin/python scripts/verify_context_inference.py
.venv/bin/python -m pytest -q tests/test_negative_sampling.py
.venv/bin/python -m pytest -q --junitxml=reports/tests-next-development-checkpoint.xml
```

Source backups retain prior measured modules under `reports/source_backups/`, including
`20261006T024151.756762Z`, `20261006T025030.932443Z`, and `20261006T025956.346703Z`.
No system installation, Git write, deployment or messaging performed.
