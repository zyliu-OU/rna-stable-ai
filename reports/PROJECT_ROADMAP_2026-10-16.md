# RNA-StableAI development roadmap — 2026-10-16

Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Status: active research development; no validated release.

## Current scope

Active development now focuses on RNA sequences shorter than 5,000 nt. The
exclusive boundary places 1–4,999 nt in active scope and 5,000 nt or longer in
preserved, deferred scope. Method-specific limits such as 512 or 1,024 nt still
apply where they are stricter.

Existing longer-sequence code, synthetic inputs, configurations, results,
reports and provenance remain retained and replayable. They will not be
deleted, truncated or counted toward active-scope validation claims. See the
[length policy](../docs/LENGTH_SCOPE.md).

## Scientific position

The seven-stage plan remains otherwise unchanged from the
[2026-10-15 roadmap](PROJECT_ROADMAP_2026-10-15.md). Independent biological
structure validation remains the current gate. The first frozen fresh-contact
panel produced 12 informative references but no family with three, so its
readiness gate failed and the cohort is exposed.

A second metadata-only, sequence-diversity-oriented panel exists only as an
unverified draft. It remains bounded to 512 nt and therefore fits within the
new project focus, but it must be reviewed and tested before any freeze or
acquisition. No model inference is authorized.

Long biological RNA work at 5,000 nt or above is deferred rather than removed.
The prior synthetic 5,000/10,000-nt studies remain historical engineering and
resource evidence, not biological validation.

## Next work

Review the draft second-panel configuration, planner and tests. If they pass
scientific and software review, freeze the metadata-only plan before reading
candidate sequences or contact labels. Continue enforcing annotation lineage,
exposure, coverage and tool-training provenance gates. Do not schedule new
5,000-nt-or-longer experiments unless the project scope is explicitly revised.
