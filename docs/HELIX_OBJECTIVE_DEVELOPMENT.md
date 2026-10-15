# Matched helix training-objective development

Declare one comparison: existing full weighted BCE versus the existing pruned
margin-rescaled hinge plus 0.1 times weighted BCE. Use the helix architecture and
seeds 20261006/20261007/20261008, the original frozen 89 training and 47 validation
records, Adam at 0.001, ten epochs, identical model dimensions and initial states,
and unaugmented exact top-16 inference. This declaration precedes new training.
No new objective hyperparameter search or test data is included.

```bash
.venv/bin/python scripts/run_helix_objective_development.py
.venv/bin/python scripts/run_helix_objective_development.py --verify
```

The reference BCE fits remain their original immutable runs. The new driver
verifies their cohort/prediction/checkpoint bindings, freezes all compared
sources and code before launching any fit, and copies exact source snapshots
into unique component directories. Each component records training and validation
exposure before scoring. The same positive weight comes exclusively from full
canonical training-pair counts. Unsupported gold contacts remain excluded from
legal supervision and counted in validation references.

The structured loss uses top-16 augmented non-gold partners per right endpoint,
adds every supported gold pair to the training graph, uses margin 1, and divides
the hinge by max(1, supported gold contacts). It may retain at most 17 candidates
per endpoint. Gold labels and margin augmentation are confined to training.
Validation uses full weighted BCE and the unchanged inference decoder; there is
no validation-label augmentation of candidate pools. Compare independently
selected epochs for both objectives, using highest mean validation record F1,
then lowest full weighted validation BCE, then earliest epoch. This remains
reused-development selection, not independent biological evidence.

Three new fits each have a 600-second/8-GiB process bound and two Torch threads.
A durable attempt ledger precedes launch. Interrupted fits are not retried;
a fully written recovered summary retains unknown parent-process cost. Every
seed and all 141 paired record identities remain reported, with null new-model
metrics for incomplete fits. Empty source, length and reference-kind slices remain
visible. Capture paired record F1, false positives, selected epochs and measured
process wall time; do not compare the two training-loss scales as equivalent units.

Audit checks the deterministic full initial state against the original BCE
initialization, original initial predictions, exact snapshots, exposure events,
all training-step identities/label hashes, gold retention and loss arithmetic,
epoch loss means, the first loss-augmented graph anchor, retained checkpoint
hashes, full validation BCE and exact predictions. It verifies retained ledgers
and checkpoints without retraining every optimizer step. It does not certify
full-graph structured optimality or calibrated probabilities/energies.

New runs use `helix_objective_development` artifact names. Existing published
model pointers, inference defaults, native-fold studies and consumed prospective
panels remain preserved. Any independent evaluation needs a separately frozen,
screened source panel before testing. Repeated seeds share the same biological
labels; no independent uncertainty or stability/function claim is made.
