# RNA-StableAI Step 2: bpRNA long-training family-provenance audit

Date: 2026-10-17 (America/Los_Angeles)  
Workspace: `/home/zyliu/Documents/rna-stable-ai`

## Local inventory and direct evidence

The 17 selected training additions in `results/bprna_long_training_smoke_runs/20261017T033749.792816Z/selection.json` have seven `CRW` and ten `RFAM` source-group labels. None has a `family_id` or Rfam accession. The pinned dot-bracket archive's selected DBN files start with name, length, and page-number headers, then sequence and structure; those headers do not supply an upstream accession or family. The numeric suffix of a `bpRNA_RFAM_*` identifier must not be read as an `RFxxxxx` family accession.

The 11 development references belong to RF00177 (3), RF02540 (3), RF02541 (3), and RF02542 (2). Current Rfam pages place RF00177 and RF02542 in the SSU rRNA clan CL00111, and RF02540 and RF02541 in the LSU rRNA clan CL00112. These are two related ribosomal-RNA groups, not four unrelated broad RNA classes. See the [SSU clan membership](https://rfam.org/family/RF02542), [archaeal LSU membership](https://rfam.org/family/RF02540), and [bacterial LSU membership](https://rfam.org/family/RF02541).

The [official bpRNA-1m description](https://bprna.cgrb.oregonstate.edu/about.php) confirms that CRW and Rfam are upstream sources. Its [published database-construction archive](https://github.com/hendrixlab/bpRNA/tree/master/bpRNA_1m) was inspected locally (GitHub blob SHA `eefe166432b9c96b4549842f5ffcbd5c1aadfdf1`; ZIP SHA-256 `3ebc6e1b2f52556d964c50b83070b2484eaa7f5f61162e26a0bcb0ea1dcc2cc9`). The RNA table has source, organism, and `rna_Lineage` fields, but no explicit Rfam family-accession field. That schema does not establish a family assignment for the 17 selected IDs. A [2026 RNA paper](https://rnajournal.cshlp.org/content/32/4/428.full.pdf) also describes Rfam homology mapping for bpRNA-1m as a separate analysis; a source-group label by itself is insufficient for a family-separated claim.

## Gate and next acquisition

Family separation for the existing 11-reference development panel is **unproved**. The panel remains useful for development diagnostics because its label-informed selection was already declared, but it must not become an independent test by relabeling it. For a future independent long-reference panel, require an explicit family or clan assignment for every training addition or conservatively exclude validation families in potentially overlapping clans until the unknowns are resolved. Preserve source accession, family accession, clan, mapping method, source version, and uncertainty for each record; use exact sequence and near-duplicate screens as additional checks rather than substitutes for family lineage.

The concrete next source task is to obtain bpRNA record-level origin metadata or perform a version-pinned Rfam covariance-model assignment for the 17 additions, review ambiguous or multiple hits, and freeze the resulting mapping before choosing an independent panel. The current audit did not assign families to the 17 records or change any training or validation artifact.
