# Processed PDB evaluation and training pilot

Run: `/home/zyliu/Documents/rna-stable-ai/results/experimental_pilot_runs/20261006T010347.964097Z`

Splits: {'test': 16, 'validation': 12, 'train': 41}; selected epoch 6.

| Method | Planned test records | Measured | Mean pair F1 |
|---|---:|---:|---:|
| LinearFold | 16 | 16 | 0.9437729912383568 |
| ViennaRNA | 16 | 16 | 0.9437729912383568 |
| all_unpaired | 16 | 16 | 0.0 |
| trained_cnn | 16 | 16 | 0.06746031746031746 |
| untrained_cnn | 16 | 16 | 0.013157894736842105 |

Processed PDB-derived annotations, not raw experimental pair measurements; sequence heuristic does not establish RNA-family independence.
Local three-state labels and a greedy decoder are a simple baseline, not a global pair model.
Decoder permits AU/GC/GU pairs and at least three enclosed nucleotides; processed references may contain other contacts.
Short processed PDB records do not establish long-RNA accuracy or biological stability.
One seed and one fixed hyperparameter configuration; validation-selecting checkpoints can overfit a small validation set.
Experimental-derived annotation comparison is not a biological stability measurement.
