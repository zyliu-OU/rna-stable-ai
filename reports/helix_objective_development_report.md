# Matched-seed helix training-objective development

Development-only comparison on the same89 training/47 validation records; no independent accuracy claim.
Three seeds share biological labels. Original BCE checkpoints are reused; structured models are newly trained from matched initializations.
Both objectives independently select epoch by development F1, then lower full weighted validation BCE, then earliest epoch.
Pruned loss-augmented training retains supported gold; inference uses unaugmented positive top16 pools. No full-graph structured optimality claim.
Training losses have different units/scales and are not directly comparable; logits are not folding energies or stability measurements.
No prospective inputs, native folds or inference default changes. Resource measurements are bounded CPU observations.

| Seed | Status | BCE epoch | BCE F1 | Structured epoch | Structured F1 | Delta |
|---:|---|---:|---:|---:|---:|---:|
| 20261006 | ok | 5 | 0.5244233333981245 | 3 | 0.429375287402658 | -0.09504804599546651 |
| 20261007 | ok | 4 | 0.4950770012765886 | 7 | 0.4173918969697274 | -0.07768510430686121 |
| 20261008 | ok | 3 | 0.49106862354687564 | 4 | 0.4468246411197161 | -0.044243982427159545 |
