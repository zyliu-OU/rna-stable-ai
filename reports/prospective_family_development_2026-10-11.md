# RNA-StableAI prospective family workflow — 2026-10-11

Workspace: `/home/zyliu/Documents/rna-stable-ai`.

## Completed engineering

Added `configs/prospective_family_panel.json`,
`scripts/prepare_prospective_family_panel.py` and
`src/rnastable/prospective_data.py`. A preliminary protocol freezes the three
model-seed-20261006 baseline/stack/helix checkpoints, their source summaries and
configuration before any new source outcomes. It fixes exact sparse decoding,
zero pair penalty, a 20–512 nt screening range, sorted sequence-ID selection and
at most five nonredundant entries per proposed family. No model is selected from
new test scores. This preliminary protocol does not authorize test inference.

Proposed sources are RF00059, RF00162 and RF00167. Rfam documents JSON family
descriptions and ungapped seed FASTA endpoints in its
[API documentation](https://docs.rfam.org/en/latest/api.html). The source panel
is a prospective acquisition proposal; family/clan and training-overlap evidence
has not yet approved these families for independent evaluation.

The acquisition workflow bounds response size and socket timeouts, validates
the requested family accession, hashes original response bytes and snapshots
the live exposure ledger. Uppercase and T-to-U FASTA normalization is recorded
explicitly. Invalid sequences, redundant panel entries, cap exclusions, download
errors and unstarted requests remain visible. Successful metadata retrieval alone
does not authorize annotations or inference. No Stockholm labels are requested.
Each acquisition invocation creates a new retained directory; offline replay
uses snapshots and performs no network requests.

The exposure heuristic now skips sequence comparisons whose length-based maximum
possible SequenceMatcher score is below 0.8. This is an exact upper bound on
2*M/(len(a)+len(b)), preserving the previous screening decisions while avoiding
expensive comparisons against much longer exposed synthetic sequences. The
existing local readiness result still replays unchanged.

## Actual retained state

Frozen protocol:
`results/prospective_family_protocol_runs/20261012T023120.466587Z/manifest.json`.

Acquisition attempt:
`results/prospective_family_acquisition_runs/20261012T023237.122453Z`.

All three family-description requests failed with a DNS resolution error in the
workspace. The three dependent sequence requests remain unstarted because family
description binding is unavailable. No source files or structure labels were
downloaded. `sources_complete:false` is retained; zero selected entries here
means unavailable sources, not an empty screened biological cohort. Raw browser
alignment retrieval also failed.

The earlier local audit still reports 474 entries in four exposed families and
zero new candidates. Exact sequence matching against that local Rfam metadata
does not resolve any of the 3104 exposure entries missing family IDs. Sixty-nine
unassigned exposure records carry PDB accessions; broad RNA-type names must not
be substituted for verified family/clan assignments. These exposure records
include development and generated/inference sequences, not a count of distinct
biological training examples.

## Verification and next work

Focused source/readiness tests pass, including malformed/oversized responses,
redirect rejection, sequence normalization, cap/redundancy denominators, DNS
failure replay, successful fixture screening without inference authorization,
checkpoint tampering and new family exposure after protocol freeze. Fixtures are
test-only examples, not acquired biological data. Final suite results are in the
versioned handoff and `prospective-family-full-suite-2026-10-11.log`.

Once source access is available, rerun acquisition against the frozen protocol.
Resolve family/clan and training-overlap evidence, bind selected sequences to
exact annotation sources, and freeze the final evaluation plan before predictions.
The project remains at roadmap step 4: independent biological validation.
