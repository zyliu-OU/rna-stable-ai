# RNA-StableAI: long-RNA structure-source survey

Date: 2026-10-18 (America/Los_Angeles)
Workspace: `/home/zyliu/Documents/rna-stable-ai`
Active reference scope: 1,000–4,999 nt for this survey; no model scope expansion.

## Result

Two new **source leads**, Qβ and AP205 phage genomes, survive metadata triage with modeled-residue counts equal to deposited sequence lengths. There are still **zero newly qualified independent pair references**. Full residue counts do not establish known base identities, complete base-pair labels, family separation or independent annotation/tool provenance.

| Entity | RNA | Deposited length | Modeled residues | Metadata decision |
| --- | --- | ---: | ---: | --- |
| [7LHD_1](https://www.rcsb.org/structure/7LHD) | Qβ genomic RNA | 4,217 | 4,217 | Source lead; family/sequence/contact lineage unresolved; 4.6 Å |
| [8TOC_1](https://www.rcsb.org/structure/8TOC) | AP205 RNA | 4,269 | 4,269 | Source lead; family/sequence/contact lineage unresolved; 3.11 Å |
| [5TC1_3](https://www.rcsb.org/structure/5TC1) | MS2 genome | 3,569 | 242 | No full-length model by count |
| 9SWN_6 | Yeast TLC1 | 1,157 | 232 | No full-length model by count |
| 9SWO_1 | Yeast TLC1 | 1,157 | 98 | No full-length model by count |
| 7ZJW_3 | CrPV IRES | 1,072 | 183 | No full-length model by count; BGSU also maps author chain I to exposed RF00458 |

7LHD's [primary paper](https://doi.org/10.3390/v14020225) describes computational structural modeling based on cryo-EM density. Its deposited model must not be treated as an independent direct pair assay. Neither a full model nor publication establishes independent training/tool provenance. The AP205 label-generation method remains to be audited.

## Source and selection

The retained BGSU NR 4.61 / 3.5 Å export has 3,189 RNA rows with 1,000–4,999 observed nucleotides. Of these, 3,188 carry SSU/LSU family labels; the remaining row is `8TOC|1|R`, without a resolved Rfam family. Observed lengths remain a proxy, not an exact full-chain length test.

A separate direct [RCSB Search API](https://search.rcsb.org/) query was frozen before acquisition. It requested experimental RNA polymer entities with deposited sample lengths 1,000–4,999 nt, without a resolution cutoff. The saved response reports 4,498 entities. An explicitly heuristic description filter excluding tokens `ribosomal rRNA 16S 18S 23S 25S 28S` returned 161 entity IDs. RCSB full-text tokenization means some ribosomal names survive this filter. It is source triage, not exhaustive family exclusion or proof that the other 4,337 entities are unsuitable. Facet descriptions for the full query are retained.

All 161 shortlisted entity metadata responses and 173 associated chain-instance coverage responses were acquired and identity checked. Twenty-one entities have at least one instance with modeled-residue count equal to sample length. Metadata triage used the frozen exposure snapshot, earlier bpRNA family inventory, pinned Rfam 15.1 clans, exact single-chain BGSU mappings, and the CRW group II quarantine. No family labels were inferred from Pfam annotations. Descriptions and entry titles are conservative triage cues; neither assigns a Rfam family.

| Mutually exclusive shortlist disposition | Entities |
| --- | ---: |
| Prior whole-PDB exposure | 3 |
| Exposed family via exact single-chain BGSU metadata | 55 |
| No full-length model by residue count | 93 |
| Ribosomal description; family binding still required | 2 |
| Ribosome context; entity identity still required | 6 |
| Source lead; lineage, sequence and contacts unresolved | 2 |
| Total | 161 |

Missing family annotations never count as evidence of independence. Group II architecture, RF00029/RF02012 and CL00102 are retained as exclusions through the consumed quarantine artifact. No sequence or contact labels were requested, no new sequence exposure events were needed, and no predictions were made.

## Frozen local artifacts

- Survey protocol: `results/rcsb_long_rna_survey_protocol_runs/20261018T222353.610817Z/manifest.json`.
- Survey responses: `results/rcsb_long_rna_survey_runs/20261018T222454.417426Z/`.
- Entity metadata protocol: `results/rcsb_long_shortlist_protocol_runs/20261018T222554.392014Z/manifest.json`.
- Entity metadata: `results/rcsb_long_shortlist_metadata_runs/20261018T222614.858678Z/`.
- Coverage V2 protocol: `results/rcsb_long_coverage_protocol_runs/20261018T223020.027831Z/manifest.json`.
- Coverage: `results/rcsb_long_coverage_runs/20261018T223032.036748Z/`.
- Source-lead audit: `results/rcsb_long_source_lead_audit_runs/20261018T223215.383558Z/summary.json`.
- Official instance schema: `results/rcsb_instance_schema_2026-10-18.json`.

An initial sandbox DNS failure is preserved separately. The first coverage request used an incorrect GraphQL identifier field and was rejected. Its protocol/response and original driver remain preserved; the corrected V2 driver uses the identifier field from the official schema. No failed response was counted as empty or complete.

Verification: 12 focused tests passed across this survey and the two preceding CRW audits. Source-lead replay passed through all acquired survey, metadata, coverage and BGSU hash/identity checks. The tests cover partial-model rejection, exposure/quarantine precedence, ribosome context, missing/duplicate/out-of-range metadata, GraphQL failures and the corrected schema field.

## Next qualification work

Freeze a sequence-only acquisition plan for exactly `7LHD_1` (label/auth chain A/A) and `8TOC_1` (label/auth chain A/R). Retain failures without replacement, reject unresolved/noncanonical sequence identities, and screen against the union of training and development exposures: exact identities, shared 30-nt training segments, and near duplicates. Journal every valid acquired sequence before further analysis. Resolve family/clan and group II exclusion status before any independent panel freeze.

Then audit each source's annotation/model-generation lineage and whether its coordinates can supply a complete, sequence-bound pair reference. Full modeled-residue counts alone cannot pass that gate. Keep both leads and any failures in the denominator. Two source leads do not meet broad multi-family validation coverage requirements. No contact acquisition or inference is authorized by the frozen metadata protocols.
