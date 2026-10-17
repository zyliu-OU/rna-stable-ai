# RNA-StableAI Step 2: longer RNA development review

Date: 2026-10-16 (America/Los_Angeles)  
Workspace: `/home/zyliu/Documents/rna-stable-ai`  
Active model scope: 1–4,999 nt

## What was established

The bounded sampled-pair labeler and one-step training checks support a 4,999-nt training path without an all-pairs label tensor. The synthetic 4,999-nt step used 100 positive and 400 sampled negative pairs, with peak process RSS of 680,772 KiB. A real 3,995-nt bpRNA record completed one optimizer step using 755 legal positives and 3,020 sampled negatives, with peak process RSS of 683,184 KiB. These are feasibility measurements; neither run measures structure accuracy.

The first two preselected Rfam family panels acquired all eight requested family sources but yielded only two and one complete references, respectively. Both failed their frozen readiness rules. A subsequent screen of 338 already acquired sequences found 11 complete references in four families: RF00177 (3), RF02540 (3), RF02541 (3), and RF02542 (2), spanning 1,399–3,100 nt. That screen used reference completeness to select records. The resulting panel is suitable for development diagnosis and does not serve as an independent test.

The 24-record bpRNA metadata screen selected 17 training-only RNAs spanning 1,158–3,995 nt. The matched sampled-pair study used the same 88 prior training records in both arms and added these 17 only to the extended arm. Each seed began both arms from identical weights; both arms used the same sampled loss, 10 epochs, and a fixed final checkpoint. No validation result selected an epoch. Bounded exact decoding used the same retained top-16 sparse candidate method for both arms.

| Seed | 88-record control pair F1 | 105-record extended pair F1 | Difference |
| --- | ---: | ---: | ---: |
| 7 | 0.2832 | 0.3021 | +0.0189 |
| 1729 | 0.2358 | 0.2869 | +0.0511 |
| 20261015 | 0.2625 | 0.2989 | +0.0364 |
| Mean | 0.2605 | 0.2960 | +0.0355 |

On the same 11 development references, frozen earlier checkpoints scored 0.0817 (control) and 0.1901 (extended) pair F1 with bounded exact top-16 decoding. Native controls scored 0.4742 (LinearFold) and 0.4499 (ViennaRNA) mean pair F1; all 11 folds succeeded for each control. The three-seed result supports continued longer-sequence training experiments, but does not establish generalization or superiority to the native controls.

## Diagnostic limits

- The 11-record cohort is small, selected using label availability, and contains related sequences within four families. One length band (2,000–2,999 nt) has only one record. There is no 4,000–4,999-nt labeled validation record in this panel.
- Sequence identity overlaps with previously recorded exposures were excluded during screening, but family lineage for the newly added bpRNA training records is incomplete. Family separation from those records has not been established.
- The old checkpoint diagnostic found only 1,726 of 6,665 legal gold pairs among control top-16 candidates (25.9%) and 2,697 among extended top-16 candidates (40.5%). Candidate retention and decoding remain bottlenecks. The bounded exact decoder is a development method; no inference default changed.
- The independent structure-validation gate remains open. Expression optimization should follow a credible structure and stability validation path, with expression-specific data and objectives; this work did not start expression optimization.

## Evidence and replay

- Panel source screens: `results/long_validation_family_runs/20261017T033513.077462Z/summary.json` and `results/long_validation_family_v2_runs/20261017T033627.321212Z/summary.json`.
- Development reference screen: `results/long_validation_coverage_runs/20261017T033935.363253Z/summary.json`.
- Training-only screen and one-step resource run: `results/bprna_long_training_smoke_runs/20261017T033749.792816Z/summary.json` and `results/bprna_long_training_step_runs/20261017T033839.555671Z/summary.json`.
- Frozen checkpoint comparison: `results/long_length_checkpoint_evaluation_v3_runs/20261017T034635.042291Z/summary.json`.
- Native controls: `results/long_native_controls_runs/20261017T034318.804594Z/summary.json`.
- Candidate diagnostic: `results/long_pair_candidate_diagnostic_runs/20261017T034529.696677Z/summary.json`.
- Matched training: `results/sampled_long_development_runs/20261017T034847.147062Z/summary.json`. The six-fit deterministic replay passed, including training history, checkpoint state, and predictions.

## Next Step 2 work

1. Resolve family provenance for the 17 bpRNA additions and freeze a genuinely independent family-separated long validation panel before claiming generalization.
2. Improve candidate recall and decoded pair recovery using development-only comparisons that keep the same reference cohort and decoder budget across arms.
3. Extend labeled coverage toward 4,000–4,999 nt and measure resource use at the upper bound; keep 5,000-nt-and-longer historical assets outside active model development.
4. Keep the native methods as reference baselines and preserve all frozen runs. Do not promote a learned checkpoint or alter production defaults based on this panel.
