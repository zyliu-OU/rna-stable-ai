# Prospective complete-pair evaluation protocol

This workflow evaluates complete WUSS contacts, including pseudoknots, using the
existing frozen baseline/stack/helix checkpoints and folding controls. The model
decoder continues to predict nested structures. Scoring retains crossing gold
contacts in its denominator.

## Freeze before new source outcomes

Copy the metadata-screening configuration to a new file, replace the consumed
families with explicitly proposed unexposed families, and add:

```json
"reference_format": "pair_set_zero_based_v1"
```

Freeze using `scripts/prepare_prospective_family_panel.py --config YOUR_CONFIG`.
The field becomes part of the hashed configuration alongside the family IDs,
selection order, caps, checkpoint bytes and decoder settings. Keep its recorded
manifest path for acquisition. The format cannot be switched after acquisition;
both pair-set-to-legacy and legacy-to-pair-set mismatches reject preparation.
Historical protocols without the field remain `dot_bracket_v1`.

Acquire source metadata and evidence using the existing acquisition scripts and
their matching protocol/acquisition arguments. Missing downloads remain recorded
failures. They do not become empty biological cohorts or authorize inference.

## Bind and evaluate

After acquiring the new panel's evidence, run:

```bash
.venv/bin/python scripts/evaluate_prospective_panel.py --reference-format pair_set_zero_based_v1
.venv/bin/python scripts/evaluate_prospective_panel.py --evaluate --reference-format pair_set_zero_based_v1
.venv/bin/python scripts/evaluate_prospective_panel.py --verify --reference-format pair_set_zero_based_v1
```

Preparation checks exact sequence identity, known PDB/family/clan overlap and
prior sequence exposure. Complete WUSS contacts map to zero-based sequence
coordinates without deletion. Crossing references are supported; missing paired
columns remain `unsupported_reference`. A mismatch/unbalanced annotation blocks
binding. Partial references must not be replaced or assigned zero F1.

The final evaluation plan and source/reference format are saved before inference.
Every selected record is registered in a durable `test_started` event before
model prediction or native folding, including unsupported records. Those families
are then consumed for fresh-test planning. Every record × method retains an
outcome. Failed/missing predictions and unsupported references have null metrics;
successful predictions are scored against all reference contacts. Aggregates
report measured and planned counts explicitly.

Native requests remain bound to sequence, method, parameters and manifest.
Interrupted outcomes remain unknown and are not retried. An unfinished run can
be resumed with its directory and the same reference-format argument; changed
code/runtime/input bindings reject resumption. Completed `--verify` uses its
frozen ledger, replays the model outputs and scores, and performs no native folds
or new test exposure.

## Artifacts and interpretation

Pair-set results use separate `prospective_pair_binding` and
`prospective_pair_evaluation` names, including unique per-run directories.
Rows include `reference_has_crossing_pairs`; the summary reports the number of
complete crossing references. Existing legacy result files are preserved.

This integration was validated with constructed complete/incomplete references
and injected predictions/native fixtures. These are pipeline tests, not new
biological measurements. Known-overlap checks do not certify unknown
training-family or legacy-tool independence. Computational consensus agreement
does not establish biological stability or retained function.

RF00059/RF00162/RF00167 and earlier test families remain consumed. Do not use
this new format to rerun their existing panel as a fresh test or tune its models
from those outcomes. A new evaluation requires a separately frozen source panel.
