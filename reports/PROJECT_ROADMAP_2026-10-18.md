# RNA-StableAI development roadmap — 2026-10-18

Workspace: `/home/zyliu/Documents/rna-stable-ai`

## Current direction

The user selected **cell-free expression** for Stage 3 and explicitly requested that Stage 2 be good for RNAs **smaller than 3,000 nt** first. Active work is therefore 1–2,999 nt. Stage 2 accuracy and validation are the immediate milestone; Stage 3 expression design remains queued.

The current length policy is `configs/project_scope_2026-10-18.json`; the transition requirements are `configs/stage2_to_stage3_gate_2026-10-18.json`. Historical protocols and data stay intact. Work at 3,000 nt and above is deferred, including the recent Qβ/AP205 source leads. No sequences are truncated to fit the cap.

## Selected component architecture and current next work

The user selected **RNAfold + STRAND + RiboNN + BoTorch** after the custom
structure studies below. Fixed-input folding/ensemble extraction, reference-only
STRAND fitting, RiboNN human checkpoint replay and toy optimizer mechanics are
implemented. The original STRAND features use LinearPartition, so RNAfold feature
substitution still needs an explicit compatibility/calibration review. RiboNN is
not calibrated to the intended cell-free system. Current priorities are that
interface review, versioned score records and genuinely independent Stage 2
evidence; further custom pair-loss fitting is historical follow-up rather than
the default architecture task. No stage gate or inference default is promoted.
See the [integration guide](../docs/four_component_integration_2026-10-18.md),
[STRAND reproduction](strand_reference_reproduction_review_2026-10-18.md),
[RiboNN replay](ribonn_fixed_inference_review_2026-10-18.md) and
[current development handoff](RNA-StableAI_HANDOFF_2026-10-18_V12.md).

## Historical Stage 2 custom-model evidence

An audit restricted the existing longer development cohort to six RNAs below 3,000 nt. Across three historical extended-model checkpoints, top-32 decoding averages pair F1 **0.2965**, versus **0.4381** for LinearFold and **0.4215** for ViennaRNA. Five references are 1,000–1,999 nt and only one is 2,000–2,999 nt. The separate five-clan feasibility cohort covers 400–535 nt and also leaves a native accuracy gap. These are exposed development cohorts, not independent validation.

The new matched study now uses only in-scope training sequences: 88 control records versus 103 extended records, three seeds, ten epochs and fixed-final checkpoints with top-32 decoding. Mean pair F1 is **0.2695 versus 0.3174** on the six longer development references and **0.1357 versus 0.1561** on the thirteen 400–535 nt references. Native controls still score higher on both cohorts. See [the Stage 2 review](stage2_under3000_review_2026-10-18.md).

The historical custom-model recommendation was to concentrate on pair scoring and recovery rather than another broad source inventory. The selected component architecture above now determines the default next work; Stage 2 stays open. Decoder budgets and score offsets have already been explored on exposed development data; they cannot independently validate a selected model. Improvements on either reused cohort remain development evidence.

Two subsequent frozen studies leave that baseline unchanged. Endpoint ranking improved the short development cohort but left longer mean F1 flat. A teacher-pool hard-negative mixture then regressed against its matched random-from-pool control on both cohorts in every seed. See the [endpoint-ranking review](stage2_endpoint_ranking_review_2026-10-18.md) and [hard-negative review](stage2_hard_negative_review_2026-10-18.md). The subsequent gold-label ceiling diagnostic found long full/retained-candidate oracle F1 of **0.9606/0.8257**, versus actual **0.3174**. Retained-candidate and score-selection gaps account for most missed gold pairs; these optimistic oracles use reference labels and are not model accuracy. A fixed endpoint partner/null auxiliary-loss study then improved longer mean F1 to **0.3262**, with positive differences in all three seeds; shorter mean F1 reached **0.1606**, with one seed regressing. Keep this as a development variant and preserve the original BCE comparison baseline. See the [ceiling and assignment review](stage2_recovery_ceiling_and_assignment_review_2026-10-18.md). Audit the flagged noncanonical short-reference annotations before further fitting, retaining all original labels and frozen results.

Before the Stage 3 transition, freeze quantitative accuracy acceptance criteria appropriate to the intended use, assemble genuinely independent sequence/family/clan-separated evidence in the target range, report results by length and family against native controls, address sparse 2,000–2,999 nt coverage, and pass constraint/resource/replay checks. A successful execution or lower training loss alone does not establish useful structure accuracy. No checkpoint or default is promoted by the current work.

## Stage 3 after the gate

The first expression system will be cell-free. Define the specific cell-free platform, baseline CDS and UTRs, genetic code, protected features, allowed synonymous edits, and assay conditions before designing biological candidates. Measure protein output and time-matched RNA abundance; retain original sequences and simple matched controls. Keep measured expression, RNA persistence, structural predictions and thermodynamic scores as separate outcomes. Stage 2 proxy improvements alone do not establish an expression benefit.

This preserves the seven-stage project plan while narrowing the immediate work to the user's requested transition: credible Stage 2 evidence first, then a small, controlled cell-free expression pilot.
