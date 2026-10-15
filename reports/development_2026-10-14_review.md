# RNA-StableAI reference-engineering review — 2026-10-14

Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Current scientific gate: step 4, independent biological structure validation.

## What changed

Added reference-readiness auditing, a pinned per-sequence PDB-derived source
importer, exact per-sequence coordinate binding, and a raw FR3D contact-provenance
audit. These additions strengthen the inputs to future model evaluations; they
do not retrain, select, or change the original baseline/stack/helix models.
The user's README picture is retained in the local front page.

## Evidence

| Checkpoint | Result |
|---|---|
| Historical reference readiness | Panels have 9, 8, and 4 supported references. None meets the declared 12-reference / three sufficiently represented family gate. |
| Annotation lineage | Cobalamin source explicitly says `Predicted; PFOLD`. Published source citations are not automatically per-sequence experiments. |
| Pinned Rfam 3D import | All nine predeclared files match exact upstream Git blob identities, sizes, and SHA-256 values. Original checkpoint bytes and selection policy were frozen first. |
| Per-sequence binding | 41 annotated candidates, 35 redundant, six selected and supported: glycine 3, preQ1 1, c-di-GMP 2. Crossings retained; no consensus fallback or replacement. |
| Raw FR3D provenance | Six responses; all sequences match. Three contact sets match; three differ from historical supplied strings. Original references unchanged. |
| Source archive | 264/274 recorded Python versions available; ten historical versions explicitly missing. |

The raw graph contains 27/29/75/8/25/26 unique cWW contacts for 3OWI/A, 3P49/A,
6WLT/A, 2L1V/A, 3IRW/R, and 4YAZ/A respectively. Supplied strings contain
26/34/75/8/25/25 contacts. The audit retains all actual set differences; differences
could reflect source versions or source encoding. No unsupported causal attribution.

Current raw graphs for these six chains have no multiple-cWW-partner nucleotides.
The importer still tests and retains such graphs without projecting them to a
one-partner string. Nothing here establishes cellular stability, mutation effects,
retained function, or complete training/tool independence.

## Verification and artifacts

Readiness full suite: 700 passed in 225.31 seconds. Source/binding full suite:
728 passed in 217.33 seconds. Additional raw-contact focused checks: 15 passed.
The full suite including the raw-contact stage passed **743 tests in 217.45 seconds**;
see `reports/structure-contact-provenance-full-suite-2026-10-14.log`.
All four new scripts/tests pass Ruff; retained-source/readiness/raw-contact replays
pass without new predictions or native folds.

- Readiness: `results/reference_readiness_runs/20261015T020727.857457Z`.
- Source protocol: `results/structure_derived_source_protocol_runs/20261015T021405.263740Z`.
- Source: `results/structure_derived_source_runs/20261015T021501.529110Z`.
- Binding: `results/structure_derived_binding_runs/20261015T021934.814458Z`.
- Raw-contact protocol: `results/structure_contact_provenance_protocol_runs/20261015T022345.539073Z`.
- Raw-contact responses/audit: `results/structure_contact_provenance_runs/20261015T022710.758207Z`.

Sandbox DNS failures and approved successful retries remain separate immutable
runs. Source acquisition failures are unknown/unavailable, never empty gold
contact sets. Durable validation exposure precedes imported contact parsing.
Historical panels and newly read source families remain consumed for future planning.

## Next development

Freeze raw PDB contact graphs directly for a separately declared source panel;
verify sequence/PDB/chain/family identity and representability before predictions.
Keep the broader supported-coverage gate open. Do not substitute updated contacts
into completed studies or tune models from these provenance findings.

Upstream references: [Rfam annotation provenance](https://docs.rfam.org/en/latest/building-families.html),
[Rfam 3D pipeline](https://github.com/Rfam/rfam-3d-seed-alignments), and
[BGSU data access](https://www.bgsu.edu/content/bgsu/en/research/rna/help/rna-3d-hub-help/accessing-rna-3d-hub-data.html).
