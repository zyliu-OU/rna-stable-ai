# STRAND reference coefficient fixture

Generated from the actual R `pls` reproduction run
`results/strand_reference_reproduction_runs/20261019T042427.196161Z/`.
The fixture contains selected two-component raw-unit coefficients, three
released-reference feature vectors and their R predictions. No sequences or
weights are included. Three already released half-life values remain as
context; the replay function does not use those target values.

Source: `S00NYI/BITS_STRAND`, commit
`ea9e7de635e7cf4053c676c495b8e65717369206`, MIT repository license, pinned
manifest `results/four_component_source_runs/20261019T040820.389955Z/manifest.json`.
Numerical source blocks: Figure_Scripts_1.R lines 678–681 and 699–703.
Execution environment: R 4.5.3, pls 2.8.5, jsonlite 2.0.0, kernelpls, scaled
predictors, full 69-record nLuc fit, components selected by nLuc LOO PRESS.

The expected values come from R `predict.mvr`, before Python replay.
R `coef.mvr` slopes were divided by `fit$scale` for use with raw input features;
the intercept remains the coefficient export's intercept. Tests would fail if
that scaling were omitted or applied twice. GC inputs are percent, not fraction.

The example MEV row comes from the nine MEV entries of the supplied validation
CSV and is an exploratory arithmetic check. It is not claimed to reproduce the
separate MEV Figure 6 dataset or independently validate biological performance.
These are already released/exposed reference data. RNAfold features remain
incompatible with this reference-only scoring contract until reviewed/calibrated.
