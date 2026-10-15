# RNA-StableAI helix objective development review — 2026-10-13

Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Run: `/home/zyliu/Documents/rna-stable-ai/results/helix_objective_development_runs/20261014T002930.596309Z`.
Protocol: [HELIX_OBJECTIVE_DEVELOPMENT.md](../docs/HELIX_OBJECTIVE_DEVELOPMENT.md).

Completed the declared three-seed comparison of original helix BCE checkpoints
against fresh fits using the existing pruned structured hinge plus 0.1 weighted
BCE. All model settings, 89 training/47 validation records, deterministic
initial states, ten epochs, Adam and exact top-16 inference remain matched.
Each objective selects its epoch independently using development F1, full
validation BCE for ties, then earliest epoch. No new test input was read.

| Seed | BCE epoch | BCE F1 | Structured epoch | Structured F1 | Difference |
|---:|---:|---:|---:|---:|---:|
| 20261006 | 5 | 0.524423 | 3 | 0.429375 | -0.095048 |
| 20261007 | 4 | 0.495077 | 7 | 0.417392 | -0.077685 |
| 20261008 | 3 | 0.491069 | 4 | 0.446825 | -0.044244 |

Structured training reduces total validation false positives from 1502/1409/1363
to 1297/958/930 for the three respective seeds. It regresses record F1 on
33/23/24 of 47 records, improving on 6/17/16. Reduced false positives do not
compensate for reduced recovery of reference contacts. All 141 paired outcomes
and 30 fixed slices, including three empty length slices, remain retained.
Repeated initialization seeds share biological labels and do not establish
independent uncertainty. Do not select the new checkpoints as a validated gain.
Keep the original BCE checkpoint pointers, decoder and inference defaults.

The three bounded CPU processes took 50.368/50.116/51.415 seconds, each under
the declared 600-second/8-GiB bound. These include training, epoch validation and
exports and overlap other host work. They are not isolated throughput estimates
or measurements comparable to original BCE training time. Training-loss units
also differ between objectives.

Each new fit retains 890 structured decisions in deterministic training order,
loss/label/graph hashes, gold retention counts, loss arithmetic and epoch means.
Audit anchors the first augmented graph, compares the complete initial state and
initial predictions to original BCE, replays initial/selected checkpoints and
full validation BCE, and verifies input/checkpoint/exposure/outcome bindings.
The audit does not retrain every optimizer step or establish unrestricted-graph
structured optimality. No native folds or prospective inputs occurred.

Fourteen new focused tests cover the objective-only configuration contract,
missing/tampered training decisions, loss arithmetic, failed-fit accounting and
empty slices. A broader 53-test set passes. Complete replay and full-suite results
are recorded in the next versioned handoff. New code lives in a separate script;
existing inference/training implementation and prior audit code remain preserved.

Next obtain a separately frozen annotated panel for the unchanged comparison
models. Improving model training would require a new declared development design;
this experiment does not justify more posthoc validation tuning or reuse of
consumed prospective panels as independent evidence.
