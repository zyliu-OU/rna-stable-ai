# Supplied-reference structure evaluation

Dataset: `pdb_processed_pilot_test`

Reference labels and sources are caller declarations. This report scores supplied structures.

| Method | Reference kind | Planned | Measured | Missing | Failed | Mean pair F1 |
|---|---|---:|---:|---:|---:|---:|
| LinearFold | experimental | 16 | 16 | 0 | 0 | 0.9437729912383568 |
| ViennaRNA | experimental | 16 | 16 | 0 | 0 | 0.9437729912383568 |
| all_unpaired | experimental | 16 | 16 | 0 | 0 | 0.0 |
| trained_cnn | experimental | 16 | 16 | 0 | 0 | 0.06746031746031746 |
| untrained_cnn | experimental | 16 | 16 | 0 | 0 | 0.013157894736842105 |

A mean is over measured references only; compare coverage before comparing means.
Two all-unpaired structures score one; if only one structure has pairs, pair F1 is zero.

Reference kinds and source descriptions are supplied by the caller, not independently verified.
Only complete, pseudoknot-free dot-bracket structures using .() are supported; no projection or imputation.
Metrics use exact base-pair coordinates; no alignment, offset tolerance or sequence mutation is permitted.
Missing and failed predictions stay in planned denominators and have no metric values.
Means describe measured inputs only, with one vote per reference within each method and reference kind.
Agreement with supplied structures does not measure biological stability or experimental fitness.
No folding, optimization, neural training or dataset download is performed.
