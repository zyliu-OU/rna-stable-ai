# RNA-StableAI — Handoff 2026-10-20 V3

- **Project:** RNA-StableAI
- **Date:** 2026-10-20 (America/Los_Angeles)
- **Version:** V3 (follows [V1](RNA-StableAI_HANDOFF_2026-10-20_V1.md), the Stage 2 gate
  review, and [V2](RNA-StableAI_HANDOFF_2026-10-20_V2.md), BoTorch and the Pareto
  formulation; both stand unedited)
- **Workspace:** `/home/zyliu/Documents/rna-stable-ai`
- **Publication clone:** `/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad/verify`
- **Remote:** `https://github.com/zyliu-OU/rna-stable-ai.git` — **PUBLIC**
- **Headline:** the optimisation **domain** is now specified and enumerated — windowed
  synonymous edits over 30 codons at the 5′ end of the Fluc ORF, sampled into two 512-member
  pools. **Nothing is scored, nothing is proposed for assay, and no gate switch was opened.**
  A measured GC confound makes the free/neutral mode choice a real, open decision.

---

## 1. User instruction in this stretch

| Instruction | Reading | Consequence |
|---|---|---|
| "Windowed synonymous edits over the 5′ region, sure" | Choose that generator for the candidate pool, over codon-usage targets and whole-ORF random sampling. | `configs/synonymous_window_design_space_v1_2026-10-20.json`, the module, the driver, two pools and 44 tests. |

**What this does not authorise.** Specifying a domain is not scoring it and not proposing
assay candidates. `new_sequence_scoring_enabled` and `expression_candidate_design_enabled`
remain **false** in gate v5, which is **unchanged and not superseded**. The driver refuses
to start if either switch has been opened.

**Prior decisions this builds on:** the Pareto formulation (V2 §3), and the reframe that the
real question is which ~10 constructs enter an assay panel, which makes this a pool-selection
problem rather than a search over 10²⁷³ variants.

---

## 2. Why a window, and why a pool

| Domain | Size | Verdict |
|---|---|---|
| whole-ORF synonymous | ~10²⁷³ (551 codons, 535 with synonyms) | not a domain any optimizer can search |
| 30-codon 5′ window, free GC | ~10¹³·² | still not enumerable; must be sampled into a pool |
| 30-codon 5′ window, GC-neutral | ~10³·⁹, about 8,000 variants | **small enough to enumerate exhaustively** |

Window-size scaling, computed from the real ORF: 20 codons ~10⁹·¹, 30 ~10¹³·², 40 ~10¹⁹·¹,
50 ~10²³·⁴.

**The 5′ region and the 30-codon width are declared choices, not findings.** The region is
the one usually implicated in initiation; nothing in this project shows 5′ edits matter more
than edits elsewhere, and the config says so in capitals. A different window gives a
different space.

**Rejected alternatives**, recorded in the config: codon-usage targets (low-dimensional and
GP-friendly, but per-site control is lost and the knobs are themselves confounded with
structure) and whole-ORF random synonymous sampling (simplest, least interpretable, changes
a dozen things at once).

---

## 3. The reference ORF

`data/constructs/fluc_orf.txt`, 1,653 nt, 551 codons.

- Starts `ATG GAG GAC GCC AAG AAC …`, protein begins **MEDAKNIKKG**, ends `GTG TGA`.
- Reference ORF longest homopolymer run: **exactly 6**.
- Reference window (codons 1–30) GC fraction: **0.6667**, which is the **highest value in
  the free-mode pool** — see §6.
- UTRs and poly(A) are **not** part of the design space and are held exactly as the
  collaborator supplied them.

---

## 4. Specification

`configs/synonymous_window_design_space_v1_2026-10-20.json`.

### 4.1 Window

Codons **1–30 inclusive, zero-based** (ORF nt 4–93).

- **Position 0 excluded:** AUG is its own only synonym, so changing it is not a synonymous
  edit in any case.
- **Terminator excluded:** its substitutions change the stop identity, and the tandem-stop
  arrangement (ORF ends `TGA`, 3′UTR begins `TAA`) is a deliberate design the collaborator
  confirmed, not something to vary.

### 4.2 Constraints, all checked on every member

| Constraint | Value |
|---|---|
| protein preserved exactly | checked by translating the full ORF and comparing |
| length unchanged | yes |
| changes confined to the window | yes |
| start codon unchanged | yes |
| stop codon unchanged | yes |
| no internal in-frame stop | guaranteed by synonymous substitution, checked anyway |
| max homopolymer run | **6** |

**Why 6:** the reference's own longest run is exactly 6, so the bound admits the reference
and rejects anything worse than it. It is a **no-regression bound, not a literature
threshold**, and the config says so.

**Failures are discarded and counted by cause, never repaired**, so a pool cannot contain a
silently corrected sequence.

### 4.3 Deliberately not constrained, and why

- **Restriction sites** — no cloning strategy has been stated, so no site list can be
  justified.
- **Out-of-frame AUG creation** — plausible as a concern but speculative here; naming the
  gap beats inventing a constraint.
- **Local 5′ secondary structure** — constraining it would bake a structural prior into the
  domain, which is the optimizer's job to explore, not the generator's to presuppose.

---

## 5. Implementation

### 5.1 `src/rnastable/synonymous_window.py`

`codon_table`, `synonyms`, `split_codons`, `translate`, `window_indices`,
`longest_homopolymer`, `check_variant`, `describe`, `build_pool`.

- The codon table is built once from Biopython's standard code (id 1) with stops mapped to
  `*`, rather than retyped here. Synonym groups are in deterministic sorted order.
- `split_codons` validates a complete reading frame: multiple of three, ACGT only, starts
  with a start codon, ends with a stop, no internal in-frame stop. Accepts RNA spelling.
- `check_variant` **returns a reason rather than raising**, which is what lets the sampler
  count rejections by cause and makes a pool's composition auditable.
- `describe` records composition only — substituted indices, counts, window GC, ORF GC, GC3,
  longest homopolymer, ORF sha256. **No score and no feature vector**; a test asserts no key
  contains `score`, `objective`, `feature`, `rank` or `predicted`.
- `build_pool` seeds `random.Random(seed)` locally; a test asserts the caller's **global**
  RNG state is untouched.

### 5.2 Sampling rule, and why it is not per-position independent

Per member: draw the number of substituted positions **uniformly over 1..substitutable**,
then which positions without replacement, then a codon different from the reference at each.

**The first attempt drew a codon independently per position and was wrong.** With 29
substitutable positions, almost every member changed **14 to 19** of them, so the pool had
nothing near the reference. Edit distance to the reference is the axis most likely to matter,
so it is sampled evenly rather than left to emerge. After the fix, substitution counts span
**0–29 with all 30 distinct values present**.

### 5.3 GC decorrelation

A GC tendency is drawn **once per member, independent of the edit count**, and shared across
that member's substitutions, so the pool spans the GC range at every edit distance. This
moved the confound from r = −0.9837 to −0.8777 — it helps, and it does not fix the problem,
for the reason in §6.

---

## 6. The GC confound — measured, and partly irreducible

| Mode | window GC | Pearson r, substitutions vs window GC |
|---|---|---|
| free, no decorrelation | 0.3444 – 0.6667 | **−0.9837** |
| free, with decorrelation | 0.3444 – 0.6667 | **−0.8777** |
| neutral | **0.6667 constant** | undefined (constant) |

**Why sampling cannot fix free mode.** The reference 5′ window is **GC-maximal for this
protein segment**: its GC fraction of 0.6667 is the highest in the pool, so every synonymous
edit moves GC down or sideways. The correlation is a property of editing away from a
GC-optimised reference, not a sampler artifact. A test pins both the sign of the correlation
and the fact that the reference is the pool maximum.

**Consequence, binding:** in free mode, **edit distance and GC content cannot be separated**.
Any effect attributed to one could be the other, and no analysis of a free-mode pool may
claim otherwise.

**Neutral mode** restricts substitution to synonyms with the same GC count as the reference
codon. Window GC is then held **exactly constant**, removing the confound by construction.
Cost: **13 of 30 positions** have an equal-GC alternative instead of 29, edit distance spans
**0–13**, and the space is ~8,000 variants.

**Which mode is primary is NOT DECIDED.** Both pools are built and recorded so the choice
rests on these measurements rather than being made before them. This is the first open
decision in §9.

---

## 7. Artifacts

- Driver: `scripts/build_synonymous_window_pool.py`
- Run: `results/synonymous_window_pool_runs/20261020T172950.906827Z/`
  - `summary.json`, `pool_free.json`, `pool_neutral.json` (2.2 MB total)

| Mode | n | subs | window GC | r | substitutable | rejected | verification failures |
|---|---|---|---|---|---|---|---|
| free | 512 | 0–29 | 0.3444–0.6667 | −0.8777 | 29 | homopolymer 93, duplicate 8 | **0** |
| neutral | 512 | 0–13 | 0.6667 constant | constant | 13 | duplicate 173 | **0** |

The driver **re-verifies every member itself** rather than trusting the generator: protein
identity, length, changes confined to the window, the homopolymer bound, and the recorded
sha256 recomputed from the sequence; plus pool-level uniqueness and that member 0 is the
unmodified reference. **It refuses to write a pool if any check fails.**

`scored: false`, `optimizer_features_emitted: false`,
`candidates_proposed_for_assay: false`.

---

## 8. Verification actually run

| Check | Outcome |
|---|---|
| `scripts/build_synonymous_window_pool.py --dry-run` | both modes, 0 verification failures |
| `scripts/build_synonymous_window_pool.py` | exit 0; wrote 3 files |
| `pytest -q tests/test_synonymous_window.py` | 26 passed |
| `pytest -q tests/test_synonymous_window_pool_run.py` | 18 passed |
| `ruff check` on the four new files | All checks passed |
| **Full suite** | **1394 passed, 38 skipped** in 136.31 s |

Suite arithmetic: 1350 (V2) → 1394 with the 44 tests added here (26 + 18). The 38 skips are
unchanged and remain the retired-checkpoint replays.

### Not verified / not claimed

- **Nothing was scored.** No structure, stability or translation value was computed for any
  member, and no optimizer feature matrix was emitted.
- **No member was proposed for an assay.**
- **Protein preservation is verified; nothing else about a member is.** Whether any variant
  folds better, is more stable or translates better is unknown and untested.
- The 30-codon window and the 5′ region are **declared choices, not findings**.
- The ~8,000 figure for neutral mode is an **enumeration count**, not a claim that
  enumerating it is useful.

---

## 9. Open decisions, in priority order

1. **Free or neutral GC mode.** The first and most consequential. Free keeps 29 positions and
   a wider GC range but cannot separate edit distance from GC. Neutral gives a clean,
   exhaustively enumerable ~8,000-variant space at 13 positions. **My recommendation:
   neutral**, because an uninterpretable win on a confounded axis is worth less than a
   smaller clean space, and because 8,000 members can be scored exhaustively so the
   optimizer's job becomes panel selection rather than search.
2. **Whether to score the pool at all yet**, which requires:
   - `new_sequence_scoring_enabled` true — depends on the **unresolved base-pair span
     policy**; the blinded 85-record evaluation set is unspent;
   - a transcript assembly path that accepts a variant CDS. `transcript_assembly.assemble`
     is **hash-gated on the reference CDS and will refuse a variant by design**. That gate
     is correct and must be changed deliberately, not worked around;
   - a reference point on the real objective scales, which does not exist.
3. **Panel size.** The real bound on everything here is how many constructs Ping's lab can
   run in one experiment. That number is still unknown and it should set the pool's role.
4. Carried forward: assay CVs and decision costs; whether Fluc-PEST enters the panel; the
   power convention; the two questions for Ping (5′UTR shortening, parent construct);
   acquiring experimental-structure references in scope; the C++ toolchain for the fused
   qLogEHVI kernel; V12 §6 item 7, the `archive` build re-run.

**No process is running.** Every run completed with exit 0 and wrote a complete artifact.

---

## 10. Exact safe continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai

# Full suite (expect 1394 passed, 38 skipped)
.venv/bin/python -m pytest -q

# Just the design-space work
.venv/bin/python -m pytest -q \
  tests/test_synonymous_window.py \
  tests/test_synonymous_window_pool_run.py

# Rebuild the pools without writing anything
.venv/bin/python scripts/build_synonymous_window_pool.py --dry-run

# A smaller pool, for a quick look
.venv/bin/python scripts/build_synonymous_window_pool.py --size 32 --dry-run

# Re-measure the GC confound in both modes
.venv/bin/python -c "
import sys, statistics; sys.path.insert(0,'src')
from pathlib import Path
from rnastable.synonymous_window import build_pool
cds = ''.join(Path('data/constructs/fluc_orf.txt').read_text().split())
for mode in ('free','neutral'):
    p = build_pool(cds, window_codons=30, size=512, seed=1729, gc_mode=mode)
    x=[m['substitution_count'] for m in p['members']]
    y=[m['window_gc_fraction'] for m in p['members']]
    r = 'constant' if len(set(y))==1 else '%+.4f' % statistics.correlation(x,y)
    print(mode, 'r =', r, 'substitutable', p['substitutable_positions'])"

# Size a different window before changing the declared one
.venv/bin/python -c "
import sys, math; sys.path.insert(0,'src')
from pathlib import Path
from collections import Counter
from rnastable.synonymous_window import split_codons, synonyms, codon_table
cds = ''.join(Path('data/constructs/fluc_orf.txt').read_text().split())
ref, g, t = split_codons(cds), synonyms(), codon_table()
for w in (20, 30, 40, 50):
    counts = [len(g[t[c]]) for c in ref[1:1+w]]
    print(w, 'codons ~10^%.1f' % sum(math.log10(c) for c in counts))"

# Lint (ruff is NOT in the venv)
ruff check src/rnastable scripts tests
```

Writing a pool creates a **new** timestamped directory and never overwrites one
(`mkdir(exist_ok=False)`). The driver exits non-zero rather than writing if verification
fails.

### Publishing

```bash
PUB=/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad/verify
git -C "$PUB" fetch origin && git -C "$PUB" status --short
sha256sum "$PUB/diagram_10182026.png"   # must stay baa831ce16df27ed…
diff "$PUB/README.md" README.md          # merge upstream edits before copying
```

The local repository has **no commits** and its `origin` is the placeholder
`https://github.com/YOUR_USERNAME/RNA-StableAI.git`. Publication goes through the clone
above, with `git -c user.name=zyliu-OU -c user.email=<the user's address> commit`, because
that clone has no committer identity configured.

---

## 11. Published state

| Item | Value |
|---|---|
| Commit before this stretch | `e9d7685` Record the Pareto-formulation commit hash in handoff 2026-10-20 V2 |
| Commit published with this handoff | see §11.1 |
| README picture | `diagram_10182026.png`, `sha256 baa831ce16df27ed44a41c2a3b481455a213b328122227b9b2a3820dda47cff1`, **byte-unchanged**, re-verified before publishing |
| Gate | `configs/stage2_to_stage3_gate_v5_2026-10-20.json`, **unchanged**; not superseded by either the formulation or the design-space config |

The README diagram still reads "0 of 6" because the user supplied that SVG; a caption below
it carries the correction. **Regenerating it needs the user's say-so and has not been done.**

### 11.1 Publication record

This handoff is published in the commit titled *"Specify the optimisation domain as windowed
synonymous 5′ edits and enumerate it into pools"*. Its hash is recorded by the commit
immediately after it, since a file cannot contain the hash of the commit that adds it.
