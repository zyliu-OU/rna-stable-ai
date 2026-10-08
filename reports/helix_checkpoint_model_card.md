# RNA-StableAI local-helix checkpoint model card

## Intended use and evidence boundary

The checkpoint is a development-only RNA pair scorer. It supports structure-prediction experiments on supplied sequences and ranks constrained proposal pools before native tools evaluate them. It has no validated biological-stability, retained-function or independent-generalization claim. Pair logits are scores, not folding energies or calibrated contact probabilities.

The canonical source is `results/helix_comparative_development_summary.json`, retaining its immutable run directory and best checkpoint. It uses model seed20261006. The matched head study additionally retains independently initialized model seeds20261007 and20261008 on the same already exposed records. None is an independent biological replicate or a new test set.

## Data and selection

Training contains89 processed development annotations, lengths20–552nt. Reused validation contains47 annotations, lengths21–543nt:12 PDB-derived processed records,23 Rfam-comparative records and12 CRW-comparative records. Dataset source tags distinguish experimental-derived and computational annotations; no new experimental pair measurements were collected. Sequence/accession filtering does not establish family/clan independence.

Training scores all legal canonical pairs with endpoint distance at least4, using full weighted BCE, ten epochs and Adam at0.001. The positive weight derives only from the training population:1,180,545 negatives/4,462 positives =264.5775. Unsupported annotated contacts remain excluded from supervision and recorded in its denominator metadata. Checkpoint selection maximizes mean pair F1 on the reused validation cohort, with lower full validation BCE as tie break.

The seed20261006 checkpoint was selected at epoch5 with reused-validation F1=0.5244. Across three matched model seeds, helix F1 was0.5244,0.4951,0.4911. Absolute source-slice performance remains uneven: mean CRW F1 across those seeds was0.3326, despite an increase over the baseline. Five of47 records regressed relative to baseline when averaging predictions across seeds. Complete results remain in `development_slices_report.md`.

## Architecture and scoring

A nucleotide embedding and dilated convolutional encoder have91nt receptive field. Global pair scores combine endpoint/projected embeddings and a learned distance network. The helix head adds eight sequence-only indicators: prefix-contiguous canonical support at outer/inner offsets1,2,3, GC pair and GU pair. Weights start at zero with the matched base initialization. No reference annotation enters these sequence-only features at inference.

All-distance inference scores in64-column tiles and retains at most16 positive legal left partners per right endpoint. Scoring still requires quadratic work. The frozen exact sparse decoder maximizes summed positive logits over those retained candidates with nested/noncrossing and endpoint constraints. It is exact for that candidate graph, not for all legal pairs or biological agreement.

## Bounds and explicit overrides

Default exact sparse inference rejects sequences longer than1,024nt before output. Explicit greedy/refined overrides support up to10,000nt with approximate decoding. The input plan permits at most10 records and20,000nt total. Synthetic resource runs show executable scoring/decoding at long lengths; they do not demonstrate biological accuracy beyond the observed annotation lengths.

`--pair-penalty` accepts an explicit0..8 logit offset, with default0 preserving existing decoding. The posthoc reused-development grid selected0 for every helix checkpoint. Penalties are not calibrated physical energies and were not jointly optimized with epoch selection.

```bash
.venv/bin/python scripts/predict_context.py --source-summary results/helix_comparative_development_summary.json --fasta YOUR_INPUT.fasta
.venv/bin/python scripts/predict_context.py --source-summary results/helix_comparative_development_summary.json --fasta YOUR_LONG_INPUT.fasta --decoder refined
.venv/bin/python scripts/verify_helix_comparative_development.py
.venv/bin/python scripts/run_pair_head_development_study.py --verify
.venv/bin/python scripts/analyze_development_slices.py --verify
.venv/bin/python scripts/run_helix_scalability.py --verify
```

## Sampled objective variant

The population-sampled variant keeps all positive contacts and a uniform subset of negatives. Negative losses receive inverse inclusion weighting and the positive weight still comes from the full training population. Its loss/gradient are unbiased over draws; each actual fit reuses one fixed draw across epochs. Primary sampled-array byte counts exclude API private copies, model, optimizer and other allocations. Full validation labels and the same exact decoder remain in use.

Three draw seeds with fixed model initialization gave reused F1=0.5251,0.5196,0.5245. Their source summaries live under `results/population_development_runs/.../sampling_SEED/summary.json`; inference accepts the component summary and records `trained_population_helix_sparse`. No draw is selected as independent evidence of biological performance.

## Native proposal use

The prior scorer uses compatible contacts from the native input template. Compatibility count is the first ranking key; mean compatible learned logits break ties. Native LinearFold decides search acceptance under the frozen mutation/energy rules. ViennaRNA final validation decides whether to retain a mutated sequence or the original. Protected positions and mutation limits are enforced and replayed. These constraints do not establish preserved biological function.

The native studies use previously exposed synthetic sequences and matched planned fold budgets. Their code and checkpoints are frozen, interrupted request costs stay unknown, and failed requests stay in denominators. The helix studies explicitly allow300-second Vienna final validation; the older stack study's30-second10,000nt timeouts remain preserved alongside a separately budgeted300-second extension. Results are descriptive native-energy measurements. Repeated controls and checkpoint seeds add cost and share inputs.
