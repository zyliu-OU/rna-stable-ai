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

Development resumed after the completed GitHub publication. The reference-readiness
audit now makes coverage and annotation lineage explicit. None of the three earlier
panels meets the new broad-coverage minimum. A pinned per-sequence PDB-derived
source import retains six references across three families, after 35 redundant
annotations are excluded. Raw FR3D provenance auditing found three historical
contact-set differences. A separately frozen six-family raw-contact feasibility
cohort now retains ten supported references from 21 source requests; all 60
model/control outcomes and 20 native calls completed. Mean pair F1 is 0.325531
for helix and 0.626116 for both native controls. This narrow feasibility result
does not close the broad gate. The full suite passed **803 tests**. A checkpoint
lineage audit identifies 83/136 development records without confirmed family
assignments. Next work targets a source-labelled, family/clan-aware training and
validation plan. Detailed commands remain in
[DEVELOPMENT.md](../DEVELOPMENT.md).

Next research work is to design a screened, independently annotated biological
structure panel with adequate supported references and documented training/tool
provenance. Previously consumed families and the measured-assay source cannot be
reused as fresh independent tests. The raw-contact comparison is explicitly a
small feasibility study. Newly imported PDB-derived source families are consumed for
future fresh-test planning. These source/evaluation artifacts accompany the
development progress summary; the user's README picture is preserved.

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
- [Reference readiness](../docs/REFERENCE_READINESS.md)
- [PDB-derived reference engineering](../docs/STRUCTURE_DERIVED_REFERENCES.md)
- [Source/binding test log](structure-derived-full-suite-2026-10-14.log)
