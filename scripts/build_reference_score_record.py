#!/usr/bin/env python3
"""Build the score record for the supplied reference construct.

Every existing score record carries one side only: the 91 STRAND reference
sequences have a stability score and no translation score, and the synthetic
RiboNN inputs have the reverse. `records_with_both_sides` is 0.

The reference construct now has both, so this builds the project's first record
carrying a stability and a translation score for one sequence. That is an
integration milestone, not a scientific one: the two numbers sit side by side
precisely because they cannot be combined.

No composite score is emitted. The composite remains prohibited by
`score_record_schema_v1`: the stability side is in hours on the released STRAND
in-solution scale, the translation side is on a released RiboNN task scale with
no inverse transform or physical unit, and no floor has been selected.
"""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.score_records import (
    build_record, coding_annotation, coverage, exclusion_entry, score_entry,
    sequence_identity,
)

SCHEMA = ROOT / "configs/score_record_schema_v1_2026-10-19.json"
CALIBRATION = ROOT / "results/strand_rnafold_calibration_runs/20261019T174049.053308Z"
COMPONENTS = ("strand_reference_replay", "strand_rnafold_calibration_v1",
              "ribonn_released_task")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def calibration_features(fold, sequence):
    """The three features the primary calibration arm consumes.

    The energy hypothesis is `ensemble_energy_per_nt`, as selected by the frozen
    agreement criterion, not the MFE per nucleotide.
    """
    return {
        "energy_per_length": fold["fold"]["ensemble_free_energy_per_nt_kcal_mol"],
        "GC": (sequence.count("G") + sequence.count("C")) / len(sequence) * 100,
        "aup": fold["fold"]["mean_unpaired_probability"],
    }


def training_domain():
    """Per-feature training ranges, so extrapolation can be stated rather than hidden."""
    rows = list(csv.DictReader((CALIBRATION / "features/train_features.csv").open()))
    domain = {}
    for feature in ("energy_per_length", "GC", "aup"):
        values = [float(row[feature]) for row in rows]
        domain[feature] = {"min": min(values), "max": max(values)}
    targets = [float(row["in_solution_half_life"]) for row in rows]
    domain["target_hours"] = {"min": min(targets), "max": max(targets)}
    return domain


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--tx-id", default="FLUC-REF-V1")
    parser.add_argument("--fold", default="results/reference_fold/FLUC-REF-V1_core.json")
    parser.add_argument("--assembly", default="results/reference_transcript/FLUC-REF-V1.json")
    parser.add_argument("--ribonn-run",
                        default="results/ribonn_fixed_inference_runs/20261020T021707.178744Z")
    parser.add_argument("--ribonn-tx-id", default="FLUC-REF-V1-core")
    parser.add_argument("--out", default="results/reference_score_record")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    fold = json.loads((ROOT / args.fold).read_text())
    assembly = json.loads((ROOT / args.assembly).read_text())
    sequence = assembly["sequence_rna"]
    identity = sequence_identity(sequence)
    annotation = coding_annotation(len(sequence), assembly["cds_start"], assembly["cds_end"])

    model = json.loads((CALIBRATION / "calibration_model.json").read_text())
    arm = model["component"]
    features = calibration_features(fold, sequence)
    # Verified against the calibration run's own R predictions: intercept plus
    # the raw-unit coefficient dot product reproduces them exactly.
    prediction = arm["intercept"] + sum(arm["coefficients"][f] * features[f]
                                        for f in arm["feature_order"])
    domain = training_domain()
    outside = [f for f in arm["feature_order"]
               if not domain[f]["min"] <= features[f] <= domain[f]["max"]]

    ribonn = {row["tx_id"]: row for row in json.loads(
        (ROOT / args.ribonn_run / "joined_predictions.json").read_text())}
    translation = ribonn[args.ribonn_tx_id]
    ribonn_summary = json.loads((ROOT / args.ribonn_run / "summary.json").read_text())

    extrapolation = (
        "EXTRAPOLATION: " + ", ".join(
            f"{f} = {features[f]:.4f} lies outside the training range "
            f"[{domain[f]['min']:.4f}, {domain[f]['max']:.4f}]" for f in outside)
        if outside else
        "All three features lie inside the calibration's training ranges.")

    scores = [
        score_entry(
            ROOT,
            component="strand_rnafold_calibration_v1",
            score_name="predicted_in_solution_half_life",
            value=float(prediction),
            units="hours",
            target_scale="released STRAND in-solution half-life of purified RNA in buffer",
            model_identity={
                "name": model["name"],
                "arm": model["primary_arm"],
                "ncomp": arm["ncomp"],
                "calibration_model_sha256": sha(CALIBRATION / "calibration_model.json"),
                "criterion_sha256": model["criterion_sha256"],
            },
            tool_identity={
                "tool": fold["fold"]["tool"],
                "version": fold["fold"]["version"],
                "parameter_file_sha256": fold["fold"]["settings"]["parameter_file_sha256"],
            },
            settings=dict(fold["fold"]["settings"], features=features,
                          feature_order=arm["feature_order"],
                          energy_hypothesis="ensemble_energy_per_nt"),
            raw_artifact_paths=[args.fold, args.assembly,
                                str((CALIBRATION / "calibration_model.json").relative_to(ROOT))],
            run=str(CALIBRATION.relative_to(ROOT)),
            interpretation=(
                "A separately named refit, NOT the published STRAND model, which this "
                "project's frozen agreement criterion rejected for RNAfold-derived "
                "features. The calibration is unvalidated: it has no independent "
                "evaluation against held-out measurements. "
                + extrapolation +
                " It predicts in-solution half-life of purified RNA in buffer, whereas "
                "the planned assay measures in-cell mRNA decay by RT-qPCR, so the two "
                "are different quantities. Every uridine in the assayed molecule is "
                "N1-methylpseudouridine, which neither the folding engine nor the "
                "calibration represents. This number ranks nothing and establishes no "
                "stability benefit."),
            independent_validation=False,
        ),
        score_entry(
            ROOT,
            component="ribonn_released_task",
            score_name=translation["score_column"],
            value=float(translation["mean_score"]),
            units="released RiboNN predicted translational-efficiency task scale",
            target_scale="RiboNN predicted_TE_A549, released task scale",
            model_identity={
                "task": translation["score_column"],
                "checkpoints": ribonn_summary["selected_models"],
                "folds": ribonn_summary["folds"],
                "weight_archive_sha256": ribonn_summary["archive_sha256"],
            },
            tool_identity={
                "component": "ribonn-inference",
                "torch_version": ribonn_summary["workers"][0]["versions"]["torch"],
                "numpy_version": ribonn_summary["workers"][0]["versions"]["numpy"],
                "weight_archive_sha256": ribonn_summary["archive_sha256"],
                "weights_files_verified": ribonn_summary["weights_files_verified"],
                "bitwise_replay_across_processes": ribonn_summary["replay"]["bitwise_float_equal"],
            },
            settings={"aggregation": "mean over released per-fold checkpoint predictions",
                      "fold_scores": translation["fold_scores"],
                      "poly_a_included": False},
            raw_artifact_paths=[str(Path(args.ribonn_run) / "joined_predictions.json"),
                                str(Path(args.ribonn_run) / "summary.json")],
            run=args.ribonn_run,
            interpretation=(
                "Released-task score for the A549 arm only, on the task's own scale. It "
                "is not a prediction of luminescence in the planned assay and carries "
                "the documented out-of-distribution caveat for a designed reporter "
                "construct rather than an endogenous human transcript. The T-cell arm is "
                "declared model-blind and receives no translation score. Every uridine "
                "is N1-methylpseudouridine, which RiboNN does not represent."),
            independent_validation=False,
        ),
    ]

    exclusions = [exclusion_entry(
        component="strand_reference_replay",
        reason=("The published STRAND model is not applicable to RNAfold-derived "
                "features. configs/strand_rnafold_agreement_criterion_v1 returned "
                "feature_level_compatible false, output_level_equivalent false and "
                "outcome rejected, so the unchanged published coefficients may not be "
                "applied to this sequence."),
        run="results/strand_rnafold_agreement_runs/20261019T172402.804593Z",
    )]

    record = build_record(identity, annotation, scores, exclusions, COMPONENTS)
    records = [record]
    payload = {
        "schema_version": 1,
        "schema_sha256": sha(SCHEMA),
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "tx_id": args.tx_id,
        "records": records,
        "coverage": coverage(records, COMPONENTS),
        "calibration_training_domain": domain,
        "features_outside_training_domain": outside,
        "composite_score_emitted": False,
        "no_claim": [
            "A bound score record. It establishes no stability, translation or "
            "expression benefit.",
            "The two scores are incommensurable and are deliberately not combined.",
            "No floor is selected, no gate requirement is satisfied, and no candidate "
            "was designed or scored.",
        ],
    }
    print(json.dumps({k: v for k, v in payload.items() if k != "records"}, indent=2))
    print(f"\nstability  {prediction:.6f} hours"
          f"{'  (EXTRAPOLATED: ' + ', '.join(outside) + ')' if outside else ''}")
    print(f"translation {translation['mean_score']:.6f} on {translation['score_column']}")

    if args.dry_run:
        print("\nDry run: nothing written.", file=sys.stderr)
        return 0
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{args.tx_id}_score_record.json"
    if target.exists():
        raise SystemExit(f"{target} already exists; remove it deliberately.")
    target.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(f"\nWrote {target}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
