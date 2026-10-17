# RNA-StableAI Stage 2 family-validation progress

Date: 2026-10-17 (America/Los_Angeles)  
Active length scope: 1–4,999 nt

## Evidence added

- The official archived bpRNA SQL origin table was bound by exact sequence to the 17 added training RNAs. Ten RFAM records have archived Rfam family labels (one has two plausible labels in the same SSU clan); seven CRW records have original names/accessions but no direct archived Rfam family. Numeric IDs are unsafe for this join. See [origin audit](bprna_long_origin_binding_2026-10-17.md).
- A fixed 11-reference longer development panel shares exact 30-nt segments with 14 of those 17 additions. This reinforces its development-only status. See [segment audit](long_training_reference_segment_audit_2026-10-17.md).
- Rfam 15.1 seed metadata screened 433 provisional bpRNA candidates of 400–999 nt. Sixty-one candidates are in already exposed clans; 179 have known, distinct clans; 193 have no assigned clan. All 433 bind by exact sequence to bpRNA structure files, although none binds by the SQL numeric name. See [candidate inventory](bprna_family_separated_candidate_inventory_2026-10-17.md) and [clan/source binding](bprna_candidate_clan_and_sequence_binding_2026-10-17.md).
- A metadata-selected five-clan feasibility panel was frozen before its structure labels were read. All 13 references of 400–535 nt passed fixed pair-reference checks. Across three matched seeds, mean record pair F1 was **0.1413** for the 88-record control and **0.1669** for the 105-record extension; paired seed differences were **−0.0064, +0.0297, +0.0535**. Mean clan-balanced difference was **+0.0095** across seeds. LinearFold and ViennaRNA scored **0.3301** and **0.3346**. The panel is small, uses computational bpRNA labels, and CRW training lineage is incomplete. It is conditional feasibility evidence, not an independent accuracy claim or grounds for checkpoint promotion. Frozen evaluation summary: `results/bprna_five_clan_feasibility_evaluation_runs/20261017T191445.852927Z/summary.json` (retained locally with its source archive).
- One CRW record (`bpRNA_CRW_13049`) returned a full-sequence-verified Rfam batch result with four SSU-family hits, all in clan CL00111. Six further CRW jobs were accepted and were still pending at this report's last check. The [Rfam sequence-search API](https://docs.rfam.org/en/latest/api.html#sequence-searches) returns incomplete responses before jobs finish; empty `searchSequence` fields were not counted as zero hits.
- A release-pinned Rfam 15.1 seed scan found 582 valid 1,000–4,999 nt seed sequences across 10 families. 578 are in already exposed families, two are exact exposed sequences, and two share a 30-nt training segment. No candidate survives this screen. This and the bpRNA SQL screen leave the 1,000–4,999 nt independent-reference gap open. Frozen local summary: `results/rfam_seed_long_candidate_audit_runs/20261017T191603.870444Z/summary.json`.

## Next release gates

Complete sequence-bound CRW family/clan searches; obtain a new source of 1,000–4,999 nt complete references outside exposed families and clans; preregister and evaluate an independent panel. No model defaults changed in these studies. Upstream bpRNA and Rfam source archives remain local rather than being redistributed in this report.
