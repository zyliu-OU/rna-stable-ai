# Fresh structure metadata and candidate plan — 2026-10-15

The retained Rfam 3D seed PDB mapping can now support a **frozen candidate
plan**, but the new biological structure panel has not been bound or evaluated.
No new contact labels, candidate sequences, or model outcomes were read while
choosing the panel.

The 92 missing family descriptions were frozen in
`results/fresh_structure_metadata_protocol.json`. The first acquisition failed
in the sandbox because DNS was unavailable. The approved network retry
validated 91 of 92 accession/release-bound Rfam 15.1 responses; RF04222
returned HTTP 404 and remains unresolved. Both acquisition journals are
retained. The successful run is replayable through
`results/fresh_structure_metadata_summary.json`.

The refreshed inventory is
`results/fresh_structure_inventory_after_metadata_2026-10-15.json`. Of 142
mapped families, 38 have prior family/PDB exposure, one was screened during
development, 21 overlap an exposed clan, 81 remain metadata candidates, and
one lacks clan metadata. Mapping counts alone are not supported references.

A fixed metadata-only panel was frozen in
`results/fresh_structure_panel_protocol.json`: eight families and 56 distinct
PDB accessions/chains. The families are RF00015 (U4), RF00080 (manganese
riboswitch), RF00100 (7SK), RF01734 (fluoride riboswitch), RF01763
(guanidine-III), RF01831 (THF), RF02977 (THF-II), and RF03013 (nadA). Their
candidate counts are 8, 6, 8, 6, 7, 8, 5 and 8 respectively. Selection used
Rfam clan metadata and sorted family/PDB/chain identifiers, screened known
family/clan/PDB exposures, and allowed each PDB accession only once across the
panel. The declared future binding will retain all source failures, exclude
sequence overlaps, reject multiple-partner raw cWW graphs without deleting
contacts, and never replace unsupported selected records. The practical
readiness minimum remains 12 supported references with at least three families
contributing three each; that minimum is not a power calculation.

The next step is to acquire the exact 56 frozen BGSU RNA 3D Hub responses and
bind candidate sequences before parsing contacts. Audit response bytes,
sequence redundancy, annotation lineage and unsupported denominators. Run the
reference-readiness gate before any model inference. FR3D-derived cWW labels
remain computational, and independent training/tool provenance is unresolved.

Verification:

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/acquire_fresh_structure_metadata.py --verify results/fresh_structure_metadata_summary.json
.venv/bin/python scripts/audit_fresh_structure_inventory.py --verify results/fresh_structure_inventory_after_metadata_2026-10-15.json
.venv/bin/python scripts/freeze_fresh_structure_panel.py --verify results/fresh_structure_panel_protocol.json
```
