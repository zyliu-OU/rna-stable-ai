# RNA-StableAI handoff — 2026-10-19 V5

Project: RNA-StableAI
Date: 2026-10-19, America/Los_Angeles
Version: V5
Workspace: `/home/zyliu/Documents/rna-stable-ai`
Selected architecture: **RNAfold + STRAND + RiboNN + BoTorch**
Scientific record for the work published here: [V1](RNA-StableAI_HANDOFF_2026-10-19_V1.md) (engine agreement), [V2](RNA-StableAI_HANDOFF_2026-10-19_V2.md) (named calibration), [V3](RNA-StableAI_HANDOFF_2026-10-19_V3.md) (score records), [V4](RNA-StableAI_HANDOFF_2026-10-19_V4.md) (Stage 2 band census).
Previous publication record: [V13](RNA-StableAI_HANDOFF_2026-10-18_V13.md).

## Scope of this session

The user asked to "update to github", then mid-task added: "could you also generate a new diagram for the workflow and put it into the same location in readme on github?" Both are done and verified. The user subsequently confirmed the published diagram renders correctly on GitHub.

This handoff records the publication only. No new science, no inference, no refit, no census re-run; every number published was already measured and recorded in V1–V4.

## Decisions that supersede earlier handoffs

- **V4 item 7 ("Optional: publish … Not done") is superseded.** V1–V4's configs, modules, scripts, tests and concise evidence are published.
- **The README diagram was replaced at the user's explicit request.** That instruction authorizes the swap, exactly as the equivalent V13 instruction did. The standing preserve-the-picture rule remains in force for future unrelated changes, and now applies to `diagram_10192026.svg`.
- **The earlier picture was not deleted.** `diagram_10182026.png` remains tracked and live, and the new README caption links to it.

## Published commit

Published to **[zyliu-OU/rna-stable-ai main](https://github.com/zyliu-OU/rna-stable-ai)** at commit **[`1ca32bb3ea4eaf05c4931fa1060be64c6d1cd82d`](https://github.com/zyliu-OU/rna-stable-ai/commit/1ca32bb3ea4eaf05c4931fa1060be64c6d1cd82d)**, titled *Publish engine-agreement rejection, named RNAfold calibration, score records and Stage 2 band census*.

Base was freshly fetched upstream **`5875d93245ee13a9e9e9433bd93608f32d67d56e`** (V13's commit) and re-confirmed unchanged immediately before the commit, so no rebase, conflict resolution or force push was involved. **52 files changed, 15,407 insertions, 4 deletions, no tracked-file deletions.** The four deletions are the two replaced README lines (image reference and caption).

Commit used command-local author identity matching recent upstream: Zongyuan Liu, 74483335+zyliu-OU@users.noreply.github.com. No global identity change. Attribution trailer `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

Publication used an isolated fresh clone at `/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/854cc336-3973-4ac5-9775-bc9c0e2d5fc8/scratchpad/publish`. **The original workspace index and its placeholder `origin` (`YOUR_USERNAME/RNA-StableAI.git`) were not used for staging or publication**, and the workspace's pre-existing staged/untracked state was left untouched.

### What was published

**Code and protocols (20 files):** the four frozen configs (`strand_rnafold_agreement_criterion_v1`, `strand_rnafold_calibration_criterion_v2`, `score_record_schema_v1`, `stage2_band_coverage_census_v1`), three new modules (`strand_agreement.py`, `score_records.py`, `stage2_census.py`), five scripts (`audit_strand_rnafold_agreement.py`, `fit_strand_rnafold_calibration.py`, `fit_strand_rnafold_calibration.R`, `build_score_records.py`, `audit_stage2_band_coverage.py`), four test modules, and handoffs V1–V4.

**Concise evidence (29 files)** under `reports/stage2_and_strand_calibration_publication_2026-10-19/`, with a [MANIFEST](stage2_and_strand_calibration_publication_2026-10-19/MANIFEST.json) recording each file's original local path, SHA-256 and byte count. Every copy was asserted byte-identical to its source at staging time. Largest published file is the agreement run's `agreement.json` at 106,501 bytes, retained because the rejection decision is not auditable without its per-record deltas.

**Deliberately excluded and listed as such in the manifest:** 102 local artifacts totalling **7,186,789 bytes** — the 91 per-sequence probability-array folds, the 2,084,600-byte `per_record_features.json`, the 471,583-byte `score_records.json`, the R `.rds` fit objects and the duplicate `fit_repeat1/` outputs. Each carries the reason "bulk array or binary fit object; not required for the recorded decision". No raw datasets, model weights, checkpoints or installed environments were staged. Run `source/` copies were excluded because the same files are published at their canonical paths.

## New workflow diagram

**`diagram_10192026.svg`** at the repository root, 11,574 bytes, SHA-256 **`258d8e244e508b69f8489ac7aa56044f490a11e5fd20997e9c38b250fa5520a2`**, `viewBox="0 0 1420 830"`.

Authored by hand as SVG rather than a raster so it is diffable and scales. Two deliberate choices:

- **Explicit colors over an explicit white background rect, not `currentColor`.** The loaded `artifact-diagramming` guidance recommends `currentColor` so strokes and text follow the page theme, but that assumes *inline* SVG in an HTML document. A standalone `.svg` referenced by `![](…)` renders in isolation, so `currentColor` resolves to the SVG's own default and the drawing would become unreadable in GitHub's dark theme. The deviation is intentional and the diagram reads identically in both themes.
- **It depicts implementation state, not an aspiration.** Blue is implemented and replayed, red is rejected or blocked, grey dashed is behind the open Stage 2 gate, and a legend carries those three repeated encodings. So the rejected RNAfold-into-published-STRAND edge, the blocked composite score, the unselected RiboNN task, the missing numeric boundaries, and the gated BoTorch and cell-free boxes are all visible. V13 had warned that the previous diagram's future experimental/Pareto feedback could imply unimplemented workflows; this one states what is wired and what is not. It also carries `<title>` and `<desc>` for non-visual readers, and the README alt text repeats the claim.

README changes: the image reference and caption at lines 3–5, two updated rows in the architecture status table (STRAND now records the rejection; RiboNN records that no released task is cell-free and none is selected), one new table row for `strand_rnafold_calibration_v1`, and a new section *2026-10-19: engine agreement, a named calibration, score records and a Stage 2 census* summarising the four protocols with their outcomes and linking the handoffs and manifest.

## Verification performed

- **Pre-publication**: fetched live main and the live README before editing. Live README SHA-256 was **`19e855d8705391ecfcb18494af8fbe40fa6ad3dc24cafc6ebd7b1270c48e6770`**, byte-identical to V13's record, and the only image reference was the expected `diagram_10182026.png` at line 3. **No upstream user edits existed to merge.** The cloned checkout's README was confirmed identical to the live one.
- **193 focused tests passed in 2.09 s** inside the publication checkout, with module paths explicitly verified to resolve to the checkout's own `src/rnastable/`, not the workspace.
- **SVG structure**: well-formed XML; no `script`, `style`, `foreignObject` or `image` elements; all 60 text labels verified by computed width to fit both their containing boxes and the canvas.
- **Staging integrity**: every copied file asserted byte-identical to source; `git diff --cached --check` clean except verbatim R `sessionInfo` output; secret/PII scan clean; `/home/zyliu` present only in the four handoffs, where AGENTS.md requires the absolute workspace path.
- **Post-push, live**: main is `1ca32bb3…`; live README byte-identical to the published file, SHA-256 **`d4e6983f152e063b0c2fc301538dafc2854448e95142ea731961b6be35d84b87`**, all **53** links resolving and exactly one image reference; live `diagram_10192026.svg` byte-identical to local and served as `image/svg+xml` with HTTP 200; `diagram_10182026.png` still live at blob `56e1c7b0052279f1acb9330245d2224aab71be63`, 1,693,715 bytes, matching V13's record exactly.
- **Workspace synchronised** to the published README bytes after remote verification. The local `diagram_10182026.png` is unchanged at SHA-256 `baa831ce16df27ed44a41c2a3b481455a213b328122227b9b2a3820dda47cff1`. The original Git index was left untouched.
- **Visual rendering confirmed by the user** on GitHub. This is the one check the environment could not perform: no rasterizer (`rsvg-convert`, `inkscape`, `cairosvg`) is installed, so the diagram was verified structurally and geometrically but never rendered locally.

**Not run and therefore unverified:** no folding, refit, RiboNN inference, BoTorch run, training, census re-run or full repository suite for this publication. Preserved measured results were not re-measured. Trailing whitespace in the published `fit/R_sessionInfo.txt` is verbatim R output and was preserved rather than trimmed to satisfy the whitespace check; no captured output or license text was rewritten.

## Scientific state

Unchanged from V4 and not restated here. In brief, so a later reader is not misled by the publication itself: the Stage 2 gate is **open with 0 of 6 requirements satisfied**; substituting RNAfold features into published STRAND is **rejected**; `strand_rnafold_calibration_v1` is a named candidate with **no independent validation**; **no composite score exists or is permitted**; **no sequence carries both a stability and a translation score**; the 2,000–2,999 nt band is **blocked on acquisition**. Publishing this material establishes no stability, translation or expression benefit, and the public snapshot is a research prototype with no validated release.

## Pending work, prioritized

Unchanged from V4, with its item 7 now complete. The two acquisitions remain the only things that unblock the rest, and both need network plus a versioned acquisition protocol with lineage screening:

1. **Band-length (2,000–2,999 nt) structure references from a clan outside CL00111 and CL00112**, for gate requirement 3.
2. **Transcripts carrying both a measured stability readout and numeric coding annotation**, which simultaneously unblocks the joint objective, the remaining half of V13 item 2, and the independent evaluation of `strand_rnafold_calibration_v1`.
3. Decide the RF02462 question: acquire unexposed CL00004 band references, or retrain without the exposed records.
4. Obtain experimental native structure controls in the band, or formally narrow gate requirement 4 to computational references by explicit review rather than quiet redefinition.
5. Define the intended assay before any RiboNN task or floor selection.
6. Hold the gate review once 1–5 produce evidence. Until then do not freeze parents, allowed edits, the biological objective, budgets or the cell-free assay protocol.

Do not infer expression benefit from software execution, and do not optimize actual expression candidates while the gate stays open.

## Outstanding processes

None. The clone, tests, commit, push and remote verification all completed. No background job or pending approval remains. The publication checkout at `/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/854cc336-3973-4ac5-9775-bc9c0e2d5fc8/scratchpad/publish` is clean at `1ca32bb` and is session-scoped scratch; it may be discarded, since the published commit is the canonical record. Other system processes were not exhaustively audited.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-19_V5.md
cat reports/RNA-StableAI_HANDOFF_2026-10-19_V4.md

# Read-only live publication verification; network required:
gh api repos/zyliu-OU/rna-stable-ai/commits/main --jq .sha
gh api repos/zyliu-OU/rna-stable-ai/contents/README.md --jq .content | base64 -d | sha256sum
gh api repos/zyliu-OU/rna-stable-ai/contents/diagram_10192026.svg --jq .content | base64 -d | sha256sum

# Local verification of everything published, cheapest first; no network:
PYTHONPATH=src:scripts .venv/bin/python scripts/audit_strand_rnafold_agreement.py \
  --verify-run results/strand_rnafold_agreement_runs/20261019T172402.804593Z
PYTHONPATH=src:scripts .venv/bin/python scripts/fit_strand_rnafold_calibration.py \
  --verify-run results/strand_rnafold_calibration_runs/20261019T174049.053308Z
PYTHONPATH=src:scripts .venv/bin/python scripts/build_score_records.py \
  --verify-run results/score_record_runs/20261019T175011.658062Z
PYTHONPATH=src:scripts .venv/bin/python scripts/audit_stage2_band_coverage.py \
  --verify-run results/stage2_band_coverage_census_runs/20261019T180243.655199Z
```

Focused suite, 193 tests, is listed in [V4](RNA-StableAI_HANDOFF_2026-10-19_V4.md#exact-continuation-commands).

For future publication: fetch latest upstream first, merge any user edits into the snapshot, and **preserve `diagram_10192026.svg` and its README Markdown plus the retained `diagram_10182026.png`** unless the user explicitly requests another replacement. Publish concise summaries rather than bulk arrays. All four 2026-10-19 configs are frozen; do not edit any of them to change an outcome. Preserve all previous versioned handoffs.
