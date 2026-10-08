# Expanded candidate diagnostics

Reference-informed diagnostic on already exposed development records. Oracle candidate upper bounds are not predictions. No fitting, fresh test or threshold selection.

| Method | Group | Records | Nonpositive reference pairs | Top-k removed | Decoder omitted | Oracle candidate F1 bound | Decoded F1 |
|---|---|---:|---:|---:|---:|---:|---:|
| trained_expanded_sparse | all | 47 | 1193 | 222 | 762 | 0.7574771609091185 | 0.20857850721519425 |
| trained_expanded_sparse | PDB-derived annotation | 12 | 7 | 2 | 46 | 0.9785714285714286 | 0.5622727175358754 |
| trained_expanded_sparse | Rfam comparative | 23 | 144 | 28 | 391 | 0.8402134434751342 | 0.10762048692752478 |
| trained_expanded_sparse | CRW comparative | 12 | 1042 | 192 | 325 | 0.3778050183286114 | 0.04838716911254617 |
| trained_sampled_sparse | all | 47 | 990 | 385 | 806 | 0.6500046183577534 | 0.20172616105030025 |
| trained_sampled_sparse | PDB-derived annotation | 12 | 36 | 0 | 22 | 0.8359188197423492 | 0.5815512095117358 |
| trained_sampled_sparse | Rfam comparative | 23 | 353 | 3 | 230 | 0.599622848317183 | 0.07731531795060397 |
| trained_sampled_sparse | CRW comparative | 12 | 601 | 382 | 554 | 0.560655476217584 | 0.06035522852994927 |
