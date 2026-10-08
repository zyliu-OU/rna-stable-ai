# RNA-StableAI handoff — 2026-10-05 — V14

Project: RNA-StableAI
Date: 2026-10-05 (America/Los_Angeles)
Version: V14
Absolute workspace: `/home/zyliu/Documents/rna-stable-ai`

Continuous development authorized. User requests save+stop if GPT-6 usage finishes.
No observable usage-limit signal; account quota telemetry unavailable. Proactive checkpoint.

Completed independent target-template sparse checkpoint scoring and constrained pooled
proposal search. Compatible original LinearFold template contacts rank first; learned
mean pair logits break ties in neural arm. Direct sparse target scoring supports1–10000
nt, no quadratic all-pair inference/decoding, no labels. Proxy logits are not energy.
Old`optimization.py` and historical budget code/provenance remain unchanged.

Measured3-arm pilot on previously exposed synthetic1000 nt resource input, seed20261006,
8 native proposals/16candidate pools/16mutation cap/protectedpositions1–3, all nucleotide
counts preserved. Random-pool/compatibility-only controls, same native requests:
1 baseline+8 proposals+2 Vienna validation folds perarm =33 raw successful native folds.
Selected Vienna deltas:random_pool -11.0 kcal/mol (12mutations,6accepted);
compatibility_only -8.4 (8mutations,4accepted);
checkpoint_prior -18.5 (14mutations,7accepted),128 added neural proxy evaluations.
NativeLinearFold energy alone accepts search moves; Vienna improvement required for
selection. All trajectories/pools/checkpoint logits/constraints/raw folds/selections/
exposure events/cost denominators replayed successfully. One input/one seed; no accuracy
test, new model fitting, biological stability or population-level advantage claim.
Run:`results/checkpoint_prior_pilot_runs/20261006T035130.449329Z`.
Report:`reports/checkpoint_prior_pilot_report.md`.

Verification:last full suite363 passed in166.80s
(`reports/tests-long-override-checkpoint.xml`). Subsequent8 prior/core tests passed;
measured prior pilot audit passed. Focused suite including new measured-pilot test running
when this checkpoint was written; inspect completion before updating count.

Next:before extending native search across inputs/seeds, add per-request atomic native
journaling and resumable orchestration. Preserve completed native requests on resumption;
code/config/model/source guards; lock concurrent drivers; interrupted requests stay
unknown/failed rather than being silently retried or invented. Keep all candidate pools
and exposure-before-scoring evidence. Code snapshots should support future continuation
without changing historical search source. Start interruption/cache tests before measured
larger native studies. Then replicate fixed3-arm pilot on additional synthetic inputs.

Exact commands:

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/verify_checkpoint_prior_pilot.py
.venv/bin/python -m pytest -q tests/test_checkpoint_prior.py tests/test_pooled_proposals.py
.venv/bin/python scripts/verify_stack_comparative_development.py
.venv/bin/python scripts/run_stack_scalability.py --verify
.venv/bin/python -m pytest -q
```

Do not label rerun resource/pilot inputs fresh independent tests. RF00008/RF00017 consumed;
reuse89/47 development snapshots, no CRW recuration. Longer independent experimental/
family data still pending. V13 retains long FASTA override and363-suite details.
No installs, Git writes, deployment or messages. Continue after verified stages.
