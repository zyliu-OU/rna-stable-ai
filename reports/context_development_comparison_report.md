# Context development comparison

Selected development run: `/home/zyliu/Documents/rna-stable-ai/results/context_development_runs/20261006T022313.519739Z`

Highest record-weighted reused-validation pair F1; ties prefer earlier run. This is development selection, not independent evaluation.

| Span | Weight power | Mean validation F1 | PDB-derived F1 | Comparative F1 | Excluded val contacts |
|---|---|---|---|---|---|
| 64 | 0.5 | 0.2177 | 0.6184 | 0.0087 | 208 |
| 128 | 0.5 | 0.2597 | 0.5790 | 0.0930 | 0 |
| 128 | 1.0 | 0.3074 | 0.6000 | 0.1548 | 0 |

Figure: `/home/zyliu/Documents/rna-stable-ai/results/context_comparison_runs/20261006T022454.836497Z/development_comparison.png`

Three configurations, one fixed seed, reused validation: no significance or fresh-test accuracy claim.
64-span and 128-span candidate coverage differs and is reported.
PDB-derived and comparative annotations are mixed; family identities of PDB records remain unresolved.
