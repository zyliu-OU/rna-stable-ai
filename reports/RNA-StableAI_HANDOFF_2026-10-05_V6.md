# RNA-StableAI handoff — 2026-10-05 — V6

Project: RNA-StableAI
Date: 2026-10-05 (America/Los_Angeles)
Version: V6
Absolute workspace: `/home/zyliu/Documents/rna-stable-ai`

This is a checkpoint during continuous work, not a request to stop. User explicitly
authorized automatic continuation after every verified stage.


Implemented exact span-constrained O(nw)-storage/O(nw²)-work inference; compared
against dense dynamic programming and sparse/dense head scores. Synthetic10,000 nt:
span64 ~9.1 s,13.12 MB arrays; span128 wider-context checkpoint ~19.1 s,25.92 MB arrays.
CPU/RSS includes Torch; one observation, no speedup or accuracy claim.

Wider-context model:26,097 params,91 nt receptive field, sparse supervised pair
scoring. Identical reused65 train /35 validation records,10 epochs,one seed:
span64/sqrt weight F1 .21773512713604878; span128/sqrt .2596583332104007;
span128/full ratio .3074254052121712 (selected epoch6). Selected by reused validation,
not an independent test. PDB-derived F1 .59997 versus comparative .15479. Zero
excluded development contacts atspan128. All three checkpoint audits passed.
Comparison: `results/context_comparison_runs/20261006T022454.836497Z/summary.json`.

Fresh comparative trial: `results/context_family_trial_runs/20261006T022922.302415Z`.
Random model trained onlyRF00001(24)/validatedRF00169(23), selectedepoch1(F1 .0863159),
testRF00017(12),lengths290–317 nt. TestF1 trained .003643045940328309,
initial .0047127108236874595, ViennaRNA .4780596903544601,
LinearFold .47994718111707635, all unpaired0. All60 predictions and24 native folds
measured/audited;314 test reference contacts excluded byspan128. This is a negative
transfer result on processed comparative annotations. RF00017 is consumed alongside
RF00008. Repeating the default context family trial is rejected before output.
Family/clan/tool-training independence and prior PDB family assignments remain
unresolved; no biological stability or unrestricted long-RNA claim.

Reusable trainer API has onlytrain/validation inputs. Checkpoint-bound FASTA inference
freezes bytes,records test-start exposure before inference, and exports JSON/DBN plus
supplied-reference prediction JSON. Inputs bounded10 records,10,000 nt each,20,000 nt
total; CPU threads<=2. Source hashes, checkpoints, sequence binding, export/tamper checks
passed. Exposure events nowcover all`results/*_runs/*/exposures/*.json`; fsync includes
file andparent-directory entries. Registry138 records afterRF00017 andsyntheticdemo.

Local PDB train/holdout inventory128–1024 nt: one353 nt training record,no validation.
No test-source files read for this inventory; insufficient larger experimental cohort.
Next active development stage: sparse scoring for unrestricted distances plus a
bounded-memory approximate decoder, verified on synthetic/reused development only.
Acquire new verified experimental/family data before any further fresh test.

Exact verification:

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/verify_banded_development.py
.venv/bin/python scripts/verify_context_comparison.py
.venv/bin/python scripts/verify_context_scalability.py
.venv/bin/python scripts/verify_context_family_trial.py
.venv/bin/python scripts/predict_context.py --fasta configs/context_inference_demo.fasta
.venv/bin/python scripts/verify_context_inference.py
.venv/bin/python -m pytest -q
```

Prior complete fullsuite289 passed. Final fullsuite after reference-export/fsync
improvements is running; check`reports/tests-context-inference-checkpoint.xml` and
command logs. Prior family/pilot/pair/long-budget summary hashes match preceding
status; no historic measured results overwritten. NoGit/system/package changes.
Source backups: `reports/source_backups/20261006T021942.277060Z`,
`20261006T022115.459702Z`, `20261006T022311.717783Z`,
`20261006T022638.127412Z`, `20261006T023431.640545Z`.
