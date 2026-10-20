# RNA-StableAI — Handoff 2026-10-20 V2

- **Project:** RNA-StableAI
- **Date:** 2026-10-20 (America/Los_Angeles)
- **Version:** V2 (follows [2026-10-20 V1](RNA-StableAI_HANDOFF_2026-10-20_V1.md), which
  recorded the Stage 2 gate review; V1 stands unedited)
- **Workspace:** `/home/zyliu/Documents/rna-stable-ai`
- **Publication clone:** `/tmp/claude-1000/-home-zyliu-Documents-rna-stable-ai/0ee06306-9b85-4f30-b6cb-6f4268e4635e/scratchpad/verify`
- **Remote:** `https://github.com/zyliu-OU/rna-stable-ai.git` — **PUBLIC**
- **Headline:** BoTorch is installed and verified in the pinned integration path, and the
  optimisation objective is now **formulated as a Pareto front over the two score sides**
  by user decision. Mechanics verified on toy objectives. **No RNA was designed, proposed
  or scored, and no gate switch was opened.**

---

## 1. User instructions in this stretch, and what they authorise

| Instruction | Reading | Consequence |
|---|---|---|
| "install botorch" | Install the missing package. | Installed into `.venv`; added to `pyproject.toml` dependencies. |
| "now we have we botorch, whats next? optimization?" | A question, answered: **not a candidate campaign.** BoTorch was a tooling blocker, not the scientific one. | Laid out that there was **no objective function**, and asked for the one decision only the user can make. |
| "Pareto front over both sides" | Choose the multi-objective formulation over single-objective-with-a-floor. | `configs/pareto_objective_formulation_v1_2026-10-20.json`, plus the implementation and mechanics run below. |

**What this does NOT authorise, stated because it is the easy mistake to make here:**
choosing how an objective *would* be formulated is not permission to run a campaign.
`expression_candidate_design_enabled` and `new_sequence_scoring_enabled` remain **false**
in gate v5, which is **unchanged and not superseded** by the formulation config.

---

## 2. BoTorch installation

The venv had **no `pip`**, so it was bootstrapped with `.venv/bin/python -m ensurepip
--upgrade` (pip 25.0.1). `uv` was not available on this machine despite
`external/uv-cache` existing.

Installed under a **torch constraint file** pinning `torch==2.14.1+cu130`, so the resolver
could not silently replace the working CUDA build with a generic wheel. A `--dry-run`
confirmed the plan before installing.

```
botorch 0.18.1   gpytorch 1.15.2   linear_operator 0.6.1
torch 2.14.1+cu130  (unchanged)   Python 3.12.14   ViennaRNA 2.7.2
```

13 packages added, all pure additions: `botorch`, `gpytorch`, `linear_operator`,
`scikit-learn`, `joblib`, `threadpoolctl`, `cloudpickle`, `multipledispatch`, `ninja`,
`pyre-extensions`, `typing-inspect`, `mypy-extensions`, `narwhals`. **torch, numpy, scipy
and pandas were untouched.**

**The resolved versions are exactly those pinned** by
`configs/four_component_build_v1_2026-10-18.json`'s `required_optimizer_versions`
(`botorch 0.18.1`, `gpytorch 1.15.2`, `linear_operator 0.6.1`). This restores the
environment that build ran in rather than a newer one. BoTorch had therefore been present
on 2026-10-19 and was absent by 2026-10-20; **how it was lost was not determined.**

**Known caveat, performance only:** BoTorch logs
`Failed to compile fused qLogEHVI C++ extension: Ninja is required…` and falls back to the
pure-Python implementation (~3× slower). `.venv/bin/ninja` exists, so the missing piece is
a usable C++ toolchain for the extension load, not the package. Results are unaffected;
every figure in this handoff was produced on the fallback path.

### 2.1 Verification of the install in the pinned path

`scripts/build_four_component_integration.py` was run fresh — **not** `--resume`, which
would have written into a frozen run directory.

- Run: `results/four_component_build_runs/20261020T170451.596055Z/`
- The script's own `required_optimizer_versions` check **passed**, which is a real test of
  the install rather than an import smoke test.
- All five folds `ok` (64, 400, 1000, 2000, 2999 nt; 0.011 s to 58.8 s).
- **All three toy seeds reproduced their recorded value exactly:**
  `best_value = 1.0391607991935734` for seeds 7, 1729 and 20261015, matching
  `results/four_component_build_runs/20261019T041458.024816Z/`.

`tests/test_discrete_bo.py` had been skipping via a module-level `pytest.importorskip`;
it now collects and passes (2 tests).

---

## 3. The objective formulation decision

### 3.1 Why a decision was needed at all

BoTorch needs a scalar objective or an explicit multi-objective formulation. The project
had neither:

- stability is in **hours** on the released STRAND in-solution scale;
- translation is on a **released RiboNN task scale** with no inverse transform and no
  physical unit;
- no weighting between them is justified, no floor has been selected, and
  `score_record_schema_v1` **forbids emitting a composite**.

### 3.2 What was chosen, and why it is not an evasion

**A Pareto front over both sides.** Dominance compares objectives **coordinate-wise**, so
it requires neither a shared unit nor a weight, and it never produces a single number
standing for both sides. The formulation therefore **respects** the composite prohibition
rather than routing around it.

**Rejected:** a weighted sum or any other scalarisation, because the weights would be
arbitrary and would silently encode an unjustified trade-off. Also single-objective with a
floor on the other side, because that floor is a number that does not exist yet.

### 3.3 Frozen record

`configs/pareto_objective_formulation_v1_2026-10-20.json` records: the decision and who
made it; both objectives with quantity, unit, direction, source and caveat; the method; the
reference-point policy; the hypervolume prohibition; the current mechanics-only scope; five
blocking items; and what it does not change.

| Objective | Quantity | Unit | Direction | Caveat recorded |
|---|---|---|---|---|
| 0 stability | in-solution half-life of purified RNA in buffer | hours | maximize | **not** in-cell decay by RT-qPCR; the calibration refit is unpublished and unvalidated |
| 1 translation | predicted translational efficiency | released RiboNN task scale, no inverse transform | maximize | **not** luminescence from a designed reporter; the CD3+ T-cell arm is model-blind |

---

## 4. Implementation

### 4.1 `src/rnastable/pareto.py`

Pure-Python bookkeeping: `as_maximization`, `dominates`, `non_dominated_indices`,
`pareto_front`, `hypervolume_2d`.

- **Imports neither torch nor botorch**, so dominance and hypervolume are auditable
  without the optimizer. `tests/test_pareto.py` enforces this by walking the module's AST
  rather than grepping its text (the docstring legitimately mentions botorch).
- Direction is **explicit per objective**; the maximization flip happens once, in one
  place, so a sign error cannot hide inside the comparison logic.
- Equal points **do not** dominate each other, so a front keeps ties rather than
  discarding one arbitrarily.
- `hypervolume_2d` is exact by sweep; points failing to beat the reference contribute
  **zero**, not a negative area, which a naive sweep would produce.

### 4.2 `src/rnastable/multi_objective_bo.py`

`select_next_pareto` and `run_toy_pareto`, mirroring `discrete_bo.py`'s contracts so both
paths fail the same way on the same bad input.

| Setting | Value | Why |
|---|---|---|
| acquisition | `qLogNoisyExpectedHypervolumeImprovement` | the Pareto-native acquisition |
| model | `ModelListGP` of **independent** `SingleTaskGP` | a multi-output model would impose a stability/translation correlation **nothing in this project establishes** |
| noise variance | 1e-6 | matches `discrete_bo.py` |
| fit maxiter | 50 | matches `discrete_bo.py` |
| domain | finite pool, `optimize_acqf_discrete` | matches `discrete_bo.py` |
| determinism | `torch.manual_seed` inside `torch.random.fork_rng(devices=[])` | preserves the caller's RNG state |
| reference point | **required**, never inferred | hypervolume only compares across runs sharing a reference; `infer_reference_point` would drift with the observations |

`run_toy_pareto` reports `pareto_indices`, `pareto_front`, `hypervolume` and a
same-budget random baseline. **It reports no `best_value`** — with two incommensurable
objectives there is none, and inventing one would be the forbidden composite.

The toy objectives **conflict on purpose**: the first peaks near 0.73, the second falls
monotonically, so no point maximises both. A pair that agreed would pass the mechanics
without exercising a trade-off.

---

## 5. Mechanics run

- Script: `scripts/run_pareto_mechanics.py`
- Artifact: `results/pareto_mechanics_runs/20261020T171040.511872Z/summary.json`
- Pool 31 members, 25 feasible (0.40–0.60 excluded), fixed initial design `[0, 10, 30]`,
  budget 8 unique evaluations, reference point `(0.0, 0.0)`.
- The driver **refuses to start** if the gate has opened a campaign switch.

| Seed | front size | hypervolume | random hypervolume |
|---|---|---|---|
| 7 | 7 | 0.906181 | 0.892258 |
| 1729 | 7 | 0.906181 | 0.867321 |
| 20261015 | 7 | 0.906181 | 0.861925 |

`all_fronts_non_dominated: true`, `all_resumes_reproduced: true`,
`optimizer_ahead_of_random_on_every_seed: true`.

**The three seeds are not three independent confirmations, and the artifact says so.** The
optimizer selects the *identical* points on every seed (`distinct_optimizer_hypervolumes:
1`, `distinct_optimizer_histories: 1`). With 25 feasible members and a fixed 3-point
initial design the acquisition ordering is effectively determined, and the fit seed does
not change it; only the random baseline varies. This shows the mechanics are stable on
this pool. **It does not demonstrate robustness to seed on a larger domain.**

An earlier run of the same script was deleted and the script re-run once, to add the
`seed_sensitivity` field before any artifact was published. No published artifact was
edited.

---

## 6. Verification actually run

| Check | Outcome |
|---|---|
| `.venv/bin/python -m pip install --dry-run -c <constraint> botorch` | plan confirmed; torch untouched |
| `.venv/bin/python -m pytest -q tests/test_discrete_bo.py` | 2 passed (previously skipped) |
| `.venv/bin/python scripts/build_four_component_integration.py` | exit 0; version gate passed; 3/3 seeds reproduced exactly |
| `.venv/bin/python -m pytest -q tests/test_pareto.py` | 15 passed |
| `.venv/bin/python -m pytest -q tests/test_multi_objective_bo.py` | 16 passed |
| `.venv/bin/python -m pytest -q tests/test_pareto_mechanics_run.py` | 14 passed |
| `.venv/bin/python scripts/run_pareto_mechanics.py` | exit 0 |
| `ruff check` on all six new/changed files | All checks passed |
| **Full suite** | **1350 passed, 38 skipped** in 137.14 s |

Suite arithmetic: 1303 → 1305 on the botorch install (`importorskip` was one
collection-time skip becoming two passing tests, so skips 39 → 38) → 1350 with the 45
tests added here (15 + 16 + 14). **All 38 remaining skips were individually confirmed to
be retired-checkpoint replays**, listed by `pytest -q -rs`; no BoTorch skip remains and
nothing else became skipped.

### Not verified / not claimed

- **No RNA was designed, proposed or scored.** The objectives are mathematical functions.
- A toy mechanics run is **software verification, not biological evidence**.
- A hypervolume improvement over random on a toy objective **says nothing about RNA**.
- The reference point `(0.0, 0.0)` is meaningful **for the toy objectives only**.
- Hypervolume is a diagnostic of a **set** and must never be attached to a candidate as
  its score — that would be the composite reached by a different route.

---

## 7. What blocks a real campaign

Recorded in the formulation config under `blocking_before_a_real_campaign`.

1. **Design-space parameterisation — not decided.** The Fluc ORF is 1,653 nt, **551
   codons, 535 of them with synonyms**, giving **~10²⁷³** synonymous variants
   (distribution: 16 codons with 1 option, 204 with 2, 40 with 3, 192 with 4, 99 with 6).
   A one-hot encoding over all positions is **not a tractable BO domain**. A reduced
   parameterisation — codon-usage targets, windowed edits, or a finite candidate pool —
   must be chosen and frozen first. Computed from `data/constructs/fluc_orf.txt` with the
   standard genetic code.
2. **Reference point on the real scales — not decided.** Requires the measured assay
   scales.
3. **Base-pair span policy — unresolved.** `new_sequence_scoring_enabled` is false; `alo`
   moves ~3× tolerance from the clipping convention alone; the **blinded 85-record
   evaluation set is unspent** and should stay so until the policy is decided.
4. **Assay side — not available.** Measured CVs for both readouts; the decision cost of a
   false accept against a false reject; whether Fluc-PEST enters the panel.
5. **Proxy quality — known limitation.** The objectives rest on structure at 0.42–0.44
   pair F1 against computational consensus, feeding two proxies that predict neither of
   the assay's units. Optimising hard against a weak proxy produces candidates that win on
   the metric and not in the cell. See `reports/remaining_limitations_addendum_2026-10-20.md`
   §N5.

Also outstanding, carried from V1: the power convention (`lognormal_exact` vs `log1p_cv`);
questions for Ping about the 5′UTR shortening and the parent construct; acquiring
experimental-structure references in scope (the only proper cure for requirement 1 and the
band); V12 §6 item 7, re-running the `archive` build.

**No process is running.** Every run completed with exit 0 and wrote a complete artifact.

---

## 8. Exact safe continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai

# Full suite (expect 1350 passed, 38 skipped)
.venv/bin/python -m pytest -q

# Just the optimizer work
.venv/bin/python -m pytest -q \
  tests/test_pareto.py \
  tests/test_multi_objective_bo.py \
  tests/test_pareto_mechanics_run.py \
  tests/test_discrete_bo.py

# Re-run the Pareto mechanics without writing anything
.venv/bin/python scripts/run_pareto_mechanics.py --dry-run

# Confirm the remaining skips are all retired-checkpoint replays
.venv/bin/python -m pytest -q -rs | grep '^SKIPPED'

# Re-verify the install in the pinned path (writes a NEW run directory; ~90 s)
.venv/bin/python scripts/build_four_component_integration.py

# Re-size the synonymous design space
.venv/bin/python -I -c "
from pathlib import Path
from collections import Counter
import math
from Bio.Data.CodonTable import unambiguous_dna_by_id
seq = ''.join(Path('data/constructs/fluc_orf.txt').read_text().split()).upper().replace('U','T')
t = unambiguous_dna_by_id[1]
fwd = dict(t.forward_table) | {s: '*' for s in t.stop_codons}
syn = Counter(fwd.values())
counts = [syn[fwd[seq[i:i+3]]] for i in range(0, len(seq)-2, 3)]
print(len(counts), 'codons;', sum(c>1 for c in counts), 'with synonyms; ~10^%.0f' %
      sum(math.log10(c) for c in counts))"

# Lint (ruff is NOT in the venv; it resolves to /home/zyliu/anaconda3/bin/ruff)
ruff check src/rnastable scripts tests
```

`scripts/run_pareto_mechanics.py` without `--dry-run` writes a **new** timestamped
directory and never overwrites one (`mkdir(exist_ok=False)`).

### If BoTorch goes missing again

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python -m ensurepip --upgrade
printf 'torch==2.14.1+cu130\n' > /tmp/torch-constraint.txt
.venv/bin/python -m pip install --dry-run -c /tmp/torch-constraint.txt botorch   # inspect first
.venv/bin/python -m pip install -c /tmp/torch-constraint.txt botorch
```

The constraint matters: without it the resolver may replace the CUDA build. The
four-component build pins `botorch 0.18.1 / gpytorch 1.15.2 / linear_operator 0.6.1` and
will refuse to run on anything else, so a newer resolution breaks that protocol.

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

## 9. Published state

| Item | Value |
|---|---|
| Commit before this stretch | `415d081` Record the gate-review commit hash in handoff 2026-10-20 V1 |
| Commit published with this handoff | see §9.1 |
| README picture | `diagram_10182026.png`, `sha256 baa831ce16df27ed44a41c2a3b481455a213b328122227b9b2a3820dda47cff1`, **byte-unchanged**, re-verified before publishing |
| Gate | `configs/stage2_to_stage3_gate_v5_2026-10-20.json`, **unchanged**; not superseded by the formulation config |

### 9.1 Publication record

This handoff is published in the commit titled *"Install BoTorch and formulate the
optimisation objective as a Pareto front over both score sides"*. Its hash is recorded by
the commit immediately after it, since a file cannot contain the hash of the commit that
adds it. Run `git -C "$PUB" log --oneline -3` to see both.
