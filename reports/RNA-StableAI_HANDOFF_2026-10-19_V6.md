# RNA-StableAI handoff — 2026-10-19 V6

Project: RNA-StableAI
Date: 2026-10-19, America/Los_Angeles
Version: V6
Workspace: `/home/zyliu/Documents/rna-stable-ai`
Selected architecture: **RNAfold + STRAND + RiboNN + BoTorch**
Publication record: [V5](RNA-StableAI_HANDOFF_2026-10-19_V5.md). Scientific record: [V1](RNA-StableAI_HANDOFF_2026-10-19_V1.md) engine agreement, [V2](RNA-StableAI_HANDOFF_2026-10-19_V2.md) named calibration, [V3](RNA-StableAI_HANDOFF_2026-10-19_V3.md) score records, [V4](RNA-StableAI_HANDOFF_2026-10-19_V4.md) Stage 2 band census.
Earlier component/scope record: [V13](RNA-StableAI_HANDOFF_2026-10-18_V13.md).

## Scope of this session

Three things happened after the V5 publication, all of them corrections or clarifications rather than new pipeline work:

1. The user challenged my claim that the remaining blockers "need network", offering to run download commands in their own terminal. **The claim was wrong and is retracted here.**
2. I then checked, for the first time, whether the band-length references V4 called `blocked_on_acquisition` actually exist upstream. **They do not.** This materially strengthens V4's finding.
3. The user asked what "which assay and organism" meant, then stated that **their lab team uses a luciferase reporter assay**, and asked for the six follow-up questions to be recorded so they can prepare answers.

No inference, folding, refit, census re-run or publication occurred. No config, protocol, module, canonical run or frozen artifact was created or modified. Nothing in `results/` changed.

## Correction that supersedes V1–V5

**"Needs network" was inaccurate wording, repeated across V1–V5 and most prominently in V4 item 1 and V5's pending list.** This session has network access and used it throughout the V5 publication (`gh api`, `gh repo clone`, `curl`, `git push`). Reachability was then confirmed directly, HTTP 200 on each of:

- `https://ftp.ebi.ac.uk/pub/databases/Rfam/CURRENT/`
- `https://rfam.org/`
- `https://www.ncbi.nlm.nih.gov/`
- `https://ftp.ebi.ac.uk/pub/databases/Rfam/CURRENT/database_files/clan_membership.txt.gz`

The defect was conflating "not present on local disk" with "requires an action I cannot perform". The V4 census was correct that *local* material cannot resolve the band; the handoff prose then wrongly framed the remedy as blocked on access. **No reader should take any "needs network" line in V1–V5 at face value.** What the remaining work actually needs is recorded below.

A user terminal is genuinely required only for an interactive or credentialed login, a licensed dataset behind a click-through, or a transfer large enough to belong on the user's filesystem rather than in a session sandbox. None of those applied.

## New finding: gate requirement 3 is not reachable through Rfam

V4 classified the sparse 2,000–2,999 nt requirement as `blocked_on_acquisition`, with the blocker "acquisition of band-length references from a clan outside the selected baseline". That acquisition was never tested. It has now been tested and **it cannot succeed from Rfam**.

### Evidence

Downloaded into an isolated directory and parsed with an interpreter run as `python -I`, scripts kept outside the download directory and paths passed as arguments:

| File | SHA-256 | Bytes |
| --- | --- | --- |
| `clan_membership.txt.gz` | `2f199aaaa0a1e340145acb8fa20639427d1c0a38f4dedce29901888f222afbec` | 1,685 |
| `family.txt.gz` | `5662343d24b6f8dab566977fabebeb9df4bbec47fb8991400749fc642f03df69` | 378,804 |
| `Rfam.seed.gz` | `41f014f4ab5628620935f089b1bb77987ebc162fda7c72bff368a32c9cccabac` | 5,928,432 |

All from `https://ftp.ebi.ac.uk/pub/databases/Rfam/CURRENT/`, retrieved 2026-10-19.

**Family metadata.** 4,227 families parsed with **0 rows skipped**; 480 clan memberships across 151 clans. Consensus-length (`clen`) distribution across all families:

| consensus length | families |
| --- | --- |
| < 500 nt | 4,187 |
| 500–999 nt | 30 |
| 1,000–1,999 nt | 7 |
| **2,000–2,999 nt** | **2** |
| ≥ 3,000 nt | 1 |

The `clen` column was located by position from the end of each row, so it was validated against families whose sizes are independently known. All eight matched: tRNA RF00005 = 71, 5S RF00001 = 120, 5.8S RF00002 = 154, SSU microsporidia RF02542 = 1311, SSU archaea RF01959 = 1478, SSU bacteria RF00177 = 1533, SSU eukarya RF01960 = 1831, LSU bacteria RF02541 = 2925, LSU archaea RF02540 = 2987, LSU eukarya RF02543 = 3401.

The complete set of Rfam families over 1,000 nt consensus length, with clan:

| family | clan | clen | id |
| --- | --- | --- | --- |
| RF02543 | CL00112 | 3401 | LSU_rRNA_eukarya |
| RF02540 | CL00112 | 2987 | LSU_rRNA_archaea |
| RF02541 | CL00112 | 2925 | LSU_rRNA_bacteria |
| RF02462 | CL00004 | 1858 | Telomerase_Asco |
| RF01960 | CL00111 | 1831 | SSU_rRNA_eukarya |
| RF00177 | CL00111 | 1533 | SSU_rRNA_bacteria |
| RF01959 | CL00111 | 1478 | SSU_rRNA_archaea |
| RF02542 | CL00111 | 1311 | SSU_rRNA_microsporidia |
| RF01050 | CL00004 | 1208 | Sacc_telomerase |
| RF01272 | CL00037 | 1008 | snR86 |

Both band-length families are CL00112, the clan already represented in the frozen selection.

**Seed sequences, by individual ungapped length.** Because individual sequences can exceed their family's consensus length, every Rfam seed alignment was scanned by actual ungapped sequence length. **166** sequences fall in 2,000–2,999 nt, across 5 families:

| family | clan | band seqs | outside baseline clans? |
| --- | --- | --- | --- |
| RF02541 | CL00112 | 81 | no |
| RF02540 | CL00112 | 57 | no |
| RF01960 | CL00111 | 24 | no |
| RF02543 | CL00112 | 2 | no |
| **RF02462** | **CL00004** | **2** | **yes** |

The only two band-length seed sequences in all of Rfam outside CL00111/CL00112 are **`RF02462:CABT02000003.1/521099-523170` (2,072 nt)** and **`RF02462:AL355930.2/32605-30557` (2,049 nt)** — which are **exactly the two records the V4 census already held locally and flagged `prior_exposure_overlap`**. The local candidate pool was therefore already exhaustive for this question, and the census's `new_clan_opportunities_blocked: {"CL00004": {"family": "RF02462", "records": 2, "reasons": {"prior_exposure_overlap": 2}}}` describes not merely the local situation but the whole of Rfam seed.

### What this changes, and what it does not

V4's census artifact and its `blocked_on_acquisition` status remain **accurate and unmodified**: local material cannot resolve the band. What changes is the remedy. Acquiring more Rfam data cannot add a single new-clan band record, so requirement 3 is not an acquisition task. The remaining options are:

1. **Retrain without the RF02462 exposure**, which would make those two records usable and give clan CL00004 in-band at n = 2. Small n, and a retrain is a substantial undertaking with its own lineage accounting.
2. **Leave Rfam for experimental structures.** The repository already holds BGSU/RCSB survey machinery, and `results/rcsb_long_rna_survey_protocol_runs/20261018T222353.610817Z/exposures.json` carries 144 band-length records, 6 of them with no family assignment. Whether any lie outside CL00111/CL00112 is **unchecked** and is the obvious next census.
3. **Amend gate requirement 3 by explicit review**, for instance narrowing the clan-separation demand in a band where Rfam structurally cannot supply it. This is a gate amendment and must not be a quiet redefinition.

**Limitation, stated plainly.** Only Rfam **seed** alignments were scanned. Full alignments hold far more sequences and were not examined. Band-length sequences outside the baseline clans could only plausibly come from the three non-baseline families over 1,000 nt — RF02462 and RF01050 (both CL00004) and RF01272 (CL00037) — so this is a bounded, checkable follow-up rather than an open question.

**This finding is not yet a reproducible artifact.** It was produced by ad-hoc scans in the session scratchpad, with no versioned run directory, no protocol, no manifest and no `--verify-run` audit. The scratchpad is session-scoped and its scripts will not survive. The commands and hashes below reproduce it, and promoting it to a frozen census version is the first pending item.

## New finding: a pinned in-solution degradation source was never downloaded

While answering the assay question I found that `docs/MEASURED_DEGRADATION_SOURCE.md` already pins the **OpenVaccine** chemical-degradation dataset at author commit **`b95af835cc38bd7dc55ed6e7397d124787f86996`**, file `data/Kaggle_RYOS_data/Kaggle_RYOS_trainset.json`, with an acquisition and verification driver at `scripts/prepare_degradation_source.py` (`--acquire`, `--verify`) and a protocol config `configs/degradation_source_pilot_2026-10-13.json`.

Protocol-side artifacts exist: `results/degradation_source_runs/20261014T010830.291679Z/`, plus `results/degradation_source_protocol.json`, `degradation_source_summary.json`, `degradation_binding_summary.json`, `degradation_pilot_plan.json`, `degradation_pilot_summary.json`. **The assay bytes themselves are absent** — no `Kaggle_RYOS*` file exists anywhere in the workspace.

This matters because it is the only in-solution degradation source already scoped in the project, and in-solution half-life is precisely what `strand_rnafold_calibration_v1` predicts. V2 recorded that the calibration has **no independent evaluation of any kind**; this is the nearest available route to one. Caveats the project's own doc already states and which must be carried forward: 107/130-nt non-coding designs, per-base chemical reactivity rather than whole-molecule half-life, different conditions, and the explicit instruction that an exact assay-schema binding step must be implemented and verified **before** any predictions. It would be a transfer test, not a like-for-like validation, and it cannot help the RiboNN side at all because those sequences carry no CDS.

Nothing was downloaded, acquired or run. The pinned acquisition remains untouched pending the user's decision.

## Assay definition: what the luciferase reporter assay settles

The user stated that their lab team uses a **luciferase reporter assay**. Recorded here because the assay definition is the artifact currently blocking RiboNN task selection and both floors.

Three distinct quantities are in play across the stack and must not be conflated:

| Quantity | Predicted by | Units | Measured where |
| --- | --- | --- | --- |
| In-solution RNA half-life | STRAND, `strand_rnafold_calibration_v1` | hours | purified RNA in buffer |
| In-cell translational efficiency | RiboNN, 78 released human cell-type tasks | released TE scale, no inverse transform | inside human cells |
| **Protein output / expression** | **nothing in the stack** | **the assay's own units, e.g. RLU** | **the Stage 3 target** |

What the luciferase assay settles:

- It targets **expression**, the third row — the quantity the project actually cares about and which no component currently predicts. It places the work in the "generate your own measurements" option rather than either public-data option.
- It is **favourably comparable to STRAND's provenance**: `configs/strand_reference_reproduction_v1_2026-10-18.json` records STRAND's training cohort as 69 released **nLuc** records with 13 eGFP held out, so the user's constructs are in the same reporter family as the data the stability model was fit on. This is better comparability than endogenous transcripts would have given.

What it does **not** settle, and the consequence:

- **Luminescence measures protein, not RNA half-life.** It therefore cannot validate `strand_rnafold_calibration_v1` against that model's own target; it can only test whether the prediction *correlates with* expression. Those are different claims and must be labelled differently.
- RiboNN's tasks are endogenous human **in-cell** TE. If the assay is cell-free, V3's census finding stands and "no applicable released task" may be the honest selection outcome rather than a failure.
- Nothing predicts the assay's units, so the components would enter a future objective as **features for a calibration fitted against the lab's own measurements**, not as pre-calibrated predictors.

### Six questions the user is preparing answers to

Recorded verbatim so the prepared answers map onto them. Items 1–2 are sufficient to begin; 3–6 are required before anything is frozen.

1. **Cell-free or transfected cells?** Decides whether RiboNN is applicable at all, and whether this is the Stage 3 assay itself or a proxy for it.
2. **Is the mRNA also measured, over time** (RT-qPCR or equivalent)? If yes, one experiment yields stability *and* expression on the same constructs, which closes the joint-scoring gap with real data on sequences the lab controls and annotation the lab defines exactly. If no, the stability side has no ground truth in this assay and stays uncalibrated.
3. **Endpoint or time course**, and the lysate/system if cell-free (human, *E. coli*, wheat germ, rabbit reticulocyte).
4. **What varies between constructs** — UTRs, codon usage, both? This is the design space, and the same thing the gate requires frozen as parents and allowed edits.
5. **Replicates and dynamic range**, including typical CV. `configs/score_record_schema_v1_2026-10-19.json` already requires measurement error before any floor may be frozen, so no threshold can be set without it.
6. **Which luciferase** (nLuc, Fluc, Rluc) and the UTR scaffold. STRAND used hHBB 5′ and 3′ UTRs.

On receipt, the intended output is a **versioned assay-definition config**, which is the artifact that unblocks RiboNN named-task selection and both floors. It would **not** open the Stage 2 gate; that still requires structure-validation evidence, which is independent of the assay.

## Scientific state

Unchanged from V4 and V5. Restated so this handoff is not read as progress: the Stage 2 gate is **open with 0 of 6 requirements satisfied**; substituting RNAfold features into published STRAND is **rejected**; `strand_rnafold_calibration_v1` is a named candidate with **no independent validation**; **no composite score exists or is permitted**; **no sequence carries both a stability and a translation score**; the 2,000–2,999 nt band is unresolved and now known to be unresolvable through Rfam. No stability, translation or expression benefit is established. Published snapshot remains commit `1ca32bb3ea4eaf05c4931fa1060be64c6d1cd82d`.

## Verification performed

- Network reachability confirmed on four endpoints, HTTP 200 each.
- Three Rfam files downloaded into their own empty directory and SHA-256 recorded; parsing scripts kept outside that directory; every parse run with `python -I`; file paths passed as arguments.
- Family metadata parse reported **0 skipped rows** out of 4,227, and the `clen` column was validated against **ten** independently known family sizes, all matching.
- Seed scan derived lengths from ungapped sequence characters, concatenating interleaved Stockholm blocks per sequence name.
- The two new-clan band sequences were cross-checked by accession against the V4 census's locally recorded `prior_exposure_overlap` rows and matched exactly.
- Absence of the OpenVaccine assay bytes verified by filesystem search across the workspace.
- STRAND's nLuc/eGFP cohort composition read from the frozen reproduction config rather than recalled.

**Not run and therefore unverified:** no versioned run, manifest or `--verify-run` audit exists for the Rfam finding; Rfam **full** alignments were not scanned; the RCSB/BGSU band records were not checked for clan membership; the OpenVaccine data was not downloaded; no module, config, test or canonical run was created or changed; the focused test suite was not re-run, as no code changed.

## Pending work, prioritized

1. **Promote the Rfam finding to a frozen census artifact.** It is currently decisive but unreproducible outside this session. Should pin the three file hashes, carry the sanity-check validations, and update requirement 3's blocker text from "needs acquisition" to "not reachable through Rfam seed; remaining options are retrain, non-Rfam structures, or gate amendment". Must be a **new versioned config**; `configs/stage2_band_coverage_census_v1_2026-10-19.json` is frozen and must not be edited.
2. **Check the RCSB/BGSU band records for clan membership** — `results/rcsb_long_rna_survey_protocol_runs/20261018T222353.610817Z/exposures.json`, 144 band records, 6 without family. This is the only untested route to a new in-band clan and needs no new download.
3. **Scan Rfam full alignments for RF02462, RF01050 and RF01272** — the only non-baseline families over 1,000 nt. Bounded and cheap; would close the seed-only limitation above.
4. **Await the user's answers to the six assay questions**, then write the versioned assay-definition config. Items 1–2 of that list are sufficient to start.
5. **Decide the OpenVaccine acquisition.** If taken up, acquire and verify only, stopping before any prediction, per the project's own instruction that the assay-schema binding step be implemented and verified first.
6. **Then, and only with the assay defined**, select the RiboNN named task — accepting "none applicable" as a legitimate outcome if the assay is cell-free — and freeze the stability and translation floors in their own versioned config with measurement error in hand.
7. **Hold the gate review** once structure-validation evidence exists. Until then do not freeze parents, allowed edits, the biological objective, budgets or the cell-free assay protocol.

Do not infer expression benefit from software execution, and do not optimize actual expression candidates while the gate stays open.

## Outstanding processes

None. All downloads and scans completed synchronously. No background job or pending approval remains. The scratchpad directory holding the Rfam downloads and scan scripts is session-scoped and will not persist; the commands below reproduce the finding from scratch.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-19_V6.md
cat reports/RNA-StableAI_HANDOFF_2026-10-19_V4.md
cat docs/MEASURED_DEGRADATION_SOURCE.md
cat configs/stage2_band_coverage_census_v1_2026-10-19.json
```

Reproduce the Rfam finding. Downloads are untrusted data, so they go in their own empty directory, the scan script lives elsewhere, paths are passed as arguments and the interpreter runs isolated:

```bash
DL=$(mktemp -d); cd "$DL"
curl -sS -O https://ftp.ebi.ac.uk/pub/databases/Rfam/CURRENT/database_files/clan_membership.txt.gz
curl -sS -O https://ftp.ebi.ac.uk/pub/databases/Rfam/CURRENT/database_files/family.txt.gz
curl -sS -O https://ftp.ebi.ac.uk/pub/databases/Rfam/CURRENT/Rfam.seed.gz
sha256sum *.gz
# expect:
#   2f199aaaa0a1e340145acb8fa20639427d1c0a38f4dedce29901888f222afbec  clan_membership.txt.gz
#   5662343d24b6f8dab566977fabebeb9df4bbec47fb8991400749fc642f03df69  family.txt.gz
#   41f014f4ab5628620935f089b1bb77987ebc162fda7c72bff368a32c9cccabac  Rfam.seed.gz
# then, with a scan script kept OUTSIDE "$DL":
#   /home/zyliu/Documents/rna-stable-ai/.venv/bin/python -I <scan_script.py> "$DL"
```

Local verification of everything already published, no network:

```bash
cd /home/zyliu/Documents/rna-stable-ai
PYTHONPATH=src:scripts .venv/bin/python scripts/audit_stage2_band_coverage.py \
  --verify-run results/stage2_band_coverage_census_runs/20261019T180243.655199Z
PYTHONPATH=src:scripts .venv/bin/python scripts/build_score_records.py \
  --verify-run results/score_record_runs/20261019T175011.658062Z
PYTHONPATH=src:scripts .venv/bin/python scripts/fit_strand_rnafold_calibration.py \
  --verify-run results/strand_rnafold_calibration_runs/20261019T174049.053308Z
PYTHONPATH=src:scripts .venv/bin/python scripts/audit_strand_rnafold_agreement.py \
  --verify-run results/strand_rnafold_agreement_runs/20261019T172402.804593Z
```

OpenVaccine acquisition, **only if the user takes up pending item 5**, and stopping after verification:

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/prepare_degradation_source.py            # source-only, no download
.venv/bin/python scripts/prepare_degradation_source.py --acquire   # downloads pinned assay bytes
.venv/bin/python scripts/prepare_degradation_source.py --verify    # offline byte/ledger check
```

Focused suite, 193 tests, is listed in [V4](RNA-StableAI_HANDOFF_2026-10-19_V4.md#exact-continuation-commands); no code changed this session, so it was not re-run.

All six 2026-10-19 configs are frozen; do not edit any of them to change an outcome, including the band census whose blocker text this handoff corrects in prose only. For future publication fetch latest upstream first and preserve `diagram_10192026.svg` with its README Markdown plus the retained `diagram_10182026.png`, unless the user explicitly requests another replacement. Preserve all previous versioned handoffs.
