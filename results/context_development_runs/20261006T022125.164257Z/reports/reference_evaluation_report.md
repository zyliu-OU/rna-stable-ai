# Supplied-reference structure evaluation

Dataset: `reused_context_validation`

Reference labels and sources are caller declarations. This report scores supplied structures.

| Method | Reference kind | Planned | Measured | Missing | Failed | Mean pair F1 |
|---|---|---:|---:|---:|---:|---:|
| trained_context | computational | 23 | 23 | 0 | 0 | 0.09302419405880484 |
| trained_context | experimental | 12 | 12 | 0 | 0 | 0.5790404332509596 |
| untrained_context | computational | 23 | 23 | 0 | 0 | 0.08216547582437835 |
| untrained_context | experimental | 12 | 12 | 0 | 0 | 0.21539571539571542 |

A mean is over measured references only; compare coverage before comparing means.
Two all-unpaired structures score one; if only one structure has pairs, pair F1 is zero.

Reference kinds and source descriptions are supplied by the caller, not independently verified.
Only complete, pseudoknot-free dot-bracket structures using .() are supported; no projection or imputation.
Metrics use exact base-pair coordinates; no alignment, offset tolerance or sequence mutation is permitted.
Missing and failed predictions stay in planned denominators and have no metric values.
Means describe measured inputs only, with one vote per reference within each method and reference kind.
Agreement with supplied structures does not measure biological stability or experimental fitness.
No folding, optimization, neural training or dataset download is performed.
