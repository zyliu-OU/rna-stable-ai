# STRAND reference reproduction — 2026-10-18

The released numerical fit is reproduced under pinned R 4.5.3 / pls 2.8.5 /
jsonlite 2.0.0. nLuc training-only LOO PRESS selects **two** components with ALO,
**one** without ALO. This is reference-data reproduction, not new independent
validation or approval for expression candidate design.

Canonical run: `results/strand_reference_reproduction_runs/20261019T042427.196161Z/`.
[Protocol](../configs/strand_reference_reproduction_v1_2026-10-18.json),
[driver](../scripts/reproduce_strand_reference.py),
[R numerical reproduction](../scripts/reproduce_strand_reference.R),
[reference scorer](../src/rnastable/strand_reference.py).

The upstream author commit is `ea9e7de635e7cf4053c676c495b8e65717369206`.
The pinned source manifest is
`results/four_component_source_runs/20261019T040820.389955Z/manifest.json`.
Selected exact upstream numerical blocks (Figure_Scripts_1.R lines 610–613,
631–635, 678–681 and 699–703) execute alongside the reproduction; native
coefficients and selected eGFP predictions have zero difference.

## Numerical replay and coefficient export

Two fresh full fits produce identical component models, LOO PRESS and prediction
CSVs. Python feature extraction differs from R by at most 4.663e-15, and raw-unit
coefficient predictions differ by at most 5.330e-15. Saved RDS inference replay
and cached LOO outputs agree with saved predictions within 5.552e-15. The
**42-artifact** manifest and **91 reference identities** verify successfully.
[Replay and corruption check log](strand-reference-replay-checks-2026-10-18.log).

`pls::coef` exports slopes for scaled predictor inputs. The export divides each
slope by `fit$scale` to accept raw-unit values, while retaining the intercept.
The selected reference equation is:

```text
predicted half-life [h] = -0.16879280662927765
  - 0.7979700541988914 * energy_per_length [kcal/mol/nt]
  + 0.02653795111985797 * GC [percent]
  - 1.0239404489087613 * AUP [fraction]
  - 0.016562821266091512 * ALO [natural log odds]
```

This equation is verified on released features only. The adapter rejects
RNAfold/unknown feature provenance, altered sequence identities and altered
feature values outside the frozen inventory. Raw coefficients, scales, means
and all component counts are retained in `fit/r_models.json`; R objects in
`fit/with_alo_model.rds` and `fit/without_alo_model.rds`; input identities in
`reference_inventory.json`; selected export in `reference_model.json`; reference
predictions in `python_reference_predictions.json` and `fit/r_predictions.csv`.

Summary SHA-256: `45c676301131bd5c66d88b0a81e8df879068ecc14214115e4e6bdf3ab9935669`.
Selected model SHA-256: `660d07587f0c906fa3eb3663ee9ca8ccb4affaac541d67b85bd434da5018d354`.

## Reference results and limitations

All **69** supplied nLuc rows are used for fitting, in supplied order. eGFP has
**13** rows from the supplied validation CSV. Nine other rows in that CSV are
MEV and are reported separately as exploratory evidence; they are not the
separate later-figure MEV dataset. None is newly independent evidence for this
project. Selection uses nLuc training outcomes only, never eGFP/MEV performance.

| Cohort | Arm | Components | N | RMSE h | MAE h | R² |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| train | without_alo | 1 | 69 | 0.282382921 | 0.236402186 | 0.311919153 |
| train | with_alo | 2 | 69 | 0.280334209 | 0.230370897 | 0.321867104 |
| train_loo | without_alo | 1 | 69 | 0.292920102 | 0.244732121 | 0.259609272 |
| train_loo | with_alo | 2 | 69 | 0.297497329 | 0.242988037 | 0.236289506 |
| egfp | without_alo | 1 | 13 | 0.217427967 | 0.177115445 | 0.349878487 |
| egfp | with_alo | 2 | 13 | 0.189321885 | 0.165062754 | 0.507092566 |
| mev_exploratory | without_alo | 1 | 9 | 2.207148606 | 2.175971894 | -30.687470535 |
| mev_exploratory | with_alo | 2 | 9 | 2.187611339 | 2.155888927 | -30.128970262 |

The ALO variant improves this eGFP reference result, while its selected nLuc LOO
RMSE is slightly worse than the selected no-ALO control. Both models transfer
poorly to the nine exploratory MEV rows. No broad generalization or universal
ALO advantage is inferred. Selection used these LOO scores, so they are not a
nested estimate of the complete model-selection procedure. Displayed training
fits in the author script use one component with ALO and three without; those
variants and every component count remain in the artifacts rather than being
silently replaced by the selected models. No neural training or checkpoint
promotion occurred.

## Feature extraction audit

The [paper methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC13264031/) identify
LinearPartition as the source of structural features and positional pairing
probabilities; RNAfold is used for visualization. They report R 4.4.0 for
regression, but do not pin the LinearPartition version/beam/parameterization or
historical pls build in the inspected material. Archived article XML:
`results/strand_methods_source_runs/20261019T042128.056915Z/article.xml`, with
source URL/hash in adjacent `manifest.json`. Our numerical reproduction uses
recorded R 4.5.3; it does not claim an identical historical environment.

Six sequences were fixed before folding: first/middle/last nLuc and eGFP rows,
928 and 1,215 nt respectively. Both MFE and ensemble-energy substitutions were
compared diagnostically, using 37 °C Turner2004 settings and unchanged positional
probability extraction from the earlier integration worker. Full feature deltas,
uncalibrated arithmetic outputs and raw folds are in `rnafold_compatibility.json`
and `rnafold_{reference_name}.json`.

The largest absolute energy-per-nt gap is **0.020549576**
for MFE versus **0.000051666**
for ensemble energy. Largest absolute AUP gap is
**0.003090857**,
ALO gap **0.277052462**.
Tiny GC differences include rounding of released eGFP percentages. The maximum
absolute diagnostic selected-equation output change is
**0.006669322 h**
using ensemble energy. These six inputs support ensemble energy as the more
plausible energy mapping, but do not establish unchanged-model compatibility,
independent calibration, long-input support or biological benefit. Diagnostic
substitutions are explicitly not accepted stability predictions.

Original reference values outside [0,1] remain untouched; the released R bounding
rule is reproduced. New ViennaRNA probabilities retain the earlier strict checks.
Compatibility must be reviewed with a prespecified criterion or calibrated as a
separately named model before unrestricted scoring. RNAfold remains the selected
structural engine; no silent switch to LinearPartition was made.

## Verification and continuation

**36 focused tests passed in 1.69 s**, including the R-derived portable fixture,
reference-identity/provenance guards, and earlier integration/scope tests.
[Test record](strand-reference-focused-tests-2026-10-18.log). No full repository
suite or new independent biological validation was run.

```bash
cd /home/zyliu/Documents/rna-stable-ai
PYTHONPATH=src .venv/bin/python scripts/reproduce_strand_reference.py --verify-run results/strand_reference_reproduction_runs/20261019T042427.196161Z
PYTHONPATH=external/four_component_deps:src .venv/bin/python -m pytest -q tests/test_strand_reference.py tests/test_component_integration.py tests/test_discrete_bo.py tests/test_project_scope.py tests/test_stage2_scope_audit.py
# Fresh reproduction: two R fits plus six fixed-input folds.
PYTHONPATH=src .venv/bin/python scripts/reproduce_strand_reference.py
```

Next: RiboNN isolated pretrained inference, plus an explicit original-feature
compatibility/calibration decision for the RNAfold-to-STRAND interface.
Stage 2 remains open; Stage 3 and expression candidate design remain queued.
No publication or README edit was made.
