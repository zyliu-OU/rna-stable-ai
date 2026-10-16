# Fresh biological structure inventory — 2026-10-15

The next independent-structure panel is **not ready for model inference**. A
metadata-only audit of the retained Rfam 3D seed PDB mapping found 142 mapped
families and 19,193 family/PDB/chain rows. The audit read no new structure
contacts, annotation labels, candidate sequences, or model predictions. Its
replayable artifact is
`results/fresh_structure_inventory_2026-10-15.json`.

After conservative screening, 38 mapped families have known family/PDB
exposure, one additional family (RF00024) was screened during the development
source study, six have a cached Rfam 15.1 clan that overlaps a used group, and
92 have no retained clan description. Only five have resolved clan metadata and
no known exposure: RF00013, RF00015, RF00031, RF00037, and RF00044. Of those,
only RF00015 and RF00044 have at least three distinct unexposed PDB accessions
in the mapping (13 and three respectively). These are mapping counts, not
supported sequence-bound reference counts; the latter remain zero for a new
panel. The declared broad readiness minimum requires 12 supported references
and three families with three supported references each.

The 92 unresolved clans are the immediate data gap. Acquire and freeze Rfam
15.1 metadata for those families, then rerun family/clan and whole-PDB exposure
screening. Only after that should a fixed candidate panel be chosen using
metadata, before fetching candidate sequence/contact annotations. Preserve
unsupported candidates without replacement, audit source annotation lineage
and checkpoint/tool-training provenance, and run the readiness gate before any
model inference. PDB-derived FR3D contacts are computational labels; this audit
does not establish per-sequence experimental truth or independent training.

Verification:

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/audit_fresh_structure_inventory.py --verify results/fresh_structure_inventory_2026-10-15.json
.venv/bin/python -m pytest -q tests/test_fresh_structure_inventory.py
```
