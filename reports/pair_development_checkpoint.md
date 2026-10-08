# Pair-scoring and family-planning development checkpoint

Project: RNA-StableAI
Date: 2026-10-05 (America/Los_Angeles)
Absolute workspace: `/home/zyliu/Documents/rna-stable-ai`

## Completed development

Added a symmetric all-pair scoring head using convolutional sequence features,
learned endpoint terms, projected affinities and distance terms. A deterministic
interval dynamic program maximizes summed positive logits over canonical nested
pairs with at least three enclosed nucleotides. Unpaired sites score zero. Scores
have no physical-energy units. The pair matrix uses quadratic memory and decoding
uses cubic work; the implementation is explicitly limited to 256 nt.

Training supervises legal upper-triangle pairs once. The square-root
negative/positive loss weight is calculated from training data only. Unsupported
reference contacts are counted explicitly (zero in this development run).

Added an explicit family-plan validator and replay audit. Every reference needs a
sequence-bound family assignment and source. Family lists must be disjoint; shared
accessions and exact/similar sequences across splits reject the plan. Proposed test
records are checked against an exposure ledger, including all 69 prior project-pilot
records added automatically by the CLI. Known exposed family IDs are also rejected
for a proposed test. The sequence heuristic is symmetric SequenceMatcher >=0.8,
not an alignment identity measurement. Valid plans freeze both supplied inputs and
the effective exposure ledger. Broad RNA types are not inferred as families.

No real family-separated plan was created: verified family assignments and a fresh
cohort are still unavailable. Synthetic tests establish the planner's behavior.

## Development run

Run: `/home/zyliu/Documents/rna-stable-ai/results/pair_development_runs/20261006T013412.256466Z`.
A prospective manifest froze the 41 training / 12 validation snapshots,
configuration and code hashes before fitting. Ten CPU epochs, two threads,
seed 20261006; 11,697 model parameters. Validation selected **epoch 10**.

| Model | Development-validation pair F1 |
|---|---:|
| Trained pair model | 0.5411434849 |
| Initial pair model | 0.1487670826 |

These are previously used development-validation inputs. No old or new test cohort
was evaluated with the new pair model. This is not independent test accuracy or a
held-out comparison with the previous CNN. No native folding was rerun.

## Verification

**257 tests passed**, including 24 new pair/family tests, recorded in
`reports/tests-pair-development-checkpoint.xml`.

Tests cover global-decoder optimality against exhaustive enumeration, a nested
solution beating a largest-pair greedy choice, canonical/contact/bound constraints,
finite symmetric differentiable scores, unsupported-contact accounting, actual
parameter updates, family/hash/provenance/duplicate/overlap/exposure rejection,
case-insensitive accession matching, inability to bypass known exposures with an
empty supplied ledger, immutable-plan replay after live input removal and ledger
corruption rejection. Saved-run checkpoint inference and hash-corruption guards pass.

The pair-run audit independently reloads frozen data/checkpoints, verifies development
split separation and training-only pair counts/weight, epoch ledger and validation
selection, reproduces all 24 checkpoint predictions, and audits retained scores/exports.
The original experimental pilot summary and long-study summary/manifest hashes match
previous values. Their measured artifacts remain preserved. Old-pilot regression
audits may replay old checkpoints for integrity; they do not evaluate this new model
on the old test or use those scores for fitting/tuning.

Source/status backups: `reports/source_backups/20261006T013114.578273Z/`.
Commands/output: `reports/commands.jsonl`. No dependency/system changes or GitHub push.

## Continue

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/verify_pair_development.py
.venv/bin/python -m pytest -q
```

A new family-separated study first requires verified family assignments and a fresh
cohort. README documents reference/assignment/plan/exposure schemas and commands.
Reserve the new test before training or hyperparameter tuning. Do not use this
validation F1 as a new test claim or tune against the already observed 16-record test.

Algorithm context: [Nussinov and Jacobson](https://pubmed.ncbi.nlm.nih.gov/6161375/).
Loss API: [PyTorch BCEWithLogitsLoss](https://docs.pytorch.org/docs/2.14/generated/torch.nn.BCEWithLogitsLoss.html).
