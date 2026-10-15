# Frozen checkpoint source lineage

PDB-level family matches are conservative any-chain candidates, not exact sequence/chain family assignments.
RNA type, organism and accession text are retained metadata; unknown Rfam accessions are not invented from those labels.
Original upstream train/holdout/test names are provenance, not this project's model roles. Source-test rows reused as development validation are exposed, not fresh tests.
Input byte bindings do not reproduce historical training or establish legacy native-tool training independence.

| Model | Project role | Records | Supplied family IDs | PDB candidates only | Family unresolved | Upstream splits |
|---|---|---:|---:|---:|---:|---|
| baseline | train | 89 | 24 | 5 | 60 | {'train': 65, 'holdout': 24} |
| baseline | validation | 47 | 23 | 1 | 23 | {'holdout': 29, 'test': 10, 'train': 8} |
| helix | train | 89 | 24 | 5 | 60 | {'train': 65, 'holdout': 24} |
| helix | validation | 47 | 23 | 1 | 23 | {'holdout': 29, 'test': 10, 'train': 8} |
| stack | train | 89 | 24 | 5 | 60 | {'train': 65, 'holdout': 24} |
| stack | validation | 47 | 23 | 1 | 23 | {'holdout': 29, 'test': 10, 'train': 8} |

All three models use identical train/validation corpus bytes: True
