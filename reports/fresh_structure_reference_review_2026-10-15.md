# Fresh structure contact panel — 2026-10-15

The frozen eight-family panel **failed the reference-readiness gate**. All 56
predeclared BGSU RNA 3D Hub requests succeeded and replay from
`results/fresh_structure_references_summary.json`. Sequence-first screening
found 53 valid source sequences, three unsupported source sequences, and 40
within-panel sequence redundancies. Thirteen records were selected before
contact parsing; all thirteen raw cWW graphs bound to their exact sequences.
Their source sequences were recorded as validation exposure before graph
binding, so these families and PDBs are now consumed for future fresh tests.

One accepted raw graph contains zero cWW contacts. The separate informative
reference audit counts **12** graphs with at least one contact, not thirteen,
and **zero** families with three informative references. The declared coverage
minimum is twelve total and three families with at least three each. The
family counts are:

| Family | Selected and accepted | Informative contacts |
|---|---:|---:|
| RF00015 U4 | 3 | 2 |
| RF00080 manganese | 2 | 2 |
| RF00100 7SK | 1 | 1 |
| RF01734 fluoride | 2 | 2 |
| RF01763 guanidine-III | 1 | 1 |
| RF01831 THF | 2 | 2 |
| RF02977 THF-II | 1 | 1 |
| RF03013 nadA | 1 | 1 |

The raw accepted graphs contain 260 unique cWW contacts; six have crossing
contacts. No selected raw graph required deletion of multiple-partner
contacts. The zero-contact graph remains visible in the source binding and is
marked uninformative only for this positive-contact coverage audit; its lack
of cWW rows cannot establish a truly unpaired biological structure.

`results/fresh_structure_readiness_summary.json` retains Rfam 15.1 family
structure-source text. RF00080 declares a prediction; seven families cite
published sources. Those are family-level claims, not proof of per-sequence
experimental annotation. The actual reference basis is current FR3D-derived
PDB cWW contacts, and exact upstream annotation version and tool-training
independence remain uncertified. No model inference was run or authorized.

The next data-development step must seek families and structures outside this
new exposure cohort. Freeze a broader sequence-diverse source plan before
reading its labels, and retain any failures without replacement. Long
biological RNA accuracy, causal stability, mutation effects and retained
function remain open.

Replay:

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/prepare_fresh_structure_references.py --verify results/fresh_structure_references_summary.json
.venv/bin/python scripts/audit_fresh_structure_readiness.py --verify results/fresh_structure_readiness_summary.json
```
