# RNA-StableAI prospective complete-pair evaluation review

Saved UTC: 2026-10-12T03:59:11.277885+00:00. Workspace: `/home/zyliu/Documents/rna-stable-ai`.

Roadmap step 4: first separately frozen complete-pair prospective evaluation completed and audited. These are comparative Rfam consensus contacts, not per-sequence experimental structures or stability measurements.

## Sources and fixed protocol

Protocol: `results/prospective_family_protocol_runs/20261012T035016.976142Z/manifest.json`. Acquisition: `/home/zyliu/Documents/rna-stable-ai/results/prospective_family_acquisition_runs/20261012T035150.817444Z`. Evidence: `/home/zyliu/Documents/rna-stable-ai/results/prospective_evidence_runs/20261012T035356.363981Z`.

RF00050/RF00174/RF00234 were declared before metadata outcomes; pair-set format, checkpoint seed 20261006, exact_sparse decoder, zero penalty, length bounds and five-record caps were frozen. All 13 evidence files verified. Of 598 seed entries, 597 were metadata candidates; one ambiguous Cobalamin sequence was excluded. The fixed selected panel contains 15 sequences of length 118–227 nt.

All selected sequences bind exactly. No known family/clan/PDB or heuristic sequence overlap was found. RF00174 clan CL00101 differs from known exposed clans; the other two have no assigned clan. PDB mapping counts are 8/9/21. This excludes known overlap only: 3104 of 3187 pre-evaluation exposure entries lack family identity, and legacy tool training provenance remains unresolved.

## Coverage and results

Eight complete references: four FMN, two Cobalamin, two glmS. Six have crossing contacts. Seven records lack an annotated paired column; no contacts were removed or replacements selected. All 15 records across six methods remain in 90 planned outcomes: 48 measured, 42 unsupported with null metrics. Native folding: 16 planned and completed requests; zero unknown outcomes.

| Method | Planned records | Measured records | Mean pair F1 |
|---|---:|---:|---:|
| LinearFold | 15 | 8 | 0.4977 |
| ViennaRNA | 15 | 8 | 0.5043 |
| all_unpaired | 15 | 8 | 0.0000 |
| baseline | 15 | 8 | 0.0925 |
| helix | 15 | 8 | 0.3082 |
| stack | 15 | 8 | 0.1870 |

Means weight the eight supported records equally, not the three families equally. Unsupported outcomes are excluded from the mean and retained in coverage. Helix leads the learned checkpoints overall, but stack leads helix on the two Cobalamin references. ViennaRNA and LinearFold lead all learned models overall. This is a small selected panel; no confidence or stability/function claim is made.

## Descriptive topology diagnostic

A reference-only interval dynamic program finds the largest noncrossing subset K of the N complete reference contacts. The recurrence skips the left endpoint or retains its reference partner and combines the inside and right intervals. This is an optimistic upper bound: it imposes no chemistry or loop constraints and permits a hypothetical prediction containing only these K true contacts. Its pair F1 ceiling against the unchanged full reference is 2K/(N+K). This diagnostic never changes the gold pairs or the reported model scores.

| Family | Complete records | Full contacts N per record | Maximum noncrossing K | Optimistic nested F1 ceiling |
|---|---:|---:|---:|---:|
| RF00050 | 4 | 32 | 28 | 0.9333 |
| RF00174 | 2 | 53 | 51 | 0.9808 |
| RF00234 | 2 | 38 | 38 | 1.0000 |

These ceilings show that crossing topology alone cannot explain the observed low learned-model scores. They do not establish a deployable predictor, a calibrated target, or justify choosing checkpoints or penalties from this panel. Future fitting and selection must use development-only data.

## Verification and next work

Completed evaluation: `/home/zyliu/Documents/rna-stable-ai/results/prospective_pair_evaluation_runs/20261012T035701.921281Z`. Binding: `/home/zyliu/Documents/rna-stable-ai/results/prospective_pair_binding_runs/20261012T035646.856700Z`. Audit passed exact reference-score replay, frozen model/input/code hashes, exposure event and native journal checks. Replay used no new native callbacks or test exposure. Logs: `reports/prospective-pair-binding-2026-10-11.log`, `reports/prospective-pair-evaluation-2026-10-11.log`, `reports/prospective-pair-evaluation-audit-2026-10-11.log`.

All three new families are now consumed for fresh-test planning, including unsupported records. Do not rerun this cohort as independent new evidence or tune from its labels. Original legacy evaluation artifacts and all checkpoints remain unchanged. No code changes or training occurred. The prior full suite remains 569 passing tests; source-freezing focused checks passed 18 tests in the previous continuation.

Next development must strengthen development-only training/validation and address biological coverage and provenance before another prospective round. Long biological annotation, experimental stability/function and validated release remain pending. No terminal downloads are currently needed to finish this evaluation. Changes remain local; no commit, push or publication.
