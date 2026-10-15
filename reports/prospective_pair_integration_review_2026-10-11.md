# RNA-StableAI prospective pair-set integration — 2026-10-11

Workspace: `/home/zyliu/Documents/rna-stable-ai`.

Integrated the complete pair-set scorer into prospective source binding,
evaluation and audit. Future source protocols can declare
`reference_format: pair_set_zero_based_v1` before metadata acquisition.
Historical configurations without that field retain dot-bracket scoring and
their existing result artifacts. New pair-set studies write separate binding
and evaluation publications.

Complete crossing WUSS contacts now become supported references under the
declared pair-set mode. Missing annotated paired columns remain unsupported,
with no contact deletion or record replacement. Nested model/native outputs
are scored against all reference contacts; the prediction decoder itself remains
unchanged. Crossing-reference flags and counts are retained in rows/summaries.

## Pipeline verification

Seven new tests cover format binding before acquisition, prevention of legacy
fallback, exact crossing-contact scoring, unsupported/failed denominator
accounting and the complete prepare/evaluate/audit workflow. The end-to-end
fixture has one complete crossing reference and one incomplete reference across
six methods: 12 planned outcomes, six measured and six unsupported. Two injected
native callbacks are journaled. Exposure is asserted before model/native calls;
offline audit performs no native callbacks. Reuse of the consumed fixture family
and a mismatched resume format are rejected. Altered prediction files fail audit.
Fixtures are constructed examples, not acquired Rfam families or model-accuracy
measurements.

The expanded focused set passes 64 checks, including the existing completed
prospective-panel replay. Trained checkpoint bytes and completed biological-panel
artifacts remain unchanged. No new model fitting, fresh biological test,
checkpoint/decoder selection or accuracy gain is claimed. Final full-suite
results are recorded in the versioned handoff.

## Next work

Freeze a new panel with unexposed family IDs and the pair-set field before source
outcomes. Acquire and verify its metadata/provenance/annotations, then prepare
its fixed all-record evaluation plan. Broader source independence, long biological
RNA annotations and experimental stability/function remain unresolved.
