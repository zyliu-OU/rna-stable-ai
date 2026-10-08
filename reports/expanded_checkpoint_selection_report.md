# Expanded checkpoint selection comparison

Same exposed47-record development cohort. Original models selected with refinement; posthoc exact uses that frozen checkpoint; exact-selected model uses exact decoding during validation selection. Structured training uses a pruned margin hinge plus0.1BCE; stack model adds2 sequence-only adjacent pair compatibility weights; both use exact validation selection. One seed; no new fitting, folding or test evaluation in this report.

Figure: `/home/zyliu/Documents/rna-stable-ai/results/expanded_selection_report_runs/20261006T033414.095031Z/development_selection.png`

| Group | Method | Planned | Measured | Failed | Missing | Mean pair F1 |
|---|---|---:|---:|---:|---:|---:|
| all | trained_expanded_sparse | 47 | 47 | 0 | 0 | 0.20857850721519425 |
| all | trained_sampled_sparse | 47 | 47 | 0 | 0 | 0.20172616105030025 |
| all | all_unpaired | 47 | 47 | 0 | 0 | 0.0 |
| all | ViennaRNA | 47 | 47 | 0 | 0 | 0.7177733468424221 |
| all | LinearFold | 47 | 47 | 0 | 0 | 0.7193873774786459 |
| all | trained_exact_sparse | 47 | 47 | 0 | 0 | 0.38849854106861975 |
| all | trained_expanded_sparse_posthoc_exact | 47 | 47 | 0 | 0 | 0.342535080846632 |
| all | trained_structured_sparse | 47 | 47 | 0 | 0 | 0.31288613175669067 |
| all | trained_stack_sparse | 47 | 47 | 0 | 0 | 0.423379568067344 |
| PDB-derived annotation | trained_expanded_sparse | 12 | 12 | 0 | 0 | 0.5622727175358754 |
| PDB-derived annotation | trained_sampled_sparse | 12 | 12 | 0 | 0 | 0.5815512095117358 |
| PDB-derived annotation | all_unpaired | 12 | 12 | 0 | 0 | 0.0 |
| PDB-derived annotation | ViennaRNA | 12 | 12 | 0 | 0 | 0.9138701254026332 |
| PDB-derived annotation | LinearFold | 12 | 12 | 0 | 0 | 0.9138701254026332 |
| PDB-derived annotation | trained_exact_sparse | 12 | 12 | 0 | 0 | 0.6933184668666521 |
| PDB-derived annotation | trained_expanded_sparse_posthoc_exact | 12 | 12 | 0 | 0 | 0.6806178026766262 |
| PDB-derived annotation | trained_structured_sparse | 12 | 12 | 0 | 0 | 0.5937727052996139 |
| PDB-derived annotation | trained_stack_sparse | 12 | 12 | 0 | 0 | 0.6798373793962029 |
| Rfam comparative | trained_expanded_sparse | 23 | 23 | 0 | 0 | 0.10762048692752478 |
| Rfam comparative | trained_sampled_sparse | 23 | 23 | 0 | 0 | 0.07731531795060397 |
| Rfam comparative | all_unpaired | 23 | 23 | 0 | 0 | 0.0 |
| Rfam comparative | ViennaRNA | 23 | 23 | 0 | 0 | 0.6898054001587578 |
| Rfam comparative | LinearFold | 23 | 23 | 0 | 0 | 0.7038432351685264 |
| Rfam comparative | trained_exact_sparse | 23 | 23 | 0 | 0 | 0.39591621748678685 |
| Rfam comparative | trained_expanded_sparse_posthoc_exact | 23 | 23 | 0 | 0 | 0.29725327247702216 |
| Rfam comparative | trained_structured_sparse | 23 | 23 | 0 | 0 | 0.30201311649389173 |
| Rfam comparative | trained_stack_sparse | 23 | 23 | 0 | 0 | 0.40480033722456843 |
| CRW comparative | trained_expanded_sparse | 12 | 12 | 0 | 0 | 0.04838716911254617 |
| CRW comparative | trained_sampled_sparse | 12 | 12 | 0 | 0 | 0.06035522852994927 |
| CRW comparative | all_unpaired | 12 | 12 | 0 | 0 | 0.0 |
| CRW comparative | ViennaRNA | 12 | 12 | 0 | 0 | 0.5752817994259013 |
| CRW comparative | LinearFold | 12 | 12 | 0 | 0 | 0.5546975689823873 |
| CRW comparative | trained_exact_sparse | 12 | 12 | 0 | 0 | 0.06946140213576714 |
| CRW comparative | trained_expanded_sparse_posthoc_exact | 12 | 12 | 0 | 0 | 0.09124249172505657 |
| CRW comparative | trained_structured_sparse | 12 | 12 | 0 | 0 | 0.05283950413413207 |
| CRW comparative | trained_stack_sparse | 12 | 12 | 0 | 0 | 0.20253194918713835 |
