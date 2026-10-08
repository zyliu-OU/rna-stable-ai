# Supplied-reference structure evaluation

Dataset: `rf00017_context_trial_test`

Reference labels and sources are caller declarations. This report scores supplied structures.

| Method | Reference kind | Planned | Measured | Missing | Failed | Mean pair F1 |
|---|---|---:|---:|---:|---:|---:|
| LinearFold | computational | 12 | 12 | 0 | 0 | 0.47994718111707635 |
| ViennaRNA | computational | 12 | 12 | 0 | 0 | 0.4780596903544601 |
| all_unpaired | computational | 12 | 12 | 0 | 0 | 0.0 |
| trained_context | computational | 12 | 12 | 0 | 0 | 0.003643045940328309 |
| untrained_context | computational | 12 | 12 | 0 | 0 | 0.0047127108236874595 |

A mean is over measured references only; compare coverage before comparing means.
Two all-unpaired structures score one; if only one structure has pairs, pair F1 is zero.

Reference kinds and source descriptions are supplied by the caller, not independently verified.
Only complete, pseudoknot-free dot-bracket structures using .() are supported; no projection or imputation.
Metrics use exact base-pair coordinates; no alignment, offset tolerance or sequence mutation is permitted.
Missing and failed predictions stay in planned denominators and have no metric values.
Means describe measured inputs only, with one vote per reference within each method and reference kind.
Agreement with supplied structures does not measure biological stability or experimental fitness.
No folding, optimization, neural training or dataset download is performed.
