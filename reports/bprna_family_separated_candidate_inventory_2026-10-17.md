# RNA-StableAI: provisional family-separated candidate inventory

Date: 2026-10-17 (America/Los_Angeles)

The official archived bpRNA SQL origin table was screened for RFAM records 400–4,999 nt long. This is a planning inventory for Stage 2's under-5,000-nt scope, not a held-out test or a performance result. The [V3 frozen run](../results/bprna_family_separated_candidates_v3_runs/20261017T190513.066933Z/summary.json) is canonical; its [protocol](../results/bprna_family_separated_candidates_v3_protocol_runs/20261017T190511.394650Z/manifest.json) pins all input and driver hashes. A first frozen pass excluded only the 11 selected development references. It is retained but superseded because all 338 development candidates must count as exposed. V2 was also retained; V3 removes an unused input file containing selected reference labels and clarifies that labels were not used for selection.

The corrected screen used 88 control training records, 17 added training records, all 338 development candidate sequences, and sequence-bound archived family labels for the 17 additions. It excluded any known training or development family, any exact exposed sequence, and any candidate sharing an exact 30-nt segment with training. It deduplicated by family plus full sequence. Training files contain pair labels, but the screen did not inspect them or any candidate structure labels; no model inference was run.

| Decision | Unique sequence-family entries |
| --- | ---: |
| Eligible archived RFAM entries | 1,166 |
| Known training or development family | 589 |
| Exact exposed sequence outside those families | 11 |
| Shared 30-nt training segment outside those groups | 133 |
| Provisional candidates | 433 |

The 433 candidates span 39 archived Rfam families and **all are 400–999 nt**. There are zero candidates in 1,000–4,999 nt after these exclusions. This source therefore offers a possible medium-length feasibility cohort but does not fill the longer-length independent validation gap. The 14 duplicate SQL rows within a family are excluded before the decision counts above.

These 39 families are not certified independent. Seven CRW training additions still lack direct family assignment, clan membership for the candidate families was not audited, and no candidate reference structure was bound or checked for completeness. The source's structures and any future panel must be screened before freezing a test set. The earlier 11-reference rRNA cohort remains development-only.

Next, resolve or conservatively quarantine CRW lineage, check clans and reference completeness without selecting on model performance, and seek a new source for 1,000–4,999 nt family-separated RNAs. Keep all work under the 5,000-nt project limit.
