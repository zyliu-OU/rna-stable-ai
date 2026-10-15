# External measured-assay proxy pilot

The source and assay binding are fixed in
[MEASURED_DEGRADATION_SOURCE.md](MEASURED_DEGRADATION_SOURCE.md). The evaluator
retains the declared64 sequence IDs, six frozen prediction methods and five
measured assays. It adds no model fitting, checkpoint/decoder selection or new
quality-based record filtering.

```bash
.venv/bin/python scripts/evaluate_degradation_pilot.py
.venv/bin/python scripts/evaluate_degradation_pilot.py --evaluate
.venv/bin/python scripts/evaluate_degradation_pilot.py --verify
```

The first command freezes input, checkpoint protocol, code, Python/library
versions and native runtime before scoring. Repeating preparation reuses the
same input-bound plan instead of creating another experiment. A durable selected
`test_started` event precedes every model/native call. Complete runs re-audit on
`--evaluate`; interrupted runs resume with `--resume RUN_DIR`. Native requests
use the existing bound journal; interrupted outcomes remain unknown and are
never retried. Each completed prediction is retained atomically, and resume
verifies the earlier ordered predictions. Failed predictions have no stale
structure, energy or proxy value.

Predictions retain64 × six =384 outcomes. For each record compare:

- Scored-prefix unpaired fraction for each of the six methods. A base paired to
  a position outside the measured prefix still counts as paired. No experimental
  structural truth is inferred from the author file's provided structure.
- Returned energy divided by complete-sequence length for ViennaRNA and
  LinearFold only. Learned logits are never stored as native energy. LinearFold
  uses beam100 and can differ from the exact ViennaRNA minimum.
- Scored-prefix GC fraction as a sequence-only control, without extra prediction
  or folding calls.

Each of these nine method/proxy combinations retains every record/assay slot:
2880 rows. Fixed all, quality0, quality1 and unknown-quality slices produce180
aggregate entries. The all-unpaired control can yield a constant proxy; empty
quality slices and fewer than three complete pairs retain null rho with a reason.
Every aggregate reports planned/complete counts, missing predictions, unsupported
assays and missing paired observations. No silent partial-vector averaging occurs.
Spearman rho is descriptive; p-values and independent confidence intervals are
not reported. Assay error vectors remain bound in the source without noise weighting.

Native folding uses37C, a30-second/4-GiB per-request bound and CPU execution.
The pilot's chemical assay conditions differ. Every selected row has quality1;
all and quality1 statistics repeat the same cohort. Shared construct flanks,
source preprocessing and experimental dependencies limit interpretation. These
comparisons assess short-construct computational proxies; they do not establish
whole-RNA half-life, causal mutation stabilization, long biological accuracy or
retained function. A mean normalized assay value is not a measured half-life.

Replay checks exact source/model/analysis/runtime/exposure bindings, recomputes
model predictions and proxies, and reads the retained native ledgers/raw-output
hashes without new native calls or exposure. Complete/missing denominators and
all aggregates must match. The benchmark remains a public, exposed assessment;
its results must not tune these models and then be relabeled as fresh testing.
