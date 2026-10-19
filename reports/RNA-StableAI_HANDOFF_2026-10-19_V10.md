# RNA-StableAI handoff — 2026-10-19 V10

Project: RNA-StableAI
Date: 2026-10-19, America/Los_Angeles
Version: V10
Workspace: `/home/zyliu/Documents/rna-stable-ai`
Selected architecture: **RNAfold + STRAND + RiboNN + BoTorch**
Immediately previous handoff: [V9](RNA-StableAI_HANDOFF_2026-10-19_V9.md), assay definition v2 and the power analysis. Assay v1 and the Stage 3 conflict: [V8](RNA-StableAI_HANDOFF_2026-10-19_V8.md). Band availability: [V7](RNA-StableAI_HANDOFF_2026-10-19_V7.md). Publication: [V5](RNA-StableAI_HANDOFF_2026-10-19_V5.md).

## Scope of this session

The user approved V9 pending item 7: retrieve upstream RiboNN per-task accuracy and training-overlap evidence, which V8 and V9 recorded as two of the four remaining blockers against RiboNN task selection.

**Both blockers are cleared.** Per-task accuracy was not published as a metrics table anywhere, so it was *derived* from the released measured and predicted supplementary tables. Delivered: a frozen config, a new module, a driver with `--verify-run`, 15 tests, and a canonical run. **235 focused tests pass.** No task selected, no floor frozen, no gate amended, no inference run, no publication.

## Where the evidence actually was

Neither the pinned RiboNN source nor the Zenodo weights record carries per-task metrics:

- The **11 pinned source files** are code, config, licences and one example input. The upstream repo at the pinned commit holds 20 blobs and no metrics file.
- **Zenodo record 17258709** holds exactly two files, `RiboNN-1.0.0.zip` and the `weights.zip` already retained and hash-verified.
- The weight archive's `runs.csv` carries 90 human runs with **aggregate** metrics only — `metrics.test_r2`, `metrics.test_pearson` and so on, pooled over tasks per run. All 113 columns were listed; none is per-task.

The upstream README states the models "were trained on data in the Supplementary Tables published in the RiboNN paper", which is [Nature Biotechnology 2025](https://www.nature.com/articles/s41587-025-02712-x). The article text is paywalled, but its six supplementary files are served openly, and two of them turn out to contain everything needed:

| File | Contents |
| --- | --- |
| `MOESM3.xlsx`, sheet `Human` | 10,348 transcripts with `SYMBOL`, `gene_id`, `tx_id`, sizes, `tx_sequence`, `fold`, and **78 `TE_<cell type>` measurement columns** |
| `MOESM5.xlsx`, sheet `Multi-task (Human)` | the same transcripts with **78 `predicted_TE_<cell type>` columns** |
| `MOESM2.pdf` | Reporting Summary: APPRIS v2 gene models, 3,819 profiling datasets filtered to 1,282 human samples, 10-fold CV with genes randomly allocated to folds |

Pairing measurements against predictions on `tx_id` yields per-task accuracy directly. **This is a recomputation of released data, not an independent evaluation of RiboNN.**

## Blocker 3 cleared: per-task accuracy

78 tasks evaluated, pairing 10,348 measured against 10,037 predicted transcripts; 311 transcripts carry no prediction, consistent with the documented input limits of 5′ UTR ≤ 1,381 nt and CDS+3′ UTR ≤ 11,937 nt.

Across tasks: Pearson **min 0.3623, median 0.6878, max 0.8207, mean 0.6661**; R² min 0.1203, median 0.4642, max 0.6502, mean 0.4454.

The tasks that matter for the stated assay:

| Task | n | Pearson | R² | rank of 78 | above median |
| --- | --- | --- | --- | --- | --- |
| **A549** | 9,776 | **0.7092** | 0.5013 | 23 | yes |
| **Molt-3** (T-cell line) | 8,514 | **0.7021** | 0.4894 | 29 | yes |
| Primary CD4+ T-cells | 8,149 | 0.6688 | 0.4455 | 47 | no |
| **HSB2** (T-cell line) | 8,076 | **0.5866** | 0.3403 | 66 | no |
| HEK293T (the demo column) | 9,937 | 0.7179 | 0.5136 | 22 | yes |

**This is directly actionable for the T-cell choice.** If the lab's T-cell is a line, **Molt-3 is much better supported than HSB2** — Pearson 0.70 versus 0.59, rank 29 versus 66 of 78. Primary CD4+ T-cells sit between them at 0.67. A549 is comfortably above median. So of the cell types in play, the A549 arm rests on stronger released accuracy than any T-cell option, and the specific T-cell chosen changes the evidential footing materially.

### The held-out assumption, and why it is not just asserted

These figures are only meaningful if `MOESM5` holds **out-of-fold** predictions. The table carries a `fold` column and the Reporting Summary states models were blinded to unseen data in each held-out CV fold, which is consistent — but the methods text is paywalled and was not read, so this is **assumed, not confirmed**.

The config therefore requires a consistency check rather than taking the assumption on trust: in-sample predictions would score *above* the authors' own reported test metrics. The run computes it:

- authors' pooled `test_pearson` mean over 90 runs: **0.7113**
- derived per-task Pearson mean: **0.6661**
- derived at or below authors': **true** → verdict **"consistent with out-of-fold predictions"**

The config also fixes the failure mode in advance: if a derived mean ever *exceeds* the authors' pooled metrics, the figures must be **discarded rather than adjusted**.

## Blocker 4 cleared: training overlap

The training table is 10,348 endogenous human transcripts under APPRIS v2 annotation, with 10,345 distinct standard gene symbols (SAMD11, KLHL17, HES4, ISG15, AGRN…). Screening those symbols for reporter names returns only human genes:

| Needle | Matches |
| --- | --- |
| `luc` | DGLUCY, LUC7L, LUC7L2, LUC7L3 — human splicing factors |
| `luciferase` | none |
| `GFP` | GFPT1, GFPT2 — glutamine-fructose-6-phosphate transaminases |
| `nanoluc`, `renilla` | none |

**No reporter construct of any kind is in the training set**, which is expected for an endogenous APPRIS-derived table. So overlap between the lab's Fluc construct and RiboNN's training data is nil.

**That same fact cuts both ways and must not be conflated.** Zero overlap removes the leakage concern and simultaneously confirms that a designed, codon-optimized firefly luciferase reporter is **out of distribution** for a model trained exclusively on endogenous human mRNA. The config states both as separate findings.

## Two blockers remain, and one is newly sharpened

Of the four blockers V8/V9 recorded against task selection:

1. Intended assay undefined — **resolved in V8**.
2. No released task is cell-free — **moot since V8**; the assay is in transfected cells.
3. No per-task accuracy evidence — **cleared here**.
4. Per-task training overlap unknown — **cleared here**.

Still outstanding, both now better defined:

- **The T-cell type is still unpinned** (the user is checking). The evidence above makes this choice consequential rather than cosmetic.
- **Out-of-distribution applicability.** This is no longer a suspicion; it is established that the training set contains only endogenous human transcripts and no reporter. A task may still be selected, but the applicability argument now has to address a documented distribution gap, not a hypothetical one.

**No task was selected.** Name matching remains insufficient, and the config forbids a selection by this audit.

## Completed work

### Frozen protocol

**`configs/ribonn_task_evidence_v1_2026-10-19.json`** — SHA-256 **`775d55dd80d9d5cad72cfe7a4936fe5a13c0c4eca83b77220586f5426be609bb`**. All of `task_selected`, `floors_frozen`, `gate_amended`, `new_sequence_scoring_enabled`, `expression_candidate_design_enabled`, `stage3_ready` are false.

It pins each supplementary source by URL, byte count and SHA-256; fixes the pairing method, metric definitions and `minimum_n`; records the held-out assumption with its basis, its non-confirmation, the required consistency check and the discard-don't-adjust failure rule; records the overlap screen's limits; and carries four interpretation rules and four no-claim statements.

**Deliberate decision on the sources.** The supplementary files total about 96 MB of copyrighted third-party material. They are **pinned by hash and URL but not copied into this repository**, so nothing redistributes them and the repository does not carry their bulk. Re-deriving requires re-fetching them and passing `--sources-dir`. The config records this policy explicitly, and `identity.json` records `sources_retained_in_repo: false`.

| Supplementary file | SHA-256 | Bytes |
| --- | --- | --- |
| `MOESM2_ESM.pdf` | `ea1ba32c1e17a00d630067baf433b6f5d57847422d70a73cfbb8fd174bc6b671` | 1,636,988 |
| `MOESM3_ESM.xlsx` | `5a9dd751cb8ac96dbe364e249561cb54d4912c4170e7d659b9d465bd008e4c47` | 23,027,441 |
| `MOESM4_ESM.xlsx` (mouse, unused) | `0c92358bfabfe748d1e081fdcb6da69f43fa0ff1c841fa431d8576335c1de921` | 22,934,390 |
| `MOESM5_ESM.xlsx` | `4f94777b0f7a4a9502d1fe97fac012a08fe7510f39d58f8f350ca852f133f459` | 26,192,312 |
| `MOESM6_ESM.xlsx` (mouse, unused) | `b3e8dbe5b13d8804ceceb1249ffcd7304e98d3ba11efb0aed9f81d8918f7d663` | 22,938,401 |

### Implementation

- **`src/rnastable/ribonn_task_evidence.py`** (new). `read_sheet_columns` streams one worksheet with `iterparse`, keeping only requested columns, so the 23 MB tables never have to be held in memory with their transcript sequences. `agreement` returns n, Pearson, Pearson squared **and** the coefficient of determination, which differ when predictions carry bias or scale error. `per_task_metrics`, `rank_tasks`, `overlap_check` complete the set. Raises on degenerate or mismatched series, a missing key column, an unknown sheet, an invalid minimum, and when no task can be evaluated.
- **`scripts/audit_ribonn_task_evidence.py`** (new). Verifies each pinned source's byte count and hash, refuses to run with any mutation flag set, requires `--sources-dir` with a message naming the URLs, derives the metrics, computes the held-out consistency check against the retained `runs.csv`, and writes the run. `--verify-run` re-checks artifact hashes, replays the task ranking from stored metrics and **fails if a stored run claims a task selection or gate amendment**.
- **`tests/test_ribonn_task_evidence.py`** (new, 15 tests). Config gates and the no-selection claim; the non-retention policy and well-formed hashes; the held-out assumption carrying its failure mode; exact agreement on a perfect fit; **Pearson squared staying 1.0 while R² goes negative under a pure scale error**, which is why both are reported; rejection of degenerate, short and mismatched series; task pairing restricted to tasks present in both tables; `minimum_n` enforcement; blank and non-numeric cells skipped; ranking and median placement including an absent task; the overlap screen; and a hand-built minimal workbook proving the streaming reader keeps selected columns, **skips `tx_sequence`**, and rejects a missing key column or unknown sheet.

### Canonical run

**`results/ribonn_task_evidence_runs/20261019T202103.166652Z/`** — 8 files, 41,904 bytes, `manifest.json` lists **7** artifacts.

| Artifact | SHA-256 | Bytes |
| --- | --- | --- |
| `summary.json` | `2811b36cd1d4d36c46cced31bb2b0cc052f0f5b0c97192f3cc08324c93dc8488` | 5,155 |
| `per_task_metrics.json` | `788fcd6bac4351ee1b9b8b15035d2b0e433d69e0560c4bb2747780c00b7843ce` | 12,166 |
| `training_overlap.json` | `f7066006b144a5f2b5461d51fc82a29230a27f4f2724b5545484c4eab3f30b21` | 455 |
| `identity.json` | `d20521176ffbefd1a2a4d57468d4f00cc2d1f03d8b329706f8bfa75e7dd5305f` | 1,243 |
| `protocol.json` | `9841bf67eedc89eecd4d817d8b62c7617873d68b0e2b7978e0119c071920d15d` | 6,321 |
| `manifest.json` | `dbef5ec7e72ba724cb52b5bd801d4da3b5186ee7648da1a20c04a18fcd14a64f` | 760 |

Plus `source/` copies of the two implementation files. `per_task_metrics.json` carries all 78 tasks.

## Verification performed

- **`--verify-run`**: 7 artifacts re-hashed and matched, task ranking replayed from stored metrics, and confirmed no stored task selection or gate amendment.
- **235 focused tests passed in 1.97 s** — 15 new, plus V7's 27, V4's 27, V3's 36, V2's 12, V1's 27 and the fifteen V13 suites. No regression.
- Both consumed supplementary files verified by byte count **and** SHA-256 before parsing.
- The held-out assumption checked against the authors' own pooled test metrics from the retained weight archive, not assumed.
- Absence of per-task metrics confirmed by listing all 113 `runs.csv` columns, the 20 blobs in the upstream repo tree at the pinned commit, and the two files in the Zenodo record.
- Downloads treated as untrusted: own empty directory, parsing scripts held elsewhere, paths passed as arguments, every parse run under `python -I`.

**Not run and therefore unverified:** the paper's methods text was not read, so the out-of-fold nature of the prediction table remains assumed with a consistency check rather than confirmed; `MOESM1` supplementary figures and the two mouse tables were not retrieved or used; no RiboNN inference was run; no sequence was scored, because the UTR scaffold is still missing; no inference, refit, census or publication occurred.

## Scientific state

Unchanged. Stage 2 gate **open, 0 of 6 requirements satisfied**; RNAfold substitution into published STRAND **rejected**; `strand_rnafold_calibration_v1` has **no independent validation**; **no composite score permitted**; **no sequence carries both a stability and a translation score**; the 2,000–2,999 nt band unresolvable from Rfam seed and the PDB; the **Stage 3 target conflict is unresolved**. No stability, translation or expression benefit established. Published snapshot remains `1ca32bb3ea4eaf05c4931fa1060be64c6d1cd82d`; V6–V10 are **local and unpublished**.

## Pending work, prioritized

1. **Decide the Stage 3 target conflict** — gate, README, V13 and `diagram_10192026.svg` all say cell-free; the lab does transfected cells. Still the most consequential open item.
2. **Pin the T-cell type.** Now consequential: Molt-3 carries Pearson 0.70 against HSB2's 0.59, and primary CD4+ sits at 0.67.
3. **Answer whether ORF edits must be synonymous**, which determines whether luminescence isolates mRNA-level effects at all.
4. **Supply the UTR scaffold and Ping's authoritative sequence.** Nothing can be scored until then.
5. **Supply the measured assay CV**, the last input any floor needs; V9 showed n=3 detects 1.5-fold only if CV is at or below about 14 %.
6. **Then select the RiboNN task** in its own versioned config, citing the per-task evidence here plus an explicit argument for applying an endogenous-transcript model to a designed reporter.
7. **Decide band requirement 3** from V7, and **the OpenVaccine acquisition** from V6 — the latter still the only route to evaluating the calibration against its own target.
8. **Publish V6–V10** if wanted. The supplementary files must stay unretained and unpublished; publish the derived metrics and hashes only.

Do not infer expression benefit from software execution, and do not optimize actual expression candidates while the gate stays open.

## Outstanding processes

None. Downloads, parses, the audit and the test suite all completed synchronously. No background job or pending approval remains. The supplementary files live only in session scratch and are not retained; the config's URLs and hashes allow exact re-fetching.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-19_V10.md
cat configs/ribonn_task_evidence_v1_2026-10-19.json

# This session's result, offline:
cat results/ribonn_task_evidence_runs/20261019T202103.166652Z/summary.json
cat results/ribonn_task_evidence_runs/20261019T202103.166652Z/training_overlap.json
PYTHONPATH=src:scripts .venv/bin/python scripts/audit_ribonn_task_evidence.py \
  --verify-run results/ribonn_task_evidence_runs/20261019T202103.166652Z

# Re-deriving requires re-fetching the pinned supplementary files, which are NOT in this repo:
DL=$(mktemp -d)
BASE='https://static-content.springer.com/esm/art%3A10.1038%2Fs41587-025-02712-x/MediaObjects'
curl -sS -A 'Mozilla/5.0' -o "$DL/MOESM3.xlsx" "$BASE/41587_2025_2712_MOESM3_ESM.xlsx"
curl -sS -A 'Mozilla/5.0' -o "$DL/MOESM5.xlsx" "$BASE/41587_2025_2712_MOESM5_ESM.xlsx"
curl -sS -A 'Mozilla/5.0' -o "$DL/MOESM2.pdf"  "$BASE/41587_2025_2712_MOESM2_ESM.pdf"
sha256sum "$DL"/*
PYTHONPATH=src:scripts .venv/bin/python scripts/audit_ribonn_task_evidence.py --sources-dir "$DL"

# Other local verifications, offline:
PYTHONPATH=src:scripts .venv/bin/python scripts/audit_band_clan_availability.py \
  --verify-run results/band_clan_availability_runs/20261019T185713.116447Z
PYTHONPATH=src:scripts .venv/bin/python scripts/build_score_records.py \
  --verify-run results/score_record_runs/20261019T175011.658062Z
PYTHONPATH=src:scripts .venv/bin/python scripts/run_ribonn_fixed_inference.py \
  --verify-run results/ribonn_fixed_inference_runs/20261019T045101.117038Z
```

Focused suite, 235 tests: add `tests/test_ribonn_task_evidence.py` to the list in [V7](RNA-StableAI_HANDOFF_2026-10-19_V7.md#exact-continuation-commands).

All eight 2026-10-19 configs are frozen; do not edit any to change an outcome. Selecting a RiboNN task requires its own versioned config citing this evidence plus an applicability argument; this audit may not do it. Amending the Stage 3 target requires an explicit gate review and a new versioned gate file. The supplementary files are copyrighted third-party material: keep them unretained and unpublished, and cite them by URL and hash. Preserve all previous versioned handoffs.
