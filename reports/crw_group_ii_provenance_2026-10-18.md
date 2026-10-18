# RNA-StableAI: accession context for two CRW group II records

Date: 2026-10-18 (America/Los_Angeles)
Workspace: `/home/zyliu/Documents/rna-stable-ai`

The two training records with short Rfam hits have **supported broad group II intron provenance**. This is an inference combining exact-sequence-bound archived CRW names, accession sequence alignments and annotated intron coordinates. It is not a formal whole-record Rfam assignment, nor an exact full-query accession match.

| Training record | Archived CRW name | Versioned accession | Sequence evidence |
| --- | --- | --- | --- |
| bpRNA_CRW_54679 | a.I2.m.P.littoralis.B.LSU.1787 | [Z48620.1](https://www.ncbi.nlm.nih.gov/nuccore/Z48620.1) | Query bases 2–2474 match accession bases 4028–6500 exactly: 2,473 identities, no mismatches or gaps; one leading query base remains unaligned. The span contains the entire annotated intron 2 (4052–6489). |
| bpRNA_CRW_54684 | a.I2.m.S.cerevisiae.A.OX1.i1 | [V00694.1](https://www.ncbi.nlm.nih.gov/nuccore/V00694.1) | Query bases 14–2520 align to accession bases 255–2760: 2,503 identities, three mismatches, one inserted query base; 13 leading query bases remain unaligned. The span contains the entire annotated intron 1 (295–2745). |

Coordinates in this table are 1-based inclusive. Saved alignment coordinates are 0-based half-open. No edits were made to either selected training sequence. The accession sources are longer genomic contexts, not new validation references; active model/reference scope remains below 5,000 nt.

This explains why the October 18 short-hit result should not imply that these are otherwise uncharacterized RNAs. Rfam describes [RF00029](https://rfam.org/family/RF00029) as a group II catalytic intron model containing domain V and nearby sequence, and [RF02012](https://rfam.org/family/RF02012) as a group II D1–D4 family. These models describe parts of larger introns. The archived CRW record identifies the first sequence as an intron within an LSU gene, rather than an LSU rRNA training sequence in its entirety. The broad architecture inference does not establish every family relationship or explain the terminal differences.

## Conservative planning decision

Retain both records as development/training exposures. For future independent-panel planning, exclude their homologs and group II intron architecture unless a new protocol explicitly resolves that lineage. Retain RF00029, RF02012 and CL00102 as possible exposures. A machine-readable planning artifact is saved as `quarantine.json` alongside the audit summary. It pins the summary hash; future panel drivers must explicitly incorporate this artifact. It is not automatically wired into earlier frozen screens.

The earlier five-clan feasibility result remains development evidence. The new provenance does not upgrade it to independent validation. The independent, complete 1,000–4,999 nt reference gap remains open.

## Reproducibility

- Sources: `results/crw_original_provenance_source_runs/20261018T221853.357057Z/` contains `Z48620.gb`, `V00694.gb`, original collector source and a timestamped retrieval manifest with hashes. Original CRW PDF retrieval failed TLS certificate verification; the diagrams were not used as retrieved evidence.
- Audit: `results/crw_original_provenance_audit_runs/20261018T222023.684010Z/summary.json`.
- Manifest pins both GenBank files, retrieval manifest, exact-sequence SQL origin binding, selected training inventory, driver and Biopython version. Replay also rechecks the original SQL archive through its frozen audit.
- Alignment policy: first optimal forward local alignment; match +2, mismatch −3, gap open −5, gap extension −0.5. Prefix/suffix clipping, mismatches and inserted/deleted bases are recorded explicitly. These alignments support provenance rather than serving as a new acceptance threshold for family identity.
- Six focused tests passed across the provenance and panel-exposure audits. Tests verify exact substrings, clipped query ends, internal insertions, local/unclanned exposures and invalid inputs. The frozen provenance replay passed.

No training, prediction, checkpoint promotion, README edits or publication occurred.
