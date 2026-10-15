# Development candidate diagnostics

Run the fixed-checkpoint diagnostic and its replay audit:

```bash
.venv/bin/python scripts/analyze_candidate_development.py
.venv/bin/python scripts/analyze_candidate_development.py --verify
```

The input is the existing completed nine-fit head study and its frozen 47-record
validation cohort. The script verifies retained summaries, predictions, checkpoint
hashes and identities before inference. It writes a unique run with frozen input
and code hashes, then records a validation exposure before scoring. No prospective
panel is loaded, and no fitting, native folding or checkpoint selection occurs.

Each reference contact has exactly one category, evaluated in this order:

| Category | Meaning |
|---|---|
| `illegal_reference` | Noncanonical chemistry or endpoint distance below four; the gold contact remains counted. |
| `nonpositive_logit` | Legal gold contact with a score at or below zero. |
| `positive_not_retained` | Positive gold contact outside the original top-16 pool per right endpoint. |
| `retained_not_decoded` | Gold contact is available in the pool but absent from the saved prediction. |
| `recovered` | Gold contact appears in the saved prediction. |

The decoder maximizes logits under structural constraints. A retained missed
contact need not indicate a decoder bug: competing, incorrect contacts may have
higher scores. Predicted false positives are reported separately. Candidate pairs
must be distinct, legal and positive; predictions must be subsets of the pool.
Gold logits must cover every legal reference contact and be finite. The direct
gold-score calculation and tiled pool must agree on retained positive gold pairs;
any sign discrepancy is rejected rather than silently classified.

Contact counts sum across records. Mean F1 weights records equally. Three
initialization seeds reuse the same labels, so their counts do not represent three
independent biological cohorts. Empty provenance groups retain zero counts and
unknown mean F1.

Artifacts use `candidate_development` names. The CSV preserves all 423
checkpoint-record outcomes, including reference exclusions and false positives.
Verification checks source/code/input bindings, the retained summary and exposure
event, then recomputes the diagnostic without new exposure events or native folds.
Audit does score the development sequences again; it is not a test-set evaluation.

The first run shows both sparse-pool loss and competition among retained contacts.
A future candidate-budget comparison must declare its grid before new decoding,
include all nine checkpoints and all 47 records, retain runtime/storage costs,
and be labelled posthoc development tuning. The original checkpoints were chosen
with top-16 pools; a different pool does not imply joint epoch/budget selection.
No development-selected setting should be retroactively scored on consumed
prospective panels as fresh independent evidence.
