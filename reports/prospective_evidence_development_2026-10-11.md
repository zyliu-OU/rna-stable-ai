# RNA-StableAI successful metadata acquisition and evidence download — 2026-10-11

Workspace: `/home/zyliu/Documents/rna-stable-ai`.

The user ran the frozen source acquisition from a terminal with working network
access. All six description/sequence requests succeeded and the retained files
passed the offline acquisition audit. Successful run:
`results/prospective_family_acquisition_runs/20261012T024003.811773Z`.

The three families report Rfam release 15.1. The frozen source-screening protocol
and model checkpoints remain unchanged. No model fitting, structure predictions
or new test exposure events were created.

| Family | Seed entries | Screening candidates | Selected | Clan reported by description |
|---|---:|---:|---:|---|
| RF00059, TPP | 115 | 114 | 5 | null |
| RF00162, SAM | 457 | 457 | 5 | CL00012 |
| RF00167, Purine | 133 | 133 | 5 | CL00123 |

The single excluded TPP entry has an invalid/ambiguous sequence. The 15 selected
entries are 97–128 nt long. Selection remains metadata/sequence based; no
annotation-driven replacement is permitted. The clan fields are source metadata,
not proof of separation from all training exposures. Sixty-nine previously
exposed records carry PDB accessions without verified family assignments.

## Next source batch

Added `scripts/download_prospective_evidence.py`. It binds to the successful
acquisition and derives ten fixed requests: three family-to-PDB mapping files,
four descriptions of already exposed families for clan checks, and three
Stockholm seed alignments. Endpoints follow the
[Rfam API documentation](https://docs.rfam.org/en/latest/api.html).

Every attempt retains request URLs, status, original response hashes and raw
bytes when received. File envelopes are checked for JSON shape, requested
description accession/release and complete Stockholm headers/accessions. These
checks do not parse consensus pairs or certify PDB/clan independence. If provenance
downloads fail, the dependent Stockholm requests remain unstarted. Each rerun
creates a new retained directory; offline audit performs no network requests.

The workspace attempt at
`results/prospective_evidence_runs/20261012T024646.468402Z` retains seven DNS
failures and three unstarted Stockholm requests. Its failure ledger passed audit;
no evidence or annotation files were downloaded. The user must run this batch
from the same terminal that successfully fetched the metadata.

## Verification and remaining work

Eight focused tests pass: fixed request-plan derivation, release mismatch,
wrong/truncated Stockholm envelopes, skipped annotation requests on provenance
failure, fixture success without evaluation authorization, snapshot tampering and
retained malformed raw responses. Fixture files are test-only examples.
Final full-suite results are recorded in the versioned handoff.

After successful download, inspect the real PDB mapping response schema, check
overlap with all known PDB/family exposures and bind each selected sequence to its
exact Stockholm alignment member. Consensus-derived comparative annotation is
not a direct experimental measurement. Unsupported pseudoknots, missing paired
columns or sequence mismatches must stay explicit; do not silently drop contacts
or replace the preselected records. Freeze the final evaluation plan before
inference. The project remains at roadmap step 4, independent biological
validation; no new accuracy or stability result is claimed.
