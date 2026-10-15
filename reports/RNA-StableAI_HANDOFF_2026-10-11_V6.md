# RNA-StableAI handoff

- Project: RNA-StableAI
- Date: 2026-10-11 (America/Los_Angeles)
- Version: V6
- Workspace: `/home/zyliu/Documents/rna-stable-ai`
- Saved UTC: 2026-10-12T03:30:07.260233+00:00
- Current roadmap step: **4 — biological validation tooling; complete pair-set scoring added**.

## Completed work

Added `src/rnastable/pair_reference.py`,
`scripts/evaluate_pair_reference.py`,
`scripts/validate_pair_reference_development.py`, two synthetic JSON examples
and `docs/PAIR_REFERENCE_FORMAT.md`.

The explicit `pair_set_zero_based_v1` format scores complete crossing contacts
without deleting or flattening them. Predictions can supply a pair list or
nested dot-bracket structure. Each nucleotide has at most one partner; coordinate
order/range, duplicates, conflicting partners, sequence mismatches and ambiguous
representations are rejected. Pair chemistry and minimum loop size are not
silently filtered. Missing/failed predictions retain null metrics and planned
method/reference denominators. Aggregates remain separated by reference kind.

Scoring freezes original input bytes, records conservative validation exposure
before metrics and preserves per-run CSV/report outputs. Audit replays snapshots,
metrics, coverage, exposure and exports without new inference. Added
`bind_pair_reference` to the existing WUSS binding module: it preserves all
contacts, including letter-pair pseudoknots, for exact sequence-bound complete
references. Missing annotated paired columns still reject an incomplete reference.
The old nested binding/scorer behavior remains unchanged.

## Development evidence

Equivalence run: `/home/zyliu/Documents/rna-stable-ai/results/pair_reference_development_runs/20261012T032118.139461Z`.
Pair-set scoring run: `/home/zyliu/Documents/rna-stable-ai/results/pair_reference_runs/20261012T032118.213704Z`.

All seven exact pair metrics match the old scorer for all 423 stored development
predictions (nine checkpoints × 47 previously exposed records). No new fitting,
checkpoint selection, prediction experiment or fresh test was performed.
Crossing capability is checked separately using synthetic fixtures. The CLI
example ran under `/tmp/rnastable-pair-reference-example-20261012T031600Z`; it
contains supplied toy predictions, not biological accuracy measurements.

The development report now labels computational/experimental reference-kind rows
explicitly. The earlier unlabeled report is archived; all metrics remain
unchanged. The completed prospective result files and checkpoint bytes were not
rewritten. Full-suite tests include their existing frozen-model replay audit.

## Verification

- Full suite: **562 passed in 227.14 seconds**
  (`reports/pair-reference-full-suite-2026-10-11.log`).
- Focused pair-set and existing prospective-binding tests: 46 passed.
- Twenty-seven new tests cover crossing-pair denominators, missing/failed/empty
  conventions, malformed plans, partner/coordinate validation, fixed bounds,
  randomized crossing detection, snapshot/exposure replay and complete WUSS
  mapping while preserving legacy pseudoknot rejection.
- All 423 development predictions replay with exact equality in all seven
  metrics, without inference or model fitting.
- CLI synthetic example and per-run CSV/report audit passed.
- Changed Python files pass Ruff with script bootstrap E402 ignored,
  compileall and whitespace checks.

## Pending work

Integrate the pair-set format into separately frozen future evaluation protocols
using new unexposed families with complete, sequence-bound annotation sources.
The model decoder still predicts nested structures; this is scoring support,
not a newly trained pseudoknot predictor or improved model accuracy.
Missing paired-column references remain unsupported, with no contact deletion.

Do not reuse RF00059/RF00162/RF00167 or earlier consumed test families as fresh
tests, and do not tune the evaluated checkpoints from those test outcomes.
Subsequent model development must use development cohorts and reserve new
families before another prospective test.

Broader training/tool provenance, long biological annotations, experimental
stability/function and a validated release remain pending. All changes are local;
no commit, push or publication-checkout update occurred. The existing Git index
was preserved.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/validate_pair_reference_development.py --verify
.venv/bin/python scripts/evaluate_pair_reference.py --verify /home/zyliu/Documents/rna-stable-ai/results/pair_reference_runs/20261012T032118.213704Z/summary.json
.venv/bin/python -m pytest -q tests/test_pair_reference.py tests/test_prospective_binding.py
.venv/bin/python -m pytest -q
```

Format-only synthetic example, isolated from biological results:

```bash
.venv/bin/python scripts/evaluate_pair_reference.py --references configs/pair_reference_synthetic_example.json --predictions configs/pair_predictions_synthetic_example.json --output-root /tmp/rnastable-pair-example
.venv/bin/python scripts/evaluate_pair_reference.py --verify /tmp/rnastable-pair-example/results/pair_reference_summary.json
```

No further downloads are required for this tooling/equivalence result. The
completed prospective panel remains reserved for historical audit.

## Evidence

- `docs/PAIR_REFERENCE_FORMAT.md`
- `reports/pair_reference_development_review_2026-10-11.md`
- `reports/pair_reference_development_report.md`
- `reports/pair-reference-development-audit-2026-10-11.log`
- `reports/pair-reference-cli-example-2026-10-11.log`
