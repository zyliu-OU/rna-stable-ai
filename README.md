# RNA-StableAI

<img width="1774" height="887" alt="image" src="https://github.com/user-attachments/assets/4da2605a-3a6d-4130-9014-950dc75bd34d" />

Research prototype for RNA structure prediction, constrained sequence optimization,
and reproducible folding benchmarks. Code, experimental checkpoints, input data,
and results are available for inspection. No validated release yet.

## Development plan

Updated October 14, 2026. **Current step: 4 — independent biological validation.**

| Step | Work | Progress |
|---:|---|---|
| 1 | Reproducible foundations | Implemented: bounded native tools, request journals, input hashes, exposure tracking, and replay audits. |
| 2 | Structure models | Baseline, stack, and helix models trained and compared. Candidate-budget and loss studies complete; defaults unchanged. |
| 3 | Sequence optimization | Synthetic studies and native energy checks complete. Biological benefits remain unverified. |
| **4** | **Independent structure validation** | **Current gate.** Three prospective panels evaluated; supported references and training/tool provenance remain limited. |
| 5 | Long biological RNA | Synthetic benchmarks reach 10,000 nt; exact sparse inference supports up to 1,024 nt. Longer biological validation is pending. |
| 6 | Measured stability and function | Public-assay pilot complete. Controlled mutation effects and retained function remain pending. |
| 7 | Validated release | Pending the scientific evidence above. |

The assay pilot advances part of step 6 while steps 4 and 5 remain open.
**Next research task:** design a screened, independently annotated structure panel
with enough supported references, documented provenance, and no reuse of consumed
families as fresh tests. See the [roadmap](reports/PROJECT_ROADMAP_2026-10-14.md).

## Latest results

- **Structure evaluation:** the latest panel retained all 15 planned records;
  four lysine references were supported and 11 annotations remained unsupported.
  Mean pair F1: helix **0.5332**, ViennaRNA **0.7267**, LinearFold **0.7488**.
- **Measured-assay pilot:** 64 short constructs, six methods, five assays;
  all 384 predictions and 2,880 proxy/assay comparisons completed. Native energy
  per nucleotide showed stronger descriptive associations than learned unpaired
  fractions on this selected cohort.
- **Verification:** 672 tests passed. Source archival recovered 257 of 267
  recorded Python versions; ten historical versions remain unavailable.

These results do not establish causal mutation benefits, cellular half-life,
long-RNA accuracy, or retained function. The assay cohort contains only
`SN_filter=1` constructs; complete training/tool independence remains unresolved.

[Structure review](reports/prospective_third_pair_evaluation_review_2026-10-13.md)
· [Assay review and figure](reports/degradation_pilot_review_2026-10-13.md)
· [Source archive](docs/REPLAY_SOURCE_ARCHIVE.md)
· [Test log](reports/github-update-full-suite-2026-10-13.log)

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
