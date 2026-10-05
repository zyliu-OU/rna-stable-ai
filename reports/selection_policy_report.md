# Reference-confirmed selection implementation

The optimizer and CPU sweep now publish selected.fasta. A finalist is selected
only when a completed search and two successful finite ViennaRNA folds confirm
lower energy by more than 1e-9 kcal/mol. Otherwise the input is selected.
Candidates, raw folds, errors and before-selection aggregate scores remain retained.

Verification: 84 tests passed, covering improved/equal/worsened energy, unknown or
nonfinite reference values, both validation failures, search failure, unchanged
sequence, retained rejected candidates and selected-file corruption on resume.
Simulated folds in tests are explicitly test-only, not measured benchmark data.

A fresh real 1,000-nt optimization completed 48 proposals (21 accepted) and selected
the 40-position finalist after a ViennaRNA change of -30.5 kcal/mol. Run:
`/home/zyliu/Documents/rna-stable-ai/results/optimization_runs/20261004T232517.598540Z`. The selection and trajectory audit passed.

A real two-case CPU smoke sweep completed 16 proposals, both validated; selected
outputs audited and resume reused both cells. Run: `/home/zyliu/Documents/rna-stable-ai/results/sweep_runs/20261004T232638.138092Z`.

The saved 18-case long replication was independently re-audited (144 proposal
folds). Selection review kept 14 confirmed improvements and returned inputs for
three worsenings and one equal-energy candidate. All 18 selected FASTA hashes,
constraints, decisions and CSV fields passed audit. No long folds were rerun.
Review: `/home/zyliu/Documents/rna-stable-ai/results/selection_reviews/20261004T232639.585011Z`. See [selection_review_report.md](selection_review_report.md).

No dependencies were installed, no system configuration was changed and no
training was performed. Existing files were preserved in source_backups/archive
before replacement; commands/output are in commands.jsonl.

Use selected.fasta as the output, not the retained candidate. A returned input
with failed reference folding has unknown energy. Lower computed MFE does not
establish biological stability. The policy has only been studied on synthetic
inputs; annotated biological constraints and search-seed variability remain next.

```bash
./scripts/rnastable optimize --config configs/optimization.json
.venv/bin/python scripts/verify_optimization.py
```
