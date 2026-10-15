# RNA-StableAI third prospective panel preparation — 2026-10-13

Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Frozen protocol: `results/prospective_family_protocol_runs/20261014T003018.640568Z/manifest.json`.
Configuration: `configs/prospective_pair_family_panel_2026-10-13.json`.

Proposed sources are [bacterial RNase P type A (RF00010)](https://rfam.org/family/RF00010),
[transfer-messenger RNA (RF00023)](https://rfam.org/family/RF00023), and
[lysine riboswitch (RF00168)](https://rfam.org/family/RF00168).
These official family identities were checked before freezing the configuration.
No sequence bases, structure annotations or prediction outcomes were read before
freezing. Family landing pages include region metadata; sequence selection uses
the declared sorted-ID, length, prior-exposure and redundancy rules rather than
manual choice of those regions.

The original seed-20261006 baseline/stack/helix models, exact top-16 decoder,
zero penalty, 20–512 nt screening bound and five-record family cap remain fixed.
The source protocol explicitly declares complete-pair WUSS scoring via
`pair_set_zero_based_v1`. Newly trained structured-loss models are not included
or selected using prospective outcomes. The freeze preceded their final results.
The named exposure inventory contains ten other families; 3104 of 3202 exposure
records lack explicit family identity. Full training-family/tool independence
remains unresolved even for new family IDs.

The sandbox acquisition failed DNS lookup and retains its failed ledger at
`results/prospective_family_acquisition_runs/20261014T003036.122470Z`.
An approved outside-sandbox retry downloaded all six metadata source files into
`results/prospective_family_acquisition_runs/20261014T003052.784986Z`:
458 RNase P, 477 tmRNA and 47 lysine seed sequences. That invocation must finish
exposure/redundancy screening and publish its completed hash-bound summary before
its output is used as evidence input. Raw successful file requests alone are not
a completed screening or inference authorization.

The first evidence command was issued while screening was unfinished and rejected
the incomplete acquisition pointer. It downloaded no annotation files. Continue
from the exact successful acquisition run after its summary exists, preserving
the failed attempt. Later annotation binding must check current exposures,
family/clan/PDB overlap, exact sequence identity and complete contact mapping.
Missing paired columns must retain unsupported outcomes and null metrics.

## Completed state after preparation

The earlier status above records the initial acquisition stage. The retry
completed with15 selected metadata records, and a full deterministic screening
replay passed. All16 annotation/provenance files then downloaded and audited.
Complete-pair binding retained four supported lysine references and11 unsupported
records without replacement. The six-method evaluation retains90 outcomes:
24 measured and66 unsupported. All15 selected identities are now exposed for
future test planning. See `prospective_third_pair_evaluation_review_2026-10-13.md`
for final scores, exact run directories and limitations.
