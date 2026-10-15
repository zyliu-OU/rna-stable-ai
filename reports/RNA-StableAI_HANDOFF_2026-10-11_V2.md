# RNA-StableAI handoff

- Project: RNA-StableAI
- Date: 2026-10-11 (America/Los_Angeles)
- Version: V2
- Workspace: `/home/zyliu/Documents/rna-stable-ai`
- Saved UTC: 2026-10-12T02:23:11.099358+00:00
- Current roadmap step: **4 — independent biological validation**.

## Completed work

Added `src/rnastable/family_readiness.py` and
`scripts/audit_family_readiness.py` to screen FASTA family metadata and sequences
before opening new structure annotations. It checks exposed families and
identical/similar prior sequences with the existing symmetric SequenceMatcher
0.8 heuristic. Invalid sequences and excluded entries stay in the denominator.
Repeated strand IDs with different processed fragments are bound to full sequence
hashes; exact duplicate identities are rejected. Each run freezes FASTA inputs,
exposure ledger and a hash-bound manifest for offline replay.

Tightened `select_cohort` so an exposed proposed test family is rejected even
when its candidate sequences are dissimilar. Historical trial replay still passes.

The completed local audit at `/home/zyliu/Documents/rna-stable-ai/results/family_readiness_runs/20261012T021712.363806Z`
checked 3172 known exposure records, of which 3104 lack explicit family IDs.
There are 474 Rfam metadata entries: RF00001 (361), RF00008 (47), RF00017 (22),
RF00169 (44). All four families are already exposed; **zero metadata candidates**
remain. No new structure labels, predictions, fitting or test exposure events were
created. This is a completed availability audit, not a new accuracy evaluation.
The initial duplicate-ID rejection log is retained as
`reports/family-readiness-2026-10-11.log`; corrected execution is in
`reports/family-readiness-completed-2026-10-11.log`.

Created `reports/PROJECT_ROADMAP_2026-10-11.md` to explain the seven development
stages and current scientific gate. Updated README entrypoint and family-planning
instructions. Earlier frozen native studies remain complete; see V1 for their
request counts and retained interrupted outcome.

## Verification

- Full suite: **497 passed in 227.75 seconds**
  (`reports/family-readiness-full-suite-2026-10-11.log`).
- Focused readiness/family-trial tests: 19 passed in 66.20 seconds.
- Nine new tests cover metadata-only execution, dissimilar sequences from exposed
  families, unknown-family sequence overlap, invalid/short sequence denominators,
  fragment identities, malformed metadata, snapshot tampering and result tampering.
- Readiness frozen-ledger replay passed; no archive access or inference required.
- New Python files pass Ruff with bootstrap E402 ignored; compileall and whitespace
  checks pass. Historical family-trial audit remains included in the tests.

## Pending work

Acquire new sequence-bound annotated RNA families and document family/source
provenance. Audit their sequences against all known training/development/test
exposures before importing labels. Existing family/clan and legacy-tool training
provenance is unresolved; sequence screening alone cannot establish independence.
Do not reuse RF00008/RF00017 as fresh tests or tune a model from their test scores.

Freeze the evaluated checkpoint and decoder, bind exact annotations to metadata,
then freeze a family plan before predictions. No model was selected or tuned in
this continuation. Independent accuracy of the current helix checkpoint remains
untested. Earlier different pair/context models had poor cross-family transfer;
reused-development helix gains do not resolve that scientific question.

Long biological annotation availability, experimental stability/function evidence
and a validated release remain pending. The project is a research prototype.
Changes remain local; no commit, publication-checkout update or GitHub push was
performed. The original workspace Git index remains preserved.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/audit_family_readiness.py --verify
.venv/bin/python scripts/plan_family_study.py --help
.venv/bin/python -m pytest -q tests/test_family_readiness.py tests/test_family_trial.py
.venv/bin/python -m pytest -q
```

After metadata acquisition or any new exposure, rerun
`.venv/bin/python scripts/audit_family_readiness.py` to create a new snapshot;
`--verify` describes its saved ledger rather than certifying future readiness.
For supplied new references, family assignments, plan and exposure files:

```bash
.venv/bin/python scripts/plan_family_study.py --references data/new_references.json --assignments data/verified_families.json --plan configs/new_family_plan.json --exposure data/exposure.json
```

## Evidence

- `reports/PROJECT_ROADMAP_2026-10-11.md`
- `reports/family_readiness_report.md`
- `results/family_readiness.csv`
- `reports/RNA-StableAI_HANDOFF_2026-10-11_V1.md`
