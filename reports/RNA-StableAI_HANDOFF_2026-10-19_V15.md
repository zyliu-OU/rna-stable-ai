# RNA-StableAI — Handoff 2026-10-19 V15

- **Project:** RNA-StableAI
- **Date:** 2026-10-19 (America/Los_Angeles)
- **Version:** V15
- **Absolute workspace path:** `/home/zyliu/Documents/rna-stable-ai`
- **Supersedes nothing.** V1–V14 remain as written.
- **Contains a withdrawal.** A finding published earlier in this session was
  investigated further and **retracted**. See §4. A reader who stops at the
  earlier report will take away a conclusion this project no longer holds.
- **Published:** `github.com/zyliu-OU/rna-stable-ai`, live HEAD **`c503d9e`**.

> **Filename date note.** Two reports written this session are named
> `..._2026-10-20.md` because they were dated from UTC timestamps while the
> America/Los_Angeles date was still 2026-10-19. They were **not** renamed, since
> they are already published and cross-referenced. All work in this handoff
> occurred on **2026-10-19 local**.

---

## 1. Headline

The transcript blockers are gone. The reference construct is assembled,
hash-verified, folded, and scored. Two constructs have been compared. One
methodological finding was published, then disproved by follow-up and withdrawn.

Scope flags, all unchanged and still binding:

- `new_sequence_scoring_enabled: false`
- `expression_candidate_design_enabled: false`
- `floors_frozen: false`
- `stage3_ready: false`
- Stage 2 gate: **0 of 6** requirements satisfied.

**Nothing this session changed any flag or satisfied any gate requirement.**

---

## 2. Published commits since V14

| Commit | What |
|---|---|
| `529ece7` | Transcript assembly, assay power arithmetic, verified construct inputs |
| `2ec4b8d` | Folded the reference transcript; poly(A) sensitivity of the folding features |
| `46678e6` | RiboNN on the reference construct; poly(A) question closed |
| `8068c35` | Fluc vs Fluc-PEST comparison; UTR–ORF coupling measured |
| `6aab265` | **Correction:** the coupling finding is a base-pair span artifact |
| `44b1845` | Span policy diagnostic; the real problem is `alo`, not span |
| `f62b369` | README points at `workflow_10192026.svg` |
| `c503d9e` | Removed the superseded `diagram_10192026.svg` |

---

## 3. Completed work

### 3.1 The reference transcript exists and is verified

`Fluc and Fluc-PEST sequence.xlsx` (workspace root, supplied by Ping via the
user) was parsed with stdlib `zipfile` + `xml.etree`; **`openpyxl` is not
installed and was deliberately not installed.**

```
Fluc       1653 nt / 551 codons / 550 aa / ATG…TGA / GC 0.6534 / GC3 0.9964
           sha256 86322fc15d89f604e34e3a3fb275f059adb834f7dc904f97f20c44498ba9168d
Fluc-PEST  1776 nt / 592 codons / 591 aa / ATG…TGA / GC 0.6464 / GC3 0.9611
           sha256 37033351becbff1532b375fd29b17afc8ca33bbf477bdfe3762cf0243dbdfc95
```

**The Fluc hash equals the value recorded in `assay_definition_v3` before the
bases were lost.** The provenance chain across sessions is intact.

Assembled reference: `results/reference_transcript/FLUC-REF-V1.json` — 1,811 nt,
CDS `[44, 1697)`, 550 aa, tandem stop `UAA`, no RiboNN exclusion. Fluc-PEST:
`FLUC-PEST-V1.json`, 1,934 nt.

Sequences persisted under `data/constructs/` so they cannot be lost to
conversation again.

**The tandem-stop decision is corroborated by the data.** Fluc ends in `TGA`, the
3′UTR begins with `TAA` — two *different* stop codons. The CDS already carries
its terminator, so the `TAA` is a genuine second stop, not a boundary split one
codon early. The user's reading was correct.

### 3.2 Component identities

| Component | Finding | Method |
|---|---|---|
| 3′UTR (114 nt) | Human **HBA1** 3′UTR (111 nt) preceded by one `TAA` | 111/111 exact match to `NM_000558.5` |
| paralogue | **HBA1, not HBA2** | `NM_000517.6` is 110 nt and differs |
| 5′UTR (44 nt) | **Shortened** Moderna mRNA-1273 5′UTR, *not* identical | 38 nt exact shared prefix |

The mRNA-1273 5′UTR is 57 nt
(`GGGAAATAAGAGAGAAAAGAAGAGTAAGAAGAAATATAAGACCCCGGCGCCGCCACC`). The supplied
sequence omits the leading `GGG` **and** the internal 10 nt `CCCCGGCGCC`, keeping
the terminal `GCCACC` Kozak, so it is **not a substring**. GC falls 0.474 → 0.318.
Ping described it as "moderna 1273 5' UTR"; whether the shortening is deliberate
is **unconfirmed**.

### 3.3 Ping's answers

| Question | Answer |
|---|---|
| Parent/baseline | The Excel construct is the **internal control**: Moderna 1273 5′UTR + HBA1 3′UTR |
| Delivery | **IVT mRNA**, transfected |
| Poly(A) | **103 nt, template-encoded**, directly after the 3′UTR |
| Cap / modification | **Cap 1 analogue (Hongene ON-134)** + **N1-methylpseudouridine** |
| CDS history | **Unclear.** Use the supplied CDS as baseline and improve from it |

Ping independently confirmed the HBA1 3′UTR, which this project had already
established by exact RefSeq match **before** the answer arrived.

### 3.4 Folding and RiboNN on the reference

`FLUC-REF-V1` core, ViennaRNA 2.7.2 / Turner 2004 / 37 °C / dangles 2:

| | value |
|---|---|
| MFE | −740.400024 kcal/mol (−0.408835 /nt) |
| Ensemble free energy | −771.977661 kcal/mol |
| `strand_alo` | 1.143062 |
| Mean unpaired | 0.377889 |
| 5′UTR / CDS / 3′UTR mean unpaired | 0.838862 / 0.362727 / 0.419823 |

RiboNN `predicted_TE_A549`, 50 released human checkpoints, 182 weight files
hash-verified, **bitwise-identical replay across two independent worker
processes**:

- `FLUC-REF-V1-core` **0.827672**
- `FLUC-PEST-V1-core` **0.785629**

### 3.5 Poly(A) resolved on both sides

| Quantity | Poly(A) sensitivity |
|---|---|
| MFE | **0.000000** — exactly none |
| Ensemble free energy | 0.002% |
| **`strand_alo`** | **−48%** (1.143062 → 0.594838) |
| RiboNN `predicted_TE_A549` | +0.085%, **0.019 SD** — noise |

The tail is thermodynamically inert: the core MFE structure is an exact **prefix**
of the tailed one, the tail is entirely unpaired (mean unpaired 0.9997), and all
other regions are unchanged to the fourth decimal. Only `strand_alo` responds,
and that is **dilution of a positional mean by 103 maximally unpaired
positions**, not signal.

**Recommendation recorded: use the 1,811 nt core throughout, both arms.** One
representation everywhere removes the risk of a comparison silently mixing
conventions. *Still a user decision; see §6.*

### 3.6 Fluc vs Fluc-PEST

RiboNN difference **−0.042043 (−5.08%)**, systematic: all ten folds agree in
sign, effect **1.15× the between-fold SD** (0.0367). Per nucleotide the two
constructs are nearly indistinguishable (MFE/nt differs 0.004; mean unpaired
agrees to three decimals); the raw −42 kcal/mol gap is mostly length.

**This is not a biological result.** It is confounded with CDS length, which
RiboNN consumes as an input feature and which is 7.4% greater here, and **RiboNN
is structurally blind to what a PEST tag does** — the tag is a protein-degradation
signal, downstream of translation efficiency. **Fluc-PEST is not shown to
translate less well.**

For the assay this cuts the other way: fast protein turnover means Fluc-PEST
luminescence tracks current mRNA more closely, while untagged Fluc integrates
past translation.

### 3.7 Assembler hardened

`assemble()` gained `cds_component`, binding each construct to its own hash.
Verified both ways: Fluc is refused under `cds_fluc_pest` and vice versa, with
both hashes and lengths named. The UTRs and the tandem-stop decision remain
checked against the boundary decision; only CDS length comes from its own record.

### 3.8 README diagram

`workflow_10192026.svg` (`c91d1078…`) replaced `diagram_10192026.svg`, which was
removed. The caption legend was corrected from **blue** to **green** (the new
diagram's colour for implemented paths) and the alt text rewritten to describe
this image, since alt text is what screen readers receive. **`diagram_10182026.png`
— the user's picture — is unchanged (`baa831ce…`) and still linked.** Earlier
handoffs still name the removed SVG; they were left untouched as historical
records, and the file remains in git history.

---

## 4. WITHDRAWN: the UTR–ORF coupling finding

**What was published** (`8068c35`): the identical 44 nt 5′UTR has mean unpaired
probability 0.838862 in Fluc and 0.570002 in Fluc-PEST. This was reported as
empirical confirmation of the recorded `coupling_warning`, with the design
conclusion that **a 5′UTR cannot be optimised outside the transcript it will be
used in**.

**The observation reproduces. The conclusion does not hold and is withdrawn.**

Fluc-PEST is not a different ORF. It is Fluc with a 123 nt insert at position
1650: the two contexts are **byte-identical for their first 1650 nt**, and the
only difference sits ~1.65 kb downstream of the 5′UTR. Varying only
`max_bp_span`:

| span | Fluc | Fluc-PEST | &#124;Δ&#124; |
|---|---:|---:|---:|
| unlimited | 0.8389 | 0.5700 | **0.2689** |
| 600 | 0.8398 | 0.8813 | 0.0415 |
| **200** | 0.9047 | 0.9048 | **0.0001** |
| 100 / 50 | identical | identical | 0.0000 |

At ≤200 nt the 5′UTR folds **identically in both contexts to four decimal
places**. The effect is a property of unbounded global folding, not of the
sequences.

A correction notice was added at the top of the original report rather than
editing it silently, so the record shows what was claimed and why it changed.

**Process lesson:** a mechanism should be established before a design conclusion
is drawn from an observation. The observation was sound; the inference was not.

---

## 5. Span policy diagnostic, and where the real problem is

**Hypothesis tested:** LinearPartition (the engine behind STRAND's released
features) is beam-pruned, so perhaps it behaves locally, making our unlimited-span
substitute mismatched — in which case the recorded
`feature_level_compatible: false` verdict might be an artifact of the span
default, and bounding the span could restore **published STRAND** applicability.

**The hypothesis is wrong.** On the six selection-set records (928–1215 nt):

| `max_bp_span` | within tolerance | mean &#124;Δ&#124; energy/len |
|---|---:|---:|
| **unlimited** | **13/18** | **0.000014** |
| 600 | 7/18 | 0.006996 |
| 200 | 2/18 | 0.038494 |
| 100 | 1/18 | 0.063250 |

Agreement degrades **monotonically** when bounded. Unlimited agrees best, and on
`energy_per_length` to **1.4 × 10⁻⁵** — effectively exact. LinearPartition tracks
the exact global partition function closely at this length.

**Per feature at unlimited span:** `energy_per_length` **6/6**, `aup` **5/6**,
`alo` **2/6**. The incompatibility is an **`alo` problem**.

`alo` is numerically fragile. For `X320004D1` only **16 of 928** positions sit
below 1e-5, yet log-odds diverges near zero. Holding the folding **completely
fixed** and varying only the clipping epsilon:

| epsilon | 1e-10 | 1e-6 | 1e-5 | 1e-4 | 1e-3 |
|---|---:|---:|---:|---:|---:|
| alo | 1.7401 | 1.7504 | 1.7776 | 1.7618 | 1.6267 |

A spread of ~0.15, **about 3× the tolerance of 0.0513**, from convention alone —
and the released LinearPartition value **1.66408 lies inside that range**.
Meanwhile `aup`, the same probabilities without the log transform, agrees to
0.0004.

**Cohort discipline:** selection-set records only, which
`strand_rnafold_agreement_criterion_v1` records as **burned**. The blinded
85-record evaluation set was **not touched**, so nothing here can contaminate the
set a real decision must rest on. Six burned records can point at a mechanism;
they cannot decide anything.

**Recommendation: keep `max_bp_span: -1`, as a decision rather than an inherited
default.** Every alternative tested moves features further from the engine STRAND
was built on.

**The long-range sensitivity caveat stands.** Folding features on ~1–2 kb
transcripts remain partly set by kilobase-range pairs. What changed is the
attribution: the released STRAND features **share** that property, so it is
inherent to the feature definition on long mRNA, not something introduced here.
Carry it as a known limitation of the stability arm.

---

## 6. Scientific consequences that must not be lost

### 6.1 N1-methylpseudouridine is a live limitation

Every uridine in the transfected molecule is m1Ψ. RNAfold, STRAND,
`strand_rnafold_calibration_v1` and RiboNN all represent it as canonical U.

- Computed structures and free energies are **systematically not those of the
  assayed molecule**. This bears directly on the stability arm.
- The modification is **constant across the panel**, so it does not by itself
  confound a *ranking*; it does invalidate any absolute or calibrated prediction.
- Even the ranking argument assumes the effect is sequence-independent, which is
  **unverified**.

### 6.2 The AATAAA hexamer is inert

Resolved by the IVT answer: with a template-encoded tail there is no cleavage and
polyadenylation, so the 3′UTR's `AATAAA` has no function here.

### 6.3 Fluc and Fluc-PEST cannot be pooled

Different hashes, different lengths, different protein turnover. Comparisons must
be within a construct.

### 6.4 Parent construct identification remains unconfirmed

mRNAutilus Figure 4D–F benchmarks against "a GenScript F-Luc CDS paired with
human alpha-globin UTRs" in **Jurkat, A549** and HepG2 — two of which are this
project's arms — and GenScript USA is an author affiliation (Ping's). This
suggests the parent is the **baseline mRNAutilus was designed to beat**, which
would mean headroom exists. **Ping did not confirm it** ("history unclear"), and
the 5′UTR is an mRNA-1273 derivative rather than alpha-globin, so the
correspondence is **partial and indicated, not established**.

External fold-change figures (mRNAutilus 400× vs wild-type; GEMORNA 41× vs an
optimized benchmark) **may not be compared** to the 1.5-fold target until the
parent baseline is known.

---

## 7. Verification actually run

| Check | Outcome |
|---|---|
| **Full suite** | **1,238 passed, 1 skipped, 0 failed** in 222.49 s |
| Lint | `ruff check` clean on every file changed this session |
| CDS hash gate, negative | correct-length wrong-sequence CDS **refused**, both hashes named |
| CDS hash gate, positive | real Fluc ORF **matched** `86322fc1…` |
| Cross-construct gate | Fluc refused under `cds_fluc_pest` and vice versa |
| RiboNN replay | two processes **bitwise-identical**, all released tasks |
| Published snapshot | 105 tests pass from a clean clone with no local state |
| README images | all references resolve from a fresh clone; picture byte-unchanged |

Suite trajectory: 1,103 → 1,149 → 1,186 → 1,197 → 1,203 → **1,238**, zero
failures throughout. Python **3.12.14**, scipy **1.18.1**, ViennaRNA **2.7.2**.

**Environment note.** Use `/home/zyliu/Documents/rna-stable-ai/.venv/bin/python`.
The default `python3` is Anaconda base (3.14.6) and lacks biopython, producing 15
collection errors that are an environment artifact, not code defects.

### Key file hashes at session end

| File | SHA-256 |
|---|---|
| `src/rnastable/transcript_assembly.py` | `533d6e6a159e8167107c1c4f7fc24bdcdfa7a36552fc77e2d4d23cd9d9c2ebf5` |
| `scripts/fold_reference_transcript.py` | `02144bf2a93b5e357520f258dc5beb9baf9dca825e3954a83e2ee2f9ee84bc31` |
| `scripts/measure_utr_orf_coupling.py` | `e486bbdf53798dd762f3422b7684bebe5faae34af4a9b8b4d7dd84f4035bf3dc` |
| `scripts/diagnose_bp_span_policy.py` | `5a7a1e267081a944d2474486594100e9ae28e22beb81dc574d488f58682cdef5` |
| `scripts/run_ribonn_fixed_inference.py` | `04ac0de95e1e164b918b7c313d1d7a710b4e3daf64f3ac41c77a3a4f56f4e177` |
| `tests/test_transcript_assembly.py` | `9455205b1bd2e2ea9927e02fa171fa313a397be9b369e092dd6dd866119daf80` |
| `tests/test_utr_orf_coupling.py` | `fc64ac82979fea79c5252306090141109f62f4197797e93c9ab89399cd171278` |
| `configs/transcript_inputs_v1_2026-10-19.json` | `2cfb849f9260cd854b2ff253ee2739e5ee577718621a43781ba950342a69ffba` |
| `README.md` | `1d4015029c394d23422c64ed702c8d04595c0f866cb4ffdc42d514d65c4d28c6` |
| `workflow_10192026.svg` | `c91d10784c7fa8b888d25eb09b3be920f3ef05d3b9fac6e2efc45c7aa2df75aa` |

---

## 8. Unverified / not done

- **No measured CV exists.** All power figures are arithmetic on an assumed bound.
- **Nothing has been compared to a measurement.** No cell data exists.
- The RiboNN run directories are **kept local**, consistent with every prior
  inference run; their conda metadata (13 MB) and vendored upstream source are
  not redistributed. All numbers are in the reports.
- The archive `build` was again **not** re-run (V12 §6 item 7 still undecided).
- `assay_definition_v3` was **not** edited; the V13 power-convention decision is
  still open.
- The 5′UTR shortening relative to mRNA-1273 is **not confirmed** as deliberate.
- BLAST jobs for the 5′UTR (`DDD1AV4C014`, `DDDP560M016`) were rendered moot by
  Ping's answer; results never used.
- `classify_construct_edit` has still **never been run against a candidate**,
  because none exists.

---

## 9. Prioritized next steps

**Not blocked — the strongest lead:**

1. **Attack `alo`, not the span.** `energy_per_length` and `aup` already agree
   with LinearPartition. The concrete question is what near-zero convention
   LinearPartition's output implies and whether matching it brings `alo` inside
   tolerance. Bounded work with a real payoff: it could flip the frozen
   `feature_level_compatible: false` verdict and make **published STRAND**
   applicable. Must be designed on the burned selection set and only then, if
   promising, run once against the blinded evaluation set.

**Needs a user decision:**

2. **Poly(A) inclusion** in the modelled transcript (§3.5; recommendation: core).
3. **Does Fluc-PEST enter the panel?** (§3.6)
4. **Span policy**: adopt `max_bp_span: -1` as an explicit decision (§5).
5. **Power convention** → `assay_definition_v4` or leave v3 (V13 §6 item 1).
6. **Measured CVs** for both readouts, and the **decision cost** of a false accept
   vs false reject — the last inputs any floor needs.
7. Band requirement 3 (V7); OpenVaccine acquisition (V6).

**Worth asking Ping:**

8. Is the 5′UTR shortening (omitted `GGG` and internal `CCCCGGCGCC`) deliberate?
9. Is the parent the same GenScript F-Luc + alpha-globin composition used as the
   mRNAutilus baseline? Would settle §6.4.

---

## 10. Exact safe continuation commands

Run from `/home/zyliu/Documents/rna-stable-ai`. All are read-only or test-only.

```bash
# Full suite — MUST use the project virtualenv
timeout 3000 .venv/bin/python -m pytest -q

# Re-assemble the reference transcript, verifying without writing
.venv/bin/python scripts/assemble_reference_transcript.py \
  --cds data/constructs/fluc_orf.txt \
  --provenance "Fluc ORF from Excel via Ping 2026-10-19" --dry-run

# Fluc-PEST, bound to its own recorded hash
.venv/bin/python scripts/assemble_reference_transcript.py \
  --cds data/constructs/fluc_pest_orf.txt --cds-component cds_fluc_pest \
  --tx-id FLUC-PEST-V1 --provenance "..." --dry-run

# Confirm the recovered CDS still hashes to the recorded reference
tr -d '\n' < data/constructs/fluc_orf.txt | sha256sum   # 86322fc1…

# Re-run the span diagnostic (burned selection set only)
.venv/bin/python scripts/diagnose_bp_span_policy.py --spans="-1,600,200,100"

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

# Confirm live publication state
git ls-remote https://github.com/zyliu-OU/rna-stable-ai.git main   # c503d9e
```

Do **not** run `scripts/archive_replay_sources.py` without `--verify` until V12
§6 item 7 is decided. The assembly and fold scripts refuse to overwrite existing
artifacts; remove them deliberately or pass a different `--tx-id`.

---

## 11. What must not be claimed

- This session satisfied **no** Stage 2 gate requirement. Still **0 of 6**.
- A green suite of 1,238 tests is **not** evidence of structure accuracy,
  stability, translation or expression benefit.
- **Assembling, folding or scoring a transcript establishes nothing biological.**
- **No computed structure or free energy is the assayed molecule's**, because
  every U is actually m1Ψ and no component models it.
- Hash-matching the CDS proves **sequence identity with the earlier record**,
  nothing more.
- Sequence identifications (HBA1 3′UTR, shortened mRNA-1273 5′UTR) are **identity
  results only**. No functional property follows.
- **The UTR–ORF coupling conclusion is withdrawn** (§4). Do not re-derive it from
  the earlier report without reading the correction notice.
- Unlimited span agreeing best with LinearPartition is **not** evidence that it
  is physically correct; it is agreement with a reference engine.
- The published STRAND verdict stands: `feature_level_compatible: false`,
  `outcome: rejected`.
- **Fluc-PEST is not shown to translate less well**; the −5.08% is confounded
  with CDS length and RiboNN cannot represent a PEST tag's function.
- No external fold-change figure may be compared to the 1.5-fold target.
- PARADE's Jurkat data is **not** evidence about activated primary CD3+ T cells;
  the T-cell arm remains **model-blind**.
- The power figures are planning arithmetic on an **assumed** CV.
- No floor is selected or frozen, and sequence scoring remains disabled.
