# RNA-StableAI handoff

- Project: RNA-StableAI
- Date: 2026-10-11 (America/Los_Angeles)
- Version: V7
- Workspace: `/home/zyliu/Documents/rna-stable-ai`
- Saved UTC: 2026-10-12T03:46:26.322235+00:00
- Current roadmap step: **4 — prospective pair-set workflow integrated; new biological evaluation pending**.

## Completed work

Integrated `pair_set_zero_based_v1` into `build_binding` and the existing
`scripts/evaluate_prospective_panel.py` preparation, evaluation, resume and audit
workflow. `scripts/prepare_prospective_family_panel.py` accepts an explicit
`reference_format` in the source configuration. This field must be frozen before
metadata acquisition; both legacy-to-pair-set changes and accidental legacy
fallback are rejected. Resume also requires the same format, input/code/runtime
bindings and protocol. Historical configs without the field retain
`dot_bracket_v1` behavior.

Complete WUSS crossing contacts are supported in the declared pair-set mode.
Incomplete paired columns remain unsupported, with unknown metrics and full
record/method denominators. Nested model/native outputs are compared against all
reference contacts. Failure states cannot retain stale contacts. New rows and
summaries track complete crossing-reference counts. The prediction decoder
and all trained checkpoints remain unchanged.

New studies write separate `prospective_pair_binding` and
`prospective_pair_evaluation` publications and unique run directories. Existing
completed prospective result artifacts and their legacy scores remain unchanged.
The final plan and a durable exposure event precede inference. Native request
journaling preserves interrupted/unknown work without retry. Completed audit
replays frozen model predictions and scores without new native callbacks or test
exposure.

Added seven tests in `tests/test_prospective_pair_integration.py` and instructions
in `docs/PROSPECTIVE_PAIR_PROTOCOL.md`. The complete fixture pipeline has two
constructed references across six methods: one complete crossing reference and
one incomplete reference. All 12 outcomes remain planned; six are measured and
six unsupported. Two injected native calls are journaled, and event-before-call
ordering is asserted. Replay performs no native callbacks; reuse of the fixture
family, mismatched format and altered prediction files are rejected. These are
pipeline fixtures, not biological data or accuracy gains.

## Verification

- Full suite: **569 passed in 215.97 seconds**
  (`reports/prospective-pair-full-suite-2026-10-11.log`).
- Expanded focused set:64 passed in2.05seconds.
- Final seven integration tests:7 passed in0.11seconds.
- Historical completed prospective panel and pair-score equivalence checks remain
  included in regression testing. No fresh biological prediction, training,
  model/decoder selection or completed-panel rewrite occurred.
- Changed files pass Ruff with script bootstrap E402 ignored, compileall and
  whitespace checks.

## Pending work

Choose a new unexposed source-family panel and freeze its configuration with
`"reference_format": "pair_set_zero_based_v1"` before source outcomes.
Then acquire and verify metadata, provenance and complete annotations before
binding/evaluation. No new biological protocol or family panel was frozen in
this continuation; current pair-set pipeline evidence is synthetic test fixtures.

RF00059/RF00162/RF00167 and earlier evaluated families remain consumed. Do not
relabel or rerun the completed panel as a fresh test. Subsequent model development
must use development cohorts and reserve new families before prospective testing.

Unknown training/tool provenance, long biological annotation availability,
experimental stability/function and validated release remain pending. The model
still predicts nested structures. Evaluation of crossing contacts does not imply
a trained pseudoknot predictor or improved biological accuracy.

Changes remain local; no commit, push or publication-checkout update was made.
The original staged Git index remains preserved.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python -m pytest -q tests/test_prospective_pair_integration.py tests/test_prospective_binding.py tests/test_pair_reference.py tests/test_prospective_data.py
.venv/bin/python scripts/evaluate_prospective_panel.py --verify
.venv/bin/python scripts/validate_pair_reference_development.py --verify
.venv/bin/python -m pytest -q
```

For a future, separately frozen and acquired pair-set protocol (not the consumed
existing panel), after its evidence download:

```bash
.venv/bin/python scripts/evaluate_prospective_panel.py --reference-format pair_set_zero_based_v1
.venv/bin/python scripts/evaluate_prospective_panel.py --evaluate --reference-format pair_set_zero_based_v1
.venv/bin/python scripts/evaluate_prospective_panel.py --verify --reference-format pair_set_zero_based_v1
```

First prepare a new configuration using `docs/PROSPECTIVE_PAIR_PROTOCOL.md`;
the old frozen protocol did not declare pair-set scoring and cannot be changed
retrospectively. No downloads are needed to verify the completed integration.

## Evidence

- `docs/PROSPECTIVE_PAIR_PROTOCOL.md`
- `reports/prospective_pair_integration_review_2026-10-11.md`
- `reports/prospective-pair-final-focused-2026-10-11.log`
- `reports/prospective-pair-final-pipeline-2026-10-11.log`
- `reports/prospective-pair-full-suite-2026-10-11.log`
