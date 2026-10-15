# RNA-StableAI measured-assay proxy review — 2026-10-13

Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Run: `results/degradation_pilot_runs/20261014T014758.273076Z`.
Protocol: [MEASURED_DEGRADATION_PILOT.md](../docs/MEASURED_DEGRADATION_PILOT.md).
Figure: [all declared comparisons](../results/degradation_pilot_figures/20261014T015409.276053Z/assay_proxy_correlations.png).
Vector export and provenance are retained alongside the PNG.

Implemented the frozen external measured-proxy assessment without fitting,
calibration, checkpoint selection or changing inference defaults. All64 declared
sequence IDs and five assay vectors remain fixed. All384 predictions and2880
proxy-assay rows complete;180 aggregate entries retain empty/constant slices.
A selected exposure event preceded every model/native request. All128 native
requests completed, zero unknown, with11.229217 known wall seconds.

## Descriptive correlations

Spearman rho on the64 selected quality1 constructs. Unpaired fraction uses the
exact scored prefix. Native energy/nt uses the complete sequence. GC is a
sequence-only control. All-unpaired correlations are undefined, not zero.

| Proxy | Reactivity | Mg/pH10 degradation | pH10 degradation | Mg/50C degradation | 50C degradation |
|---|---:|---:|---:|---:|---:|
| Baseline unpaired | 0.2568 | 0.0647 | 0.2691 | 0.2799 | 0.3707 |
| Stack unpaired | 0.5171 | 0.3629 | 0.5145 | 0.5472 | 0.5367 |
| Helix unpaired | 0.4402 | 0.2912 | 0.4884 | 0.5544 | 0.5703 |
| All unpaired | null | null | null | null | null |
| ViennaRNA unpaired | 0.5192 | 0.2876 | 0.5830 | 0.6201 | 0.5704 |
| LinearFold unpaired | 0.5290 | 0.2948 | 0.5914 | 0.6295 | 0.5796 |
| ViennaRNA energy/nt | 0.6464 | 0.4830 | 0.6340 | 0.7601 | 0.8077 |
| LinearFold energy/nt | 0.6464 | 0.4830 | 0.6340 | 0.7601 | 0.8077 |
| Scored-prefix GC | -0.6051 | -0.4126 | -0.5708 | -0.5958 | -0.6152 |

Within this cohort, native energy per nucleotide has stronger degradation
associations than the learned unpaired-fraction proxies. GC alone is also
associated with the measurements, so the table cannot isolate the contribution
of structural predictions. Matching native coefficient rows are not independent
replication. Differences between learned methods must not select checkpoints
or architecture from these observed measurements. Keep defaults unchanged.

## Scope and limits

The pinned public author file has1589 processed rows, and the pilot uses its first64
lexicographic IDs. All selected quality flags are1; quality0/unknown slices remain
empty and all/quality1 statistics duplicate the same cohort. Shared construct
flanks, experimental dependencies, source processing and the nonrandom pilot
selection limit generalization. No p-values, independent confidence intervals or
noise weighting are reported. Error vectors remain retained. Negative normalized
measurements are not clipped, and supplied predicted structures or derived
half-lives are not used as truth.

Folding uses37C and fixed defaults while chemical assay conditions differ.
LinearFold's beam100 energy is not guaranteed to be a global minimum. A mean
normalized assay value is not a whole-RNA half-life. Associations between
absolute sequence properties and assays do not establish the effects of the
project's mutations, long biological accuracy, cellular stability or retained
function. All imported source sequences remain exposed for future planning.

## Verification and next work

Twenty new evaluator checks cover complete/missing outcomes, exact prefix ranks,
constant/empty slices, stale results, model/input/source association gates,
environment/runtime changes, event-before-native ordering, raw-output tampering,
and interrupted/partial-run recovery without retry. The combined source/binding/
evaluator set passes55 checks. Full suite: **663 passed in219.22seconds**.

Complete replay recomputes model outputs and every proxy/aggregate, verifies
source/model/code/runtime/exposure bindings, and reads retained native ledgers
and raw hashes without new native requests or exposure. The final source-bound
PNG/SVG figure was inspected and retains all nine proxy rows and five assays.
Ruff, compileall and whitespace checks pass. No Git index changes or publication.

Before further core-code development, preserve executable source versions for
historical replay. Current runs bind absolute code paths and some diagnostics
compare the current source inventory, which complicates future module changes.
Audit code-snapshot coverage, archive exact available bytes with their hashes,
report missing historical versions honestly, and establish a versioned replay
path before editing shared model/data/decoder modules. This is an engineering
provenance step, not further tuning on these measurements. Longer biological
annotations and controlled mutation/function measurements remain pending.

Logs under `reports/`: `degradation-pilot-final-focused-2026-10-13.log`,
`degradation-pilot-freeze-2026-10-13.log`, `degradation-pilot-evaluation-2026-10-13.log`,
`degradation-pilot-audit-2026-10-13.log`, `degradation-pilot-full-suite-2026-10-13.log`,
`degradation-pilot-figure-final-2026-10-13.log`.
