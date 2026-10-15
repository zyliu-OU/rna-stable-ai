# Per-sequence structure-derived reference engineering

The original Rfam consensus panels did not provide broad supported coverage.
This workflow imports a distinct annotation for each PDB-derived sequence and
keeps its sequence, PDB accession, chain, source tag, and coordinates together.
It does not replace a missing per-sequence annotation with family consensus.

## Pinned source and declared panel

Official source: [Rfam 3D seed alignments](https://github.com/Rfam/rfam-3d-seed-alignments),
commit `a22cc827b5b99a3e97935384cc0812b73bc49668` (2023-11-06).
All nine input files are pinned by Git blob identity, size, and retained SHA-256.
The source Apache-2.0 license, README, annotation writer, alignment pipeline,
automatic/curated PDB mappings, and three alignments are retained together.

The source protocol froze RF00504 (glycine), RF00522 (preQ1-I), and RF01051
(c-di-GMP-I), original seed-20261006 baseline/stack/helix checkpoints, exact top-16
decoder, zero penalty, 20–512 nt bound, five-record family cap, sequence-overlap
threshold 0.8, and the broad reference-readiness policy before downloads.

Selection uses family, PDB, chain, and sequence identity before contact parsing.
Exact prior PDB/family exposure and conservative families inferred from retained
PDB mappings are excluded. Repeated/highly similar source sequences are removed
by the declared rule, rather than counted as independent structures. Every
candidate decision remains recorded. Valid annotated source sequences are
registered as validation exposure before any pair-coordinate mapping.

Each bracket type has its own stack, so crossings such as `(..{..).}` survive.
Gap-bound, unbalanced, unknown, or otherwise unsupported annotations remain
unsupported after selection; later candidates do not replace them. No source
contacts are deleted to obtain a nested reference.

## Completed binding and limits

The 41 annotated source records yield **six selected/supported references**:
three glycine, one preQ1, and two c-di-GMP. Thirty-five candidates are excluded
as redundant. This does not meet the frozen 12-reference / three sufficiently
represented family coverage gate. No model prediction or native fold is run.

The official source writer takes FR3D cWW annotations and assigns brackets to
nucleotide positions. A positional string cannot demonstrate that an underlying
raw graph with multiple partners was preserved. Its nested-versus-all merging
also needs exact contact provenance. These supplied annotations therefore retain
`reference_kind=computational`, a separate PDB-derived basis, and explicit false
flags for raw-interaction completeness and per-sequence experimental verification.
This conservative label does not deny that the upstream coordinates are structural
measurements; it avoids certifying a contact graph that has not been verified.

`scripts/audit_structure_contact_provenance.py` freezes a separate, model-free
integrity audit for the six selected PDB chains. It retains current raw FR3D
responses, exact sequence matches, all cWW edges (including multiple partners),
reverse/duplicate accounting, and differences from supplied annotations. Invalid
or unavailable source data remain unknown. It never replaces frozen references.
Version differences between current annotations and the pinned historical source
must not be attributed to a writer bug without exact-version evidence.

The first integrity audit retrieved all six responses and matched every sequence.
Exactly three supplied contact sets match current raw FR3D: 6WLT/A, 2L1V/A, and
3IRW/R. The remaining three differ: 3OWI/A and 4YAZ/A each have an additional
terminal cWW contact in the current raw response; 3P49/A has several differences
in both directions. All original annotations and all raw edges remain retained.
These findings motivate freezing raw contact graphs directly for a future panel,
with explicit one-partner/contact-completeness gates before model evaluation.

Raw data access is described by [BGSU](https://www.bgsu.edu/content/bgsu/en/research/rna/help/rna-3d-hub-help/accessing-rna-3d-hub-data.html);
the sequence/contact endpoint used here is recorded in the official pinned
`fr3d_2d.py` source. Successful provenance checks still would not establish
complete training/tool independence, biological stability, or retained function.

## Replay

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/prepare_structure_derived_source.py --verify results/structure_derived_source_runs/20261015T021501.529110Z/summary.json
.venv/bin/python scripts/prepare_structure_derived_binding.py --verify results/structure_derived_binding_summary.json
.venv/bin/python -m pytest -q tests/test_structure_derived_source.py tests/test_structure_derived_binding.py tests/test_structure_contact_provenance.py
```

Do not reacquire these consumed families as a fresh test. Future independent
evaluations need a separate frozen source panel and adequate supported coverage.
