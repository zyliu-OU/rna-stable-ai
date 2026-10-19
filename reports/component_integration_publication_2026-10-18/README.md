# Four-component integration publication — October 18, 2026

This snapshot publishes adapter code, portable tests, exact component identities,
licenses and concise numerical evidence for **RNAfold + STRAND + RiboNN + BoTorch**.
Stage 2 remains open; cell-free calibration and expression candidate design remain
queued. Model defaults and historical studies are preserved.

- Fixed-input RNAfold MFE/partition-function checks reached 2,999 nt; BoTorch toy
  selection and resume checks passed. These establish software mechanics only.
- STRAND's released-reference PLS fit was reproduced; training-only LOO PRESS
  selected two components. The original features use **LinearPartition**, so
  unrestricted RNAfold-to-STRAND substitution remains unvalidated.
- RiboNN human inference loaded 50 checkpoints over ten folds. Two fresh CPU
  processes yielded byte-identical raw files for 70 rows and all 78 tasks. The
  named HEK293T score is on its released target scale, without cell-free meaning.

MANIFEST.json records original host paths and SHA-256 for 16 byte-identical
summary/protocol/model-metadata/environment-lock copies. The STRAND coefficient
export is reference-only; no RiboNN checkpoint bytes are included. The full local
run artifacts, source CSVs, article XML, encoded inputs, weights and installed
runtimes are not bundled. Do not pass these concise copies to drivers expecting
full local run directories. A fresh clone can run the portable tests after
installing the required dependencies. Complete refitting/inference requires
acquiring the pinned sources/weights and a separately versioned protocol with
its newly created local paths, plus the appropriate isolated runtime.

Original third-party source and weight licenses are under docs/third_party.
RiboNN's weights restrict academic research/noncommercial use and are not
redistributed here. See the [integration guide](../../docs/four_component_integration_2026-10-18.md),
[STRAND review](../strand_reference_reproduction_review_2026-10-18.md),
[RiboNN review](../ribonn_fixed_inference_review_2026-10-18.md) and
[development handoff V12](../RNA-StableAI_HANDOFF_2026-10-18_V12.md).

Publication verification: **91 focused tests passed in 3.43 s** in the isolated
checkout using retained dependencies. See the [test log](../component-integration-publication-focused-tests-2026-10-18.log).

The user explicitly requested replacing the README's old attachment diagram with
`diagram_10182026.png`. The repository now contains the exact supplied PNG;
other upstream README content and repository image assets were preserved.
