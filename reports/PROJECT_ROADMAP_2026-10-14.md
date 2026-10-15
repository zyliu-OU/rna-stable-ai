# RNA-StableAI development roadmap — 2026-10-14

Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Status: research prototype; no validated release.

| Step | Stage | Status |
|---:|---|---|
| 1 | Reproducible foundations | Implemented and tested: resource bounds, native journals, hashes, exposure tracking, and replay caching. Source archive retains 257/267 recorded Python versions. |
| 2 | Structure-model development | Nine matched baseline/stack/helix BCE fits, candidate diagnostics, budgets 16/32/64, and three matched helix objective comparisons complete. Defaults unchanged. |
| 3 | Model-guided optimization | Synthetic studies and native energy verification complete; biological benefits unverified. |
| **4** | **Independent biological structure validation** | **Current scientific gate.** Three prospective panels evaluated; latest panel has four supported lysine references and eleven unsupported annotations among fifteen records. Broad accuracy and complete training/tool independence remain unresolved. |
| 5 | Long biological RNA validation | Synthetic controls reach 10,000 nt; exact sparse inference is bounded to 1,024 nt. Complete longer biological annotations and screened evaluation remain pending. |
| 6 | Measured stability and function | Descriptive OpenVaccine pilot complete: 64 constructs, 320 assay outcomes, 384 predictions, 2,880 proxy/assay comparisons, and 128 completed native requests. Controlled mutation effects and function validation pending. |
| 7 | Validated release | Gated on the evidence above; published artifacts remain experimental. |

## Current work and next step

The interrupted GitHub update packages the completed development, input data,
experimental checkpoints, evidence, and source archive. The front page now shows
the plan and current gate; detailed commands remain in [DEVELOPMENT.md](../DEVELOPMENT.md).
The final pre-publication suite passed **672 tests**.

Next research work is to design a screened, independently annotated biological
structure panel with adequate supported references and documented training/tool
provenance. Previously consumed families and the measured-assay source cannot be
reused as fresh independent tests. No new experiment is run by this publication.

The assay pilot is descriptive and uses only `SN_filter=1` short constructs.
Its associations do not establish causal mutation benefits, cellular half-life,
long biological accuracy, or retained function. Ten historical Python source
versions remain explicitly unavailable; the archive is not a complete portable
training environment.

## Evidence

- [Candidate-budget review](candidate_budget_development_review_2026-10-13.md)
- [Helix-objective review](helix_objective_development_review_2026-10-13.md)
- [Latest prospective structure review](prospective_third_pair_evaluation_review_2026-10-13.md)
- [Measured-assay review](degradation_pilot_review_2026-10-13.md)
- [Source archive limitations](../docs/REPLAY_SOURCE_ARCHIVE.md)
- [Final test log](github-update-full-suite-2026-10-13.log)
