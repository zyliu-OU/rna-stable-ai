# Supplied-reference evaluation development checkpoint

Project: RNA-StableAI
Date: 2026-10-05 (America/Los_Angeles)
Workspace: `/home/zyliu/Documents/rna-stable-ai`

Implemented `evaluate-reference`, a no-folding evaluator for caller-supplied complete
pseudoknot-free reference structures and saved predictions. Exact A/C/G/U sequences
are required. Reference IDs and methods define the scoring plan before output creation.
Sequence mismatch, duplicate/out-of-plan records, incomplete metadata and malformed
structures reject the input. Missing/failed predictions retain planned denominators
and null metrics. Synthetic, computational and experimental caller labels are grouped
separately; labels are not independently verified. Measured means give each reference
one vote. No annotated input structure is transferred to a mutated sequence.

Each unique run freezes exact input bytes, method/reference plan, scoring policy,
source hashes and environment versions, plus CSV/JSON/report exports. Repeated runs
preserve previous evidence and archive replaced publications. `verify_reference.py`
checks both the requested publication and retained run exports against frozen inputs;
original live inputs need not remain present. It verifies scores, coverage and sequence
identity and rejects changed evidence.

Verification: **210 tests passed**, including **33 new reference-evaluation tests**,
recorded in `reports/tests-reference-final.xml`. Tests cover numerical pair metrics,
all-unpaired conventions, missing and failed outcomes, separate reference kinds,
invalid identity/schema/structures, CLI dry-run/publication/verifier behavior,
retained-run auditing after input removal, and tampering with input snapshots,
manifests, metrics, coverage and latest/retained exports.

Real CLI demonstration and audit passed. It used handwritten software controls,
not experimental references: four planned predictions, two scored and two missing.
Run: `/home/zyliu/Documents/rna-stable-ai/results/reference_runs/20261006T005240.380877Z`.

The existing long equal-budget study independently re-audited successfully. Its
published summary and frozen manifest hashes are unchanged. No refolding, neural
training, dependency/system changes or GitHub push was performed.

New source/configuration files:

- `src/rnastable/reference.py`
- `src/rnastable/reference_audit.py`
- `scripts/verify_reference.py`
- `tests/test_reference.py`
- `configs/reference_demo.json`
- `configs/reference_predictions_demo.json`

Modified CLI, README and prior status were backed up before development in
`reports/source_backups/20261006T004822.149269Z/`. Commands and outputs are retained
in `reports/commands.jsonl`. README describes input formats, denominator conventions,
reference labels, supported structures and latest/per-run audit commands.

Next research step: select an experimental reference dataset with recorded source
and measurement conditions, then supply independent saved predictions. The current
demonstration establishes software behavior only. Development remains local.
