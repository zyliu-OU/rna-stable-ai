# Fixed-checkpoint candidate-budget development study

The declared grid is 16/32/64 positive partners per right endpoint. Evaluate
all nine previously selected baseline/stack/helix checkpoints (seeds 20261006,
20261007, 20261008) and every one of the frozen 47 validation records. This
produces 1269 outcomes. The original checkpoint epochs were chosen with top-16;
this comparison is posthoc development tuning, not joint epoch/budget selection
or independent biological testing. The source study and development diagnostic
are described in [CANDIDATE_DEVELOPMENT.md](CANDIDATE_DEVELOPMENT.md).

```bash
.venv/bin/python scripts/compare_candidate_budgets.py
.venv/bin/python scripts/compare_candidate_budgets.py --verify
```

Before model scoring, the driver checks the original source study, freezes
source/checkpoint/code hashes, cohort and budget grid in a unique run directory,
and records validation exposure. It leaves trained checkpoints and inference
defaults unchanged and reads no prospective panel. The decoder is the existing
exact noncrossing maximum-logit decoder, bounded to 1024 nt and 64 candidates per
right endpoint; source block sizes stay fixed. Torch uses two CPU threads.

For each checkpoint-record, evaluate budgets in ascending order. Score each pool
independently; enforce nested candidate sets and nondecreasing exact objective.
All 423 top-16 structures must exactly equal the original saved structures.
Partition all reference contacts using the existing diagnostic, including illegal
or nonpositive reference contacts in the denominator. Report precision, recall,
F1, false positives and retained gold coverage for every outcome. A larger pool
can retain more gold contacts and still reduce F1 by introducing incorrect
competitors. Gold-contact score diagnostics run outside the timed pool/decoder
sections.

Retain source, length and reference-kind slices, including empty slices with
zero counts and null mean F1. Report per-record F1 differences versus top-16 and
counts of improved, regressed and unchanged records within each checkpoint/slice.
Contact totals sum contacts; F1 averages records. Initialization seeds share the
same labels and do not estimate independent biological uncertainty.

Measure pool-construction and decoder wall times separately. These are single
CPU observations, affected by warmup, fixed budget order and concurrent host
work; do not interpret differences as a statistically established speed gain.
Record candidate-array bytes, DP-array bytes and peak score-tile elements.
Candidate/DP bytes exclude Python containers and other temporaries; score-tile
elements exclude pair-context feature tensors. They are not total process memory.
Aggregates sum times and report maximum per-outcome array/tile costs.

Write partial outcomes after each record. On a scoring/decoding/invariant failure,
flush all completed outcomes and a separate failed planned identity with its
error; do not publish a complete summary. Start a new immutable run rather than
retrying into the earlier run. Successful runs preserve all outcomes with hashes
and publish a summary, CSV and report. Replay checks source/code/input/exposure
bindings, recomputes all predictions, contact partitions and array costs, and
rebuilds all aggregates. Historical timings are hash-bound and validated as
finite nonnegative observations; they are not expected to match fresh timings.
Replay records no new exposure and performs no native folding.

Any subsequent model or decoder development must remain development-only and
reserve a new screened source panel before testing. Previously consumed panels
cannot become fresh tests through rerunning or changing formats.
