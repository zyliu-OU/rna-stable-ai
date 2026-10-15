# RNA-StableAI candidate development review — 2026-10-11

Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Diagnostic run: `/home/zyliu/Documents/rna-stable-ai/results/candidate_development_runs/20261012T040208.111315Z`.

Added a complete reference-contact partition to the existing nine-checkpoint,
47-record development comparison. The driver checks the retained source study,
checkpoint identities and hashes, records a frozen manifest and validation exposure
before scoring, and publishes all 423 outcomes. Verification recomputes the same
partition from bound sources without native folds or new exposure. No prospective
panel was loaded or tuned against. Existing model checkpoints and decoding remain
unchanged. The protocol is `docs/CANDIDATE_DEVELOPMENT.md`.

For seed 20261006 helix, all 2351 development reference contacts partition as:

| Outcome | Contacts |
|---|---:|
| Excluded by chemistry/minimum distance | 7 |
| Legal but nonpositive score | 30 |
| Positive but absent from sparse pool | 402 |
| Retained but absent from saved decoding | 841 |
| Recovered | 1071 |

The saved prediction contains 1502 false-positive contacts. Its original mean
record F1 remains 0.5244. Counts sum contacts while F1 averages records; these
are different weighting conventions. Retained-but-unselected contacts can lose
against higher-scoring competing pairs under the correct exact decoder, so the
partition does not establish a decoding bug.

Across initialization seeds, baseline prunes 1200–1305 positive reference pairs,
stack 731–1192 and helix 402–757. Each checkpoint sees the same 2351 contacts;
these seed ranges are descriptive, not independent biological uncertainty. The
47-record development cohort includes 1621 contacts from 12 CRW records, so
contact totals are strongly influenced by longer records. All provenance slices
and all seeds remain in the published output.

A subsequent study should declare candidate budgets 16/32/64 for all nine frozen
checkpoints and all 47 development records before new decoding. Compare coverage,
record F1 and score/decoder runtime and storage; do not change defaults based on
this diagnostic alone. Larger pools can introduce stronger incorrect competitors,
so improved retention does not guarantee improved F1. Checkpoints were originally
selected with top-16; budget tuning is posthoc development, not joint epoch/budget
selection or fresh test evidence. Consumed prospective panels remain excluded.

Verification: eight new partition/input tests and six existing slice tests pass
(14 total). Replay of all 423 outcomes passes. Ruff, compileall and whitespace
checks pass. Full-suite verification is recorded in the versioned handoff.

Logs: `reports/candidate-development-2026-10-11.log`,
`reports/candidate-development-audit-2026-10-11.log`,
`reports/candidate-development-focused-2026-10-11.log`,
`reports/candidate-development-full-suite-2026-10-11.log`.
No Git index change, commit, push or publication occurred.
