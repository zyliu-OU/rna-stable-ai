# Why the learned structure model loses to native folding — diagnosis — 2026-10-20

- **Project:** RNA-StableAI
- **Workspace:** `/home/zyliu/Documents/rna-stable-ai`
- **Question:** Stage 2 gate requirement 4,
  `Demonstrate_credible_structure_accuracy_with_explicit_review_of_native_baseline_gaps`,
  is `not_satisfied` because the learned model sits below both native controls.
  Is that gap closable by modelling work?
- **Answer:** **Not at the current data scale.** The loss is localised to pair
  scoring, it is not a decoding or threshold artifact, and the model is
  *relatively worse* where the reference labels are most trustworthy.
- **Nothing was trained, fitted or promoted.** This is analysis of existing
  frozen runs only.

---

## 0. A clarification worth stating first

The project contains **two separate workstreams that both involve folding**, and
conflating them causes confusion:

| | Engine | Status |
|---|---|---|
| **mRNA design stack** | **ViennaRNA directly** (2.7.2, Turner 2004) | In use. Folded `FLUC-REF-V1`, produced `strand_alo`/`aup`, fed the score record |
| **Learned structure prediction** | a trained pair model, with LinearFold/ViennaRNA as controls to beat | The subject of the Stage 2 gate |

**The mRNA stack does not use the learned model.** Verified: nothing in
`component_integration.py`, `transcript_assembly.py`, `score_records.py`,
`ensemble_worker.py`, `fold_reference_transcript.py` or
`build_reference_score_record.py` imports it. The two are independent.

So the gate's requirement 4 concerns a model that the production path does not
depend on, and which is currently outperformed by the engine that path already
uses.

---

## 1. The gap, measured

### Rfam-consensus long references (6 records, 1,000–2,999 nt)

| Method | mean pair F1 |
|---|---:|
| **LinearFold** | **0.4381** |
| **ViennaRNA** | **0.4215** |
| learned, `extended_105_top32` (best) | 0.2965 |
| learned, `control_88_top16` | 0.2537 |

*Source:* `results/stage2_under3000_audit_runs/20261018T223708.786045Z/summary.json`.

### Structure-derived references (10 records, 6 families)

| Method | pair precision | pair recall | **pair F1** | % of native |
|---|---:|---:|---:|---:|
| **LinearFold** | 0.6647 | 0.6011 | **0.6261** | — |
| **ViennaRNA** | 0.6647 | 0.6011 | **0.6261** | — |
| `helix` (best learned head) | 0.3082 | 0.3464 | **0.3255** | **52%** |
| `stack` | 0.1373 | 0.1437 | 0.1402 | 22% |
| `baseline` | 0.1179 | 0.1312 | 0.1236 | 20% |
| `all_unpaired` | 0.0000 | 0.0000 | 0.0000 | 0% |

*Source:* `results/raw_structure_feasibility_runs/20261015T025936.192087Z/summary.json`.

Note that **LinearFold and ViennaRNA produce identical F1** here. Both are
Turner-model thermodynamic folders and they agree completely, so the learned
model is not supplying an orthogonal signal that the controls lack — it is
supplying a worse version of the same thing.

---

## 2. The loss is in pair scoring, not candidate generation or decoding

`results/under3000_recovery_ceiling_runs/20261018T234344.201186Z` already
decomposes where the true pairs go. Long cohort, 18 record-seed rows:

| Quantity | Value |
|---|---:|
| Actual model F1 | 0.3174 |
| Oracle F1 over all legal gold pairs | **0.9606** |
| Oracle F1 within retained candidates | **0.8257** |
| Candidate legal-gold recall (micro) | 0.7618 |
| Model recovery of TPs present in its own candidate pool | **0.4595** |

Attribution of missed gold pairs:

| Cause | Fraction |
|---|---:|
| **Score selection gap** | **56.6%** |
| Retained candidate limit | 32.8% |
| Unsupported gold (unrepresentable) | 10.6% |
| Legal/non-crossing limit | 0.0% |

**Reading:** the labels are reachable in principle (oracle 0.96). Candidate
generation retains 76% of legal gold pairs, capping achievable F1 at 0.83. The
model then reaches only 0.32, recovering **under half** of the true pairs that
are *already sitting in its own candidate list*. The majority of the loss —
**56.6%** — happens at scoring.

### It is not a threshold or over-prediction artifact

A natural hypothesis is that the decoder emits too many pairs and a better
threshold would fix the precision. It does not:

| Quantity, long cohort (18 rows) | Value |
|---|---:|
| predicted / reference pair-count ratio | **1.056** (range 0.959–1.194) |
| mean precision | **0.311** |
| mean recall | **0.325** |

The model predicts **about the right number of pairs**, and precision and recall
are nearly equal. There is no precision/recall imbalance to trade away.
**Re-thresholding or re-calibrating the decode cannot recover the gap** — the
decoder picks the wrong pairs, not too many of them.

This rules out the cheapest possible fix.

---

## 3. The model is relatively worse where the labels are most trustworthy

| Reference set | Learned best | Native | Learned as % of native |
|---|---:|---:|---:|
| Rfam-consensus long refs | 0.2965 | 0.4381 | **68%** |
| Structure-derived refs (6 families) | 0.3255 | 0.6261 | **52%** |

The learned model closes more of the gap against **Rfam consensus** references
than against **structure-derived** ones. If the model had learned general RNA
secondary structure, the relationship would not be expected to run this way.

The pattern is consistent with the model having partly fit characteristics of
Rfam consensus annotation rather than physical structure. This is a **hypothesis
consistent with the numbers, not a demonstrated mechanism** — two reference sets
of different composition is weak evidence, and the cohorts differ in family and
length as well as in label provenance.

---

## 4. The binding constraint looks like data scale

`results/family_pair_set_training_runs/20261016T012741.486402Z`:

```
train_records            61
validation_records       22
train_positive_pairs      1,235
train_negative_pairs    216,942       (176:1 imbalance)
training_max_length       1,024 nt
```

Sixty-one structures, carrying 1,235 positive pairs in total, is a very small
training set for learning RNA secondary structure. The comparison is against
Turner-model folders encoding decades of optical-melting thermodynamics.

Supporting evidence that the limit is not architecture or supervision design:

- **Three heads tried** — `helix`, `stack`, `baseline` — all below native, with
  `helix` best at roughly half of native on structure-derived references.
- **Auxiliary supervision**: partner/null supervision moved 0.3174 → 0.3262 on
  the long cohort, a gain of **0.009**, with a short-cohort **regression in one
  of three seeds**.
- **Endpoint ranking** was mixed; a **hard-negative mixture regressed** against
  its matched control.
- **Label provenance is itself uncertain**: 83 of 136 records still lack
  confirmed family assignments, and every in-scope reference is a computational
  Rfam consensus rather than an experimental structure.

Several independent attempts to improve scoring have produced changes at the
level of ~0.01 F1, against a gap of ~0.13 to the nearest control and ~0.30 on
structure-derived references.

---

## 5. What this means for requirement 4

Requirement 4 asks for **credible structure accuracy with explicit review of
native baseline gaps**. On the present evidence:

1. The learned model is **below both native controls on every cohort measured**,
   by 32% relatively on Rfam consensus and 48% on structure-derived references.
2. The deficit is **not** recoverable by decoding, thresholding or calibration —
   those were tested and excluded here.
3. The remaining headroom is real in principle (0.32 → 0.83 within the existing
   candidate pool) but sits entirely in **pair scoring quality**, which is the
   component most constrained by the 61-record training set.
4. Multiple prior supervision and ranking variants moved F1 by ~0.01.

**A session of modelling work will not close this gap.** Closing it would require
substantially more labelled structure data — ideally experimental rather than
consensus — which is an acquisition programme, not a training run.

### Options, for a decision rather than a recommendation to act on silently

| | Option | What it costs | What it gives |
|---|---|---|---|
| **A** | **Amend requirement 4 by gate review** to reference native controls, recording that the learned model is retired or demoted to research | A gate amendment; abandons learned-model upside | Honest, immediate; the mRNA stack already uses ViennaRNA and loses nothing |
| **B** | Acquire substantially more structure data, then retrain | An acquisition programme of unknown length | The only route that could genuinely satisfy requirement 4 as written |
| **C** | Keep requirement 4 unsatisfied indefinitely | Stage 3 stays closed | Nothing changes |

**Recommendation: A.** The requirement as written asks the project to demonstrate
something the evidence says is not currently true, for a component the production
path does not use. Amending it to reference the native controls — which *do*
achieve 0.63 on structure-derived references — would state the real capability
accurately. Option B remains open as future work and is not foreclosed by A.

**This is a scope decision and has not been taken.** Requirement 4 remains
`not_satisfied`, and nothing in this document changes any flag.

---

## 6. What must not be claimed

- **Nothing was trained, fitted, tuned or promoted.** This is analysis of frozen
  runs; `model_defaults_changed` remains false.
- **Not** that the learned model cannot work — only that it does not now, and
  that the gap is not closable by decoding, thresholding, or marginal
  supervision changes at 61 training records.
- The claim in §3 that the model partly fit consensus annotation is a
  **hypothesis consistent with two cohorts**, not a demonstrated mechanism. The
  cohorts differ in family and length as well as label provenance.
- Native controls reaching 0.6261 on structure-derived references is **not** a
  claim of biological validation; that cohort is a six-family feasibility set and
  its own run records `broad_validation_gate_satisfied: false` and
  `independence_certified: false`.
- The oracle figures (0.9606, 0.8257) are **label-informed upper bounds**, not
  model accuracy, and are explicitly flagged in their own run as
  `oracle_is_model_prediction: false`.
- Requirement 4 is **not satisfied**, and `requirements_satisfied` remains **1 of
  6**. No floor is frozen; sequence scoring and candidate design remain disabled.
