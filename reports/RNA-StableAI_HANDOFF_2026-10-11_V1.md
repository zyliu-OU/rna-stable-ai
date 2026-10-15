# RNA-StableAI handoff

- Project: RNA-StableAI
- Date: 2026-10-11 (America/Los_Angeles)
- Version: V1
- Workspace: `/home/zyliu/Documents/rna-stable-ai`
- Saved UTC: 2026-10-12T02:12:38.369572+00:00

## Completed work

Fixed the expired hard-coded helix replication deadline. New studies default to
an execution window of two hours; `--deadline-utc` explicitly extends a resume
without changing its frozen manifest. Separate execution receipts retain original
and effective deadlines and manifest/driver hashes. Resume validates frozen code,
plan and directory before child execution. Added seven deadline/source regression
tests, README instructions and updated native-study model-card evidence.

Resumed the seed20261007 helix study from
`results/helix_prior_replication_runs/20261007T023827.967339Z` and completed its
sixth component. All six components and the aggregate passed their frozen audits.
The original manifest hash remains
`ac958c9c3156257401b9796d40ebda812ad117f660bbac9cf4d7dbfee28bc3d2`.
Of198 planned native requests,197 completed and one earlier interrupted request
remains unknown and unretried. All requests started; no orphan outputs were found.
The six checkpoint-prior selected deltas are−21.9/−15.0 at1000nt,
−2.2/−11.6 at5000nt and−5.9/−17.9kcal/mol at10000nt (search seeds20261006/07).

Generated and replayed the comparison of54 stack/helix trajectories,12 paired
prior comparisons and24 reproduced controls. Helix selected lower native energy
than stack in nine paired comparisons and higher in three. Eight comparisons
against compatibility have lower energy, three higher, one unknown. No new model
fitting, fresh test-set evaluation or checkpoint selection occurred.

Review: `reports/development_2026-10-11_review.md`.
Comparison: `reports/checkpoint_prior_comparison_report.md`.
Request ledger: `reports/helix_prior_execution_report.md`.

## Verification

- Full suite: **488 passed in222.51seconds**; `reports/development-tests-2026-10-11.log`.
- Focused deadline/frozen-source/accounting checks:10 passed.
- Original and seed20261007 helix aggregate audits passed.
- Request ledger audit passed with zero native callbacks.
- Combined comparison replay passed with zero native callbacks.
- Changed Python files pass Ruff with script bootstrap E402 ignored, compileall
  and whitespace checks.

## Pending work and limitations

Independent biological family evaluation and longer biological annotations remain
pending. Freeze the model/decoder and audit exposure exclusions before evaluating
fresh records. RF00008/RF00017 and repeatedly reused development records are
already exposed. Synthetic native energy improvements do not establish biological
stability, structure accuracy, retained function or generalization. The interrupted
compatibility reference at10000nt/search seed20261007 has unknown outcome/cost;
do not interpret its selected delta as zero. Known timing excludes interrupted
cost and overlapped testing, so it is not an isolated speed benchmark.

Changes and artifacts are local. The pre-existing workspace Git index and
publication checkout were preserved; no commit or GitHub push was made.
Both helix studies are now complete, so there is no remaining native component to
resume. Review independent-family planning next.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/run_helix_prior_replication.py --verify
.venv/bin/python scripts/run_helix_prior_replication.py --verify --publish-name helix_prior_seed7_replication
.venv/bin/python scripts/audit_native_study_accounting.py --verify
.venv/bin/python scripts/compare_checkpoint_priors.py --verify
.venv/bin/python scripts/plan_family_study.py --help
.venv/bin/python -m pytest -q
```

For another unfinished frozen helix study, use `--resume STUDY_DIRECTORY` with
its matching publication name and a future timezone-aware `--deadline-utc`.
Never edit the frozen snapshot or retry an unknown journal request.
