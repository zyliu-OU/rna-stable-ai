# RNA-StableAI handoff

- Project: RNA-StableAI
- Date: 2026-10-11 (America/Los_Angeles)
- Version: V5
- Workspace: `/home/zyliu/Documents/rna-stable-ai`
- Saved UTC: 2026-10-12T03:14:15.693210+00:00
- Current roadmap step: **4 — biological validation remains ongoing; limited prospective comparative panel completed**.

## Completed work

The user completed all ten evidence downloads. Successful evidence run:
`/home/zyliu/Documents/rna-stable-ai/results/prospective_evidence_runs/20261012T025400.354107Z`. Original file hashes, source identity and envelopes verified.

Added `src/rnastable/prospective_binding.py`,
`scripts/evaluate_prospective_panel.py` and nineteen new regression tests.
Strict source checks found no overlap with known exposed PDB accessions in the
TPP/SAM/Purine mapping rows, and no overlap with the reported clans of the known
exposed families. Unknown training-family and legacy-tool provenance still
prevent a complete independence claim.

All 15 preselected sequences bind exactly to Stockholm alignment members.
Complete WUSS contacts are mapped without deleting contacts or replacing records.
All five TPP and four Purine records have supported references. The five SAM
references contain unsupported pseudoknots, and one Purine record lacks an
annotated paired column. Those six records retain unsupported outcomes and
unknown metrics for every method.

Binding run: `/home/zyliu/Documents/rna-stable-ai/results/prospective_binding_runs/20261012T030228.664684Z`.
Completed evaluation run: `/home/zyliu/Documents/rna-stable-ai/results/prospective_evaluation_runs/20261012T030338.012553Z`.

The final plan retains all 15 records × six methods = 90 outcomes: 54 measured,
36 unsupported. Model-seed-20261006 baseline/stack/helix checkpoints, exact sparse
decoding and zero penalty were fixed before source acquisition. A durable test
exposure event records all 15 records before any predictions/native folds.
No model fitting, decoder tuning or checkpoint selection used test outcomes.

Mean pair F1 on the nine supported references:

| Method | Mean F1 |
|---|---:|
| Baseline | 0.1396 |
| Stack | 0.2319 |
| Helix | 0.3561 |
| ViennaRNA | 0.6065 |
| LinearFold | 0.6065 |
| All unpaired | 0.0000 |

Helix improves over the learned controls in this limited fixed panel but remains
behind the native folding controls. These are comparative consensus-reference
scores, not direct experimental stability/function or fully independent
population-wide accuracy measurements. Means exclude unsupported references;
SAM has zero measured records and unknown mean F1, not a mean of zero.

All 18 native requests completed successfully, with zero unknown requests. Their
known wall time sums to 1.45624 seconds; testing overlapped execution, so this is
cost accounting rather than an isolated speed benchmark. Journals bind exact
sequences, request parameters and the evaluation manifest. Interrupted native
requests remain unknown and are not automatically retried.

## Verification

- Final full suite: **535 passed in 221.95 seconds**
  (`reports/prospective-evaluation-final-full-suite-2026-10-11.log`).
- Expanded focused binding/native checks: 33 passed.
- Earlier suite before four additional checks: 531 passed; its log is preserved.
- Audit replays all 27 frozen learned-model predictions, all-unpaired controls,
  exact metrics, source/model/input hashes, the exposure event and native journals
  without new native callbacks or test exposure.
- Fresh reuse of the consumed panel is rejected. The current registry contains
  3187 exposure records; all three new families are now consumed, including the
  unsupported records.
- New files pass Ruff with script bootstrap E402 ignored, compileall and
  whitespace checks.

The original completed manifest and summary remain unchanged. Additional model
replay/native accounting checks were added after execution; their results are
in `reports/prospective-evaluation-audit-2026-10-11.log`. The original summary
was not retroactively edited to add a cost field. A new unit fixture initially
omitted required native energy; the corrected fixture and final suite passed.

## Pending work

Model changes must use development cohorts and reserve new, unexposed families
under a separately frozen prospective protocol. Do not reuse RF00059/RF00162/
RF00167 as fresh tests or tune the evaluated checkpoints/decoder from these scores.

Resolve broader training-family and tool-training provenance. Only two families
have supported references here, and lengths are 97–128 nt. Pseudoknot-capable
reference evaluation, long biological annotations, experimental stability/function
validation and a validated release remain pending. No full independence or
biological stability result is claimed.

All development remains local; no commit, push or publication-checkout update
was made. The pre-existing staged Git index remains preserved.

## Exact continuation commands

Read-only replay of completed artifacts:

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/evaluate_prospective_panel.py --verify
.venv/bin/python -m pytest -q tests/test_prospective_binding.py tests/test_native_journal.py
.venv/bin/python -m pytest -q
```

Do not rerun binding/preparation or `--evaluate` to create another fresh test
from this panel: live-exposure checks reject it. `--verify` audits the frozen
historical ledger without starting another test. No further download is needed
for this completed panel. Retained per-record outputs:
`results/prospective_evaluation.csv` and `reports/prospective_evaluation_report.md`.

## Evidence

- `reports/prospective_evaluation_review_2026-10-11.md`
- `reports/prospective_binding_report.md`
- `reports/prospective_evaluation_report.md`
- `reports/prospective-evaluation-audit-2026-10-11.log`
- `reports/PROJECT_ROADMAP_2026-10-11.md`
