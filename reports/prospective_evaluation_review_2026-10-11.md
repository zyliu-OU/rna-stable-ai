# RNA-StableAI prospective comparative evaluation — 2026-10-11

Workspace: `/home/zyliu/Documents/rna-stable-ai`.

## Source and annotation binding

The user completed the ten-file evidence download from a terminal with network
access. Successful retained evidence:
`results/prospective_evidence_runs/20261012T025400.354107Z`.
All files passed byte-hash and envelope verification. The original metadata panel
and model-seed-20261006 checkpoint/decoder settings remain unchanged.

Strict mapping checks found no known exposed PDB accession in the 38 TPP, 29 SAM
and 84 Purine mapping rows. Reported SAM/Purine clans CL00012/CL00123 differ from
the known exposed clans CL00113/CL00010/CL00003; TPP reports null clan membership.
These checks do not establish all unknown training-family or legacy-tool
independence. Sequence overlap uses the previously frozen symmetric heuristic.

All 15 selected sequences match their exact Stockholm alignment members after
the recorded uppercase/T-to-U normalization and gap removal. Complete consensus
contacts are mapped to sequence coordinates without deleting contacts. Rfam
WUSS letter pairs annotate pseudoknots, as documented in the
[Infernal guide](https://eddylab.org/infernal/Userguide.pdf). Those pairs are counted
but not flattened into a nested structure. The references are comparative
conserved-consensus annotations, not direct per-sequence experimental measurements.

| Family | Planned records | Supported references | Unsupported reason |
|---|---:|---:|---|
| TPP, RF00059 | 5 | 5 | None |
| SAM, RF00162 | 5 | 0 | Pseudoknots; some sequences also lack paired columns |
| Purine, RF00167 | 5 | 4 | One record lacks an annotated paired column |

No record is replaced using labels. Unsupported outcomes retain null metrics
rather than an imputed zero. The six-method comparison retains all 90 planned
record/method outcomes: 54 measured and 36 unsupported. Means below describe the
nine supported records, not all 15 references or all three families.

## Frozen comparison

Completed run:
`results/prospective_evaluation_runs/20261012T030338.012553Z`.
The final manifest was saved before predictions. All 15 records were registered
in a durable `test_started` event before any inference/native folding. The three
families are now consumed for future fresh-test planning, including the six
unsupported records. No model was fitted or selected from test scores.

| Method | Planned | Measured | Mean pair F1 | TPP F1, n=5 | Purine F1, n=4 |
|---|---:|---:|---:|---:|---:|
| Baseline | 15 | 9 | 0.1396 | 0.1365 | 0.1435 |
| Stack | 15 | 9 | 0.2319 | 0.1014 | 0.3949 |
| Helix | 15 | 9 | 0.3561 | 0.2828 | 0.4478 |
| ViennaRNA | 15 | 9 | 0.6065 | 0.5630 | 0.6609 |
| LinearFold | 15 | 9 | 0.6065 | 0.5630 | 0.6609 |
| All unpaired | 15 | 9 | 0.0000 | 0.0000 | 0.0000 |

Helix improves over the learned controls in this panel while remaining behind
the native folding controls. These small shared-family comparisons are
descriptive; they do not establish population-wide generalization, long-RNA
accuracy, retained biological function or experimental stability. No statistical
significance or model deployment claim is made.

## Execution and audit

All 18 planned native requests completed; zero outcomes remain unknown.
Known native wall time sums to 1.45624 seconds and includes subprocess startup.
Testing overlapped the run, so this is cost accounting, not an isolated speed
benchmark. Native requests are bound by manifest, exact sequence and request
parameters. Interrupted outcomes are retained and not automatically retried.

The completed audit verifies source/input/model hashes, all 27 learned-model
predictions, exact reference scores, all-unpaired controls, the test event and
native request identities/results. Audit creates no new native callback or fresh
test exposure. Later code changes can be audited against completed artifacts;
unfinished resumption rejects changed code/runtime bindings.

The original completed manifest and summary remain unchanged. Additional request
accounting and model replay were added after execution and are retained in
`reports/prospective-evaluation-audit-2026-10-11.log`; the original summary does
not gain a retroactive cost field. One new unit fixture initially omitted a
required native-energy value; its corrected regression passed. Earlier logs are
preserved. Final full-suite and focused test totals are in the versioned handoff.

## Remaining scientific work

Roadmap step 4 remains ongoing: unknown training-family and legacy-tool provenance
limits independence, and only two families have supported references here.
Use development cohorts for subsequent model changes; do not reuse these outcomes
as fresh tests or tune the evaluated model/decoder on them. Reserve additional
families under a new exposure-aware protocol before another fresh test.
Pseudoknot-capable evaluation, longer biological annotations and experimental
stability/function validation remain pending.
