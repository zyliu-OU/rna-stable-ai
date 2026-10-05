# CPU pipeline development checkpoint

Implemented search-seed robustness reporting, sequence-bound protected intervals,
dry-run input validation and live command logging. No new dependencies, system
changes or neural training.

## Verified results

108 tests passed. The real CPU robustness study completed 36/36 searches with no
tool failures; 288 proposal folds, six inputs and 18 paired beam comparisons were
audited. Thirty-four searches selected confirmed improvements; two returned the
input. Resume reused all 36 completed cells. Search repeats are summarized within
inputs before across-input averages. See [search_robustness_report.md](search_robustness_report.md).

Robustness run: `/home/zyliu/Documents/rna-stable-ai/results/sweep_runs/20261005T022904.959274Z`.

The real protected-interval demo preserved all 49 protected positions, nucleotide
counts, GC content and length. Eight proposals, three accepted, six changed
positions; ViennaRNA improvement -2.8 kcal/mol. Selection/trajectory/constraint
audit passed. Run: `/home/zyliu/Documents/rna-stable-ai/results/optimization_runs/20261005T023719.583673Z`. Synthetic intervals have no inferred
biological meaning. Dry-run sequence-hash/coordinate checks passed before folding.

Logging tests verified progress before command completion, durable starts,
nonzero/missing-executable results and forwarded/recorded interruption. Commands
and exact installed versions are preserved in logs and run provenance.

New files:

- configs/evaluation_robustness.json
- configs/optimization_protected_demo.json
- configs/constraints_synthetic_example.json
- src/rnastable/robustness.py
- src/rnastable/annotations.py
- scripts/summarize_robustness.py
- scripts/verify_robustness.py
- tests/test_robustness.py
- tests/test_command_logging.py
- tests/test_annotations.py

Modified files were backed up or archived before changes:

- src/rnastable/cli.py
- scripts/log_command.py
- README.md

Generated results include four robustness CSVs, a summary JSON, a report and
standalone figure; a protected demo input/finalist/selected FASTA and raw folds;
test XML/output, verification reports and source/version manifests. Previous
benchmarks, long replication and selection review remain preserved.

## Rerun

```bash
./scripts/rnastable evaluate --config configs/evaluation_robustness.json
.venv/bin/python scripts/summarize_robustness.py
.venv/bin/python scripts/verify_robustness.py
./scripts/rnastable optimize --config configs/optimization_protected_demo.json --constraints configs/constraints_synthetic_example.json
.venv/bin/python scripts/verify_optimization.py
```

The next research work is application-specific constraints or long-input
search-seed replication; training remains deferred. Account/model usage quota
is not exposed in this environment, so its remaining amount cannot be verified.
