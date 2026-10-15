# RNA-StableAI handoff

Project: RNA-StableAI. Date: 2026-10-13 (America/Los_Angeles). Version: V3.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Status: **Active autonomous build. Third prospective evaluation and measured-assay
binding are complete; the empirical proxy evaluation driver is the next step.**
User requested continuation until a necessary terminal command must be run by them.
No user terminal command is currently required. The active goal remains running.

## Completed work

1. Declared and completed three matched helix structured-hinge-plus-0.1-BCE fits
   against the original BCE checkpoints. All89 training/47 validation records,
   initialization states, optimizer, ten epochs and exact top16 decoder are fixed.
   Structured F1:0.429375/0.417392/0.446825 versus BCE0.524423/0.495077/0.491069.
   False positives improve but F1 regresses on every seed. Keep BCE/top16 defaults.
   All141 paired outcomes,30 slices and890 loss decisions per fit remain verified.
   Run: `results/helix_objective_development_runs/20261014T002930.596309Z`.
   Review: `reports/helix_objective_development_review_2026-10-13.md`.

2. Added verified metadata replay caching in
   `scripts/prepare_prospective_family_panel.py`. The first successful audit fully
   recomputes screening; later calls check source/protocol/attempt hashes and reuse
   a summary/manifest/code-bound result outside immutable source directories.
   Changed inputs/results/code and malformed caches reject or recompute. The flag
   `--verify --recompute-screening` forces full replay. Live exposure/reference gates
   remain separate and active. Six cache tests and full pipeline regression pass.
   Protocol: `docs/PROSPECTIVE_REPLAY_CACHE.md`.

3. Frozen, acquired, bound and evaluated RF00010/RF00023/RF00168 with the unchanged
   seed20261006 baseline/stack/helix models. Sandbox DNS failed; approved external
   access worked. All982 metadata entries are screened, all6 metadata and16 evidence
   files are retained. All15 selected records stay planned. Four lysine references
   are complete;11 references lack paired columns and stay unsupported.
   Evaluation:90 planned outcomes,24 measured,66 unsupported/null;8 native requests
   complete,zero unknown. Mean pair F1 on four lysine references:
   baseline0.065709,stack0.177214,helix0.533167,ViennaRNA0.726724,
   LinearFold0.748810,all-unpaired0.0. This is one supported family, not broad
   independent replication. Known overlap checks pass; unknown provenance persists.
   All three families, including unsupported records, are now consumed.
   Review: `reports/prospective_third_pair_evaluation_review_2026-10-13.md`.
   Protocol: `results/prospective_family_protocol_runs/20261014T003018.640568Z`.
   Acquisition: `results/prospective_family_acquisition_runs/20261014T003052.784986Z`.
   Evidence: `results/prospective_evidence_runs/20261014T010916.985395Z`.
   Binding: `results/prospective_pair_binding_runs/20261014T011058.285068Z`.
   Evaluation: `results/prospective_pair_evaluation_runs/20261014T011253.580452Z`.

4. Implemented `scripts/prepare_degradation_source.py` and
   `scripts/prepare_degradation_binding.py`,35 focused tests, source configuration
   and `docs/MEASURED_DEGRADATION_SOURCE.md`. Frozen the public OpenVaccine author
   source at commit `b95af835cc38bd7dc55ed6e7397d124787f86996`, with the original
   three-model weights before downloading assay bytes. Raw URL returns a Git-LFS
   pointer; the declared media fallback works. Dataset:10,260,945 bytes, SHA256
   `bd1e611d7c9b626c5266eadda33cc3b50c28db146d1bbccdf15e8f33485ce3e5`.
   Source protocol: `results/degradation_source_protocol_runs/20261014T010051.844721Z`.
   Source acquisition: `results/degradation_source_runs/20261014T010830.291679Z`.
   The author file is Pandas column-mapped JSON with1589 rows. Strict conversion
   requires matching row indices across every column and preserves identities.
   The initial NDJSON-only attempt rejected before exposure/binding and remains
   retained. No cohort re-selection or assay-value substitution occurred.
   Successful binding: `results/degradation_binding_runs/20261014T012248.606470Z`.
   Pilot:64 lexicographic IDs,320/320 supported assay outcomes,zero prior overlaps.
   All pilot quality flags are1; retain empty quality0/unknown groups in analysis.
   Every source sequence is conservatively registered as validation exposure before
   assay binding. Targets/errors map to exact scored-prefix coordinates; negative
   values remain unchanged. Source predicted structures and derived half-lives are
   ignored. No model predictions or native folds have yet used these measurements.

Updated README, the stale training sentence in RESEARCH_USE_NOTICE.md, and
`reports/PROJECT_ROADMAP_2026-10-13.md`. No Git index edit, commit, push or publication.
All earlier handoffs, failed attempts and immutable runs remain preserved.

## Verification

- Final full suite: **643 passed in215.00seconds**,
  `reports/degradation-binding-columnar-full-suite-2026-10-13.log`.
- Source/binding focused set:35 passed in0.12seconds; earlier objective14 tests,
  broader objective integration53 tests, and cache/prospective51 tests pass.
- Complete helix-objective replay passes3/3 fits and141 paired records.
- First full large metadata replay passes; later cached source/evidence audits pass.
- Third pair evaluation replay passes all90 outcomes, full gold scores, hashes,
  exposure and native accounting without new folds or test exposure.
- Measured source and assay binding replays pass byte/model/code/coordinate/value/
  error/selection/prior-overlap/exposure bindings without model/native calls.
- Ruff, compileall and whitespace checks pass. Failed schema-test runs and their
  corrected checks are preserved in reports; the final suite includes both formats.
- Relevant logs: `helix-objective-*2026-10-13.log`,
  `prospective-third-family-full-replay-2026-10-13.log`,
  `prospective-third-evidence-audit-2026-10-13.log`,
  `prospective-third-pair-evaluation-audit-2026-10-13.log`,
  `degradation-source-audit-2026-10-13.log`,
  `degradation-binding-columnar-audit-2026-10-13.log`,
  `degradation-binding-columnar-focused-2026-10-13.log` under reports/.

## Pending work

Implement and test `scripts/evaluate_degradation_pilot.py` from the immutable
binding manifest's `analysis_plan` before running predictions. Do not change the
binding or source scripts after freeze; their hashes are part of replay gates.
Preserve64 records × six methods and all five assays, failures and empty slices.
Freeze source/model/code/native-runtime inputs, record selected test exposure before
model/native calls, and use durable NativeJournal requests with no retry of unknown
outcomes. Native controls are at37C,30-second/4-GiB per request,beam100.

Use predicted unpaired fraction over the scored prefix, scored-prefix GC fraction
(as a sequence-only control) and native MFE per nucleotide (native methods only).
Do not use learned logits as folding energy. Report fixed descriptive Spearman rho
for each assay/quality slice, complete/missing counts, null values for constant
inputs or fewer than three complete pairs, and no p-values/independent confidence
claims. Do not fit/calibrate/select models on the measurements. Native assay
conditions differ from folding conditions. The64 records share construct flanks
and all have quality1; this is a restricted public short-construct benchmark.
Audit must replay models and retained native journals without fresh native calls
or new exposure. Test event-before-call ordering, missing outcomes, constant/empty
correlations, tampered bindings, and interrupted-native non-retry.

Long biological annotations, full training/tool provenance, causal stabilization
of proposed mutations, experimentally retained function and validated release
remain pending. Previous prospective families and the imported measured source
cannot be reused as fresh independent tests.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat reports/PROJECT_ROADMAP_2026-10-13.md
cat docs/MEASURED_DEGRADATION_SOURCE.md
.venv/bin/python scripts/prepare_degradation_source.py --verify
.venv/bin/python scripts/prepare_degradation_binding.py --verify
.venv/bin/python scripts/evaluate_prospective_panel.py --verify --reference-format pair_set_zero_based_v1
.venv/bin/python -m pytest -q tests/test_degradation_source.py tests/test_degradation_binding.py
```

Inspect the frozen plan without changing it:

```bash
.venv/bin/python -c 'import json,pathlib; s=json.loads(pathlib.Path("results/degradation_binding_summary.json").read_text()); print(json.loads((pathlib.Path(s["run_dir"])/"manifest.json").read_text())["analysis_plan"])'
```

All shell sessions are completed at save; no processes need interruption. The next
step is implementation/testing of the empirical evaluation driver, followed by
its frozen run and replay. Continue autonomously under the active goal.
