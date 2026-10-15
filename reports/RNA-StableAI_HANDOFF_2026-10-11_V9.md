# RNA-StableAI handoff

Project: RNA-StableAI. Date: 2026-10-11 (America/Los_Angeles). Version: V9.
Workspace: `/home/zyliu/Documents/rna-stable-ai`. Saved UTC: 2026-10-12T03:59:11.277885+00:00.
Current roadmap step: **4 — second prospective panel evaluated; complete-pair scoring audited**.

## Completed work

User downloaded all source metadata and 13/13 evidence files for the frozen
RF00050/RF00174/RF00234 panel. Bound all 15 exact sequences without known
family/clan/PDB or heuristic sequence overlap. Eight full references are supported,
six containing crossing contacts; seven incomplete paired-column references
remain unsupported. Full reference contacts were retained, with no re-selection.

Executed the frozen six-method comparison: 90 planned outcomes, 48 measured,
42 unsupported with null metrics. Sixteen native requests completed, zero unknown.
Mean pair F1 on the eight supported references: baseline 0.0925, stack 0.1870,
helix 0.3082, ViennaRNA 0.5043, LinearFold 0.4977, all-unpaired 0.0000.
No training, model/decoder/penalty selection or experimental stability claim.

Source run: `/home/zyliu/Documents/rna-stable-ai/results/prospective_family_acquisition_runs/20261012T035150.817444Z`.
Evidence run: `/home/zyliu/Documents/rna-stable-ai/results/prospective_evidence_runs/20261012T035356.363981Z`.
Binding run: `/home/zyliu/Documents/rna-stable-ai/results/prospective_pair_binding_runs/20261012T035646.856700Z`.
Evaluation run: `/home/zyliu/Documents/rna-stable-ai/results/prospective_pair_evaluation_runs/20261012T035701.921281Z`.
Review and descriptive nested-contact ceilings: `/home/zyliu/Documents/rna-stable-ai/reports/prospective_pair_evaluation_review_2026-10-11.md`.

## Verification

Completed pair-set audit passed all planned outcomes, exact reference scores,
model/input hashes, exposure event and native journals. Audit performs no new
native folds or fresh test exposure. Logs are listed in the review. Pipeline code
unchanged; prior full suite 569 passed, preceding source-freeze checks 18 passed.
Whitespace check passed. Git index preserved; no commit, push or publication.

## Pending work

All three new families are consumed, including unsupported records. Do not treat
any rerun or format change as fresh independent testing. Unknown training/tool
provenance remains unresolved (3104 pre-evaluation entries have unknown family),
and reference contacts are comparative consensus annotations. Full independence,
long biological accuracy, experimental stability/function and validated release
remain pending. Next model development must use development-only cohorts and
reserve new families before testing; do not tune using this or the earlier panel.
No further terminal commands are needed to finish this evaluation.

## Exact continuation commands

For saved-run verification, not a new evaluation:

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/evaluate_prospective_panel.py --verify --reference-format pair_set_zero_based_v1
.venv/bin/python scripts/evaluate_prospective_panel.py --verify
.venv/bin/python scripts/validate_pair_reference_development.py --verify
.venv/bin/python -m pytest -q tests/test_prospective_pair_integration.py tests/test_prospective_binding.py tests/test_pair_reference.py tests/test_prospective_data.py
```

Read `/home/zyliu/Documents/rna-stable-ai/reports/prospective_pair_evaluation_review_2026-10-11.md` and `docs/PROSPECTIVE_PAIR_PROTOCOL.md` before subsequent
work. The legacy panel remains available through its separate publications.
Previous current status archived at `/home/zyliu/Documents/rna-stable-ai/reports/archive/20261012T035911.277885Z`.
