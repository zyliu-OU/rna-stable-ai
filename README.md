# RNA-StableAI

<img width="1774" height="887" alt="image" src="https://github.com/user-attachments/assets/4da2605a-3a6d-4130-9014-950dc75bd34d" />

Research prototype for RNA structure prediction, constrained sequence optimization,
and reproducible folding benchmarks. Code, experimental checkpoints, input data,
and results are available for inspection. No validated release yet.

**Current length focus:** active development targets RNA sequences shorter than
5,000 nt (1–4,999 nt). Existing 5,000/10,000-nt code, data, results and
provenance are preserved as deferred work; they are not deleted or counted as
active-scope validation. Method-specific lower limits still apply. See the
[sequence-length policy](docs/LENGTH_SCOPE.md).

## Development plan

Updated October 16, 2026. **Current step: 4 — independent biological validation below 5,000 nt.**

| Step | Work | Progress |
|---:|---|---|
| 1 | Reproducible foundations | Implemented: bounded native tools, request journals, input hashes, exposure tracking, and replay audits. |
| 2 | Structure models | Baseline, stack, and helix models trained and compared. Candidate-budget and loss studies complete; defaults unchanged. |
| 3 | Sequence optimization | Synthetic studies and native energy checks complete. Biological benefits remain unverified. |
| **4** | **Independent structure validation** | **Current gate.** Three prospective panels and a six-family raw-contact feasibility study evaluated; broader coverage/provenance remain limited. |
| 5 | Longer RNA evidence | New work at 5,000 nt or above is deferred. Existing synthetic benchmarks through 10,000 nt remain preserved; exact sparse inference supports up to 1,024 nt. |
| 6 | Measured stability and function | Public-assay pilot complete. Controlled mutation effects and retained function remain pending. |
| 7 | Validated release | Pending the scientific evidence above. |

The assay pilot advances part of step 6 while steps 4 and 5 remain open.
Development resumed with a frozen 12-training/four-validation family source plan.
Its original selection failed the per-family gate. A separately versioned,
label-informed development dataset now passes that gate with 61 training and
22 validation pair references. A matched nine-run pair-set training study is
complete; independent biological validation remains open. See the
[roadmap](reports/PROJECT_ROADMAP_2026-10-16.md).
The next-panel metadata acquisition resolved 91 of 92 missing family
descriptions; RF04222 returned 404. An eight-family, 56-candidate structure
panel was frozen and acquired. All 56 contact requests succeeded, but sequence
redundancy left 12 informative references and no family with three. The
reference-readiness gate failed; no new model inference ran.

## Latest results

- **Structure feasibility:** 10 raw PDB-derived references across six families;
  all 60 outcomes complete. Mean pair F1: helix **0.3255**, ViennaRNA and
  LinearFold **0.6261**. Broad biological validation remains open.
- **Measured-assay pilot:** 64 short constructs, six methods, five assays;
  all 384 predictions and 2,880 proxy/assay comparisons completed. Native energy
  per nucleotide showed stronger descriptive associations than learned unpaired
  fractions on this selected cohort.
- **Provenance:** all three learned models use the same frozen development data;
  83/136 records still lack confirmed family assignments.
- **New development data:** the failed sequence-first source run is retained.
  A disclosed coverage selection yields 61 training and 22 validation complete
  pair references across 12 and four groups.
- **New model study:** three heads × three seeds trained from random initialization
  on the new pair sets. Mean selected development validation pair F1 is 0.322
  baseline, 0.391 stack and 0.482 helix; independent accuracy is unmeasured.
- **Verification:** 831 tests passed. Source archival recovered 271 of 281
  recorded Python versions; ten historical versions remain unavailable.

These results do not establish causal mutation benefits, cellular half-life,
long-RNA accuracy, or retained function. The assay cohort contains only
`SN_filter=1` constructs; complete training/tool independence remains unresolved.

[Structure review and figure](reports/raw_structure_feasibility_review_2026-10-14.md)
· [Assay review and figure](reports/degradation_pilot_review_2026-10-13.md)
· [Source archive](docs/REPLAY_SOURCE_ARCHIVE.md)
· [Reference engineering](docs/STRUCTURE_DERIVED_REFERENCES.md)
· [Family source review](reports/family_provenance_source_review_2026-10-15.md)
· [Coverage dataset review](reports/family_coverage_development_review_2026-10-15.md)
· [Pair-set training review](reports/family_pair_set_training_review_2026-10-15.md)
· [Fresh structure inventory](reports/fresh_structure_inventory_review_2026-10-15.md)
· [Fresh structure candidate plan](reports/fresh_structure_metadata_and_panel_review_2026-10-15.md)
· [Fresh structure contact review](reports/fresh_structure_reference_review_2026-10-15.md)
· [Latest test handoff](reports/RNA-StableAI_HANDOFF_2026-10-15_V6.md)
· [Model-study test log](reports/family-pair-set-training-full-suite-2026-10-15.log)

## Quick start

Requires Python 3.12+. Setup installs local dependencies and attempts native tool
builds; use `doctor` to check availability on your machine.

```bash
git clone https://github.com/zyliu-OU/rna-stable-ai.git
cd rna-stable-ai
python3 scripts/setup.py
.venv/bin/python -m rnastable doctor
.venv/bin/python -m pytest -q
```

Generate synthetic controls and run the original CPU folding / separate encoder
benchmark:

```bash
./scripts/rnastable generate --config configs/benchmark.json
./scripts/rnastable benchmark --config configs/benchmark.json
```

See the [development and command reference](DEVELOPMENT.md) for model training,
inference, optimization, evaluation protocols, and recorded studies. Historical
evidence retains original host paths; rerun pipelines for local artifacts on
another machine. Native folding runs on CPU; encoder GPU timings are separate.

## Project files

| Location | Contents |
|---|---|
| [src/rnastable](src/rnastable) / [scripts](scripts) | Pipeline, models, command-line tools, and audits |
| [configs](configs) / [tests](tests) | Declared protocols and regression checks |
| [checkpoints](checkpoints) / [data](data) / [results](results) | Experimental weights, inputs, and retained evidence |
| [docs](docs) / [reports](reports) | Methods, limitations, reviews, and dated handoffs |

See [data attribution](docs/DATA_ATTRIBUTION.md) and the
[research-use notice](RESEARCH_USE_NOTICE.md). The public assay source is pinned
to the [KaggleOpenVaccine author commit](https://github.com/eternagame/KaggleOpenVaccine/tree/b95af835cc38bd7dc55ed6e7397d124787f86996);
its [MIT license](docs/third_party/KaggleOpenVaccine_LICENSE.txt) is retained.
