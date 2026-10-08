# Context comparative family trial

Run: `/home/zyliu/Documents/rna-stable-ai/results/context_family_trial_runs/20261006T022922.302415Z`

Counts: {'train': 24, 'validation': 23, 'test': 12}
Families: {'train': ['RF00001'], 'validation': ['RF00169'], 'test': ['RF00017']}

Excluded test reference contacts: 314

| Method | Planned | Measured | Mean test pair F1 |
|---|---:|---:|---:|
| LinearFold | 12 | 12 | 0.47994718111707635 |
| ViennaRNA | 12 | 12 | 0.4780596903544601 |
| all_unpaired | 12 | 12 | 0.0 |
| trained_context | 12 | 12 | 0.003643045940328309 |
| untrained_context | 12 | 12 | 0.0047127108236874595 |

Processed comparative references, not new experimental measurements.
One family per split; no population-wide family/clan or biological stability claim.
Legacy tool-training overlap and prior PDB family identities remain unresolved.
Max pair span128 excludes distant contacts; test lengths290–317 do not establish long-RNA accuracy.
RF00017 is consumed after this test; no test-driven model/threshold selection.
