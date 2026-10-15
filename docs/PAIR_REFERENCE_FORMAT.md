# Complete pair-set reference format

Both reference and prediction JSON objects require `schema_version: 1` and
`format: "pair_set_zero_based_v1"`. References also require a `dataset_id`.
Coordinates are zero-based and bound to the exact supplied RNA sequence.

Each reference record contains `id`, `sequence`, `pairs`, `reference_kind` and
`source`. `reference_kind` is one of `synthetic_control`, `computational` or
`experimental`. Optional `family_id` and `pdb_accession` are retained in the
exposure event. Provenance labels are caller-supplied evidence.

```json
{
  "id": "crossing_fixture",
  "sequence": "GGAAACAC",
  "pairs": [[0, 5], [2, 7]],
  "reference_kind": "synthetic_control",
  "source": "Constructed example"
}
```

Every pair is `[left, right]` with integer coordinates satisfying
`0 <= left < right < sequence_length`. Every nucleotide has at most one partner.
Crossing contacts are retained. Pair chemistry and minimum loop size are not
inferred or filtered. Complete sequences are bounded to 10,000 nt.

Predictions require a nonempty `methods` list and `records`. Each record has
`id`, exact matching `sequence`, `method` and `status`. An `ok` record supplies
exactly one of `pairs` or `structure`; structures use complete nested `.()`
notation. `error`, `timeout` and `unavailable` records require a reason in
`error` and contain neither representation. An absent prediction remains
`missing` in the planned method/reference matrix.

For the example above, a nested prediction containing only `[0,5]` has precision
1, recall 0.5 and F1 2/3. A prediction containing both contacts has F1 1. No
contact is removed from the reference denominator to make the prediction fit.
Two empty contact sets score F1 1; failed/missing predictions have null metrics.
Aggregates are macro means over measured records, separated by reference kind.

`run_evaluation` validates the whole input before creating a run, freezes the
original JSON bytes and records validation exposure before scoring. Snapshot,
metric, exposure and per-run CSV/report replay is available through `--verify`.
The scorer performs no folding, inference, training or model selection.

`bind_pair_reference` in `prospective_binding.py` maps a selected alignment
member and complete WUSS contacts to this representation. Sequence equality and
hashes are checked after explicit uppercase/T-to-U normalization and gap removal.
Every annotated paired column must contain a residue. Letter-pair pseudoknots
are preserved. Missing paired columns are rejected rather than deleting contacts.

The older dot-bracket evaluator and completed prospective results remain intact.
The current model decoder predicts nested structures. Pair-set scoring expands
evaluation coverage; it does not establish new model accuracy, family
independence or biological stability.
