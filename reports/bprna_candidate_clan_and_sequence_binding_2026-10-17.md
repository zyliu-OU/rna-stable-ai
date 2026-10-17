# RNA-StableAI: clan and source-sequence audit for provisional bpRNA candidates

Date: 2026-10-17 (America/Los_Angeles)

The 433 provisional 400–999 nt bpRNA RFAM candidates from the [V3 inventory](../results/bprna_family_separated_candidates_v3_runs/20261017T190513.066933Z/summary.json) were checked against Rfam release 15.1's [seed alignment archive](https://ftp.ebi.ac.uk/pub/databases/Rfam/15.1/Rfam.seed.gz). That archive supplies the family accession, name, and clan in Stockholm `GF` annotations. The local 5,928,432-byte source has SHA256 `41f014f4ab5628620935f089b1bb77987ebc162fda7c72bff368a32c9cccabac`. The [frozen clan audit](../results/bprna_candidate_clans_runs/20261017T190647.643559Z/summary.json) replayed successfully, and its mappings agree with 163 previously cached Rfam 15.1 family descriptions with no conflicts.

| Clan status relative to known training and development families | Families | Candidate sequences |
| --- | ---: | ---: |
| Known, distinct clan | 10 | 179 |
| Already exposed clan | 6 | 61 |
| No Rfam clan assigned | 23 | 193 |

The 10 known, distinct-clan families include six RNase P or RNase MRP families in CL00002 (148 sequences). A family with no assigned clan is not certified independent. Unknown CRW training lineage could also reveal further overlaps, so none of the 179 are yet an independent test. The 61 candidates in known exposed clans should be excluded from that use.

The [frozen sequence binding](../results/bprna_candidate_sequence_binding_runs/20261017T190750.775148Z/summary.json) found an exact normalized sequence match in the bpRNA `.dbn` archive for all 433 candidate sequences, including all 179 known, distinct-clan candidates. Ten sequences have multiple matching archive files (445 matches total); these are retained. None of the SQL row names matches its `.dbn` file name, confirming that numeric IDs cannot be used as a join key. No candidate dot-bracket labels or model predictions were parsed in this step.

These results establish source availability only. The next checks are CRW lineage, reference structure validity, and a frozen evaluation plan. The longer 1,000–4,999 nt range remains without a surviving candidate from this source.
