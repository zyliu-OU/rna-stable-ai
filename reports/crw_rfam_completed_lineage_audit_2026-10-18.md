# RNA-StableAI CRW completed-search and panel exposure audit

Date: 2026-10-18 (America/Los_Angeles)
Workspace: `/home/zyliu/Documents/rna-stable-ai`

All six outstanding Rfam jobs returned completed responses on October 18. The existing frozen audit verified the response job IDs and exact full query sequences for all seven CRW training records. The original completed response for `bpRNA_CRW_13049` was retained; six new responses were saved separately, with retrieval timestamps, hashes and collector source. Empty interim responses remain preserved.

| CRW record suffix | Length (nt) | Returned hits | Significant-hit families | Query span / query length |
| --- | ---: | ---: | --- | --- |
| 13049 | 1,411 | 4 | RF00177, RF01959, RF02542, RF01960 | All 100% |
| 3489 | 1,514 | 4 | RF00177, RF01959, RF02542, RF01960 | 99.7–99.9% |
| 54679 | 2,474 | 2 | RF00029, RF02012 | 3.0%, 6.4% |
| 54684 | 2,520 | 1 | RF00029 | 3.4% |
| 55280 | 2,896 | 3 | RF02541, RF02540, RF02543 | 94.1–100% |
| 55339 | 2,925 | 4 | RF02540, RF02541, RF02543, RF00002 | 95.0–99.8%; RF00002 4.6% |
| 55396 | 3,946 | 4 | RF02543, RF02540, RF02541, RF00002 | 93.9–95.9%; RF00002 4.0% |

Every returned hit has E-value ≤ 1e-5 and is retained as a possible exposure. Hit family/clan annotations were checked against the pinned Rfam 15.1 seed archive. Query span is the inclusive coordinate span divided by query length; it does not establish a complete reference structure or whole-record family assignment. The service's model release was not independently established by this check.

The possible exposed clans are CL00111 (SSU), CL00112 (LSU), and CL00102. RF00029 has no assigned clan in this archive. In particular, `54679` combines an unclanned hit with a CL00102 hit, both local: the original audit's `single_strong_clan` field only counts non-null clan IDs and must not be read as resolving the whole RNA to one clan. The short local hits for `54679` and `54684` leave their broader lineage unresolved.

There are **zero returned-hit family/clan overlaps among the 13 frozen five-clan references**. Among the earlier 39 candidate families, RF02545 and RF02546 overlap SSU/LSU clans; both were already excluded as known exposed clans (four candidates each). These observations do not establish absence of homology, resolve full-length lineage, or upgrade the earlier feasibility study to independent validation. No reference labels, predictions, checkpoints or model defaults were changed.

## Local evidence and verification

- Responses and retrieval manifest: `results/crw_rfam_batch_response_runs/20261018T221626.685196Z/`.
- Completed frozen audit: `results/crw_rfam_batch_result_audit_runs/20261018T221637.760541Z/summary.json` (7/7 completed and sequence verified).
- Supplementary coverage/exposure audit: `results/crw_panel_exposure_runs/20261018T221708.139284Z/summary.json`. Its manifest pins the completed audit, panel selection, earlier clan inventory, Rfam seed archive and driver. Replay also verifies the saved response hashes through the original audit.
- Three focused tests passed for local/unclanned exposures, weak hits, unverified sequences and out-of-range coordinates. Supplementary replay passed.
- Prior 1,000–4,999 nt Rfam seed audit replay passed: no surviving candidates. A separate complete structure-reference source remains necessary.

The next lineage work should inspect the original provenance of CRW records `54679` and `54684`, or conservatively quarantine their unresolved whole-record lineage in future independent-panel design. A completed search is not a completed lineage gate.
