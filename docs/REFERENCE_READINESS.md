# Reference readiness before another structure study

`scripts/audit_reference_readiness.py` audits fixed annotation bindings without
loading prediction outcomes, fitting models, calling folding tools, or recording
new exposure. It retains every planned record and unsupported reference.

The declared design minima in `configs/reference_readiness.json` are at least
12 supported references and at least three families with three supported
references each. These are practical coverage minima, not sample-size or
statistical-power calculations. Adequate coverage does not certify independence.

The audit reads retained Stockholm `SS` provenance and separates explicitly
predicted annotations, published sources, mixed claims, unverified experimental
claims, and unknown origins. It preserves source text, source-specific PubMed
identifiers, family bibliography identifiers, and declared prediction tools.
An article citation never automatically becomes per-sequence experimental truth.
[Rfam explains](https://docs.rfam.org/en/latest/building-families.html) that both
experimental and predicted structures can underlie published seed annotations.

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/audit_reference_readiness.py \
  --binding results/prospective_binding_runs/20261012T030228.664684Z/summary.json \
  --binding results/prospective_pair_binding_runs/20261012T035646.856700Z/summary.json \
  --binding results/prospective_pair_binding_runs/20261014T011058.285068Z/summary.json
.venv/bin/python scripts/audit_reference_readiness.py --verify results/reference_readiness_summary.json
```

For a new prospective binding, add `--require-ready` before running any evaluator.
It exits with code 2 if coverage, exact sequence binding, known provenance, or
fresh-family gates fail. This command does not authorize inference or replace
the evaluator's final live exposure and native-request gates. Consumed panels
cannot be made fresh by running this audit again.

The three historical panels retain 9, 8, and 4 supported references respectively.
They contain 2, 1, and 1 families meeting the per-family minimum. None meets the
new coverage minimum, and all contain consumed families. Cobalamin RF00174 is
explicitly labelled `Predicted; PFOLD`; the remaining source citations remain
unverified as per-sequence experiments. Historical scores are unchanged.

Each run freezes policy, exposure inventory, exact source inputs, and code hashes.
Replay checks those retained inputs without reading the current exposure ledger.
Adding future studies does not rewrite an earlier readiness decision.

Next source engineering work targets the official
[Rfam 3D seed annotations](https://github.com/Rfam/rfam-3d-seed-alignments), which
incorporate per-sequence FR3D annotations from PDB structures. Their published
annotation pipeline and contact-selection policy must be inspected and retained;
a derived annotation is not a direct chemical-probing measurement or proof of
independent tool training.
