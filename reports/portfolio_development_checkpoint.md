# Saved-search portfolio development checkpoint

Implemented `rnastable select-portfolio` and an independent `verify_portfolio.py`
audit. These commands reuse saved CPU folding evidence without new folds, changes
to the measured studies, installations or neural training.

The source sweep is audited before selection. Candidates must have compatible
constraints, exact input identity and consistent successful input-reference energy.
Only completed searches with confirmed ViennaRNA improvement are eligible. The
lowest energy wins, with deterministic job-ID tie breaking. If none is eligible,
selection returns the input; unknown reference energy remains unknown.

The saved long robustness study yields four selected FASTAs from 16 searches and
128 proposals, with four searches / 32 proposals per input:

| Input | Selected beam | Search seed | ViennaRNA change (kcal/mol) |
|---|---:|---:|---:|
| mixed_5000_seed1729 | 400 | 2719 | -5.70 |
| mixed_5000_seed1730 | 400 | 2719 | -4.20 |
| mixed_10000_seed1729 | 200 | 2718 | -5.20 |
| mixed_10000_seed1730 | 200 | 2718 | -4.23 |

These are best-of-several selections on synthetic inputs. They do not establish
held-out performance, statistical significance or biological stability. The saved
source study continues to expose all four candidate worsenings.

Verification: 137 automated tests passed; full source sweep and portfolio audits
passed. An isolated integrity regression accepted an unchanged copied portfolio
and rejected a modified selected FASTA. The negative-test artifact intentionally
contains a changed test copy, clearly labeled under reports/verification_checks/.
Original source artifacts remain intact. Final test evidence is in
reports/tests-portfolio-final.xml. Commands, versions, source hashes and integrity
check paths are recorded in reports/commands.jsonl and the timestamped
portfolio_development_manifest JSON.

New source files: src/rnastable/portfolio.py, scripts/verify_portfolio.py and
tests/test_portfolio.py. cli.py and README.md were backed up before editing.

```bash
./scripts/rnastable select-portfolio --summary results/evaluation_robustness_long_summary.json
.venv/bin/python scripts/verify_portfolio.py
.venv/bin/python -m pytest -q
```

The next research step is a prospectively specified, equal-budget comparison of
one longer search against several short restarts on additional input seeds. Fix
the candidate selection policy and evaluation budget before measuring those inputs.
Neural training remains deferred. These new development changes are local and have
not been pushed to GitHub.
