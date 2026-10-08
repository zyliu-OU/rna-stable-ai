# Expanded development comparison

Run: `/home/zyliu/Documents/rna-stable-ai/results/expanded_comparison_runs/20261006T030945.216172Z`

Same exposed development cohort. One seed and validation-selected checkpoints; no generalization, assay, family independence or biological stability claim.

| Source group | Method | Planned | Measured | Failed | Missing | Mean pair F1 |
|---|---|---:|---:|---:|---:|---:|
| all | trained_expanded_sparse | 47 | 47 | 0 | 0 | 0.20857850721519425 |
| all | trained_sampled_sparse | 47 | 47 | 0 | 0 | 0.20172616105030025 |
| all | all_unpaired | 47 | 47 | 0 | 0 | 0.0 |
| all | ViennaRNA | 47 | 47 | 0 | 0 | 0.7177733468424221 |
| all | LinearFold | 47 | 47 | 0 | 0 | 0.7193873774786459 |
| PDB-derived annotation | trained_expanded_sparse | 12 | 12 | 0 | 0 | 0.5622727175358754 |
| PDB-derived annotation | trained_sampled_sparse | 12 | 12 | 0 | 0 | 0.5815512095117358 |
| PDB-derived annotation | all_unpaired | 12 | 12 | 0 | 0 | 0.0 |
| PDB-derived annotation | ViennaRNA | 12 | 12 | 0 | 0 | 0.9138701254026332 |
| PDB-derived annotation | LinearFold | 12 | 12 | 0 | 0 | 0.9138701254026332 |
| Rfam comparative | trained_expanded_sparse | 23 | 23 | 0 | 0 | 0.10762048692752478 |
| Rfam comparative | trained_sampled_sparse | 23 | 23 | 0 | 0 | 0.07731531795060397 |
| Rfam comparative | all_unpaired | 23 | 23 | 0 | 0 | 0.0 |
| Rfam comparative | ViennaRNA | 23 | 23 | 0 | 0 | 0.6898054001587578 |
| Rfam comparative | LinearFold | 23 | 23 | 0 | 0 | 0.7038432351685264 |
| CRW comparative | trained_expanded_sparse | 12 | 12 | 0 | 0 | 0.04838716911254617 |
| CRW comparative | trained_sampled_sparse | 12 | 12 | 0 | 0 | 0.06035522852994927 |
| CRW comparative | all_unpaired | 12 | 12 | 0 | 0 | 0.0 |
| CRW comparative | ViennaRNA | 12 | 12 | 0 | 0 | 0.5752817994259013 |
| CRW comparative | LinearFold | 12 | 12 | 0 | 0 | 0.5546975689823873 |
