# RNA-StableAI

![RNA-StableAI four-component workflow: the transcript sequence feeds RNAfold and RiboNN; published STRAND is reference-only replay and substituting RNAfold features into it was rejected; a separately named calibration refit is unpublished and unvalidated; RiboNN contributes A549 ranking only; the three paths converge into versioned score records, whose composite score is blocked on incommensurable units with no floor selected; BoTorch and the transfected-cell assay in A549 and CD3+ T cells sit behind the Stage 2 to stage 3 gate, which is open with 0 of 6 requirements met](workflow_10192026.svg)

*Implementation state on 2026-10-19: green paths run and are replayed, red paths are
rejected or blocked, grey paths sit behind the open Stage 2 gate. No stability, translation or
expression benefit is established by any path shown. The earlier proposed-workflow
picture is retained at [diagram_10182026.png](diagram_10182026.png).*

*The diagram predates the 2026-10-20 gate review and still shows 0 of 6 requirements
met. [Gate v5](configs/stage2_to_stage3_gate_v5_2026-10-20.json) now records 6 of 6 —
two of them satisfied by accepting a documented limitation rather than by improving the
data. The grey paths behind the gate are **not** switched on by that review: candidate
design, new-sequence scoring and the assay all remain disabled.*

Research prototype for RNA structure prediction, constrained sequence optimization,
and reproducible folding benchmarks. Code, experimental checkpoints, input data,
and results are available for inspection. No validated release yet.

**Current development focus: RNA sequences shorter than 3,000 nt (1–2,999 nt).**
The selected architecture is **LinearFold / ViennaRNA → STRAND + RiboNN + BoTorch**;
component integration and independent structure validation remain active within
that range.

> **The learned pair model was retired on 2026-10-20.** It scored below both
> native controls on every cohort measured — 0.2965 against LinearFold 0.4381 on
> Rfam-consensus long references, and 0.3255 against 0.6261 on structure-derived
> references — and the production path never used it. Structure now comes from
> LinearFold and ViennaRNA. Its trained checkpoints were deleted; every run
> metric is retained, so the evidence behind the decision stays auditable. The
> learned-model results reported further below are **historical records of that
> retired component**, not current capability. See the
> [gap diagnosis](reports/structure_model_gap_diagnosis_2026-10-20.md) and
> [gate v4](configs/stage2_to_stage3_gate_v4_2026-10-20.json), carried forward in
> [gate v5](configs/stage2_to_stage3_gate_v5_2026-10-20.json).
Existing work at 3,000 nt and above, including 5,000/10,000-nt studies, is preserved as
deferred work; they are not deleted or counted as
active-scope validation. Method-specific lower limits still apply. See the
[sequence-length policy](docs/LENGTH_SCOPE.md).

## Development plan

Updated October 18, 2026. **Active work: validate and improve Stage 2 below 3,000 nt before Stage 3.**
Independent biological validation remains a separate, unresolved release gate.

| Step | Work | Progress |
|---:|---|---|
| 1 | Reproducible foundations | Implemented: bounded native tools, request journals, input hashes, exposure tracking, and replay audits. |
| **2** | **Structure validation and component integration** | **Current priority: independent validation below 3,000 nt and the RNAfold + STRAND + RiboNN + BoTorch architecture.** Fixed-input folding, STRAND reference fitting, RiboNN pretrained inference and toy optimizer replay are implemented. RNAfold-to-STRAND compatibility and independent biological validation remain open; Stage 3 is queued. Historical custom-model studies remain controls; defaults are unchanged. |
| 3 | RNA sequence optimization for stability and protein expression | Queued after Stage 2: protein-preserving design for **transfected-cell expression**, with synonymous-only ORF edits, measured protein output and time-matched RNA abundance. Expression benefits remain unverified. |
| 4 | Independent structure validation | Open release gate. Three prospective panels and a six-family raw-contact feasibility study evaluated; broader coverage/provenance remain limited. |
| 5 | Length evidence and deferred 3,000+ nt work | Independent validation below 3,000 nt is needed, especially at 2,000–2,999 nt. New work at 3,000 nt or above is deferred; historical benchmarks remain preserved. Current full-pair training is capped at 1,024 nt. |
| 6 | Measured stability and function | Public-assay pilot complete. Controlled mutation effects and retained function remain pending. |
| 7 | Validated release | Pending the scientific evidence above. |

### Selected architecture and implementation status

| Component | Role | Current status |
|---|---|---|
| RNAfold / ViennaRNA | Structural and ensemble features | Fixed-input MFE and partition-function checks through 2,999 nt passed. |
| STRAND | In-solution stability proxy | Released-reference PLS fit and coefficient replay passed. Its original features use **LinearPartition**; substituting RNAfold features into the unchanged published model was **rejected** under a prespecified criterion, because the ALO feature is not reproducible across engines. |
| strand_rnafold_calibration_v1 | Separately named RNAfold-feature refit | PLS refit on RNAfold ensemble features. Clears a prespecified minimum-competence bar on 13 project-exposed held-out records. **Not published STRAND, and not independently validated.** |
| RiboNN | Translation proxy for annotated mRNA | Human pretrained inference replay passed using 50 checkpoints across ten folds. Scores remain on the released task scale, uncalibrated to the assay. `predicted_TE_A549` is selected for the A549 arm for ranking and correlation only; the activated CD3+ T-cell arm is declared **model-blind**, because no released task matches it. |
| BoTorch | Feasible candidate selection | Discrete toy-objective budget, caching and resume checks passed; biological candidate optimization remains queued. |

The diagram above shows implementation state, including rejected and gated paths.
The Stage 3 target was amended on 2026-10-19 to **transfected-cell expression**,
replacing the earlier cell-free target. No candidate benefit or complete
biological pipeline is established. See the [integration guide](docs/four_component_integration_2026-10-18.md)
and [publication evidence](reports/component_integration_publication_2026-10-18/README.md).
The public snapshot contains code, portable tests and concise summaries; full
local run artifacts, datasets, model weights and installed environments are not
bundled. Original third-party [source](docs/third_party/RiboNN_LICENSE.txt) and
[weight-license terms](docs/third_party/RiboNN_MODEL_WEIGHTS_LICENSE.txt) are retained.

### 2026-10-20: the learned model retired, and the Stage 2 gate reviewed

The learned pair model was retired (see the note at the top), and the gate requirements
were then reviewed against the components the project actually relies on. Recorded in
[gate v5](configs/stage2_to_stage3_gate_v5_2026-10-20.json), which supersedes v4 and
leaves it frozen and unedited.

| # | Requirement | Outcome |
|---:|---|---|
| 1 | Frozen independent, family/clan-separated validation | **Accepted as a documented limitation.** Separation is satisfied by construction — thermodynamic folders have no training set, so there is no exposure to separate from — but the cohort is 6 in-scope records across 3 families and 2 clans, every one a computational Rfam consensus. There is no experimental-structure reference in scope. That is a data-acquisition problem no run can close. |
| 2 | Accuracy and failures by length band and family | **Satisfied on evidence.** Both native controls reported by band, family and clan across three cohorts: 0.4381 / 0.4215 mean pair F1 on the in-scope long references, 0.3301 / 0.3346 short, 0.6261 / 0.6261 structure-derived. |
| 3 | Resolve sparse 2,000–2,999 nt coverage | **Accepted as a documented limitation in v3**, and expanded here from 1 record to 5 with native controls: LinearFold 0.5273 ± 0.0805, ViennaRNA 0.5056 ± 0.1116. The frozen selection was not modified. All 5 are RF02540, so the cohort carries dispersion but no family contrast of its own. |
| 4 | Credible accuracy from the relied-upon native controls | **Satisfied on evidence,** with the baseline gaps reviewed explicitly. About 0.42–0.44 pair F1 against computational consensus is credible for a published thermodynamic folder; it is not a strong structural result, and it is the quality of the *input* to STRAND and the optimiser. |
| 5 | Constraint-decoder, resource and replay checks | **Re-scoped onto the native path, then satisfied.** Its replay leg reloaded learned-model checkpoints that no longer exist. On the native path: 22/22 folds reproduce the frozen structure *and* MFE exactly, 22/22 constrained folds honour every enforced pair, both tools refuse an unsatisfiable constraint, and the worst case is 8.18 s and 101 MiB against limits of 30 s and 4 GiB. The learned-model leg is **not** restored. |
| 6 | Document remaining limitations | **Satisfied on evidence.** The [2026-10-19 document](reports/remaining_limitations_before_candidate_design_2026-10-19.md) stands unedited, extended by an [addendum](reports/remaining_limitations_addendum_2026-10-20.md) covering the retirement's cost, the re-scope, the band correction and the absent optimiser. |

Two corrections belong in the record. The band's availability was overstated: the census
counted 55 further eligible records, but selection checks the per-family cap *before*
attempting to bind a pair reference, so none had been binding-tested — **only 5 of the 55
bind.** And ViennaRNA 2.7.2 **silently drops** an enforced pair that violates the minimum
hairpin size, folding without it and returning a finite energy; the constrained worker now
verifies every enforced pair against the returned structure rather than trusting the tool.

Six of six satisfied does not mean the structure evidence is strong. Two are satisfied by
narrowing what may be claimed. `stage3_ready` is true; candidate design, new-sequence
scoring and the assay remain disabled, each behind its own decision.

**BoTorch restored, and the objective formulated as a Pareto front.** `botorch 0.18.1`
is installed — the versions the four-component build pins — and a fresh integration build
reproduces its three toy seeds exactly (`best_value 1.0391607991935734`). The optimizer is
now asked for a **Pareto front over the two score sides, never a single best candidate**
([formulation v1](configs/pareto_objective_formulation_v1_2026-10-20.json)). Dominance
compares objectives coordinate-wise, so it needs neither a shared unit nor a weight: the
formulation respects the prohibition on a composite score rather than evading it, and
hypervolume is reported only as a diagnostic of a *set*, never as a candidate's score.
Mechanics verified on deliberately conflicting toy objectives across three seeds — fronts
non-dominated, resumes exact, optimizer ahead of a random baseline of equal budget — with
the artifact recording that the three seeds select the same points and are therefore **not**
three independent confirmations.

No RNA was designed, proposed or scored. Before any real campaign: a reference point on the
real scales does not exist; the span policy is unresolved; and the objectives rest on
structure at 0.42–0.44 pair F1 feeding two proxies that predict neither of the assay's units.

**The design space is windowed synonymous edits at the 5′ end of the ORF**
([specification v1](configs/synonymous_window_design_space_v1_2026-10-20.json)). The
whole-ORF synonymous space is ~10²⁷³ variants and is not a domain; a 30-codon window is
~10¹³, so even the window is sampled into a finite pool the optimizer selects from. The
protein is preserved exactly and verified on every member, edits are confined to the window,
the start codon and the confirmed tandem stop are untouched, and no homopolymer run exceeds
the reference's own longest run of 6. Members failing a constraint are discarded and counted
by cause, never repaired.

A confound worth knowing about: **the reference 5′ window is GC-maximal for this protein
segment**, so every synonymous edit moves GC down or sideways, and window GC stays
correlated with edit distance at r = −0.88 even after decorrelating the sampler (−0.98
without). That is a property of editing away from a GC-optimised reference, not a sampler
artifact — in free mode, edit distance and GC content cannot be separated. A GC-neutral mode
(only equal-GC synonyms) holds window GC exactly constant and removes the confound, at the
cost of 13 substitutable positions instead of 29 and a space of ~8,000 variants, small
enough to enumerate exhaustively. **Both pools are built and recorded; which is primary is
not yet decided.** The window width and the choice of the 5′ region are declared choices,
not findings of this project.

**The whole workflow now runs end to end**, twice, on 512 synonymous variants each:
pool → assemble → fold → stability → translation → Pareto front → panel → BO replay
(`scripts/run_design_workflow.py`). [Gate v6](configs/stage2_to_stage3_gate_v6_2026-10-20.json)
records the decision to build it before the data that would validate it exists, opening
`new_sequence_scoring_enabled` and `expression_candidate_design_enabled`. v5 stays frozen,
its six-requirement basis is carried forward verbatim, the blinded 85-record set stays
**unspent**, and the span policy stays **unresolved** — the workflow reuses the reference
record's folding settings as a provisional convention, not a resolution. Variants go through
a new `assemble_variant` path that does **not** relax the reference hash gate but adds a
stricter one: the reference is still hash-verified, and the variant must then translate to
the identical protein. Passing the reference through that path reproduces the reference
assembly exactly.

**The window was widened 30 → 50 codons and the result is mixed.** Measured across two
matched 512-member runs:

| ratio, 50 vs 30 codons | |
|---|---|
| window nucleotides | 1.67× |
| predicted half-life spread (stdev) | **1.21×** |
| predicted TE spread (stdev) | **0.94×** |

The stability spread grew **sub-linearly** and the translation spread fell slightly over
that step. Fitting the two points gave spread ∝ window^0.376, predicting about 7.8% for a
whole-ORF window.

**That prediction was then tested at the ceiling of the window axis** — every codon the
constraints allow, 549 codons, 1,647 nt, 90.9% of the transcript, 291 GC-neutral
substitutable positions, ~10⁹²·⁵ variants
([diagnostic config](configs/whole_orf_window_diagnostic_v1_2026-10-20.json), which is a
probe of a scaling relationship and deliberately **not** a design space, since editing 90.9%
of the transcript destroys regional attribution):

| window | % of transcript | half-life stdev | range as % of training range | TE stdev |
|---|---|---|---|---|
| 30 codons | 5.0% | 0.00582 | 2.62% | 0.01206 |
| 50 codons | 8.3% | 0.00702 | 3.18% | 0.01137 |
| 549 codons | 90.9% | 0.01964 | **8.39%** | 0.03279 |

Fitted on the first two widths alone, the held-out prediction for the third was **7.82%**
against a measured **8.39%** — a ratio of **1.07×**. Refitting across all three gives
exponent **0.422** (R² 0.9995) for half-life stdev and 0.375 (R² 0.9546) for TE stdev.

**Window width is exhausted as a lever.** An 18-fold increase in edited sequence bought
3.37× the spread, and at the ceiling the predicted half-life still spans under a tenth of
the calibration's training range. One earlier reading is corrected by the third point: the
translation side *does* respond — TE spread is 2.72× larger at the whole-ORF width — and the
30→50 dip was noise on a non-monotone pair, so two points misled on translation while
happening to be right on stability.

The limit is the features, not the design space: every calibration feature is a
transcript-wide mean, the protein is fixed, and synonymous rewriting moves such means only
at the margin. **But a model insensitive to synonymous rewriting may be insensitive because
the biology is, or because the features are too coarse to see it — these runs cannot
distinguish those cases.** The open remedy is region-local features, recorded rather than
quietly substituted; the cost is that the STRAND calibration was fitted on transcript-wide
features and would no longer apply as fitted.

**One thing that did hold up:** at a budget of 32 of 512, qLogNEHVI recovered 5 of 10 front
members at 30 codons and 5 of 6 at 50, against random finding 1 in both. That is the first
evidence here that the optimizer buys anything — over a landscape of its own predictions,
so it measures search efficiency, not whether the landscape is right.

No molecule in this project has been measured. Every value is a prediction from an
unvalidated model on a quantity the planned assay does not measure, the selected panels
illustrate the pipeline rather than recommending anything, and the panel size is a declared
placeholder because the assay's capacity is unknown.

### 2026-10-19: engine agreement, a named calibration, score records and a Stage 2 census

Four protocols were frozen before the work they govern, then run once. Each writes a
timestamped run with a manifest, and each ships a `--verify-run` audit that re-checks
artifact hashes and replays the recorded decision without recomputing it.

| Frozen protocol | Question | Outcome |
|---|---|---|
| [agreement criterion v1](configs/strand_rnafold_agreement_criterion_v1_2026-10-19.json) | May RNAfold features substitute for the released LinearPartition features of published STRAND? | **Rejected** on 85 held-out records. Ensemble ΔG/nt and GC transfer exactly; AUP transfers for about 95% of records; ALO does not transfer at all. |
| [calibration criterion v2](configs/strand_rnafold_calibration_criterion_v2_2026-10-19.json) | Then what does an honest RNAfold-feature model look like? | `strand_rnafold_calibration_v1`, a separately named PLS refit. Primary arm without-ALO, 1 component, held-out RMSE 0.2194 h against a 0.2780 h training-mean null. |
| [score record schema v1](configs/score_record_schema_v1_2026-10-19.json) | Can every score be bound to its provenance, and can the two sides be combined? | 99 fully bound records. **No composite score is permitted**: the units are incommensurable, no floor is selected, and **0 records carry both a stability and a translation score**. |
| [Stage 2 band census v1](configs/stage2_band_coverage_census_v1_2026-10-19.json) | Can the sparse 2,000–2,999 nt requirement be resolved from local data? | **Blocked on acquisition.** 56 eligible band records exist locally, but they span one clan that is already represented, so they add records rather than independent evidence. |

Why ALO does not transfer: the released arrays carry 1,642 exactly-zero positions and
1,522 positions at or above one across the 85 held-out records, which saturate the
feature's log-odds at ∓23.03. An exact partition function produces neither, so the
published ALO depends on numerical artifacts of the original engine's approximate
normalization. A probability-flooring fix was tested, came out worse than the plain
null on held-out data, and was discarded.

Two consequences worth stating plainly. The published with-ALO arm loses its held-out
advantage on RNAfold features (+0.046 h RMSE) while the without-ALO arm transfers
almost intact (+0.002 h), which is consistent with part of that advantage being
engine-specific rather than transferable. And the four-component design has never
scored a single sequence on both its stability and its translation side, because the
released STRAND references carry UTR/CDS descriptions without numeric boundaries while
the RiboNN inputs are synthetic sequences with no measured half-life.

As of 2026-10-19, zero of the six Stage 2 gate requirements were satisfied and no gate
review had taken place, so nothing behind the gate — parents, allowed edits, the biological objective,
budgets, or the assay protocol — is frozen. Detail, limits and exact
continuation commands are in handoffs
[V1](reports/RNA-StableAI_HANDOFF_2026-10-19_V1.md),
[V2](reports/RNA-StableAI_HANDOFF_2026-10-19_V2.md),
[V3](reports/RNA-StableAI_HANDOFF_2026-10-19_V3.md) and
[V4](reports/RNA-StableAI_HANDOFF_2026-10-19_V4.md), with concise run evidence and a
[manifest](reports/stage2_and_strand_calibration_publication_2026-10-19/MANIFEST.json).

### Step 3 goal and plan: protein expression efficiency

The Step 3 goal includes improving **measured protein expression efficiency** from
RNA sequences while retaining the intended protein sequence and required RNA
features. The first target is **transfected-cell expression**, after Stage 2 review.
Development will remain within the active 1–2,999-nt range. This is a
future optimization goal; current structure and stability proxies do not establish
an expression benefit.

1. Define the target expression system, editable regions, protein and RNA
   constraints, baseline sequences, and measurements before designing variants.
2. Generate valid sequence variants, including synonymous coding changes and UTR
   changes only when the design permits them. Compare simple baselines with
   multi-objective candidates that account for sequence constraints, predicted
   structure, RNA stability, and expression-specific evidence.
3. Evaluate candidates on held-out genes and sequence families with fixed
   baselines and recorded selection rules. Keep structure, stability, and
   expression outcomes separate so a proxy improvement is not reported as
   improved protein production.
4. Test prioritized variants with biological replicates in the target system.
   Measure protein output and time-matched RNA abundance, report protein
   output relative to RNA abundance, and track total protein output, RNA
   persistence, and retained protein function as distinct outcomes. Revise the
   optimization objective only after the measurements support it.

The assay pilot advances part of step 6 while independent validation remains open.
Development resumed with a frozen 12-training/four-validation family source plan.
Its original selection failed the per-family gate. A separately versioned,
label-informed development dataset now passes that gate with 61 training and
22 validation pair references. A matched nine-run pair-set training study is
complete; independent biological validation remains open. See the
[roadmap](reports/PROJECT_ROADMAP_2026-10-18.md).
The next-panel metadata acquisition resolved 91 of 92 missing family
descriptions; RF04222 returned 404. An eight-family, 56-candidate structure
panel was frozen and acquired. All 56 contact requests succeeded, but sequence
redundancy left 12 informative references and no family with three. The
reference-readiness gate failed; no new model inference ran.
Separately, the length-focused model track screened 60 metadata-selected
[bpRNA-1m](https://bprna.cgrb.oregonstate.edu/download.php) records and retained
27 training-only RNAs of 400–1,014 nt. A matched single-seed pilot added these
to the 61-record training set. Its reused 22-record validation set ends at
387 nt, so the pilot does not establish longer-RNA accuracy. The public snapshot
includes code, metadata, and concise results; the upstream bpRNA archive and
full frozen run artifacts remain local and are not redistributed here.
A newer sampled-pair training study added 17 training-only RNAs of 1,158–3,995 nt
to the same 88-record base set. Across three matched seeds, mean pair F1 on
11 longer development references increased from 0.2605 to 0.2960. The panel
was selected using label completeness, the bpRNA family lineage remains
incomplete, and native controls still score higher. This is development
evidence; independent longer-RNA validation remains open. See the
[longer-length Step 2 review](reports/long_length_step2_review_2026-10-16.md).
An October 17 clan-separated feasibility panel added 13 references of 400–535 nt
from five held-out Rfam clans. Across three seeds, mean pair F1 was 0.1669 with
the additional training sequences versus 0.1413 for the matched control;
LinearFold and ViennaRNA scored 0.3301 and 0.3346. This small, selected panel
does not close the independent validation gap, especially at 1,000–2,999 nt.
See the [Stage 2 progress review](reports/stage2_family_validation_progress_2026-10-17.md).

## Latest results

- **Component replay milestones (October 18):** STRAND's nLuc training-only LOO
  selection gives a two-component reference fit; saved coefficients reproduce R
  predictions within 6e-15. RiboNN's two fresh CPU processes produced byte-identical
  outputs for 70 transcript/fold rows and all 78 human tasks. UTR boundaries and
  explicit exclusions passed. These are software/reference checks, not new
  independent biological validation. See the [STRAND review](reports/strand_reference_reproduction_review_2026-10-18.md)
  and [RiboNN review](reports/ribonn_fixed_inference_review_2026-10-18.md).
  Publication verification: **91 focused tests passed** in the isolated checkout;
  see the [test log](reports/component-integration-publication-focused-tests-2026-10-18.log).
- **Below-3,000-nt Stage 2:** training on 103 in-scope RNAs gives mean pair F1
  **0.3174** on six longer development references and **0.1561** on thirteen
  shorter references. Partner/null auxiliary supervision raises these to
  **0.3262 / 0.1606**, with a short-cohort regression in one of three seeds.
  Native controls remain higher; no checkpoint or default is promoted.
- **Recovery diagnosis:** the longer cohort's gold-label oracle F1 is
  **0.9606** using all legal gold pairs and **0.8257** within retained baseline
  candidates. These are optimistic label-informed bounds, not model accuracy.
  Candidate recovery and pair scoring remain priorities. Endpoint ranking was
  mixed, and a hard-negative mixture regressed against its matched control.
  See the [recovery and assignment review](reports/stage2_recovery_ceiling_and_assignment_review_2026-10-18.md)
  and [concise study summaries](reports/stage2_publication_2026-10-18/README.md).

- **Structure feasibility:** 10 raw PDB-derived references across six families;
  all 60 outcomes complete. Mean pair F1: helix **0.3255**, ViennaRNA and
  LinearFold **0.6261**. Broad biological validation remains open.
- **Measured-assay pilot:** 64 short constructs, six methods, five assays;
  all 384 predictions and 2,880 proxy/assay comparisons completed. Native energy
  per nucleotide showed stronger descriptive associations than learned unpaired
  fractions on this selected cohort.
- **Provenance:** all three learned models use the same frozen development data;
  83/136 records still lack confirmed family assignments.
- **New development data:** the failed sequence-first source run is retained.
  A disclosed coverage selection yields 61 training and 22 validation complete
  pair references across 12 and four groups.
- **New model study:** three heads × three seeds trained from random initialization
  on the new pair sets. Mean selected development validation pair F1 is 0.322
  baseline, 0.391 stack and 0.482 helix; independent accuracy is unmeasured.
- **Length-extension pilot:** 27 training-only RNAs of 400–1,014 nt added to a
  matched helix fit. Reused short-sequence validation pair F1 was **0.49106**
  versus **0.48915** for the control (one seed). This small development change
  is not an independent or longer-length accuracy result.
- **Longer-length development:** 17 training-only RNAs of 1,158–3,995 nt added
  to a matched sampled-pair study. Across three seeds, 11-record development
  pair F1 was **0.2960** versus **0.2605** for the control. LinearFold and
  ViennaRNA scored **0.4742** and **0.4499** on that panel. Selection used label
  completeness, so this is not an independent test.
- **Clan-separated feasibility:** 13 references of 400–535 nt across five
  held-out clans gave mean pair F1 **0.1669** for the extended model versus
  **0.1413** for its matched control across three seeds. The panel is small and
  selected; no checkpoint or default was promoted.
- **Earlier October 18 Stage 2 publication checks:** 51 focused tests passed in the publication
  checkout; the saved RCSB schema fixture makes the new source-field check
  available from a fresh clone. See the [test log](reports/stage2-publication-focused-tests-2026-10-18.log).
- **Historical verification (October 16):** 864 tests passed in the working environment. A clean
  publication checkout passed 841 tests; nine historical replay tests require
  ignored external/native assets absent from that checkout. Source archival
  recovered 271 of 281 recorded Python versions; ten remain unavailable.

These results do not establish causal mutation benefits, cellular half-life,
long-RNA accuracy, or retained function. The assay cohort contains only
`SN_filter=1` constructs; complete training/tool independence remains unresolved.

[Structure review and figure](reports/raw_structure_feasibility_review_2026-10-14.md)
· [Assay review and figure](reports/degradation_pilot_review_2026-10-13.md)
· [Source archive](docs/REPLAY_SOURCE_ARCHIVE.md)
· [Reference engineering](docs/STRUCTURE_DERIVED_REFERENCES.md)
· [Family source review](reports/family_provenance_source_review_2026-10-15.md)
· [Coverage dataset review](reports/family_coverage_development_review_2026-10-15.md)
· [Pair-set training review](reports/family_pair_set_training_review_2026-10-15.md)
· [Fresh structure inventory](reports/fresh_structure_inventory_review_2026-10-15.md)
· [Fresh structure candidate plan](reports/fresh_structure_metadata_and_panel_review_2026-10-15.md)
· [Fresh structure contact review](reports/fresh_structure_reference_review_2026-10-15.md)
· [Stage 2 progress review](reports/stage2_family_validation_progress_2026-10-17.md)
· [Latest development handoff](reports/RNA-StableAI_HANDOFF_2026-10-18_V12.md)
· [Model-study test log](reports/family-pair-set-training-full-suite-2026-10-15.log)

## Quick start

Requires Python 3.12+. Setup installs local dependencies and attempts native tool
builds; use `doctor` to check availability on your machine.

```bash
git clone https://github.com/zyliu-OU/rna-stable-ai.git
cd rna-stable-ai
python3 scripts/setup.py
.venv/bin/python -m rnastable doctor
.venv/bin/python -m pytest -q
```

Generate synthetic controls and run the original CPU folding / separate encoder
benchmark:

```bash
./scripts/rnastable generate --config configs/benchmark.json
./scripts/rnastable benchmark --config configs/benchmark.json
```

See the [development and command reference](DEVELOPMENT.md) for model training,
inference, optimization, evaluation protocols, and recorded studies. Historical
evidence retains original host paths; rerun pipelines for local artifacts on
another machine. Native folding runs on CPU; encoder GPU timings are separate.

## Project files

| Location | Contents |
|---|---|
| [src/rnastable](src/rnastable) / [scripts](scripts) | Pipeline, models, command-line tools, and audits |
| [configs](configs) / [tests](tests) | Declared protocols and regression checks |
| [checkpoints](checkpoints) / [data](data) / [results](results) | Experimental weights, inputs, and retained evidence |
| [docs](docs) / [reports](reports) | Methods, limitations, reviews, and dated handoffs |

See [data attribution](docs/DATA_ATTRIBUTION.md) and the
[research-use notice](RESEARCH_USE_NOTICE.md). The public assay source is pinned
to the [KaggleOpenVaccine author commit](https://github.com/eternagame/KaggleOpenVaccine/tree/b95af835cc38bd7dc55ed6e7397d124787f86996);
its [MIT license](docs/third_party/KaggleOpenVaccine_LICENSE.txt) is retained.
