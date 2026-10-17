# RNA-StableAI Step 2: top-64 score-offset diagnostic

Date: 2026-10-17 (America/Los_Angeles)  
Workspace: `/home/zyliu/Documents/rna-stable-ai`

The matched candidate-budget study found that only about 44% of the legal gold pairs present among top-64 candidates appeared in decoded structures. To probe the learned score and pair-count tradeoff, this study froze four additive logit offsets (-0.5, 0, +0.5, +1.0) before evaluation. It used the same six fixed-final checkpoints and 11-reference label-informed development cohort. Each checkpoint and RNA was scored once to retain its top-64 **positive** legal candidates; the same exact sparse decoder then received those fixed pairs with each offset added to its logits. No negative-scored pairs were introduced by a positive offset.

| Arm | Mean pair F1, -0.5 | Mean pair F1, 0 | Mean pair F1, +0.5 | Mean pair F1, +1.0 |
| --- | ---: | ---: | ---: | ---: |
| Control, 88 records | 0.2623 | 0.2889 | 0.2967 | 0.2842 |
| Extended, 105 records | 0.3068 | 0.3123 | 0.3151 | 0.3189 |

At +0.5, control mean F1 increased by 0.0078 over zero offset. At +1.0, extended mean F1 increased by 0.0066. The best offset was not uniform across checkpoints: control seed 7 preferred +0.5, control seed 1729 barely changed at +0.5, and extended seed 7 preferred zero. The two other extended checkpoints improved at +1.0. Positive offsets increased total predicted pairs across three seeds: control 21,045 at zero to 21,790 at +0.5; extended 23,128 at zero to 24,277 at +1.0. The corresponding shared gold pairs rose from 6,282 to 6,531 and from 7,050 to 7,352. This is a development diagnostic, not a selected production calibration.

The zero-offset structures exactly matched the prior top-64 frozen predictions in all six components. Process peak RSS was 721,024 KiB. Decoder times and all per-record scores are in the run summaries. The label-informed panel is small and related within families; the 17 added bpRNA training records still lack resolved family provenance. The native controls remain higher on this panel (0.4742 LinearFold and 0.4499 ViennaRNA mean pair F1). No independent validation, biological outcome, model-default change, or checkpoint promotion follows from these results.

Canonical artifacts:

- Protocol: `results/long_score_offset_protocol_runs/20261017T184132.522583Z/manifest.json`
- Run: `results/long_score_offset_runs/20261017T184134.981159Z/summary.json`
- Driver: `scripts/study_long_score_offset.py`

Verification: source and code hashes, all six zero-offset structure sets, each per-record pair score, and aggregate pair counts passed replay. Six focused sampled-pair and long-exact-decoder tests passed; the driver compiled.

Next: investigate candidate ranking and training objectives using development evidence while resolving family provenance and building an independent long-reference panel. Do not choose a calibration value using this panel for a generalization claim.
