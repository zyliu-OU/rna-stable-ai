# RNA-StableAI

<img width="1774" height="887" alt="image" src="https://github.com/user-attachments/assets/4da2605a-3a6d-4130-9014-950dc75bd34d" />

Research prototype for RNA structure prediction, constrained sequence optimization,
and reproducible folding benchmarks. Code, experimental checkpoints, input data,
and results are available for inspection. No validated release yet.

**Current development focus: RNA sequences shorter than 5,000 nt (1–4,999 nt).**
We are extending and evaluating the core structure model within that range.
Existing 5,000/10,000-nt code, data, results, and provenance are preserved as
deferred work; they are not deleted or counted as
active-scope validation. Method-specific lower limits still apply. See the
[sequence-length policy](docs/LENGTH_SCOPE.md).

## Development plan

Updated October 16, 2026. **Active work: core-model development below 5,000 nt.**
Independent biological validation remains a separate, unresolved release gate.

| Step | Work | Progress |
|---:|---|---|
| 1 | Reproducible foundations | Implemented: bounded native tools, request journals, input hashes, exposure tracking, and replay audits. |
| **2** | **Structure models** | **Active length-focused development.** Baseline, stack, and helix models have been compared; a training-only 400–1,014-nt extension has completed a matched single-seed pilot. Defaults remain unchanged. |
| 3 | Sequence optimization | Synthetic studies and native energy checks complete. Biological benefits remain unverified. |
| 4 | Independent structure validation | Open release gate. Three prospective panels and a six-family raw-contact feasibility study evaluated; broader coverage/provenance remain limited. |
| 5 | Length evidence and deferred 5,000+ nt work | Longer held-out validation below 5,000 nt is needed. New work at 5,000 nt or above is deferred; existing synthetic benchmarks through 10,000 nt remain preserved. Current full-pair training is capped at 1,024 nt. |
| 6 | Measured stability and function | Public-assay pilot complete. Controlled mutation effects and retained function remain pending. |
| 7 | Validated release | Pending the scientific evidence above. |

The assay pilot advances part of step 6 while independent validation remains open.
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
Separately, the length-focused model track screened 60 metadata-selected
[bpRNA-1m](https://bprna.cgrb.oregonstate.edu/download.php) records and retained
27 training-only RNAs of 400–1,014 nt. A matched single-seed pilot added these
to the 61-record training set. Its reused 22-record validation set ends at
387 nt, so the pilot does not establish longer-RNA accuracy. The public snapshot
includes code, metadata, and concise results; the upstream bpRNA archive and
full frozen run artifacts remain local and are not redistributed here.

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
- **Length-extension pilot:** 27 training-only RNAs of 400–1,014 nt added to a
  matched helix fit. Reused short-sequence validation pair F1 was **0.49106**
  versus **0.48915** for the control (one seed). This small development change
  is not an independent or longer-length accuracy result.
- **Verification:** 864 tests passed in the working environment. A clean
  publication checkout passed 841 tests; nine historical replay tests require
  ignored external/native assets absent from that checkout. Source archival
  recovered 271 of 281 recorded Python versions; ten remain unavailable.

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
· [Latest development handoff](reports/RNA-StableAI_HANDOFF_2026-10-16_V15.md)
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
