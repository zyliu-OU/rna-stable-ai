# Frozen-checkpoint pair-penalty development

All checkpoints and penalties use the same exposed validation cohort; posthoc selection is development tuning, not independent accuracy.
Checkpoints were originally selected at zero penalty; this is not joint epoch-and-penalty selection and does not retrain models.
Uniform nonnegative penalties alter logit objectives over the original top-16 retained pools. Scores are not native folding energy.
Tie policy prefers the smallest penalty. Inference remains zero penalty unless explicitly requested.
Three seeds share the same biological annotations; no family/clan independence or generalization claim.

| Seed | Head | Zero-penalty F1 | Selected penalty | Selected development F1 |
|---:|---|---:|---:|---:|
| 20261006 | baseline | 0.38849854106861975 | 0.5 | 0.39792870118417956 |
| 20261006 | stack | 0.423379568067344 | 0 | 0.423379568067344 |
| 20261006 | helix | 0.5244233333981245 | 0 | 0.5244233333981245 |
| 20261007 | baseline | 0.37627740637695983 | 0 | 0.37627740637695983 |
| 20261007 | stack | 0.40101251568271834 | 0 | 0.40101251568271834 |
| 20261007 | helix | 0.4950770012765886 | 0 | 0.4950770012765886 |
| 20261008 | baseline | 0.3932529810620267 | 0 | 0.3932529810620267 |
| 20261008 | stack | 0.4055479388678194 | 0 | 0.4055479388678194 |
| 20261008 | helix | 0.49106862354687564 | 0 | 0.49106862354687564 |
