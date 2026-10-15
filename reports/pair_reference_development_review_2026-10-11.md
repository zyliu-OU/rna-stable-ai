# RNA-StableAI pair-set evaluation development — 2026-10-11

Workspace: `/home/zyliu/Documents/rna-stable-ai`.

Added a separate exact pair-set evaluator, JSON schema, CLI, synthetic example
inputs and an annotation bridge for complete WUSS contacts. It preserves crossing
contacts in all seven pair metrics and accepts supplied nested or crossing
predictions. Invalid coordinates, duplicate/conflicting partners, sequence
mismatches and ambiguous representations are rejected. Failed/missing outcomes
retain null metrics and their planned denominators. Reference chemistry and
minimum loop size are not silently filtered.

Each scoring run freezes original JSON bytes, registers conservative validation
exposure before scoring and preserves per-run outputs. Audit replays hashes,
metrics, coverage, exposure and CSV/report exports without inference. WUSS-to-pair
mapping preserves all annotated contacts and still rejects missing paired columns.
The legacy dot-bracket binding/evaluator behavior remains unchanged.

## Verification on development data

`scripts/validate_pair_reference_development.py` replays the previously frozen
development head study. All seven exact pair metrics agree with the legacy scorer
for every one of the 423 stored predictions, comprising nine checkpoints and 47
already exposed development records. The new contact-list representation does
not change existing scores. There is no new fitting, prediction, checkpoint
selection or test evaluation.

The original prospective panel remains reserved for historical audit. Its
completed result files and all trained checkpoint bytes remain unchanged.
Crossing-contact capability is exercised with constructed fixtures, including a
crossing reference scored against a nested prediction, full crossing predictions,
empty contacts and missing/failed outcomes. Fixtures do not represent biological
accuracy measurements. The CLI example executes separately under `/tmp`.

## Scientific scope

The new evaluator can assess complete pseudoknotted contact sets in future
protocols without flattening them. The prediction decoder still generates nested
structures. References with missing annotated paired columns remain incomplete
and rejected. Future biological evaluation still requires sequence-bound source
evidence, exposure checks and a frozen model/evaluation protocol.

This is an evaluation-capability improvement, not a newly measured accuracy
gain. Unknown training/tool provenance, long biological annotations and measured
stability/function remain pending. Full-suite and focused totals are recorded in
the versioned handoff; source evidence and the replayable equivalence table are
in `reports/pair_reference_development_report.md`.
