# RNA-StableAI Step 2: source-bound bpRNA long-training origins

Date: 2026-10-17 (America/Los_Angeles)  
Workspace: `/home/zyliu/Documents/rna-stable-ai`

The official bpRNA-1m [database load archive](https://github.com/hendrixlab/bpRNA/tree/master/bpRNA_1m) contains a 2018 SQL RNA table with original names, accessions, and Rfam identifiers. Its 39,672,063-byte Part 1 ZIP was pinned locally at `results/bprna_origin_metadata_source/Load_bpRNA_1m_Mysql_Part1.zip` (SHA-256 `fda31994e356b5fa61109176938b13b7221e31233df603a5c02f82ae0e779a21`). The 17 selected training sequences were bound to SQL rows by **source group and exact uppercase-normalized sequence**, with all duplicate sequence rows retained. Numeric bpRNA IDs alone were never used to transfer metadata.

| Selected group | Record-level result |
| --- | --- |
| CRW, 7 records | All seven have a SQL row with both the same bpRNA ID and sequence, giving an original CRW name and accession. Several sequences also occur under alternative structure-record names. No direct Rfam family is given. |
| RFAM, 10 records | All ten have at least one exact-sequence SQL match within the RFAM group. Nine have one archived Rfam family label; one (`bpRNA_RFAM_37081`) appears under both RF01960 and RF02542, so both are retained. |

The RFAM labels are: RF00177 (two records), RF01959 (one), RF01960 (one), RF01960/RF02542 (one ambiguous), RF02541 (two), RF02542 (one), RF02543 (one), and RF01050 (one). Current Rfam pages place RF00177, RF01959, RF01960, and RF02542 in [SSU clan CL00111](https://rfam.org/family/RF02542); RF02541 and RF02543 in [LSU clan CL00112](https://rfam.org/family/RF02540); and RF01050 in [telomerase clan CL00004](https://rfam.org/family/RF01050). Thus nine of the ten RFAM additions have archived family labels in the same two clans as the 11-reference development panel. The ambiguous RF01960/RF02542 pair stays within the SSU clan; its family remains ambiguous.

The SQL and selected dot-bracket archives do **not** share a reliable numeric ID namespace for RFAM records. Three same-numbered SQL rows have different, much shorter sequences than the selected training records, and seven selected RFAM IDs are absent from the SQL table. For example, selected `bpRNA_RFAM_22603` is 1,158 nt, while same-numbered SQL `bpRNA_RFAM_22603` is 133 nt. Its actual exact-sequence SQL match is named `bpRNA_RFAM_45205` and carries archived family RF01050. This demonstrates why ID-only joins would silently assign incorrect families. A first frozen binding attempt stopped on another legitimate feature—CRW sequences appearing under multiple alternative structure rows—and was preserved. The corrected V2 run requires the same-name CRW origin while retaining all sequence-matched alternatives.

This evidence reinforces that the existing 11-reference cohort is development-only. The seven CRW records now have source names and accessions, but still lack direct Rfam family assignments. Their names must not be converted to family IDs by guesswork. Combined with the earlier exact-segment overlap (14 of 17 additions share a 30-nt segment with the panel), there is no basis for independent family-separated validation or checkpoint promotion.

Canonical artifacts:

- Source ZIP: `results/bprna_origin_metadata_source/Load_bpRNA_1m_Mysql_Part1.zip`
- V2 frozen protocol: `results/bprna_long_origin_binding_v2_protocol_runs/20261017T185531.683657Z/manifest.json`
- V2 binding: `results/bprna_long_origin_binding_v2_runs/20261017T185531.913009Z/summary.json`
- Driver: `scripts/bind_bprna_long_origin_metadata.py`

Verification: V2 replay rechecked source and selected-sequence hashes, rescanned the SQL rows, and reproduced every binding and ambiguity. The driver compiled; three focused bpRNA source/subset tests passed. The 68-MB Part 2 archive was inspected and contains structural-feature tables, not the RNA origin table; it was not retained in the workspace.

Next: obtain version-pinned Rfam hits for the seven CRW sequences or a direct curated family crosswalk. Freeze a new independent long-reference panel outside exposed clans after family, exact-segment, and near-duplicate checks. Keep source archives local until redistribution scope is reviewed.
