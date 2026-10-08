# Prospective equal-budget CPU study checkpoint

Implemented a fixed-plan comparison of one 32-proposal search against four
8-proposal restarts. Both arms use beam 200, a 40-position mutation cap, identical
constraints, paired exact synthetic inputs and the same confirmed-ViennaRNA
selection policy. The configuration and provenance manifest were saved before
the first fold. New mixed input seeds 1732–1734 cover 1,000 and 2,000 nt.

Run: results/equal_budget_runs/20261005T042508.068755Z.

All 30 searches validated, with no recorded search failures. Each arm performed
192 proposal folds: 384 total. The long arm won five of six paired inputs;
restarts won the 2,000-nt seed-1732 input by 1.3 kcal/mol. Mean restart-minus-long
selected changes were +5.5667 kcal/mol at 1,000 nt and +9.5667 at 2,000 nt.
Positive values favor the long search. These are descriptive results from three
synthetic inputs per length, not a statistical or biological conclusion.

Recorded component wall-time totals were 218.4715 seconds for the long arm and
263.8985 seconds for restarts. These sums include search/baseline, nonreused input
reference and candidate validation times, and exclude plotting/reporting/driver
overhead. They are single observations in fixed arm order, not a speedup claim.
The long arm requested 6 baseline folds and 6 candidate validations; restarts
requested 24 baselines and 23 candidate validations (one finalist was unchanged).
Both requested six input references and 192 proposal folds.

Verification: 164 tests passed, including mismatched budgets/references/inputs,
unknown costs, failed validation, duplicate-fold exclusions, failed-arm continuation,
interruption and frozen-config resume rejection. Full sweep/portfolio/paired-budget
audits passed. A real completed-study resume reused all 30 saved searches; all 455
raw folding-file hashes and measured outcomes/costs were unchanged. New portfolio
paths on resume are expected. Test evidence: reports/tests-equal-budget-complete.xml.

Files added: src/rnastable/budget_study.py, configs/evaluation_equal_budget.json,
scripts/verify_equal_budget.py, scripts/summarize_equal_budget.py and
tests/test_budget_study.py. cli.py and README.md were backed up before editing.
Outputs include equal_budget CSV/JSON, separate cost summary/report, standalone
paired energy/cost PNG, frozen study manifests, complete source trajectories,
selected FASTAs and per-attempt records. Exact commands and environment versions
are recorded in reports/commands.jsonl and the timestamped development manifest.
Previous benchmark, optimization, robustness and portfolio artifacts are preserved.

```bash
./scripts/rnastable compare-search-budgets --config configs/evaluation_equal_budget.json
.venv/bin/python scripts/verify_equal_budget.py
.venv/bin/python scripts/summarize_equal_budget.py
```

To reuse this completed study without refolding:

```bash
./scripts/rnastable compare-search-budgets --config configs/evaluation_equal_budget.json --resume results/equal_budget_runs/20261005T042508.068755Z
.venv/bin/python scripts/summarize_equal_budget.py
```

Resume checks exact configuration/code/environment fingerprints. The next research
step is to prospectively replicate this paired design at 5,000/10,000 nt on additional
inputs before choosing a default restart strategy. Neural training remains deferred.
New portfolio and equal-budget development changes remain local, not pushed to GitHub.
