# Frozen checkpoint source lineage

`scripts/audit_checkpoint_lineage.py` inventories the actual training/validation
records for the original baseline, stack and helix models. It verifies checkpoint
sources, retained summaries, dataset byte hashes and historical exposure events.
It neither fits/evaluates a model nor creates new exposure.

All three models use identical dataset bytes: 89 training and 47 validation
records. Twenty-four training records supply RF00001; twenty-three validation
records supply RF00169. Five training and one validation record have only
whole-PDB family candidates in the retained Rfam mapping. Sixty training and
twenty-three validation records remain family-unresolved, including comparative
CRW records and PDB records without mapped family provenance.

PDB candidates are conservative exclusions for future source planning, not
confirmed sequence/chain assignments. The audit preserves RNA type, organism,
source accessions, source split and BPSEQ hash without inventing family IDs.

Project training uses 65 upstream-train and 24 upstream-holdout records.
Project validation uses 8 upstream-train, 29 upstream-holdout and 10 upstream-test
records. These are deliberate project development roles; the original source's
split names do not make them blind tests. All remain exposed for future planning.

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/audit_checkpoint_lineage.py
.venv/bin/python scripts/audit_checkpoint_lineage.py --verify results/checkpoint_lineage_summary.json
```

Outputs: `results/checkpoint_lineage_summary.json`, per-record CSV, immutable run
snapshots, and `reports/checkpoint_lineage_report.md`. Byte bindings and metadata
inventory do not reconstruct historical training execution, resolve every family,
or establish native-tool training independence.
