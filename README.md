# RNA-StableAI

**Status: work in progress — research prototype.** This project records ongoing
development and measured experiments. No release or trained model is published.

V1 research pipeline for deterministic 1,000–10,000 nt RNA controls, CPU folding
benchmarks, and a separate untrained PyTorch encoder throughput baseline.

Eight FASTA controls cover four lengths and two sequence types. Structured controls
repeat designed reverse-complement stems and loops; mixed controls alternate GC-rich,
AU-rich and balanced blocks. Seeds, sequence hashes and configuration accompany every run.

CPU folding uses RNAfold when available or ViennaRNA Python bindings in a subprocess.
LinearFold-V uses beam 100 and reports approximate minimum energy in kcal/mol;
LinearPartition-V uses partition-only mode and reports ensemble free energy, not MFE.
These tools are benchmarked on CPU. Each invocation has a 120-second timeout and an
8 GiB per-process address-space cap. Wall time includes startup. GNU time reports
maximum RSS when available; failed/timeout/unavailable values remain blank.

The separate encoder embeds A/C/G/U tokens and uses Conv1d, GELU and mean pooling.
It has no attention matrix, uses fixed random weights, and performs inference only.
CPU median wall time, GPU median CUDA event time, pinned H2D transfer time, batch size
and peak allocated/reserved GPU memory are distinct fields. CUDA failures are explicit
skips. A CPU encoder measurement is not an RNA folding measurement.

The latest publication review is recorded in
`reports/github_update_review_2026-10-07.md`. It distinguishes completed studies
from the unfinished second helix replication. Older status reports retain their
original checkpoint dates.

## Install locally

```bash
cd rna-stable-ai
python3 scripts/setup.py
.venv/bin/python -m rnastable doctor
.venv/bin/python -m pytest -q
```

Setup prefers uv and installs Python 3.12 and packages into project-local locations.
It preserves existing environments, records commands, and attempts each C++ tool even
when Python setup fails. The CUDA 13.0 PyTorch wheel requires an operational compatible
driver; it does not alter the installed toolkit. Select another official wheel index
if deploying on a different driver. Inspect upstream sources and installed versions
before assuming the setup succeeded. Successful environment freezes and tool Git hashes
are logged for pinning subsequent runs. Package specifications are unpinned until a
successful installation produces a lock. The recorded host freeze is included in reports/.

ViennaRNA pip installation supplies CPU bindings; a separately installed RNAfold is
preferred if discovered on PATH or under external/vienna/bin. Upstream references:
[ViennaRNA](https://www.tbi.univie.ac.at/RNA/documentation.html),
[LinearFold](https://github.com/LinearFold/LinearFold),
[LinearPartition](https://github.com/LinearFold/LinearPartition),
[EternaFold](https://github.com/WaymentSteeleLab/EternaFold),
[PyTorch](https://pytorch.org/get-started/locally/).
EternaFold is an optional source-build attempt, not part of the V1 timing comparison.

## Run

```bash
./scripts/rnastable generate --config configs/benchmark.json
./scripts/rnastable benchmark --config configs/benchmark.json
```

`rnastable` is installed as a console entry point when setup succeeds. The executable
`scripts/rnastable` also works directly from any directory, selecting .venv if present
and otherwise the existing python3. `--output-root` supports isolated result directories.
Existing FASTA files are accepted only if identical; differing content is preserved and
rejected. Prior benchmark CSV/JSON/report files are copied to results/runs before new
results are written. Every folding subprocess stores raw stdout/stderr under results/raw.

The host setup has succeeded with Python 3.12.14 and the project-local dependencies.
The saved benchmark has 23 successful CPU folds, one 120-second ViennaRNA timeout,
and four successful GPU encoder runs. The original restricted-session failures are
retained as historical command records. See reports/installation_summary.md for the
recorded versions and tool Git hashes, and reports/environment-*.lock.txt for the
successful package freeze.

Results are at results/folding_benchmark.csv, results/gpu_benchmark.csv,
results/benchmark_summary.json and reports/benchmark_report.md.

Tests validate generation, FASTA preservation, input and length handling, descriptive
scores, real subprocess failure/timeout handling, output parsing, CLI behavior, and
archival of prior results. They do not claim real folding integrations passed when
tools are absent. These benchmark commands do not train a neural network; the separate
processed-PDB training pilot is described below.

## Compare folds and optimize

```bash
./scripts/rnastable report
./scripts/rnastable compare-folds --retry-timeout 300
./scripts/rnastable optimize --config configs/optimization.json
.venv/bin/python scripts/verify_optimization.py
```

Comparison reuses existing raw folds after validating the exact input sequence hash.
The optional longer timeout retries missing ViennaRNA references without changing the
original benchmark. Pair precision/recall/F1, Jaccard agreement and base-pair distance
use ViennaRNA as a computational reference. LinearFold structures are independently
reevaluated with current ViennaRNA parameters to distinguish parameter differences from
search approximation. Outputs: results/folding_quality.csv,
results/folding_quality_summary.json and reports/folding_quality_report.md.

The default optimization is a 48-proposal CPU hill climb on the mixed 1,000-nt control,
with fixed seed 2718, beam 100 and at most 40 changed positions relative to input.
It accepts energy improvements of at least 0.1 kcal/mol. Swapping different nucleotides
preserves length, GC count and every nucleotide count. Configured protected positions
use one-based coordinates. Each proposal is bounded by time and memory limits; failures
are logged and do not prevent later proposals. The input and finalist receive separate
ViennaRNA CPU validation, with a 300-second timeout. A lower surrogate score can fail
independent validation; that outcome is reported explicitly.

For a full coding sequence, `--coding --input path/to/cds.fasta` uses synonymous codon
substitutions, preserves GC count, and checks the translated sequence. This mode requires
full codons in frame 0, genetic code 1, and 1,000–10,000 nt; it does not infer CDS/UTR
boundaries. Stop codons are fixed. Noncoding mode is the default for synthetic controls.

Outputs: results/optimization_history.csv, results/optimization_history_summary.json,
reports/optimization_history_report.md, and immutable results/optimization_runs/<UTC>/
directories containing input/finalist/selected FASTA, raw folds and complete summaries.
All replaced reports have archived copies. Successful search demonstrates optimization
of computed energy, not biological stability. No training is included.

Next, repeat the search across independent seeds and sequence types, then assess against
experimental reference structures and application-specific constraints before expanding
the objective or considering a learned surrogate.

## Evaluate consistency across seeds and beams

```bash
./scripts/rnastable evaluate --config configs/evaluation_sweep.json
.venv/bin/python scripts/verify_sweep.py
```

The default CPU pilot contains 36 runs: 1,000 nt, structured and mixed controls,
three sequence seeds, two search seeds and beams 50/100/200. Each search receives
24 proposals and a 40-position mutation budget. Lengths up to 10,000 nt are supported
by the configuration, but the default pilot only establishes behavior at 1,000 nt.
Larger grids can take substantially longer because every finalist is folded with
ViennaRNA on CPU. There is no GPU folding or training in this evaluation.

Beam comparisons share input sequences and search seeds, with equal proposal budgets.
Their accepted mutations and later trajectories can differ. Input ViennaRNA references
are cached once per exact sequence within the run. Shared reference timings are not
independent timing measurements. Each row retains the search status, failed proposals,
input/finalist agreement, energy changes, runtime, input/finalist hashes, and raw evidence.

Outputs:

- results/evaluation_sweep.csv: individual runs
- results/evaluation_sweep_aggregate.csv: kind/length/beam summaries
- results/evaluation_sweep_summary.json: complete run metadata and evidence paths
- reports/evaluation_sweep_report.md: results, limitations and CPU tradeoff figure
- results/sweep_runs/<UTC>/: input/finalist FASTA, raw folds, cell summaries and checkpoint

Failed validations stay missing and are reported separately from unchanged/worsened
scores. Search repeats share inputs and are not independent biological samples; the
small pilot does not support population-level or statistical-significance claims.

To resume an interrupted grid, use the same configuration and the run directory printed
in the progress/report, for example:

```bash
./scripts/rnastable evaluate --config configs/evaluation_sweep.json --resume results/sweep_runs/<UTC>
```

Resume verifies configuration, code, tool binary and environment version fingerprints,
input identity, and finalist constraints before reusing completed cells. Interrupted
attempts are retained; a cell without a saved summary is rerun in a new attempt directory.
Completed failures remain explicit failures when resumed. Ctrl-C kills the active folding
process group. Existing reports and summaries are archived before replacement.

## Bounded long-sequence scaling pilot

```bash
./scripts/rnastable evaluate --config configs/evaluation_long.json
.venv/bin/python scripts/verify_sweep.py
.venv/bin/python scripts/summarize_long.py
```

This pilot covers 2,000/5,000/10,000 nt, both synthetic sequence types, beam 200,
sequence seed 1729 and search seed 2718. Each search has eight proposals, a 40-position
mutation limit, a 60-second LinearFold timeout, and a 600-second ViennaRNA validation
timeout. Per-process address space remains capped at 8 GiB. Reference and finalist
energy/structure comparisons are performed on CPU; there is no training.

This is a scaling check with one input/search seed per kind and length, not an
independent replication study. Its proposal budget is smaller than the 1,000-nt sweep's
24 steps; absolute improvements must not be compared as though budgets were equal.
One timing per fold includes process startup and is not a statistical timing estimate.

Latest generic results are published as evaluation_sweep.* with archived prior copies.
The long-pilot summary script also saves results/evaluation_long_summary.json,
results/evaluation_long.csv, results/evaluation_long_aggregate.csv,
reports/long_sequence_report.md and a length-scaling figure within the immutable run
directory. Every raw fold and finalist remains in results/sweep_runs/<UTC>/.

Resume with the original configuration and run directory:

```bash
./scripts/rnastable evaluate --config configs/evaluation_long.json --resume results/sweep_runs/<UTC>
```

## Long mixed-RNA replication and paired beams

```bash
./scripts/rnastable evaluate --config configs/evaluation_replication.json
.venv/bin/python scripts/summarize_replication.py
.venv/bin/python scripts/verify_sweep.py --summary results/evaluation_replication_summary.json
.venv/bin/python scripts/verify_replication.py
```

This 18-search study pairs beams 200/400 on mixed RNA at 2,000, 5,000 and
10,000 nt with input seeds 1729/1730/1731 and search seed 2718. Each search
uses eight proposals, at most 40 changed positions, a 120-second LinearFold
timeout, 600-second ViennaRNA timeout, and 8 GiB per-process address-space cap.
All folds run on CPU. No training occurs. Three synthetic inputs per length
are a small replication check; search-seed and timing variability remain unmeasured.

The reporter saves separate evaluation_replication CSV, aggregate CSV, paired
CSV and summary JSON plus reports/replication_report.md. Original long-pilot
artifacts stay preserved. The sweep retains raw evidence and checkpoints.
Resume with the identical configuration and recorded directory:

```bash
./scripts/rnastable evaluate --config configs/evaluation_replication.json --resume results/sweep_runs/<UTC>
```

## Reference-confirmed output selection

Use `selected.fasta` as the optimization output. `finalist.fasta` retains the
LinearFold search candidate for research and audit. Both `optimize` and `evaluate`
select the finalist only if search completed and both ViennaRNA folds succeeded
with finite energies, with the finalist lower by more than 1e-9 kcal/mol.
Equal/worse energy, unchanged sequence, failed search or failed validation returns
the original input. Missing input reference energy remains unknown; returning the
input does not claim a measured energy or biological stability.

Summaries include selection source/reason, selected FASTA/hash, changed positions
and selected reference-energy change. Existing candidate mutation counts, scores,
validation statuses and sweep improvement/worsening aggregates retain their original
meaning, before output selection. Every proposed finalist and raw fold is retained.

```bash
./scripts/rnastable optimize --config configs/optimization.json
.venv/bin/python scripts/verify_optimization.py
./scripts/rnastable evaluate --config configs/evaluation_selection_smoke.json
.venv/bin/python scripts/verify_sweep.py
```

Review the completed long replication without rerunning its folds:

```bash
.venv/bin/python scripts/review_selection.py --summary results/evaluation_replication_summary.json
.venv/bin/python scripts/verify_selection_review.py
```

The review creates new selected FASTAs under results/selection_reviews/<UTC>/ and
separate selection_review CSV/JSON/report artifacts. It audits saved raw evidence
first and records source hashes; it is not a new folding benchmark. Previously
completed runs remain auditable. Resume requires the code/tool/environment
fingerprint from the run's manifest, now including selection.py.

## Search-seed robustness

```bash
./scripts/rnastable evaluate --config configs/evaluation_robustness.json
.venv/bin/python scripts/summarize_robustness.py
.venv/bin/python scripts/verify_robustness.py
```

This 36-search CPU study uses mixed inputs at 1,000/2,000 nt, three input
seeds, three search seeds and paired beams 200/400, with eight proposals each.
Per-input CSVs report search variability, selected output diversity and candidate
worsenings. Across-input summaries average search repeats within each input first,
then give inputs equal weight. Failures and unknown selections stay explicit.
Three synthetic inputs per length support descriptive results, not population
claims or generalization of search variability to 5,000/10,000 nt.

Outputs: results/evaluation_robustness{,_inputs,_groups,_pairs}.csv,
results/evaluation_robustness_summary.json, reports/search_robustness_report.md
and a standalone search_variability.png in the recorded sweep directory.

## Explicit protected intervals

Constraint schema version 1 requires input_sha256 matching the uppercase RNA
sequence (not the FASTA file bytes). protected_positions are one-based coordinates;
protected_regions contain one-based inclusive start/end and an optional label.
Intervals may overlap; protection is their union plus configured protected positions.
Region labels are user-supplied descriptions; no biological annotation is inferred.
Each optimization summary records the constraint file path/hash, coordinate system,
regions and complete merged position list. Protein preservation remains the existing
full-codon frame-0/code-1 mode; interval protection applies in both modes.

The example below protects two synthetic 24-nt intervals and position 1000 on
mixed_1000_seed1729. It is a demonstration, not a biological annotation.

```bash
./scripts/rnastable optimize --config configs/optimization_protected_demo.json --constraints configs/constraints_synthetic_example.json --dry-run
./scripts/rnastable optimize --config configs/optimization_protected_demo.json --constraints configs/constraints_synthetic_example.json
.venv/bin/python scripts/verify_optimization.py
```

Dry-run validates a single input, length, sequence identity, coordinate bounds and
protein mode without calling fold tools or creating optimization outputs.

## Live command logging

```bash
.venv/bin/python scripts/log_command.py ./scripts/rnastable evaluate --config configs/evaluation_robustness.json
```

New logged commands stream progress directly, save a durable start event in
reports/command_starts.jsonl, and append completion/output/exit code to
reports/commands.jsonl with a matching command ID. Ctrl-C is forwarded to the
owned child and recorded as an interruption. Existing completed records remain
compatible. The logger accepts --log-dir before its command for isolated runs.

## Long search-seed robustness with bounded CPU batches

```bash
.venv/bin/python scripts/run_robustness_batches.py --config configs/evaluation_robustness_long.json --workers 2
.venv/bin/python scripts/summarize_robustness.py --config configs/evaluation_robustness_long.json --name robustness_long
.venv/bin/python scripts/verify_robustness.py --summary results/evaluation_robustness_long_summary.json
.venv/bin/python scripts/verify_batch_study.py
```

This bounded study covers mixed RNA at 5,000/10,000 nt, two input seeds
1729/1730, two search seeds 2718/2719 and beams 200/400: 16 searches,
eight proposals each. Each independent input runs its beam/search cases serially
with shared input references. At most two input batches run concurrently.
Concurrent wall times include contention and are not isolated folding benchmarks.
The original CPU/GPU benchmark measurements remain preserved.

Each component has separate logs, raw fold evidence and checkpoints. The parent
merges actual rows in planned order and records concurrency/provenance. A child
failure does not stop other batches; an incomplete parent is recorded explicitly.
No aggregate completion is published until all component commands succeed.
Interrupted attempts are retained; Ctrl-C is forwarded to owned child processes.

Resume using the batch runner and the parent directory printed at startup:

```bash
.venv/bin/python scripts/run_robustness_batches.py --config configs/evaluation_robustness_long.json --workers 2 --resume results/sweep_runs/<UTC>
```

Configuration, worker count, driver/logger code, core code, binaries and
environment fingerprints must match. Completed cells are reused by their component
sweeps. Use the batch runner to resume a batched parent rather than the serial
evaluate command, since parent evidence is stored in component directories.

Reporting accepts --config and --name; long results are published separately as
evaluation_robustness_long CSV/JSON artifacts and search_robustness_long_report.md.
Short-study results remain separately saved. Only two inputs per long length are
replicated; these descriptive results do not establish population performance.

### Batch audit evidence

The batch runner saves native, durable events for each driver attempt under
results/sweep_runs/<UTC>/driver_events/<attempt>/events.jsonl. Its final status
references the event log, so verify_batch_study works for direct invocations
without an outer log_command wrapper. Incomplete or over-limit native traces
fail verification; they do not silently fall back to other evidence.

Older completed runs use saved outer command output when available. Direct older
runs can instead audit the latest successful per-component CLI intervals from
their existing command logs. The audit labels this narrower evidence explicitly:
parent startup/teardown concurrency is unavailable for those old runs. Original
folds and historical driver records are retained; no events are reconstructed.

## Choose among validated search restarts

```bash
./scripts/rnastable select-portfolio --summary results/evaluation_robustness_long_summary.json
.venv/bin/python scripts/verify_portfolio.py
```

The portfolio command first audits the entire completed source sweep, including raw
folds, proposal decisions, constraints and input hashes. It then chooses the lowest
confirmed ViennaRNA energy for each exact input across its saved seeds and beams.
Equal energies are resolved deterministically by job ID. Input references must agree;
all candidates must use the source sweep's constraints and parameters. Failed searches
and missing validation cannot win. With no eligible improvement, it returns the input;
unknown input energy remains null.

Outputs include one selected FASTA per input under results/portfolio_runs/<UTC>/,
results/portfolio.csv, results/portfolio_summary.json and reports/portfolio_report.md.
The summary retains every candidate decision and source evidence hashes, selected seed
and beam, attempted proposal count and original environment versions. Source artifacts
remain intact, and reruns archive previous portfolio summaries/reports.

The saved long study selects four improved outputs from 16 searches / 128 proposals.
Changes are -5.70 and -4.20 kcal/mol for its two 5,000-nt inputs, and -5.20 and -4.23
for its two 10,000-nt inputs. Each output used four searches / 32 attempted proposals.
This best-of-several selection is descriptive on these inputs; it is not a held-out
performance estimate or evidence of biological stability. No new folding or training
is performed by this command.

## Prospective equal-proposal-budget comparison

```bash
./scripts/rnastable compare-search-budgets --config configs/evaluation_equal_budget.json
.venv/bin/python scripts/verify_equal_budget.py
.venv/bin/python scripts/summarize_equal_budget.py
```

This CPU pilot fixes its configuration and provenance manifest before measuring
new mixed synthetic input seeds 1732–1734 at 1,000/2,000 nt. It compares one
32-proposal search against four 8-proposal restarts at beam 200, with the same
40-position mutation cap and constraints. The long seed 2740 also serves as the
first restart; the remaining restart seeds are 2741–2743. Each arm uses the same
confirmed-ViennaRNA portfolio selection policy, including input fallback.

Equal proposal caps do not equalize total CPU work. Each restart requires another
LinearFold baseline and can require another ViennaRNA candidate validation. The CSV
records actual attempted proposals, folding-adapter request counts, search wall time
(which already includes its baseline), input reference wall time counted once per
arm/input, and finalist validation time separately. Duplicate/no-legal-proposal events
do not request a fold. Tool unavailability may prevent a request from spawning a process.
Missing costs remain unknown. A failed candidate validation makes its paired outcome
unknown even when a selected sequence is available.

Results are isolated under results/equal_budget_runs/<UTC>/long and restarts, with
separate source sweeps, portfolios, raw folds and logs. Root outputs are
results/equal_budget.csv, results/equal_budget_summary.json and
reports/equal_budget_report.md. The original robustness studies are preserved.
The summarizer adds reports/equal_budget_cost_report.md, a versioned standalone
paired energy/cost figure, and results/equal_budget_cost_summary.json after auditing
the study. It separates search, input-reference and candidate-validation costs.
The audit checks both full source sweeps and portfolios, fixed job coverage, paired
input/reference identity, budgets, costs, file hashes and aggregate denominators.

```bash
./scripts/rnastable compare-search-budgets --config configs/evaluation_equal_budget.json --resume results/equal_budget_runs/<UTC>
```

Resume requires identical study configuration, frozen arm configs, code/tool hashes
and environment versions. Saved trajectories are reused; execution attempts are
recorded separately and their elapsed time is not substituted for original search
costs. A failed arm is recorded and the other arm continues. No successful combined
summary is published until both arms have been completed and audited.

This small paired synthetic pilot measures descriptive outcomes. It does not support
a statistical, timing speedup, biological-stability or 5,000/10,000-nt claim. Arms run
serially in a fixed order. No neural training is performed.

## Bounded long-input budget replication

```bash
./scripts/rnastable compare-search-budgets --config configs/evaluation_equal_budget_long.json --workers 2
.venv/bin/python scripts/verify_equal_budget.py --summary results/equal_budget_long_summary.json
.venv/bin/python scripts/summarize_equal_budget.py --summary results/equal_budget_long_summary.json --name equal_budget_long
```

The long pilot fixes new mixed inputs at 5,000/10,000 nt with sequence seeds
1735/1736 before measuring them. It retains beam 200, search seeds 2740–2743,
one 32-proposal search versus four 8-proposal restarts, and a 40-position mutation
cap. ViennaRNA validations have a 600-second timeout. Four paired inputs yield
20 searches and a planned total of 256 proposals across the two arms.

`--workers 2` runs at most two owned input studies concurrently; each child folds
serially and runs its long arm before its restart arm. Concurrent wall times can
include contention and are labeled accordingly. They are not isolated benchmark
timings. Without --workers the original serial command remains available.

The parent freezes config, provenance and each sequence's component config before
launching children. Native, durable events record starts, completions and heartbeats
for each driver attempt. Component failures do not stop other inputs; an incomplete
parent does not publish a successful combined summary. Ctrl-C cleans up owned child
groups and records interruption. Full per-input sweeps, portfolios, command logs,
attempts and raw folds are retained under results/equal_budget_batch_runs/<UTC>/.

```bash
./scripts/rnastable compare-search-budgets --config configs/evaluation_equal_budget_long.json --workers 2 --resume results/equal_budget_batch_runs/<UTC>
```

Resume requires unchanged config, workers, code/tool/environment fingerprints and
component configs. The auditor checks all child fixed plans and trajectories,
selected FASTAs, exact merged rows, cost fields, denominators and native event
concurrency. Results publish separately as equal_budget_long CSV/JSON/report and
equal_budget_long_cost JSON/report, preserving short-study outputs. Only two
synthetic inputs per long length are planned; this is descriptive replication, not
a population or biological-stability claim. No training is performed.

Batch heartbeats count rows only from the newest child run and newest live sweep
checkpoint in each arm; preserved archives and obsolete runs are excluded. The
progress helper is included in new batch code fingerprints. This driver update
intentionally rejects resume of historical batches whose frozen provenance differs,
before writing events or launching children. There is no provenance override.
Interrupted historical batches require their exact original driver, dependencies
and environment. Completed studies remain auditable without resuming or refolding:

```bash
.venv/bin/python scripts/verify_equal_budget.py --summary results/equal_budget_long_summary.json
```

The completed long study's original driver is preserved in
`reports/source_backups/20261006T004345.851559Z/src/rnastable/budget_batches.py`.
Its manifests, checkpoints and measured results retain their original provenance.

## Evaluate supplied reference structures

`evaluate-reference` scores saved predictions against a supplied reference dataset
without folding or training. This prepares the pipeline for externally sourced
structures; the included six-nucleotide examples are handwritten software controls,
not biological measurements or a held-out accuracy study.

```bash
./scripts/rnastable evaluate-reference --references configs/reference_demo.json --predictions configs/reference_predictions_demo.json --dry-run
./scripts/rnastable evaluate-reference --references configs/reference_demo.json --predictions configs/reference_predictions_demo.json
.venv/bin/python scripts/verify_reference.py
```

The reference JSON has `schema_version: 1`, a nonempty `dataset_id`, and nonempty
`records`. Every record supplies `id`, uppercase A/C/G/U `sequence`, full
dot-bracket `structure`, `reference_kind` and `source`. Reference kinds are
`synthetic_control`, `computational` or `experimental`; these are caller declarations,
not independent source verification. Preserve accession, experimental conditions
and other available metadata as additional fields in the source JSON. They are
retained in the frozen input copy. Experimental datasets and their use conditions
must be selected and checked before an experimental study is run.

The prediction JSON has `schema_version: 1`, a nonempty unique `methods` list,
and `records` (which may be empty). Each record supplies the reference `id`,
declared `method`, exact reference `sequence` and `status`. An `ok` record requires
`structure`; `error`, `timeout` or `unavailable` requires an `error` reason and no
structure. A missing method/reference record becomes an explicit `missing` result.
Unknown IDs/methods, duplicate records, changed sequences, malformed structures and
missing provenance descriptions reject the whole plan before output creation.

Only complete pseudoknot-free `.()` structures are supported. Ambiguous bases,
partial structures and pseudoknot brackets are rejected rather than converted.
Predicted and reference sequences must match exactly; optimized sequences cannot
inherit the input sequence's structure annotation. Pair precision, recall, F1,
Jaccard and distance compare exact pair coordinates. When both structures are
entirely unpaired, precision/recall/F1/Jaccard are one; when only one has pairs,
they are zero. Missing and failed predictions have blank CSV metrics and JSON nulls.
Each method and reference kind gets separate planned, measured, missing and failed
counts; means give each measured reference one vote. Compare coverage before means.

Outputs are `results/reference_evaluation.csv`,
`results/reference_evaluation_summary.json` and
`reports/reference_evaluation_report.md`. Each unique `results/reference_runs/<UTC>/`
holds exact input copies, source hashes, environment versions, scoring policy and
its own CSV/JSON/report exports. Replacing the latest report archives the earlier
publication and leaves earlier runs intact. The verifier checks frozen input hashes,
exact sequence bindings, every metric, coverage denominator and published export.
It can audit a retained run after the original input files change or disappear:

```bash
.venv/bin/python scripts/verify_reference.py --summary results/reference_runs/<UTC>/results/reference_evaluation_summary.json
```

Agreement with a supplied structure does not establish biological stability or
experimental fitness. No experimental dataset is bundled or downloaded by this command.

## Processed PDB evaluation and first training pilot

A separate authorized pilot has now trained a small CPU secondary-structure baseline.
It uses the PDB-source subset of RNA STRAND S-Processed records already distributed in
the local EternaFold archive. These annotations are derived from experimental PDB
structures and processed upstream; they are not raw experimental pair measurements.
The original synthetic studies and untrained throughput encoder remain separate.

```bash
.venv/bin/python scripts/run_experimental_pilot.py --dry-run
.venv/bin/python scripts/run_experimental_pilot.py
.venv/bin/python scripts/verify_experimental_pilot.py
```

Each execution creates a fresh `results/experimental_pilot_runs/<UTC>/` and freezes
the configuration and split plan before fitting or test folding. The fixed pilot
allows 20–256 nt, uses upstream train/holdout/test assignments, and excludes conflicting
PDB accessions, exact sequence duplicates and pairs with symmetric Python SequenceMatcher
similarity at least 0.8. Test records have priority over validation and training;
within a split the first sorted ID has priority. The heuristic is not an alignment
identity metric or an RNA-family split. Every exclusion and upstream source hash is saved.
BPSEQ conversion requires reciprocal, complete, nested pairs and preserves every
processed pair; ambiguous bases or crossing pairs are rejected without conversion.
Exact sequence matching binds BPSEQ records to PDB-source FASTA metadata.

The model embeds four RNA bases, applies two seven-position Conv1d layers, and predicts
dot/open/close labels. Class weights use training labels only. A fixed greedy stack
decoder creates nested AU/GC/GU pairs with at least three enclosed nucleotides; unmatched
sites become unpaired. This is a simple local baseline, not a global pair model.
Adam trains for 20 epochs on CPU with two threads and a fixed seed. Validation pair F1
selects the checkpoint, with validation loss and then earliest epoch breaking ties.
Test labels do not enter the fitting or checkpoint-selection API. Seeds and deterministic
algorithms apply to this environment; [PyTorch does not guarantee reproducibility across
versions/platforms](https://docs.pytorch.org/docs/2.14/notes/randomness.html).

The first run retained **41 train / 12 validation / 16 test** records. Actual lengths
were 20–76 nt in training, 21–75 nt in validation and 21–159 nt in test. All 32 native
ViennaRNA/LinearFold folds succeeded. Validation selected epoch 6; mean exact-pair F1
over the 16 test records was:

| Method | Mean pair F1 |
|---|---:|
| ViennaRNA | 0.9438 |
| LinearFold, beam 100 | 0.9438 |
| Trained CNN | 0.0675 |
| Initial untrained CNN | 0.0132 |
| All-unpaired baseline | 0.0000 |

The neural baseline falls well short of the folding tools. Training loss decreased
while validation quality deteriorated after the selected checkpoint; do not infer
long-RNA performance or biological stability. This small processed cohort does not
establish family-independent generalization, and legacy folding-tool parameter training
overlap has not been established. Test observations must not be used to tune this trial.

Outputs: `results/experimental_pilot_summary.json`, `results/experimental_pilot.csv`,
`reports/experimental_pilot_report.md`, and per-run input snapshots, exclusions,
initial/best checkpoints, epoch events, training summary, raw folds and a fully retained
reference evaluation. `verify_experimental_pilot.py` reconstructs imported data and
filters, verifies every snapshot, checks validation-only checkpoint selection, reruns
checkpoint inference without training, and audits raw sequence-bound fold outputs and
all test metrics. The prior measured studies remain preserved.

Sources: [RNA STRAND provenance](https://doi.org/10.1186/1471-2105-9-340),
[pinned EternaFold archive](https://github.com/WaymentSteeleLab/EternaFold/tree/87b9aac55cee14fd562049d08f7b92d3131f10ce),
and [EternaFold dataset description](https://github.com/WaymentSteeleLab/EternaFold/blob/87b9aac55cee14fd562049d08f7b92d3131f10ce/datasets_in_fasta_form/README.md).

## Pair-scoring development and family planning

The next development baseline scores nucleotide pairs directly. Convolutional
features feed a symmetric pair-affinity head with endpoint and distance terms.
Training uses eligible upper-triangle pairs once, with canonical AU/GC/GU contacts
and at least three enclosed nucleotides. Positive loss weight is the square root
of the negative/positive pair ratio from training labels only. Reference contacts
outside the representable set are counted explicitly; none occurred in this run.

A dynamic program chooses the maximum sum of positive logits over valid noncrossing
pairs. Unpaired sites contribute zero; ties prefer leaving the rightmost site
unpaired, then the smallest candidate partner. This adapts interval dynamic
programming to learned scores ([Nussinov and Jacobson](https://pubmed.ncbi.nlm.nih.gov/6161375/));
the scores have no physical energy units. Pair-score memory is quadratic and decoding
work cubic, so this development implementation is bounded to 256 nt.

```bash
.venv/bin/python scripts/train_pair_development.py
.venv/bin/python scripts/verify_pair_development.py
```

This command has only train and validation inputs. It creates a new immutable run,
freezes input/config/code hashes, trains 10 epochs on CPU and selects a checkpoint
by validation F1, then validation loss, then earliest epoch. The completed run used
the existing 41 development training / 12 validation records and selected epoch 10.
Validation mean pair F1 was **0.5411**, versus **0.1488** for its initial model.
These are reused development-validation scores, not independent test accuracy.
No old or new test cohort was evaluated and no native folding was rerun.
Outputs are under `results/pair_development_runs/<UTC>/`, with a latest pointer
at `results/pair_development_summary.json`. The verifier checks frozen train/validation
inputs, training-only pair counts/weights, epoch events, checkpoint hashes,
loaded-checkpoint predictions and the retained reference-evaluation exports.

Before a new family-separated experiment, `plan_family_study.py` requires four files:

- Reference JSON in the documented supplied-reference format.
- Assignment JSON with `schema_version: 1` and `records`; every reference requires
  an `id`, exact `sequence_sha256`, `family_id` and nonempty `source` for that assignment.
- Plan JSON with nonempty `train`, `validation` and `test` lists of family IDs;
  every family appears exactly once and has records.
- Exposure JSON containing a list of previously used sequences, each with `sequence`
  and `source`; include known `family_id` and `pdb_accession` when available.

```bash
.venv/bin/python scripts/plan_family_study.py --references data/new_references.json --assignments data/verified_families.json --plan configs/new_family_plan.json --exposure data/exposure.json
.venv/bin/python scripts/verify_family_plan.py --run results/family_plans/<UTC>
```

The planner automatically adds known exposures from historical pilot and pair-development
input snapshots and durable family-trial training/validation/test-start events, including
incomplete runs. The registry currently contains 125 distinct exposure records. Shared
accessions, identical/similar sequences across proposed splits, and prior-exposure
overlap with the proposed test set reject the plan before writing any outputs.
Known exposed families also reject proposed test families. The fixed sequence
heuristic is symmetric SequenceMatcher >=0.8. Valid plans freeze original inputs,
the effective exposure ledger and replayable assignments/splits; audit uses frozen
copies, allowing live input files to change or disappear.

Broad RNA-type labels are not family assignments. The local Rfam subset also supplies
explicit `EXT_ID=RFxxxxx` metadata; the comparative trial below binds each assignment
to its exact upstream FASTA sequence and BPSEQ annotation.


## Family-disjoint comparative trial

`configs/family_trial.json` fixes RF00001 (5S RNA) for training, RF00169 (bacterial
small SRP RNA) for validation, and RF00008 (type III hammerhead) for test. Legacy
RNA STRAND/EternaFold Rfam FASTA accessions are bound to exact sequences and BPSEQ
source hashes. These are processed comparative annotations, classified as
`computational` references; no direct experimental measurement is inferred.
Source: [RNA STRAND](https://doi.org/10.1186/1471-2105-9-340).

Selection uses source identity, a fixed 20–256 nt bound, prior-exposure filtering,
symmetric sequence-similarity filtering at 0.8, and a cap of 24 records per family.
It produced 24 training / 23 validation / 9 test records. Actual lengths are
27–121 / 77–104 / 40–58 nt respectively. Source archive train/holdout/test tags
are retained as provenance; this trial reassigns records by its frozen family plan.
A new randomly initialized pair model trained for 10 CPU epochs, selecting epoch 9
using validation only (mean pair F1 0.0343). All 18 native folds succeeded.

| Method | Test records | Mean pair F1 |
|---|---:|---:|
| Trained pair model | 9 | 0.0912 |
| Initial pair model | 9 | 0.0374 |
| ViennaRNA | 9 | 0.8794 |
| LinearFold | 9 | 0.8794 |
| All unpaired | 9 | 0.0000 |

The model transfers poorly across these families. There is only one family per
split; prior PDB family assignments, clan relationships and legacy folding-tool
training overlap remain unresolved. This trial establishes within-trial family-ID
separation, not population-wide generalization, long-RNA performance or biological
stability. Test observations must not select further model or training settings.

Verification does not train or select a new checkpoint:

```bash
.venv/bin/python scripts/verify_family_trial.py
.venv/bin/python scripts/verify_family_plan.py --run results/family_trial_runs/20261006T020448.519769Z/family_plan
.venv/bin/python -m pytest -q
```

The trial runner accepts `--config` and `--dry-run`. The completed default test
family is now exposed; repeating the default plan is intentionally rejected.
Prepare new test families and evidence before another trial. A durable `test_started`
event is written before any test inference or native folding, so interrupted runs
also consume the test. Historical snapshots are conservatively treated as exposure.
Outputs: `results/family_trial_summary.json`, `results/family_trial.csv`,
`reports/family_trial_report.md`, and immutable per-run family inputs, import
exclusions, manifest, exposure events, checkpoints, epoch ledger and raw folds.
The auditor reconstructs source binding and selection using the frozen pretrial
ledger, checks checkpoint selection and predictions, and audits all evaluation
exports and sequence-bound native results.

## Scalable fixed-span context development

The new `banded_pairs` implementation stores right-endpoint/pair-span scores and
interval tables in O(nw) memory and performs O(nw²) decoding work for sequence length
n and fixed maximum pair span w. A separate prefix recurrence joins complete nested
structures across the whole sequence. It is exact within the span constraint;
pairs farther apart than w are excluded. Tests compare it with the original exact
decoder on masked matrices, verify canonical/nested contacts and tie handling,
and check long-sequence array sizes. Scoring uses the same pair head in distance
slices, without constructing a full n-by-n tensor.

The original development checkpoint processed synthetic 10,000 nt with span64 in
about 9.1 seconds, with 13.12 MB combined score/DP arrays. A new 26,097-parameter
context model has four dilated convolutions (dilations1/2/4/8, receptive field91 nt)
and trains on sparse eligible pairs. Its span128 checkpoint processed synthetic
10,000 nt in about 19.1 seconds, with 25.92 MB score/DP arrays. These are single
observations, not isolated speedup benchmarks. Process peaks include Torch and
transient allocations; array counts are not total RAM. Synthetic inputs have no
accuracy labels, so these runs establish computation only.

Three configurations used the identical already exposed 65 train / 35 validation
records (41/12 PDB-derived plus24/23 comparative Rfam records), seed20261006 and
10 CPU epochs. Checkpoints were selected by validation F1, validation loss, then
earliest epoch. Positive loss weights came only from the training pair ratio.

| Pair span | Weight exponent | Mean validation F1 | Excluded validation contacts |
|---|---:|---:|---:|
| 64 | 0.5 | 0.2177 | 208 |
| 128 | 0.5 | 0.2597 | 0 |
| 128 | 1.0 | 0.3074 | 0 |

The full-ratio (exponent1.0) run selected epoch6. PDB-derived validation F1 was
0.6000 and comparative validation F1 was0.1548; the latter remains weak. These are
reused development scores, not fresh-test accuracy. Comparison outputs and a figure
are in `results/context_development_comparison_summary.json` and
`reports/context_development_comparison_report.md`. Source runs are retained.

```bash
.venv/bin/python scripts/verify_banded_development.py
.venv/bin/python scripts/verify_context_comparison.py
.venv/bin/python scripts/verify_context_scalability.py
```

### New RF00017 comparative trial

A separate model initialized from the fixed random seed, using the selected span128
and full-ratio weighting, trained only on the existing RF00001 train24 / RF00169
validation23 families. RF00017 supplied12 newly selected test sequences of290–317 nt,
after fixed metadata/sequence-only filtering. The immutable family plan checked125
prior exposures and test-start was recorded before predictions. Validation selected
epoch1 (F1 0.0863); all60 predictions and24 native folds were measured.

| Method | Mean RF00017 test pair F1 |
|---|---:|
| Trained context | 0.0036 |
| Initial context | 0.0047 |
| ViennaRNA | 0.4781 |
| LinearFold | 0.4799 |
| All unpaired | 0 |

Transfer is poor. The fixed span excludes314 test reference contacts. Processed
comparative annotations, one family per split, unresolved clan/prior-PDB/tool-training
independence and medium test lengths constrain interpretation. No biological-stability
or unrestricted long-RNA accuracy claim follows. RF00017 and RF00008 tests are now
consumed; their default trial runners reject a fresh rerun. New model work must use
development data and newly verified families before any fresh test.

```bash
.venv/bin/python scripts/verify_context_family_trial.py
.venv/bin/python scripts/verify_family_plan.py --run results/context_family_trial_runs/20261006T022922.302415Z/family_plan
```

An inventory of local PDB train/holdout BPSEQs at128–1024 nt found one training record
(353 nt) and no validation records. That does not support a larger experimental
training/evaluation cohort. Test-source files were not read for this inventory.

### FASTA inference from a saved checkpoint

```bash
.venv/bin/python scripts/predict_context.py --fasta configs/context_inference_demo.fasta
.venv/bin/python scripts/verify_context_inference.py
```

Use `--source-summary` to select a retained context-development or context-family-trial
summary. The default selects the latest mixed-development context run. It freezes
FASTA bytes and checkpoint/source identity in a new `context_inference_runs` directory,
records conservative test-start exposure, and writes `predictions.json`,
`predictions.dbn` and `reference_predictions.json`. The latter uses the existing
supplied-reference prediction schema. If verified references are available, evaluation
is a separate command:

```bash
./scripts/rnastable evaluate-reference --references data/verified_references.json --predictions results/context_inference_runs/<UTC>/reference_predictions.json
```

Inference itself loads no reference labels and measures no accuracy. The command
accepts at most10 unique records,10,000 nt per record and20,000 nt total, on at most
2 CPU threads. Predicted scores are logits, not free energy or measured stability.
Exposure files and their parent-directory entries are fsynced before inference starts.

### Global sparse and expanded development checkpoints

All-distance pair logits are scored in tiles, retaining top16 positive legal partners
per right endpoint. Greedy selection and two-pass local refinement are approximate;
scoring is quadratic, stable top-k sorting adds sorting work, and storage is bounded by
tiles and retained candidates. Synthetic10,000 nt inference measures resource use only.
The native folding tools currently achieve substantially higher labelled agreement.

The expanded study uses exact legacy CRW train/holdout annotations:24 new training
records317–552 nt and12 validation records319–543 nt, combined with previous development
records for89 train/47 validation. CRW sources are comparative annotations. Within-study
external-ID/sequence separation does not establish family/clan or tool-training independence.
Sampling preserves all4,462 supported positives and reduces scored training negatives
from1,180,545 to70,013; full label enumeration remains quadratic and bounded to1024 nt.
Full validation labels are retained. On identical exposed validation records, mean pair
F1 was .208579 for full-label training and .201726 for sampling, versus .717773 for
ViennaRNA and .719387 for LinearFold. One seed and validation-selected checkpoints;
these development scores do not establish generalization or biological stability.

```bash
.venv/bin/python scripts/verify_global_sparse_development.py
.venv/bin/python scripts/verify_global_sparse_scalability.py
.venv/bin/python scripts/verify_sparse_refinement.py
.venv/bin/python scripts/verify_long_comparative_development.py
.venv/bin/python scripts/verify_sampled_comparative_development.py
.venv/bin/python scripts/verify_expanded_development_comparison.py
.venv/bin/python scripts/verify_expanded_candidate_diagnostics.py
.venv/bin/python scripts/predict_context.py --source-summary results/sampled_comparative_development_summary.json --fasta configs/context_inference_demo.fasta
.venv/bin/python scripts/verify_context_inference.py
```

Per-source comparisons are saved in`reports/expanded_development_comparison_report.md`.
Candidate diagnostics in`reports/expanded_candidate_diagnostics_report.md` distinguish
nonpositive logits, top-k pruning, and omitted retained contacts. Label-informed oracle
candidate bounds are diagnostic upper bounds, not predictions. RF00008/RF00017 tests
are already consumed; all newer comparisons reuse development records only. Reuse the
frozen expanded snapshots for another comparison: rerunning CRW selection after exposure
can produce a different cohort. Checkpoint inference accepts context, global, expanded,
and sampled retained summaries; the default remains the earlier context checkpoint.

For global sparse checkpoints, exact decoding over retained candidates is available
up to1024 nt/64 positive partners per right endpoint. It uses O(n*m) work and O(n²)
storage, with deterministic noncrossing maximum-logit selection. It does not optimize
reference agreement or consider pruned/nonpositive pairs. On the identical47 exposed
development records, the full-label checkpoint scored .342535 with exact decoding,
versus .208579 with refinement and .140702 with greedy selection; native tools remain
higher. This checkpoint was selected using refinement, so the decoder comparison does
not establish an independent test gain. Full candidate/array/objective replay is retained
in`reports/exact_sparse_development_report.md`.

```bash
.venv/bin/python scripts/verify_exact_sparse_development.py
.venv/bin/python scripts/predict_context.py --source-summary results/long_comparative_development_summary.json --decoder exact_sparse --fasta configs/context_inference_demo.fasta
.venv/bin/python scripts/verify_context_inference.py
```

Exact-decoder validation selection uses the same89/47 records, initial weights, optimizer
and all10 training losses as full-label training. It selectedepoch3 with mean development
F1 .388499. The frozen source config now selects exact decoding by default in inference,
still capped at1024 nt. Native baselines remain higher. The consolidated report and
standalone figure in`reports/expanded_checkpoint_selection_report.md` compare329 predictions
on47 identical references without refitting or refolding. Checkpoint selection remains
on exposed development data, with no fresh test or generalization claim.

```bash
.venv/bin/python scripts/verify_exact_comparative_development.py
.venv/bin/python scripts/report_expanded_checkpoint_selection.py
.venv/bin/python scripts/predict_context.py --source-summary results/exact_comparative_development_summary.json --fasta configs/context_inference_demo.fasta
```

A training-only structured-loss prototype follows the margin-rescaled structured-loss
idea of [Tsochantaridis et al. (2005)](https://www.jmlr.org/papers/v6/tsochantaridis05a.html).
It retains all supported gold pairs plus top16 positive loss-augmented candidates per
right endpoint, decodes exactly within that pruned graph, and differentiates selected
logits. Pair-set symmetric difference supplies the margin loss, normalized by supported
gold count (minimum1). Brute-force oracle/gradient checks pass; this is a pruned objective,
not a full-graph structured-SVM optimizer. A fixed10epoch training run selectedepoch2
with development F1 .312886, below exact-selected BCE .388499. Full labels/validation
loss/checkpoints and890 training decision rows were audited; every optimizer step was
not replayed. The consolidated report now includes376 predictions/8 methods. Gold labels
and loss augmentation are confined to development training/diagnostics, never FASTA inference.

```bash
.venv/bin/python scripts/verify_structured_comparative_development.py
.venv/bin/python scripts/predict_context.py --source-summary results/structured_comparative_development_summary.json --fasta configs/context_inference_demo.fasta
```

Two sequence-only adjacent stackability indicators add2 learned weights to the global
scorer. They describe canonical compatibility at(i-1,j+1)/(i+1,j-1), respecting boundaries
and minimum loop distance4; they do not use labels or energy parameters. Weights initialize
zero, preserving the base logits, and are learned with the same full-label BCE on89/47
records. Selectedepoch5 development F1 .423380 exceeds the prior exact-selected .388499
on this reused validation cohort; native baselines remain substantially higher. This
one-seed development result does not establish independent test accuracy. The current
consolidated report contains423 predictions/9 methods on47 identical references.

```bash
.venv/bin/python scripts/verify_stack_comparative_development.py
.venv/bin/python scripts/run_stack_scalability.py --verify
.venv/bin/python scripts/predict_context.py --source-summary results/stack_comparative_development_summary.json --fasta configs/context_inference_demo.fasta
```

The separate synthetic resource benchmark explicitly substitutes approximate greedy/
refinement decoding for the checkpoint's bounded exact decoder. At10,000 nt one
observation measured4.40s scoring,.43s greedy,6.02s refinement,159,461 candidates/2.55MB,
and cumulative processpeak828,956KiB includingTorch. Feature/tile/retained-array statistics
exclude other transient storage. Exact candidates and both decoders replayed; no labels,
speedup, long-RNA accuracy or stability claim. FASTA source behavior remains explicit.

Global checkpoints also accept deliberate approximate FASTA decoder overrides:
`--decoder greedy` or`--decoder refined`, up to10000 nt/10records/20000 nt total.
The default`source` honors the frozen training decoder; exact remains bounded to1024 nt.
Sparse overrides reject context-only checkpoints before output. Method names record the
override, and refinement parameters are frozen in the manifest/summary for exact replay.

```bash
.venv/bin/python scripts/predict_context.py --source-summary results/stack_comparative_development_summary.json --decoder refined --fasta configs/stack_long_inference_demo.fasta
.venv/bin/python scripts/verify_context_inference.py
```

The retained10,000 nt synthetic demonstration in`results/stack_long_inference_summary.json`
exactly matches the resource benchmark's refined structure/objective. Checkpoint, bytes,
decoder settings, exposure-before-prediction and JSON/DBN/reference exports are audited.
It has no labels or accuracy evaluation; repeating it is not a fresh test.

### Checkpoint-guided native search pilot

The trained checkpoint can rank a pool of legal mutations against the original
LinearFold scaffold by compatible-contact count and then mean learned pair logits.
Target-template scoring uses sparse edges and supports1–10000 nt without all-pair
inference/decoding. Random-pool and compatibility-only controls isolate the added
ranking signal. Native LinearFold strict improvements alone accept moves; ViennaRNA
must confirm an improvement before selecting a changed output. The prior does not
supply folding energy or guarantee biological function.

On one previously exposed synthetic1000 nt input/one search seed,8 native proposals per
arm and33 total native folds yielded selected Vienna changes -11.0 (random),-8.4
(compatibility-only),-18.5 kcal/mol (checkpoint prior). The neural arm added128 proxy
calls; matched fold budgets do not imply equal total time/cost. Every pool, checkpoint
logit, constraint, raw fold, decision, exposure marker and denominator replayed. This
pilot has no labelled accuracy evaluation, new fitting or generalization/stability claim.

```bash
.venv/bin/python scripts/verify_checkpoint_prior_pilot.py
.venv/bin/python -m pytest -q tests/test_checkpoint_prior.py tests/test_pooled_proposals.py
```

Evidence:`reports/checkpoint_prior_pilot_report.md`; retained run:
`results/checkpoint_prior_pilot_runs/20261006T035130.449329Z`.
The historical optimizer and equal-budget artifacts are preserved.

### Resumable native proposal pilots

The pooled pilot now binds native request keys to the run manifest, source snapshots,
checkpoint digest, configuration, Python source digests, and native runtime commands
and executable digests. A completed request reuses its recorded result and checks its
raw-output digest. An interrupted request remains an error with unknown outcome and
cost; resume never invokes that request again. A run-level lock prevents competing
pilot drivers. Resume uses the stored configuration and rejects requested seed/input
changes or changes to bound code, snapshots, checkpoint, and native runtime.
Resume replays deterministic proposal pools and proxy scores, reuses
exposure records, and reports completed proxy calls across every execution attempt.
Incomplete attempts can have additional unknown proxy work. Audit replay costs are
separate from experimental search costs. Resume applies to newly journaled runs;
older pilots remain available through the existing audit path.

```bash
.venv/bin/python scripts/run_checkpoint_prior_pilot.py
# Substitute the printed run directory; resume uses the stored configuration.
.venv/bin/python scripts/run_checkpoint_prior_pilot.py --resume results/checkpoint_prior_pilot_runs/RUN_DIRECTORY
.venv/bin/python scripts/verify_checkpoint_prior_pilot.py results/checkpoint_prior_pilot_runs/RUN_DIRECTORY/summary.json
.venv/bin/python scripts/run_checkpoint_prior_replication.py
.venv/bin/python scripts/run_checkpoint_prior_replication.py --verify
.venv/bin/python scripts/run_checkpoint_prior_replication.py --resume results/checkpoint_prior_replication_runs/RUN_DIRECTORY
```

The replication plan uses the existing exposed synthetic 1,000-, 5,000-, and
10,000-nt resource inputs with search seeds 20261006 and 20261007. Each component
runs random-pool, compatibility-only, and checkpoint-prior arms with eight planned
native proposals, pool size 16, one LinearFold baseline, and two ViennaRNA validation
requests per arm. Failed or timed-out folds remain in the request denominator.
Repeated seeds share inputs, so the six components are not six independent biological
samples. Results are descriptive native-energy measurements and do not evaluate
accuracy, fit the checkpoint, or establish generalization or biological stability.
Evidence is retained in `reports/checkpoint_prior_replication_report.md` and
`results/checkpoint_prior_replication_summary.json`.

### Helix heads and sampled training on reused development

A local helix head adds eight sequence-only indicators to the global pair scorer:
contiguous canonical support at three outer/inner offsets, GC pair and GU pair.
Feature weights start at zero. The matched head study compares baseline, adjacent
stack and helix heads with three base initialization seeds, identical frozen
89-training/47-validation records, full BCE, optimizer and exact sparse checkpoint
selection. Helix reused-validation F1 is 0.5244, 0.4951 and 0.4911 across those
seeds. These are development measurements after repeated exposure and selection;
independent family evaluation and long biological accuracy remain pending.

```bash
.venv/bin/python scripts/verify_helix_comparative_development.py
.venv/bin/python scripts/run_pair_head_development_study.py --verify
.venv/bin/python scripts/run_helix_scalability.py --verify
.venv/bin/python scripts/run_pair_penalty_development.py --verify
.venv/bin/python scripts/run_population_development.py --verify
.venv/bin/python scripts/run_population_resource.py --verify
.venv/bin/python scripts/prepare_long_population_training.py --verify
```

The population sampler retains every representable positive and uniformly samples
negative canonical pairs by rank, avoiding dense pair-label enumeration. Negative
losses receive inverse inclusion weighting; full training population counts set
the positive weight. Full validation labels remain in use. Loss and gradient are
unbiased over draws, but each training run reuses a fixed draw. Three sampling
seeds with the same model initialization produced F1 0.5251, 0.5196 and 0.5245;
none is treated as independent biological replication. The synthetic resource
study demonstrated one sampled training update at 1,000/5,000/10,000 nt without
biological accuracy evaluation. The local CRW training archive's maximum length
is674 nt, so its fixed 1,025–4,096-nt import remains empty and auditable.

Inference supports an explicit `--pair-penalty` in 0..8, frozen and replayed in the
inference manifest. The default zero retains existing decoding. A development
grid selected zero for all three helix checkpoints and eight of nine head/seed
checkpoints overall. Default exact sparse inference remains bounded to1,024 nt;
longer inputs require an explicit `--decoder greedy` or `--decoder refined`.

### Frozen-code helix native replication

The helix prior runner snapshots its Python code/configuration so continued
workspace development cannot change an unfinished component's implementation.
It uses the same exposed synthetic resource inputs, two search seeds, three arms,
eight native proposals and pool size16. Every arm receives an explicit300-second
ViennaRNA final-validation limit. The earlier stack study's30-second10,000-nt
validation timeouts remain preserved; its separate300-second reference extension
re-evaluates the frozen finalists without new search. Native validation determines
sequence selection; learned logits remain proposal-ranking proxies.

```bash
.venv/bin/python scripts/run_checkpoint_prior_reference_extension.py --verify
.venv/bin/python scripts/run_helix_prior_replication.py --verify
# Resume with the recorded study directory and optional matching publication name.
.venv/bin/python scripts/run_helix_prior_replication.py --resume results/helix_prior_replication_runs/RUN_DIRECTORY
.venv/bin/python scripts/run_helix_prior_replication.py --verify --publish-name helix_prior_seed7_replication
# After the study driver stops, inspect all planned/unfinished request denominators.
.venv/bin/python scripts/audit_native_study_accounting.py
.venv/bin/python scripts/audit_native_study_accounting.py --verify
```

A separately named study may use `--source-summary PATH --publish-name NAME` to
freeze another measured helix checkpoint. Both unfinished and completed native
requests remain journaled; interrupted work is never automatically retried.
Linux's parent-death guard kills native descendants if their driver dies. Whole
study and native costs are reported explicitly; concurrent development checks can
affect observed timings. No fresh test-set, generalization or stability claim is
made. The current evidence review is `reports/development_2026-10-06_review.md`.
