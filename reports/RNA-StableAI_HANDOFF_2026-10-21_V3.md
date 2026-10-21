# RNA-StableAI — Handoff 2026-10-21 V3

- **Project:** RNA-StableAI
- **Date:** 2026-10-21 (America/Los_Angeles; run timestamps are UTC)
- **Version:** V3 — supersedes V1 and V2 of this date **on the measured-protein-output label
  count only** (6 → 24). V1 and V2 remain and are not edited.
- **Absolute workspace path:** `/home/zyliu/Documents/rna-stable-ai`
- **Remote:** `https://github.com/zyliu-OU/rna-stable-ai.git` — **PUBLIC**
- **Publication clone:** `/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad/pub2`
- **Project interpreter:** `.venv/bin/python` (3.12). Bare `python3` is anaconda 3.14 without
  biopython and must not be used.

---

## 1. What this stretch was

The user's instruction:

> "yes, we dont care about old record since it was based on retired model. for new work flow,
> if we need to rebuild code and test for cell expression prediction, then yes, we need to do
> it"

Read as two authorisations: regenerate the stale workflow diagram without preserving its old
content, and build the code and tests for the expression axis. Both were done. **The expression
axis is now measured for the first time in this project**, rather than inferred from stability.

**Headline: the measurement falsified the premise it was built to test.** In-cell mRNA
stability does not order protein output on a synonymous panel. The prespecified threshold was
+0.30; the measured value is **−0.0330**.

---

## 2. The correction that forced this work

V1, V2, gate v16 and assay_definition_v4 all state that **6** constructs carry measured
protein output, and conclude "expression is not currently trainable on this data."

**The count is wrong. It is 24.** Six was the pseudouridine *paired* subset used for the
modification check. `Supplementary Data 6 - Attributes for 24 CDS designs` carries 24 designs
with `Nluc_Fluc_6h_mean` and `Nluc_Fluc_24h_mean`, standard deviations for both, and matched
`half_life`; `Supplementary Data 5` carries replicate counts (**n=4** at both time points) and
the paper's own p-values for the same 24.

**Root cause:** V1 and V2 took the label count from a README sentence about the pseudouridine
experiment instead of inventorying the archive. The archive had been in hand since 2026-10-20
and was never surveyed beyond `Supplementary Data 1`.

**Does the "not trainable" conclusion survive?** In substance yes, for a better reason: gate
v15 measured that 105 training records support about one feature, so 24 supports none. What
changes is that the axis can be **measured and characterised**, which is what was done. The
13-fold sign-change evidence about the 6 paired constructs is a different measurement and
stands unaltered.

Corrected by **supersession, not editing**: gate v17 and assay_definition_v5. v16 and v4 remain
frozen and unedited, with their hashes recorded in their successors.

---

## 3. The construct set, and why it is the cleanest this project has used

| property | value |
|---|---|
| constructs | **24** |
| length with UTRs | **883 nt, constant across all 24** |
| CDS | **621 nt**, at a constant offset of `[53:674]` |
| 5′UTR / 3′UTR | **53 nt / 209 nt, identical across all 24** |
| protein | **one 207 aa protein**, every CDS starting AUG, ending in a stop, no internal stop |
| categories | Eterna 8, Ribotree 8, Commercial 3, GC-rich 2, LinearDesign 1, Control 1, Neg. Control 1 |
| overlap with Supplementary Data 1 | **zero of 24 Sequence IDs** |
| measured expression spread | **4.237-fold** between lowest and highest 24 h construct |

Three consequences, each load-bearing:

1. **Length is constant, so no correlation on this set can be a length artifact.** Both of this
   project's known length artifacts are structurally impossible here — the SUP region-fraction
   error that gate v15 had to correct, and `cds_length` as a ruler among the in-cell screen's
   held-out performers. Neither the 122-construct two-axis set nor the 203-record screen could
   make that claim.
2. **The set is unexposed.** The frozen calibration, the two-axis set and the in-cell screen all
   come from Data 1. Nothing fitted or screened in this project has seen these 24.
3. **It is a pure synonymous panel** — exactly the declared design domain, which the project's
   own 512-member pool also occupies.

---

## 4. Artifacts created

### 4.1 `configs/expression_axis_v1_2026-10-21.json`

sha256 **`ece508fffb9df036705eded5d8710206261be1c6e1c268313b99c6c1228a8701`**, declared and
hashed **before any relationship was computed**. Only inventory preceded it: row counts, column
names, sequence lengths, UTR constancy, protein identity, label ranges, GC range and the source
defect in §4.4. No predictor-against-label relationship was computed before the hash.

It declares: one confirmatory test with its direction (+), its threshold (+0.30), its
falsification criteria, **and both the success and failure texts**; five exploratory
measurements each with a declared direction; the measurement-error analysis; the data-integrity
rule; and six prohibitions for the run, including *do not revise this protocol after seeing a
number*.

It declares three limits **up front**: no fit and no split at n=24; UTR features untestable
because the UTRs are constant; and one confirmatory test against five exploratory families, so
only the primary counts.

### 4.2 `scripts/run_expression_axis.py`

Reads Data 6 and Data 5 from the zip with the **standard library only**, matching
`run_two_axis_comparison.read_table` — third-party data parsed, never executed, no spreadsheet
package introduced. Reuses `fold_one`, `CALIBRATION` and `spearman` from the two-axis script.
Enforces the archive sha256 before reading, enforces the 883/53/621/209 layout and a clean ORF
per construct, and refuses to run if the source layout changed.

### 4.3 `tests/test_expression_axis.py` — 19 tests

Pins the protocol hash used by the run; that nothing was fitted and no split was made; the
permutation detection including both cycles; that a protein check cannot catch it; length and
UTR constancy; the falsification and its recorded reasons; the family sign reversal; that the
calibration result keeps its sign-reversal caveat; that the CDS-structure signal held its
declared direction; the measured CV replacing the planning bound; that no floor is frozen; and
that gate v17 corrects v16's count without editing it and carries the run's actual numbers.

### 4.4 The source defect, found and enforced against

**The `Sequence` column in Data 6 is exactly permuted against `sequence_with_UTRs` for 5 of the
24 rows** — 0 mismatching nucleotides after the swap:

- **2-cycle:** `1220187B1` Twist_1 ↔ `1220188B1` Genewiz_1
- **3-cycle:** `1220184B1` LinearDesign → `1220185B1` GC_rich_24x_2 → `1220186B1`
  GC_rich_24x_1 → back

**Why it is dangerous:** every design is a synonymous variant of one protein, so all five
permuted rows still translate to exactly the right protein — **0 amino-acid differences**. A
protein-identity check, which this project runs on every variant, passes on every bad row. It
hits precisely the designed-comparison categories: the only LinearDesign design, both GC-rich
designs, and 2 of 3 Commercial designs. Had features been taken from the `Sequence` column,
21% of the set would carry another construct's features against its own measurements.

**Rule now enforced in code:** features come from `sequence_with_UTRs` only, CDS at
`[53:674]`; the `Sequence` column is never used, including for the 19 rows where it agrees. The
permutation is re-detected at read time and written to `integrity.json`.

**This is the second defect found in this source by reading a column other than as labelled.**
The first produced the published +0.4190 figure that gate v15 had to correct.

### 4.5 Gate v17 and assay_definition_v5

`configs/stage2_to_stage3_gate_v17_2026-10-21.json` supersedes v16 (sha256
`f93bd803a537ecb3e3813c8bffd58d90a77657cfae6f429254abc73c7d72968b`). It corrects the label
count; records the measurement; **strengthens two prohibitions** (v16_5 is now a direct
measurement on 24 rather than an inference from 6; v16_1's family-dependent sign is now
observed a second time in a different pair of quantities); **adds one** —
`v17_1_no_single_axis_may_stand_in_for_expression`; **withdraws none**; keeps
`requirements_satisfied` at 6 and `requirements_before_stage3` byte-identical; moves no switch.

`configs/assay_definition_v5_2026-10-21.json` supersedes v4 (sha256
`16f2990b554d263c266de237e5289cd14762a00f4dfaf2f961bea9c3b0f993fa`), corrects the count, and
records the measured assay error. Target set and every assay parameter are unchanged from v4.
**v1–v4 remain frozen, and code and tests still pin v3 by name; no value they read moved.**

---

## 5. Results

Run: **`results/expression_axis_runs/20261021T164736.813440Z`**

### 5.1 Primary confirmatory test — FALSIFIED

| | declared | measured |
|---|---|---|
| in-cell half-life vs **24 h** protein output | **≥ +0.30, positive** | **−0.0330** |
| in-cell half-life vs **6 h** protein output | positive | **−0.3070** |
| Eterna family, n=8 | — | **−0.5714** |
| Ribotree family, n=8 | — | **+0.5476** |

Two of the three declared falsification criteria fired: the threshold, and the sign reversing
across design families with ≥4 members.

**Interpretation.** On a synonymous panel with length and UTRs held constant, in-cell mRNA
stability does not order protein output, and it fails in the *same way* measured ribosome load
failed against stability: a **family-dependent sign**. Gate v16 prohibited treating stability
as a validated expression proxy on 6 paired constructs; that prohibition is now a direct
measurement on 24. **Family-dependent sign reversal is a recurring property of this biology,
observed twice now in different pairs of quantities, not a one-off.**

### 5.2 Exploratory — nothing adopted, n=24, declared non-confirmatory

| predictor | declared | vs half-life | vs 24 h expression |
|---|---|---|---|
| **frozen calibration, predicted hours** | positive | **+0.5904** | +0.3922 |
| transcript GC (= CDS GC here) | positive | +0.1437 | +0.2473 |
| `cds_energy_per_nt` | negative | −0.5765 | −0.3513 |
| `cds_aup` | negative | −0.5330 | −0.2470 |
| AUP, whole molecule | negative | −0.5922 | −0.3887 |
| energy per nt, whole molecule | negative | −0.5374 | −0.3765 |

1. **+0.5904 is the frozen calibration's strongest correlation anywhere in this project**, on a
   set it never saw, with only **1 of 24** constructs outside its training range, and it is the
   **first time a fitted arm here has beaten a free GC column** (+0.1437). Exploratory, n=24,
   still not independently validated. **It must not be called an expression predictor:** its
   expression correlation **reverses sign across time points**, −0.1209 at 6 h against +0.3922
   at 24 h — one of the criteria the primary test declared as falsifying.
2. **The in-cell screen's CDS-structure signal replicates** on an unexposed panel where it
   cannot be a length ruler (screen: −0.3864 held out; here −0.5765 vs half-life). And
   structure tracks expression (−0.35 to −0.39) more strongly than *measured* stability does
   (−0.03), which argues **stability is not the mediator** between structure and protein output.
3. Transcript GC and CDS GC give **identical** Spearman values by construction: the UTRs are
   constant, so transcript GC is a monotonic affine function of CDS GC. Not a bug.
4. **`utr5_frac_C`, the screen's best feature at +0.3857, could not be tested.** The UTRs are
   constant, so UTR features have zero variance here. This panel is blind to UTR composition
   exactly as the screen's first split was, roles reversed. It is neither supported nor refuted.

### 5.3 First measured assay error in this project

| | 6 h | 24 h |
|---|---|---|
| median CV, n=4 | **0.0616** | **0.0740** |
| CV range | 0.0174 – 0.1308 (24 h) | |
| minimum detectable fold-change | 1.126× | 1.152× |
| resolvable pairs of 276 | 210 | **232** |
| unresolvable pairs | 66 | **44** |

assay_definition_v3/v4 record 20% CV as a **planning bound** and name the missing measured
error as a blocker on floor selection. At that bound the design was **underpowered for its own
1.5× target**, needing 1.75× at n=3. At the measured CV with n=4 the 1.5× target **is**
detectable.

The panel's measured protein output spans **4.237-fold** with 232 of 276 pairs resolvable —
against the **1.0617×** predicted stability spread that left the design workflow's own
512-member pool entirely unresolved. **The design space is not in the noise floor; the
objective was.**

**No floor is frozen.** This is the paper's reporter and assay, not the user's lab. It bounds
what that reporter achieved; it does not predict the lab's CV. `floors_frozen` stays `false`.

---

## 6. The diagram, regenerated

`workflow_10202026.svg`, 13,095 → 13,849 bytes. Edited surgically rather than rewritten, since
it is hand-authored with no generator script.

Changed: canvas height 812 → 828 for a third caption line; title and `<desc>` accessibility
text; the terminal box from "Transfected-cell assay, unreached" to "Expression assay, unreached
— two arms" naming the reinstated cell-free arm as declared-not-defined-not-scoreable, with
"no measurement of any construct exists on either arm" retained as a fourth line (its rect grew
62 → 76 px); the gate annotation from "Gate v6, 2026-10-20" to "Gate v17, 2026-10-21" recording
that the goal is expression and stability is the modeled axis only; the assay-blocker line from
"measured CVs for both readouts" to "the lab's own CVs (paper reporter: 7.4%)"; and the caption
now carries the headline measurement. The README alt text and italic caption were updated to
match.

**Verification and its limit.** The SVG parses as well-formed XML; max text y is 812 inside a
828 canvas. A width audit against the innermost containing box for every centred text element
reports **0 overflowing lines**, with the new lines at +21.9 px margin or better against
pre-existing lines as tight as +5.4 px. **This caught a real error:** two first-draft lines
were ~75 characters in a 372 px box where existing lines top out at ~64, and were shortened.
**No renderer was available** (`rsvg-convert`, `cairosvg`, ImageMagick, Chromium all absent),
so the diagram was **not visually inspected**. The geometric checks are what was run.

`diagram_10182026.png`, the picture the user added, is **byte-unchanged** at sha256
`baa831ce16df27ed44a41c2a3b481455a213b328122227b9b2a3820dda47cff1` and still referenced.

---

## 7. Verification actually run

| Check | Command | Outcome |
|---|---|---|
| Expression-axis tests | `pytest -q tests/test_expression_axis.py` | **19 passed** |
| Full suite | `.venv/bin/python -m pytest -q` | **1,185 passed** (1,166 + 19), 1 known Ninja/BoTorch warning, 13.51 s |
| Archive hash | enforced in the script before any read | `849ed7b4…11c2`, matched |
| Protocol hash | recorded in the run artifact, pinned by a test | `ece508ff…8701` |
| Folding | 24 full transcripts + 24 CDS regions | 48/48 succeeded, 0 failures |
| Source layout | 883 nt, UTRs 53/209, ORF per construct | enforced, all 24 passed |
| Permutation | re-detected at read time | 5 of 24, both cycles resolved exactly |
| SVG | XML parse + per-box width audit | well-formed, 0 overflow |
| Picture hash | `sha256sum diagram_10182026.png` | unchanged |
| Image references | `grep -c` in README | 2 |

**Not run, and not claimed:** nothing was fitted; no train/test split was made; no p-value was
computed by this project; no model was retrained; no inference beyond ViennaRNA folding and the
frozen linear calibration was run; the SVG was not visually rendered; the cell-free arm's power
calculation was not redone.

---

## 8. What must not be claimed

1. **No expression benefit is established.** The axis was characterised, not optimised.
2. **The calibration's +0.5904 is exploratory**, n=24, and is not validation. The calibration
   remains not independently validated.
3. **The calibration must not be presented as predicting expression** — its expression
   correlation reverses sign between the 6 h and 24 h labels.
4. **No feature is adopted.** The CDS-structure replication is exploratory at n=24.
5. **No single axis may stand in for expression** (gate v17 `v17_1`). Every single-axis route
   tested in this project has now failed a prespecified check.
6. **No floor is frozen** on the measured CV; it is the paper's reporter, not the lab's assay.
7. Nothing here transfers to the project's own 1,811 nt construct, a different reporter or
   protein, or the cell-free arm.
8. **`utr5_frac_C` was not tested here** and is neither supported nor refuted.
9. In-cell and in-solution results remain non-comparable across splits, and cross-system
   ordering transfer remains prohibited.

---

## 9. Pending work — prioritized

1. **The expression axis needs its own features, not stability's.** The primary result says
   stability is not the route. The exploratory signal that *did* track expression is
   **structure**, directly (−0.35 to −0.39), more strongly than stability does. That is the
   next protocol: a declared structure-to-expression characterisation, still univariate, still
   unfittable at n=24, and it must state that it is testing the same 24 labels again — a second
   look at one label set, with the multiplicity cost that carries.
2. **Find more measured expression labels.** 24 is the binding constraint on everything above.
   Options not yet surveyed: the remaining Supplementary Data members of this archive
   (2, 3, 4, 7 were never inventoried beyond their sheet names), and external MPRA-scale
   expression datasets, which would need a declared acquisition protocol with hashes and an
   exposure record.
3. **Supply the cell-free arm's 8 blocking inputs** (`assay_definition_v5`,
   `cell_free_arm.blocking_inputs`), chiefly **which IVTT system** — reconstituted systems lack
   most decay activity, which decides whether stability features mean anything on that arm at
   all. `cell_free_scoring_enabled` stays false until then.
4. **Visually inspect the regenerated SVG** on a machine with a renderer, or install one here.
   Geometry was verified; appearance was not.
5. Tests for `in_cell_feature_screen_v1` and its runs. Still none.
6. The combined two-feature model on the in-cell axis — the two signals are only −0.182 apart.
   Needs its own protocol and the ~1–2 feature budget from gate v15.
7. Discount `cds_length` as a length ruler, or show it is not one. Note this set cannot settle
   it: length is constant here.
8. The reference transcript remains blocked on the v3 `blocking_inputs`.

No process from this stretch is still running; no partial run was left behind.

---

## 10. Exact safe continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
S=/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad

.venv/bin/python -m pytest -q                                 # expect 1,185 passed
.venv/bin/python -m pytest -q tests/test_expression_axis.py   # expect 19 passed

# Reproduce this stretch's headline run (writes a NEW timestamped run):
.venv/bin/python scripts/run_expression_axis.py --archive "$S/acq_persist/MOESM4.zip" --jobs 16

# Earlier runs, unchanged:
.venv/bin/python scripts/run_in_cell_feature_screen.py --archive "$S/acq_persist/MOESM4.zip" \
    --jobs 24 --split stratified --seed 1729
.venv/bin/python scripts/run_feature_refit.py --archive "$S/acq_persist/MOESM4.zip"
```

Re-fetch the source archive if the scratchpad is gone:

```bash
curl -L -o MOESM4.zip "https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-022-28776-w/MediaObjects/41467_2022_28776_MOESM4_ESM.zip"
sha256sum MOESM4.zip   # must be 849ed7b49198c5b97049fec8d3636deea8812db4dd45ce0bcc448297703511c2
```

`run_expression_axis.py` enforces that hash itself and refuses to read a non-matching archive.

### Publishing

```bash
PUB=$S/pub2
git -C "$PUB" fetch origin && git -C "$PUB" status --short
git -C "$PUB" rev-list --left-right --count origin/main...HEAD   # expect 0 0 when in sync
sha256sum "$PUB/diagram_10182026.png"   # must stay baa831ce16df27ed…
```

The clone needs `git config user.name zyliu-OU` and
`git config user.email liuzongyuan1993@gmail.com` if it is ever recreated.

**If `pub2` is gone**, do not publish from `/home/zyliu/Documents/rna-stable-ai`: it has **no
commits** and its `origin` is the placeholder `https://github.com/YOUR_USERNAME/RNA-StableAI.git`.
Clone the real remote into the session scratchpad, copy the changed files in, commit there.

---

## 11. Published state

| Item | Value |
|---|---|
| Commit before this stretch | `d2cf078` Record the publication commit hash in handoff 2026-10-21 V2 |
| Commits published with this handoff | `EXPR_COMMIT` (protocol, script, tests, run artifact, gate v17, assay v5, diagram, README, this handoff), then the commit recording its hash |
| README picture | `diagram_10182026.png`, sha256 `baa831ce16df27ed44a41c2a3b481455a213b328122227b9b2a3820dda47cff1`, **byte-unchanged**, still referenced |
| Workflow diagram | **regenerated** to 2026-10-21 state; geometry verified, appearance not visually inspected |
| Gates | v5–v16 frozen; **v17 current** |
| Assay definition | v1–v4 frozen; **v5 current**; code and tests still pin v3 by name |
| Protocols | `expression_axis_v1` declared and hashed before any relationship was computed |
| Tests | 1,185 passed |
| Known stale published artifacts | **none** — the diagram staleness recorded in V2 §8.1 is resolved here |
