# RNA-StableAI third prospective complete-pair evaluation — 2026-10-13

Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Source protocol: `results/prospective_family_protocol_runs/20261014T003018.640568Z`.
Acquisition: `results/prospective_family_acquisition_runs/20261014T003052.784986Z`.
Evidence: `results/prospective_evidence_runs/20261014T010916.985395Z`.
Binding: `results/prospective_pair_binding_runs/20261014T011058.285068Z`.
Evaluation: `results/prospective_pair_evaluation_runs/20261014T011253.580452Z`.

The declared source proposal retained five records each for RF00010, RF00023 and
RF00168. All six metadata files and all16 provenance/annotation files downloaded
and passed envelope/hash verification. Screening retained all982 source entries
and their reasons; sorted-ID/length/exposure/redundancy rules selected15 records.
No sequence or checkpoint was selected by new accuracy outcomes.

Exact sequence bindings and known family/clan/PDB/heuristic sequence-overlap
checks passed. Four lysine records have complete references; all five RNase P,
all five tmRNA and one lysine record lack an annotated paired column and remain
unsupported. Those records were not replaced, completed by deleting contacts,
or assigned zero accuracy. The binding retained every complete WUSS contact,
including crossing contacts where present.

The fixed six-method comparison retains90 planned outcomes:24 measured and
66 unsupported with null metrics. Mean record pair F1 on the four supported
lysine references is:

| Method | F1 |
|---|---:|
| Baseline | 0.065709 |
| Stack | 0.177214 |
| Helix | 0.533167 |
| ViennaRNA | 0.726724 |
| LinearFold | 0.748810 |
| All unpaired | 0.000000 |

These four records come from one supported family and are not independent
biological replicates. Helix improves over the other learned models but remains
below folding controls on this cohort. Results do not establish broad accuracy,
long-RNA performance, stability/function or complete training/tool independence.
Unknown training-family provenance remains unresolved. Existing models, decoder,
penalty and default checkpoints remain unchanged.

All15 selected identities, including unsupported records, were registered before
inference. These three families are now consumed for fresh-test planning. Future
model development must not tune on this panel or relabel it as a fresh test.
Eight native requests completed, zero unknown; retained wall time is0.810478s.
The final audit replays all planned outcomes, full reference scores, model/input
hashes, exposure and native journals without new native callbacks or test exposure.

The first full metadata replay now seeds a source/code/summary-bound cache, so
later evidence audits reuse the verified historical screen after checking all
snapshots. Current exposure and reference gates remain active. Cache changes
pass51 focused tests and a608-test full suite; a later639-test suite also passes.
Exact log files and final added-schema checks are recorded in the versioned handoff.
No Git index change, commit, push or publication.
