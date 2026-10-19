# RNA-StableAI handoff — 2026-10-19 V7

Project: RNA-StableAI
Date: 2026-10-19, America/Los_Angeles
Version: V7
Workspace: `/home/zyliu/Documents/rna-stable-ai`
Selected architecture: **RNAfold + STRAND + RiboNN + BoTorch**
Immediately previous handoff: [V6](RNA-StableAI_HANDOFF_2026-10-19_V6.md), which retracted the "needs network" framing and recorded the first, unreproducible version of the Rfam finding.
Publication record: [V5](RNA-StableAI_HANDOFF_2026-10-19_V5.md). Band census v1: [V4](RNA-StableAI_HANDOFF_2026-10-19_V4.md). Score records: [V3](RNA-StableAI_HANDOFF_2026-10-19_V3.md). Named calibration: [V2](RNA-StableAI_HANDOFF_2026-10-19_V2.md). Engine agreement: [V1](RNA-StableAI_HANDOFF_2026-10-19_V1.md).

## Scope of this session

The user approved the two follow-ups V6 listed: promote the Rfam finding to a frozen artifact, and check whether non-Rfam structural material could supply a new in-band clan. Both are done as **one** coherent deliverable, because they answer the same question — is gate requirement 3 achievable from any available source?

Delivered: a pinned acquisition run, a frozen census v2 protocol, a new module, a driver with `--verify-run`, 27 tests, and a canonical run. **220 focused tests pass.** No inference, no refit, no selection change, no cap change, no gate amendment. `configs/stage2_band_coverage_census_v1_2026-10-19.json` and its run remain frozen and untouched.

## Correction that supersedes V6

**V6's pending item 2 was premised on my own misreading, and it is withdrawn.** V6 proposed checking `results/rcsb_long_rna_survey_protocol_runs/20261018T222353.610817Z/exposures.json` for "144 band records, 6 without family", implying a fresh pool of PDB structures. Inspection shows that file is an **exposure ledger**, not a structural source: of its 144 band-length records, **137 came from `results/long_validation_coverage_runs/20261017T033935.363253Z`** — the very candidate pool the v1 census already analysed — with 6 from `bprna_long_training_smoke_runs` and 1 from `long_length_checkpoint_evaluation_runs`. All are already-exposed material.

The genuinely PDB-derived records in that file (266 carrying `pdb_accession`) span **20–1,072 nt**, with **zero** in the band and 261 of 266 under 500 nt. So that local survey contains no band-length structural material at all. I therefore went to the RCSB search API directly, which is what the check should have been.

## New finding: requirement 3 is not achievable from Rfam or the PDB

The gate requirement under test is `Resolve_sparse_2000_2999_nt_coverage_before_claiming_the_full_length_range`. V4 called it `blocked_on_acquisition`; V6 found Rfam cannot supply it; this session adds the PDB and makes both reproducible.

**Verdict: `not_resolvable_from_surveyed_sources_unresolved_leads_present`**, `achievable_from_surveyed_sources: false`.

### Rfam

4,227 families parsed with **0 skipped rows**; 480 clan memberships over 151 clans. The consensus-length column was validated against **ten** independently known family sizes at **zero tolerance** before any conclusion was drawn — the census raises if that check fails, so a shifted column cannot produce a silent wrong answer. All ten matched exactly: RF00005 71, RF00001 120, RF00002 154, RF02542 1311, RF01959 1478, RF00177 1533, RF01960 1831, RF02541 2925, RF02540 2987, RF02543 3401.

Consensus-length distribution: **4,187** families under 500 nt, 30 at 500–999, 7 at 1,000–1,999, **2** at 2,000–2,999, 1 at ≥3,000. The two band-length families are **RF02540 (CL00112, clen 2987)** and **RF02541 (CL00112, clen 2925)** — both in the already-represented clan.

Scanning every seed alignment by **ungapped individual sequence length** (because sequences can exceed their family's consensus length): **166** band-length sequences across 5 families — RF02541 81, RF02540 57, RF01960 24, RF02543 2, RF02462 2. Only **RF02462 (CL00004)** lies outside the baseline clans, and its 2 band sequences are **both already held locally**:

```
"RF02462": {"clan_id": "CL00004", "band_sequences": 2,
            "already_held_locally": 2, "newly_available": []}
```

**`newly_available_outside_baseline: 0`.** The cross-check against the v1 census's 138 locally held band records confirms these are the same two records V4 flagged `prior_exposure_overlap`. No clan-unresolved band families remain.

### RCSB / PDB

Queried live for experimental RNA polymer entities of 2,000–2,999 nt, faceted on description. **1,472** band-length entities exist and the facet covers 100% of them:

| class | descriptions | entities |
| --- | --- | --- |
| ribosomal | 75 | **1,448** (98.4%) |
| generically named | 15 | 21 |
| other | 1 | 3 |

The ribosomal class is dominated by 23S rRNA (518 + 495 + 177 + 55 + 18 + 18 + 17 across spelling variants) and includes an entry literally labelled "50S subunit". The 21 generically named entities are things like `RNA (2912-MER)` and `Chains: A`, plus one mis-annotated `Escherichia coli … complete genome`; the frozen protocol forbids counting these as new-clan leads **and** forbids asserting them as confirmed ribosomal, so they are reported as unresolved.

The single "other" description is **`35s rna`, 3 entities**. 35S is the ribosomal RNA precursor transcript, so this is ribosomal too — the protocol's keyword list simply did not include "35s". I have **not** edited the frozen config to reclassify it, since tuning a classifier after seeing its output is exactly what freezing prevents. The conservative verdict therefore stands at "unresolved leads present", while the honest reading is that the PDB's band is effectively entirely ribosomal.

### What this means

RNAs of 2,000–2,999 nt with known structure or curated alignment are, in both surveyed sources, essentially exclusively ribosomal. That is a fact about the data landscape, not a project deficiency, and it means **requirement 3 as written cannot be satisfied by acquisition.** The remaining options are unchanged from V6 but now evidenced:

1. **Retrain without the RF02462 exposure**, making those two records usable: clan CL00004 in-band at n = 2. Small n, and a retrain carries its own lineage accounting.
2. **Amend requirement 3 by explicit gate review** — for instance narrowing clan separation in a band where no source can supply it. The census is forbidden from doing this; `gate_amended` is false in the config, the summary and the verdict, and `requirement_status` in the v1 module already raises on any attempt to mark a requirement satisfied. **This is your decision, not mine.**
3. **Accept the band as a documented limitation** and claim the length range only up to where clan-separated evidence exists.

## Completed work

### Pinned acquisition run

**`results/band_availability_source_runs/20261019T185511.665510Z/`** — raw upstream bytes with a manifest recording origin URL, size and SHA-256 for each. No selection, scoring or inference at acquisition.

| File | SHA-256 | Bytes |
| --- | --- | --- |
| `clan_membership.txt.gz` | `2f199aaaa0a1e340145acb8fa20639427d1c0a38f4dedce29901888f222afbec` | 1,685 |
| `family.txt.gz` | `5662343d24b6f8dab566977fabebeb9df4bbec47fb8991400749fc642f03df69` | 378,804 |
| `Rfam.seed.gz` | `41f014f4ab5628620935f089b1bb77987ebc162fda7c72bff368a32c9cccabac` | 5,928,432 |
| `rcsb_query.json` | `f1778d5e8a470a9c5a54c9a54b3b2fb5d4294e0d84092b0e71ed2e21508bcfbc` | 672 |
| `rcsb_response.json` | `3df303184d5362aca042029b4ea3a38e3e9967bbea391d4f1cb7b8638c115d9c` | 6,490 |

Rfam files came from `https://ftp.ebi.ac.uk/pub/databases/Rfam/CURRENT/`; the RCSB files are the request body and response for `https://search.rcsb.org/rcsbsearch/v2/query`. Retrieved 2026-10-19. Rfam serves these at `CURRENT` without stamping a release number into the files, which the manifest records.

### Frozen protocol

**`configs/stage2_band_clan_availability_census_v2_2026-10-19.json`** — SHA-256 **`8e8f69b6830c96649dd3645a96fbf1ae0be6618b6537fcf18bfbd42aa1046aec`**. It declares what it is not, pins all five sources by hash, names the baseline clans with their provenance and the pseudo-replicate rule, requires the consensus-length validation at zero tolerance and zero skipped rows, specifies the ungapped-length seed method and why consensus length is insufficient, fixes the RCSB keyword and generic-pattern lists in advance, states that descriptions carry no clan so "other" entries are leads rather than resolved clans, defines three verdict states, and lists five no-claim statements — including that the census **may not amend, narrow or reinterpret a gate requirement**, and that surveying two sources does not prove a reference exists nowhere.

**One defect found and fixed during authoring, disclosed here:** my first draft of this config carried a **fabricated SHA-256 tail** for `rcsb_query.json`, because I had only seen the hash's first 16 characters in a terminal. I replaced it with the real value and then verified all five hashes against the acquisition run before the census ran. No run was ever produced from the bad config.

### Implementation

- **`src/rnastable/band_availability.py`** (new, 189 lines). `parse_clan_membership`, `parse_family_metadata`, `validate_consensus_lengths`, `scan_seed_band`, `classify_description`, `summarize_rcsb`, `rfam_band_availability`, `achievability_verdict`. Raises on conflicting clan assignments, empty parses, a missing or disagreeing validation family, negative tolerance, and a missing RCSB facet. A family with no clan assignment is reported as unresolved and can never be credited as a new clan.
- **`scripts/audit_band_clan_availability.py`** (new, 196 lines). Re-verifies the five pinned source hashes and the v1 census's `band_records.json` against its own manifest, asserts the requirement under test is a real gate requirement and the band ends at the active scope boundary, refuses to run if any mutation flag is set, and writes the run. `--verify-run` re-checks artifact hashes, replays the verdict from stored counts and **fails if a stored verdict claims a requirement satisfied or a gate amended**.
- **`tests/test_band_availability.py`** (new, 27 tests). Config gates and the amendment prohibition; validation requirements; clan parsing including conflict and empty; `clen` located by position from the end with skip counting; the validation catching a deliberately shifted column, a missing family and a negative tolerance; seed scanning with gaps and interleaved Stockholm blocks and band-boundary exclusion; eight description-classification cases; RCSB summarisation including incomplete facet coverage and a missing facet; the already-held subtraction that produces the zero result; unresolved clans never being credited; and all three verdict states never claiming satisfaction or amendment.

### Canonical run

**`results/band_clan_availability_runs/20261019T185713.116447Z/`** — 10 files, 64,689 bytes, `manifest.json` lists **9** artifacts.

| Artifact | SHA-256 | Bytes |
| --- | --- | --- |
| `summary.json` | `7eeb45296e02551fbf334ed714b13ecc220d23408447e6e2ffa6eaa96ee79b0a` | 13,241 |
| `rcsb_band_classification.json` | `1adc1616b5004d52c598e81504ef3ea320dfcc7c8f15adf0101088ae1a16143f` | 8,379 |
| `rfam_seed_band_sequences.json` | `6dc96272d282cdd9f8aeff0e39122811cdc7168f5d99c6a910b9e010b234e7f7` | 12,952 |
| `rfam_consensus_length_validation.json` | `4e513cac415df809ee824ef4343b1f51b6d31f35b4b9afde3829e4d1184dc150` | 1,285 |
| `rfam_families_over_1000nt.json` | `796235237ca7661d06c424e69f680c417b83068c2b7876691698db2df68cbc8c` | 928 |
| `identity.json` | `91574e3b409bf97b31cdb6f8badcb1b2107d314dc9e02a21fa9ec2634cdffecc` | 1,472 |
| `protocol.json` | `8f079fafb8d3bd81f359e1a066680934fcfef20473dafc28480ed635d73dc394` | 7,008 |
| `manifest.json` | `992b39ead2d03e2046bf4e7c0a72f9332657ad9ef80ae8f65e8c0d26944accce` | 994 |

Plus `source/` copies of the two implementation files. `rfam_families_over_1000nt.json` carries the complete set of ten Rfam families above 1,000 nt with their clans: RF02543/CL00112/3401, RF02540/CL00112/2987, RF02541/CL00112/2925, RF02462/CL00004/1858, RF01960/CL00111/1831, RF00177/CL00111/1533, RF01959/CL00111/1478, RF02542/CL00111/1311, RF01050/CL00004/1208, RF01272/CL00037/1008.

## Verification performed

- **`--verify-run`**: 9 artifacts re-hashed and matched, verdict replayed from stored counts, and confirmed that no stored requirement is satisfied and no gate amended.
- **220 focused tests passed in 1.97 s** — 27 new, plus V4's 27, V3's 36, V2's 12, V1's 27 and the fifteen V13 suites. No regression.
- All five pinned source hashes verified at config-authoring time and again inside the run.
- The v1 census's `band_records.json` re-verified against its own manifest before being used for the already-held cross-check.
- Rfam `clen` column validated against ten known family sizes at zero tolerance; family parse reported zero skipped rows out of 4,227.
- RCSB facet coverage confirmed complete: 1,472 entities in the facet against `total_count` 1,472.
- Downloads treated as untrusted: kept in their own directory, scripts held elsewhere, paths passed as arguments, every parse run under `python -I`.

**Not run and therefore unverified:** Rfam **full** alignments were not surveyed — the census says so in its own `not_surveyed` field, and only RF02462, RF01050 (CL00004) and RF01272 (CL00037) could plausibly contribute, being the sole non-baseline families above 1,000 nt. The 21 generically named PDB entities were not individually resolved to families. No inference, folding, refit, training or publication occurred, and nothing was published to GitHub this session.

## Scientific state

Unchanged. The Stage 2 gate is **open with 0 of 6 requirements satisfied**; RNAfold substitution into published STRAND is **rejected**; `strand_rnafold_calibration_v1` has **no independent validation**; **no composite score exists or is permitted**; **no sequence carries both a stability and a translation score**; the 2,000–2,999 nt band is now known to be unresolvable from Rfam seed and the PDB. No stability, translation or expression benefit is established. Published snapshot remains commit `1ca32bb3ea4eaf05c4931fa1060be64c6d1cd82d`; this session's work is **local and unpublished**.

## Pending work, prioritized

1. **Your decision on requirement 3**: retrain to free the two RF02462 records, amend the requirement by explicit gate review, or accept the band as a documented limitation. The census deliberately cannot choose, and nothing further can be learned by surveying.
2. **Awaiting your answers to the six assay questions** recorded in [V6](RNA-StableAI_HANDOFF_2026-10-19_V6.md#six-questions-the-user-is-preparing-answers-to). Items 1–2 of that list are enough to start the versioned assay-definition config, which is what unblocks RiboNN named-task selection and both floors.
3. **Optional, cheap, closes the stated gap**: scan Rfam **full** alignments for RF02462, RF01050 and RF01272. Would remove the one "not surveyed" caveat on this verdict.
4. **Optional**: resolve the 21 generically named PDB band entities to families, which would convert "unresolved leads present" into a clean verdict either way.
5. **Decide the OpenVaccine acquisition** (V6 pending item 5) — the pinned in-solution degradation source whose assay bytes were never downloaded, and the nearest route to the independent evaluation `strand_rnafold_calibration_v1` entirely lacks. Acquire and verify only; stop before any prediction.
6. **Publish V6/V7** if wanted. Not done. If done, fetch latest upstream first and preserve `diagram_10192026.svg` with its README Markdown plus the retained `diagram_10182026.png`. Publish concise summaries; note `Rfam.seed.gz` is 5.9 MB and belongs in the excluded list.
7. **Hold the gate review** once structure-validation evidence exists. Until then do not freeze parents, allowed edits, the biological objective, budgets or the cell-free assay protocol.

Do not infer expression benefit from software execution, and do not optimize actual expression candidates while the gate stays open.

## Outstanding processes

None. Downloads, parses, the census and the test suite all completed synchronously. No background job or pending approval remains. The pinned sources now live in `results/band_availability_source_runs/20261019T185511.665510Z/` rather than session scratch, so the finding is reproducible without re-downloading.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-19_V7.md
cat reports/RNA-StableAI_HANDOFF_2026-10-19_V6.md
cat configs/stage2_band_clan_availability_census_v2_2026-10-19.json

# This session's result, cheapest first; no network needed:
cat results/band_clan_availability_runs/20261019T185713.116447Z/summary.json
cat results/band_clan_availability_runs/20261019T185713.116447Z/rcsb_band_classification.json
PYTHONPATH=src:scripts .venv/bin/python scripts/audit_band_clan_availability.py \
  --verify-run results/band_clan_availability_runs/20261019T185713.116447Z

# Re-running the census re-reads the pinned sources and writes a new run directory:
PYTHONPATH=src:scripts .venv/bin/python scripts/audit_band_clan_availability.py

# Earlier local verifications, all offline:
PYTHONPATH=src:scripts .venv/bin/python scripts/audit_stage2_band_coverage.py \
  --verify-run results/stage2_band_coverage_census_runs/20261019T180243.655199Z
PYTHONPATH=src:scripts .venv/bin/python scripts/build_score_records.py \
  --verify-run results/score_record_runs/20261019T175011.658062Z
PYTHONPATH=src:scripts .venv/bin/python scripts/fit_strand_rnafold_calibration.py \
  --verify-run results/strand_rnafold_calibration_runs/20261019T174049.053308Z
PYTHONPATH=src:scripts .venv/bin/python scripts/audit_strand_rnafold_agreement.py \
  --verify-run results/strand_rnafold_agreement_runs/20261019T172402.804593Z
PYTHONPATH=src:scripts .venv/bin/python scripts/audit_stage2_under3000.py \
  --verify-run results/stage2_under3000_audit_runs/20261018T223708.786045Z/summary.json
```

Focused suite, 220 tests:

```bash
cd /home/zyliu/Documents/rna-stable-ai
PYTHONPATH=external/four_component_deps:src:scripts .venv/bin/python -m pytest -q \
  tests/test_band_availability.py tests/test_stage2_census.py tests/test_score_records.py \
  tests/test_strand_agreement.py tests/test_strand_rnafold_calibration.py \
  tests/test_component_integration.py tests/test_discrete_bo.py \
  tests/test_strand_reference.py tests/test_ribonn_integration.py tests/test_crw_panel_exposure.py \
  tests/test_crw_original_provenance.py tests/test_rcsb_long_source_survey.py tests/test_project_scope.py \
  tests/test_stage2_scope_audit.py tests/test_endpoint_ranking.py tests/test_hard_negative_supervision.py \
  tests/test_recovery_ceiling.py tests/test_endpoint_assignment.py tests/test_sampled_pair_supervision.py \
  tests/test_long_exact_sparse_pairs.py
```

All five 2026-10-19 configs then in force are frozen; do not edit any of them to change an outcome, including this census's RCSB keyword lists — the `35s rna` classification is discussed in prose above and deliberately left as the protocol scored it. Amending gate requirement 3 requires an explicit gate review and a new versioned gate file; no census, module or script may do it. Preserve all previous versioned handoffs.
