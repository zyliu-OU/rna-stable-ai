# RNA-StableAI — Handoff 2026-10-19 V14

- **Project:** RNA-StableAI
- **Date:** 2026-10-19 (America/Los_Angeles)
- **Version:** V14
- **Absolute workspace path:** `/home/zyliu/Documents/rna-stable-ai`
- **Supersedes nothing.** V1–V13 of 2026-10-19 remain as written.
- **Headline:** the transcript blockers are gone. All construct components were
  supplied, the reference CDS was recovered and **hash-verified against the value
  recorded before it was lost**, and the reference transcript now assembles
  end-to-end from committed inputs.

---

## 1. Current user priorities and scope

The user instructed: continue the build without stopping, and publish to GitHub
if needed. Earlier in the session the user asked to hold the handoff until the
CDS landed; it has landed, so this handoff is written.

Scope flags, all unchanged and still binding:

- `new_sequence_scoring_enabled: false`
- `expression_candidate_design_enabled: false`
- `floors_frozen: false`
- `stage3_ready: false`
- Stage 2 gate: **0 of 6** requirements satisfied.

Nothing in this session changed any flag or satisfied any gate requirement.

Decisions carried from V11–V13 unchanged: Stage 3 target
`transfected_cell_expression`; ORF edits synonymous only; T-cell arm model-blind;
CV below 20% as a **planning bound, not a measurement**.

### New decision recorded this session

| Decision | Value | Source |
|---|---|---|
| 3′UTR region boundary | **Intentional tandem stop**; concatenate as supplied | user: "Intentional tandem stop … concatenate as given, transcript = 44 + 1653 + 114" |

---

## 2. Completed work

### 2.1 Assay power arithmetic made replayable (from V13, carried here for context)

`src/rnastable/assay_power.py` + `tests/test_assay_power.py` (46 tests). The four
numerical power claims in `assay_definition_v3` were reproduced exactly, and the
convention under which they were computed was identified as `ln(1+CV)`. Under the
exact log-normal relation `sqrt(ln(1+CV²))` three of four figures move less
favourably (power at n=3: 0.542 → 0.479; MDE 1.75 → 1.84-fold; paired n=6 0.989 →
0.976) while **`required_n = 5` is unchanged**. Full detail in V13 §3.

### 2.2 Transcript inputs recorded, identified and verified

**`configs/transcript_inputs_v1_2026-10-19.json`** now records every component
with DNA and RNA hashes. Created because the CDS bases had previously been lost
while only their hash survived; this file exists so that cannot recur.

Identity findings, each established by exact comparison, not inference:

| Component | Finding | Method |
|---|---|---|
| 3′UTR (114 nt) | Human **HBA1** 3′UTR (111 nt) preceded by one `TAA` | 111/111 exact match to RefSeq `NM_000558.5`, CDS 38..466 |
| 3′UTR paralogue | **HBA1, not HBA2** (`NM_000517.6` is 110 nt and differs) | exact comparison |
| 5′UTR (44 nt) | **Shortened** Moderna mRNA-1273 5′UTR — *not* identical | 38 nt exact shared prefix, then divergence |

The 5′UTR detail matters: mRNA-1273's 5′UTR is 57 nt
(`GGGAAATAAGAGAGAAAAGAAGAGTAAGAAGAAATATAAGACCCCGGCGCCGCCACC`). The supplied
sequence omits the leading `GGG` **and** the internal 10 nt `CCCCGGCGCC`,
retaining the terminal `GCCACC` Kozak. It is therefore **not a substring** of the
mRNA-1273 5′UTR. GC falls from 0.474 to 0.318. The omitted block is GC-rich and
sits immediately 5′ of the Kozak, so its removal changes 5′UTR length (a RiboNN
input), overall GC, and local folding near the start codon (a STRAND feature).
**It must not be modelled as the full mRNA-1273 5′UTR.**

### 2.3 Ping's answers, and the reference CDS recovered

All construct blocking inputs were answered and are recorded under
`construct_context_from_ping`:

| Question | Answer |
|---|---|
| Parent/baseline | The supplied Excel construct is the **internal control**: Moderna 1273 5′UTR + HBA1 3′UTR |
| Delivery | **IVT mRNA**, transfected (not plasmid DNA) |
| Poly(A) | **103 nt, template-encoded**, directly following the 3′UTR |
| Cap / modification | **Cap 1 analogue (Hongene ON-134)** and **N1-methylpseudouridine** |
| CDS history | **Unclear.** Use the supplied CDS as the baseline and improve from it |

Ping independently confirmed the HBA1 3′UTR, which this project had already
established by exact RefSeq match *before* the answer arrived.

**The reference CDS is recovered and verified.** From
`Fluc and Fluc-PEST sequence.xlsx` (supplied by the user at the workspace root):

```
Fluc ORF   1653 nt, 551 codons, 550 aa, starts ATG ends TGA, GC 0.6534, GC3 0.9964
sha256     86322fc15d89f604e34e3a3fb275f059adb834f7dc904f97f20c44498ba9168d
           == the value recorded in assay_definition_v3 before the bases were lost
```

So the provenance chain across sessions is intact. A second construct was also
supplied:

```
Fluc-PEST  1776 nt, 592 codons, 591 aa, starts ATG ends TGA, GC 0.6464, GC3 0.9611
sha256     37033351becbff1532b375fd29b17afc8ca33bbf477bdfe3762cf0243dbdfc95
```

123 nt (41 codons) longer than Fluc, consistent with a C-terminal PEST
degradation tag. **Different hash, different length, not interchangeable.**

Sequences are now persisted as plain files under `data/constructs/`
(`fluc_orf.txt`, `fluc_pest_orf.txt`, `utr5.txt`, `utr3.txt`, `polya_103.txt`) so
they can never be lost to conversation again.

**The tandem-stop decision is corroborated by the data.** The Fluc CDS ends in
`TGA` and the 3′UTR begins with `TAA` — two *different* stop codons in sequence.
The CDS already carries its own terminator, so the `TAA` is a genuine second stop
rather than a boundary split one codon early. The user's reading was correct.

### 2.4 Transcript assembly built and run

- **`src/rnastable/transcript_assembly.py`** — verifies supplied bases against
  the recorded CDS hash *before anything else*, converts DNA→RNA explicitly
  (`Transcript` performs no silent normalization), cross-checks component lengths
  against the recorded boundary decision, assembles, and returns a frozen
  `AssemblyReport`.
- **`tests/test_transcript_assembly.py`** — **48 tests**.
- **`scripts/assemble_reference_transcript.py`** — the CLI.

Deliberate design points:

1. **No bypass on the hash check.** Tests build their own config fixture around a
   synthetic CDS rather than receiving a test-only override, so the production
   gate runs unmodified.
2. **Component lengths are cross-checked against the boundary decision**, and the
   refusal says the decision "must be revisited" rather than offering a workaround.
3. **The tandem stop is measured, not assumed** from the recorded decision.
4. **A multi-record FASTA is refused** rather than silently taking the first
   record, which would quietly choose the reference construct.
5. **Poly(A) is opt-in** — see §3.

Assembled artifact: **`results/reference_transcript/FLUC-REF-V1.json`**

```
transcript_length_nt   1811      utr5 44 | cds 1653 | utr3 114
cds boundaries         [44, 1697)        protein 550 aa
tandem_stop            present, UAA      ribonn_exclusion  null
cds sha256             86322fc1…         transcript sha256 403a45c5…
```

The script refuses to overwrite an existing assembled reference in place, because
it is the input every later score binds to.

### 2.5 External literature evidence recorded

**`configs/external_design_evidence_v1_2026-10-19.json`**, from four papers the
user supplied in `papers/`. Every figure is flagged as author-reported; **none was
reproduced or verified here.**

- **PARADE** (bioRxiv 2024.12.31.630783) measured 60,000 UTR segments across six
  lines including **Jurkat (T cells)**. It **does not lift the model-blind
  declaration**, for three recorded reasons: Jurkat is a transformed line while
  the lab uses activated primary CD3+ (the same class of mismatch that got
  RiboNN's `Primary_CD4+` task rejected, and V12 recorded that transformed
  lymphoid lines are *worse* matches); PARADE scores UTR segments in a fixed
  reporter, not TE of an arbitrary transcript; and it measures protein output
  from genome-integrated eGFP/mCherry, a different quantity in a different
  delivery context.
- **mRNAutilus** (arXiv:2605.31296 v1 — a **preprint**, despite the local filename
  saying NBT) steers generation with regressors for half-life (Saluki), TE
  ("Zheng et al., 2025") and protein abundance. Its Zenodo deposit contains
  `Ribo-NN-human.xlsx`, indicating its TE regressor is trained on RiboNN-derived
  data — weak external corroboration that RiboNN is a sane component, **not**
  validation for this assay. Notably they report their *highest* R² on half-life
  and only "competitive" on TE, and TE is the property overlapping our A549 arm.
- **Parent construct identification.** mRNAutilus Figure 4D–F benchmarks against
  "a GenScript F-Luc CDS paired with human alpha-globin UTRs" in **Jurkat, A549**
  and HepG2 — two of which are this project's assay arms — and GenScript USA is an
  author affiliation (Ping's). This **corrected an earlier speculation** in this
  project that the parent might itself be machine-designed and therefore nearly
  unimprovable; the evidence points the other way, to the parent being the
  *baseline*. **Ping did not confirm it** ("history unclear"), so it remains
  indicated but **unconfirmed**, and the 5′UTR is a mRNA-1273 derivative rather
  than alpha-globin, so the correspondence is partial.
- **Fold-change figures are not comparable.** mRNAutilus reports 400-fold vs
  **wild-type** (HEK293T); GEMORNA 41-fold vs **an optimized benchmark**; this
  project targets 1.5-fold vs a parent at GC3 0.996. No comparison may be drawn.

---

## 3. Scientific consequences that must not be lost

### 3.1 N1-methylpseudouridine is now a live limitation, not a hypothetical

Every uridine in the transfected molecule is m1Ψ. RNAfold, STRAND,
`strand_rnafold_calibration_v1` and RiboNN all represent it as canonical U and
have no representation of the modification.

- m1Ψ alters base-pairing and stacking thermodynamics, so computed structures and
  folding free energies are **systematically not those of the assayed molecule**.
  This bears directly on the stability arm, which rests on folding-derived features.
- Because the modification is **constant across the panel**, it does not by itself
  confound a *ranking* of constructs differing in sequence. It does invalidate any
  absolute or calibrated structural/stability prediction.
- Even the ranking argument assumes the modification's effect is
  sequence-independent, which is **unverified**.

### 3.2 Poly(A) inclusion is an open decision, deliberately not defaulted

The real molecule is 44 + 1653 + 114 + **103** = **1914 nt**. The recorded
boundary decision covers only the 1811 nt core.

- `assay_definition_v3` says a supplied poly(A) counts toward scope → include it.
- Against that, RiboNN and the STRAND features derive from transcript
  representations that do not generally carry long homopolymeric tails, so
  appending 103 adenosines may push the input out of distribution and changes 3′
  region sizes RiboNN consumes.

Current behaviour: `--poly-a` opt-in; 1811 by default, 1914 when passed. Neither
triggers a RiboNN exclusion. **Recommendation: score both and treat the
difference as the stack's sensitivity to poly(A) representation, not as biology.**

### 3.3 Fluc and Fluc-PEST cannot be pooled

A PEST tag shortens protein half-life, so luminescence from Fluc-PEST tracks
current mRNA level more closely, while untagged Fluc integrates past translation.
Comparisons must be within a construct. No decision has been taken on whether
Fluc-PEST enters the panel.

### 3.4 The AATAAA hexamer is inert here

Resolved by the IVT answer: with a template-encoded tail there is no cleavage and
polyadenylation, so the 3′UTR's `AATAAA` has no function in this context. The
earlier recorded caveat is resolved, not merely noted.

---

## 4. Verification actually run

| Check | Command | Outcome |
|---|---|---|
| Inherited state | `pytest -q` | 1,103 passed — matched V12 exactly |
| Power tests | `pytest tests/test_assay_power.py -q` | **46 passed** |
| Assembly tests | `pytest tests/test_transcript_assembly.py -q` | **48 passed** |
| **Full suite** | `timeout 3000 .venv/bin/python -m pytest -q` | **1,197 passed, 1 skipped, 0 failed** in 219.31 s |
| Lint | `ruff check` on all changed files | **All checks passed** |
| CDS hash gate, negative | correct-length wrong-sequence CDS vs real config | **refused**, both hashes and lengths named |
| CDS hash gate, positive | real Fluc ORF vs real config | **matched** `86322fc1…` |
| Config self-consistency | hashes, lengths, 44+1653+114 arithmetic, duplicate-key scan | passed |
| Cross-config agreement | `transcript_inputs_v1` vs frozen `assay_definition_v3` | CDS hash, length, codons, protein length all agree |

Suite went 1,103 → 1,149 → 1,186 → **1,197**, 0 failures throughout.
Runtime: Python **3.12.14**, scipy **1.18.1**.

**Environment note, still important.** Use
`/home/zyliu/Documents/rna-stable-ai/.venv/bin/python`. The default `python3` is
Anaconda base (3.14.6) and lacks biopython, producing 15 collection errors that
are an environment artifact, not code defects. `openpyxl` is **not** installed and
was deliberately **not** installed; the Excel was parsed with stdlib
`zipfile` + `xml.etree`.

### Files changed this session

| File | SHA-256 |
|---|---|
| `src/rnastable/assay_power.py` | `301dd9a67b9a5b1f41daa4ca4219e394641cff5af0b35d1a7910253f229233a3` |
| `src/rnastable/transcript_assembly.py` | `70c3f019ca4715ae8eec69a4cd119400701f228afb07bd3e93f08c2ed8e25f68` |
| `scripts/assemble_reference_transcript.py` | `70648ca9c093a93463313c36086587b5a778f36784f82f8c01b14529aacf8d90` |
| `tests/test_assay_power.py` | `75e7a1ef5e31174a6b596e4a30f77f8801b18161511d274097f34d29d92f0ba6` |
| `tests/test_transcript_assembly.py` | `2be2b7ff54aa23f3eda4f4c5a20228539ab10ceb429b63c8c981873356a0679d` |
| `configs/transcript_inputs_v1_2026-10-19.json` | `961b42fd20580bc267a12dbffc4c9043bee0250fc4497a83f1ee0a5271ab1ca2` |
| `configs/external_design_evidence_v1_2026-10-19.json` | `a343e66fec17f5ba6693e54572e60256012ebc2d1d200e5618bb53c32ed02518` |
| `results/reference_transcript/FLUC-REF-V1.json` | `2f2203918c44366e117f30791b4d0cd02fc1d80ca46f44df897cbd2cebba42aa` |

Carried unchanged from V12: `component_integration.py`
(`9ef50ff8…`), `archive_replay_sources.py` (`fbd073cd…`),
`test_construct_edit_classification.py` (`36735e05…`).

---

## 5. Unverified / not done

- **No measured CV exists.** All power figures are arithmetic on an assumed bound.
- **Nothing has been folded or scored.** No RNAfold, STRAND or RiboNN run was
  made on the assembled transcript this session.
- The assembled transcript has **not** been run through
  `classify_construct_edit` against any candidate, because no candidate exists.
- The archive `build` was again **not** re-run (V12 §6 item 7 still undecided).
- `assay_definition_v3` was **not** edited. The V13 §6 item 1 decision on the
  power convention is still open.
- The 5′UTR shortening relative to mRNA-1273 has not been confirmed as deliberate
  with Ping.
- BLAST jobs submitted for the 5′UTR (`DDD1AV4C014`, `DDDP560M016`) were rendered
  moot by Ping's answer and their results were never used.

---

## 6. Prioritized next steps

**Not blocked — the obvious next build step:**

1. **Fold and score the assembled transcript.** This is now possible for the
   first time. Run RNAfold/STRAND on `FLUC-REF-V1`, both with and without
   poly(A), and record the m1Ψ caveat (§3.1) against every number produced.

**Needs a user decision:**

2. **Poly(A) inclusion** in the modelled transcript (§3.2).
3. **Fluc-PEST**: does it enter the panel (§3.3)?
4. **Power convention** → `assay_definition_v4` or leave v3 (V13 §6 item 1).
5. **Measured CVs** for both readouts, and the **decision cost** of a false accept
   vs false reject — the last inputs any floor needs.
6. Band requirement 3 (V7); OpenVaccine acquisition (V6).

**Worth asking Ping:**

7. Whether the 5′UTR shortening (omitted `GGG` and internal `CCCCGGCGCC`) is
   deliberate.
8. Whether the parent is the same GenScript F-Luc + alpha-globin composition used
   as the mRNAutilus baseline — would settle §2.5.

---

## 7. Exact safe continuation commands

Run from `/home/zyliu/Documents/rna-stable-ai`. All are read-only or test-only.

```bash
# Full suite — MUST use the project virtualenv, not the Anaconda base python3
timeout 3000 .venv/bin/python -m pytest -q

# This session's tests
.venv/bin/python -m pytest tests/test_transcript_assembly.py tests/test_assay_power.py -q

# Re-assemble the reference transcript, verifying without writing
.venv/bin/python scripts/assemble_reference_transcript.py \
  --cds data/constructs/fluc_orf.txt \
  --provenance "Fluc ORF from Excel via Ping 2026-10-19" --dry-run

# Same, including the 103 nt template-encoded poly(A)
.venv/bin/python scripts/assemble_reference_transcript.py \
  --cds data/constructs/fluc_orf.txt --provenance "..." --poly-a --dry-run

# Confirm the recovered CDS still hashes to the recorded reference
sha256sum data/constructs/fluc_orf.txt   # file includes a trailing newline
tr -d '\n' < data/constructs/fluc_orf.txt | sha256sum   # 86322fc1…

# Both power conventions side by side
.venv/bin/python -c "
from rnastable.assay_power import assess
for c in ('log1p_cv','lognormal_exact'):
    r = assess(0.20, 3, 1.5, c)
    print(c, round(r.power_at_target,4), round(r.minimum_detectable_fold_change,4),
          r.required_replicates_for_target_power)
"

# Verify the frozen source archive without recomputing it
.venv/bin/python scripts/archive_replay_sources.py --verify
```

Do **not** run `scripts/archive_replay_sources.py` without `--verify` until V12
§6 item 7 is decided: it overwrites a frozen artifact. The assembly script
refuses to overwrite `results/reference_transcript/FLUC-REF-V1.json`; remove it
deliberately or pass a different `--tx-id`.

---

## 8. What must not be claimed

- This session satisfied **no** Stage 2 gate requirement. Still **0 of 6**.
- A green suite of 1,197 tests is **not** evidence of structure accuracy,
  stability, translation or expression benefit.
- **Assembling a transcript establishes nothing biological.** It produces a
  validated model input.
- **No computed structure or free energy may be presented as the value for the
  assayed molecule**, because every U is actually m1Ψ and no component models it.
- Hash-matching the CDS proves **sequence identity with the earlier record**, not
  correctness, optimality or provenance beyond that record.
- Identifying the 3′UTR as HBA1 and the 5′UTR as a shortened mRNA-1273 derivative
  are **sequence identity results only**. No functional property follows.
- The parent-construct correspondence to the mRNAutilus baseline is **indicated,
  not confirmed** — Ping explicitly said the CDS history is unclear.
- **No external fold-change figure may be compared to the 1.5-fold target.**
- PARADE's Jurkat data is **not** evidence about activated primary CD3+ T cells;
  the T-cell arm remains model-blind with no translation-side score.
- The power figures are planning arithmetic on an **assumed** CV, not measurements.
- No floor is selected or frozen, and no sequence scoring is enabled.
