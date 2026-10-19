"""Fit and audit strand_rnafold_calibration_v1 under frozen criterion v2.

Reuses the hash-verified RNAfold folds from the v1 agreement run, refits the
published PLS method on RNAfold ensemble features, selects components from the
nLuc training LOO PRESS only, and reads the eGFP cohort once against a
prespecified training-mean null. This is a separately named model, not
published STRAND, and it does not enable new-sequence scoring.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from rnastable.strand_agreement import substituted_features
from rnastable.strand_reference import FEATURE_ORDER, linear_prediction, reference_record

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT/"configs/strand_rnafold_calibration_criterion_v2_2026-10-19.json"
COLUMNS = ["name", *FEATURE_ORDER, "in_solution_half_life"]
COHORT_FILES = {"train": "train_features.csv", "egfp": "egfp_features.csv",
                "mev_exploratory": "mev_features.csv"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, obj):
    with Path(path).open("x") as f:
        f.write(json.dumps(obj, indent=2, allow_nan=False)+"\n")


def load_references(criterion):
    """Rebuild the frozen 91-record inventory from pinned upstream sources."""
    source_run = ROOT/criterion["feature_source"]["reuse_run"]
    # The v1 agreement run recorded the pinned manifest's hash rather than
    # copying it; resolve the file through that run's own protocol and identity
    # so the sources here are exactly the ones its folds were computed from.
    reference_run = ROOT/json.loads((source_run/"protocol.json").read_text())["reference_run"]
    manifest_path = reference_run/"source_manifest.json"
    if sha(manifest_path) != json.loads((source_run/"identity.json").read_text())["source_manifest_sha256"]:
        raise ValueError("Pinned source manifest differs from the one used for the stored folds")
    manifest = json.loads(manifest_path.read_text())
    files = {}
    for entry in manifest["files"]:
        if entry.get("component") != "strand":
            continue
        if sha(ROOT/entry["local_path"]) != entry["sha256"]:
            raise ValueError(f"Pinned source hash mismatch: {entry['upstream_path']}")
        files[entry["upstream_path"]] = ROOT/entry["local_path"]
    raw_train = list(csv.DictReader(files["Data/nluc_cleaned_new_final.csv"].open(encoding="utf-8-sig")))
    raw_validation = list(csv.DictReader(files["Data/validate_cleaned_new_final.csv"].open(encoding="utf-8-sig")))
    records = [reference_record(r, "train") for r in raw_train]
    for row in raw_validation:
        cohort = {"CDS (eGFP) variants": "egfp", "CDS (MEV) variants": "mev_exploratory"}[row["group"]]
        records.append(reference_record(row, cohort))
    counts = {c: sum(r["cohort"] == c for r in records) for c in COHORT_FILES}
    if counts != {"train": 69, "egfp": 13, "mev_exploratory": 9}:
        raise ValueError("Unexpected cohort inventory")
    return records


def load_verified_folds(criterion, records):
    """Read stored v1 folds, re-verifying each against that run's manifest."""
    source_run = ROOT/criterion["feature_source"]["reuse_run"]
    manifest = json.loads((source_run/"manifest.json").read_text())["artifacts"]
    expected = criterion["feature_source"]
    folds = {}
    for record in records:
        relative = f"folds/{record['name']}.json"
        path = source_run/relative
        if relative not in manifest or sha(path) != manifest[relative]:
            raise ValueError(f"Stored fold missing or altered: {relative}")
        folding = json.loads(path.read_text())
        if folding["status"] != "ok":
            raise ValueError(f"Stored fold is not ok: {record['name']}")
        if folding["settings"]["parameter_file_sha256"] != expected["parameter_file_sha256"]:
            raise ValueError(f"Folding parameter set differs from the frozen criterion: {record['name']}")
        folds[record["name"]] = folding
    return folds


def build_feature_rows(criterion, records, folds):
    """RNAfold feature table per cohort, under the frozen energy and transform."""
    source = criterion["feature_source"]
    rows = {cohort: [] for cohort in COHORT_FILES}
    for record in records:
        values = substituted_features(folds[record["name"]], source["energy_feature"],
                                      source["alo_transform"])
        rows[record["cohort"]].append({"name": record["name"],
                                       **{k: values[k] for k in FEATURE_ORDER},
                                       "in_solution_half_life": record["observed_half_life"]})
    return rows


def write_feature_csvs(rows, destination):
    for cohort, name in COHORT_FILES.items():
        with (destination/name).open("x", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
            writer.writeheader()
            for row in rows[cohort]:
                writer.writerow({k: (row[k] if k == "name" else repr(row[k])) for k in COLUMNS})


def cross_language_check(fit_dir, rows, tolerance):
    """Replay every exported component in Python against the R predictions."""
    models = json.loads((fit_dir/"r_models.json").read_text())
    lookup = {(c, r["name"]): r for c in rows for r in rows[c]}
    worst = 0.0
    compared = 0
    for line in csv.DictReader((fit_dir/"r_predictions.csv").open()):
        if line["cohort"] == "train_loo":
            continue
        component = models["models"][line["arm"]]["components"][line["ncomp"]]
        features = lookup[(line["cohort"], line["name"])]
        predicted = linear_prediction(component, {k: features[k] for k in component["feature_order"]})
        worst = max(worst, abs(predicted-float(line["prediction"])))
        compared += 1
    if worst > tolerance:
        raise ValueError(f"Python/R prediction replay differs by {worst}")
    return {"comparisons": compared, "max_abs_difference": worst, "tolerance": tolerance}


def primary_arm(loo):
    """Frozen rule: lower nLuc training-only LOO RMSE, with_alo on a near tie.

    Reads no held-out record, so published eGFP accuracy cannot steer it.
    """
    if set(loo) != {"with_alo", "without_alo"}:
        raise ValueError("Both prespecified arms are required")
    if abs(loo["with_alo"]-loo["without_alo"]) < 1e-12:
        return "with_alo"
    return min(loo, key=loo.get)


def metric(models, arm, ncomp, cohort):
    for row in models["metrics"]:
        if row["arm"] == arm and row["ncomp"] == ncomp and row["cohort"] == cohort:
            return row
    raise ValueError(f"Missing metric row: {arm} {ncomp} {cohort}")


def verify(run):
    """Re-check stored artifact hashes and replay the acceptance decision."""
    manifest = json.loads((run/"manifest.json").read_text())
    for relative, expected in manifest["artifacts"].items():
        path = run/relative
        if not path.resolve().is_relative_to(run.resolve()) or sha(path) != expected:
            raise ValueError(f"Artifact checksum mismatch: {relative}")
    summary = json.loads((run/"summary.json").read_text())
    models = json.loads((run/"fit/r_models.json").read_text())
    arm = summary["primary_arm"]
    selected = models["models"][arm]["selected_ncomp"]
    egfp = metric(models, arm, selected, "egfp")["rmse"]
    null_egfp = models["training_mean_null"]["egfp"]["rmse"]
    if egfp != summary["primary_egfp_rmse_hours"] or null_egfp != summary["training_mean_null_egfp_rmse_hours"]:
        raise ValueError("Stored metrics do not match the stored summary")
    if (egfp <= null_egfp) != summary["acceptance"]["bar_passed"]:
        raise ValueError("Stored acceptance decision does not replay")
    result = {"artifacts_verified": len(manifest["artifacts"]),
              "model_name": models["model_name"], "primary_arm": arm,
              "selected_ncomp": selected, "primary_egfp_rmse_hours": egfp,
              "training_mean_null_egfp_rmse_hours": null_egfp,
              "outcome": summary["acceptance"]["outcome"],
              "mode": "artifact and stored-fit audit; no new fit"}
    print(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT)
    parser.add_argument("--verify-run", type=Path)
    args = parser.parse_args()
    if args.verify_run:
        verify(args.verify_run.resolve())
        return
    criterion = json.loads(args.config.read_text())
    if (criterion["new_sequence_scoring_enabled"] or criterion["stage3_ready"]
            or criterion["expression_candidate_design_enabled"]):
        raise ValueError("Named calibration fit only")
    if not criterion["arms"]["both_prespecified"]:
        raise ValueError("Both arms must be prespecified before fitting")

    records = load_references(criterion)
    folds = load_verified_folds(criterion, records)
    rows = build_feature_rows(criterion, records, folds)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out = ROOT/"results/strand_rnafold_calibration_runs"/stamp
    out.mkdir(parents=True, exist_ok=False)
    print(out, flush=True)
    write(out/"protocol.json", criterion)
    inputs = out/"features"
    inputs.mkdir()
    write_feature_csvs(rows, inputs)

    implementations = [Path(__file__), ROOT/"scripts/fit_strand_rnafold_calibration.R",
                       ROOT/"src/rnastable/strand_agreement.py",
                       ROOT/"src/rnastable/strand_reference.py",
                       ROOT/"src/rnastable/component_integration.py"]
    identities = {}
    for path in implementations:
        target = out/"source"/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        identities[str(path.relative_to(ROOT))] = sha(path)
    source_run = ROOT/criterion["feature_source"]["reuse_run"]
    write(out/"identity.json",
          {"implementation": identities, "criterion_sha256": sha(args.config),
           "feature_source_run": criterion["feature_source"]["reuse_run"],
           "feature_source_manifest_sha256": sha(source_run/"manifest.json"),
           "feature_source_agreement_sha256": sha(source_run/"agreement.json"),
           "feature_csv_sha256": {name: sha(inputs/name) for name in COHORT_FILES.values()}})

    fits = []
    for index in range(criterion["fitting_procedure"]["fit_repetitions"]):
        destination = out/("fit" if index == 0 else f"fit_repeat{index}")
        destination.mkdir()
        start = time.perf_counter()
        command = [str(ROOT/"external/strand-r/bin/Rscript"), "--vanilla",
                   str(out/"source/scripts/fit_strand_rnafold_calibration.R"),
                   str(inputs), str(destination)]
        process = subprocess.run(command, env=dict(os.environ, TZ="UTC", OPENBLAS_NUM_THREADS="1"),
                                 capture_output=True, text=True)
        (destination/"command.log").write_text(" ".join(command)+"\n"+process.stdout+process.stderr)
        if process.returncode:
            raise RuntimeError(process.stderr)
        fits.append({"repeat": index, "runtime_seconds": time.perf_counter()-start,
                     **cross_language_check(destination, rows, 1e-10)})
    models = json.loads((out/"fit/r_models.json").read_text())
    runtime = {"R": models["R_version"].split()[2], "pls": models["pls_version"],
               "jsonlite": models["jsonlite_version"]}
    if runtime != criterion["fitting_procedure"]["runtime"]:
        raise ValueError(f"Runtime mismatch: {runtime}")
    repeated = json.loads((out/"fit_repeat1/r_models.json").read_text())
    if repeated["models"] != models["models"]:
        raise ValueError("Repeated fits differ")

    loo = {arm: metric(models, arm, models["models"][arm]["selected_ncomp"], "train_loo")["rmse"]
           for arm in ("with_alo", "without_alo")}
    primary = primary_arm(loo)
    selected = models["models"][primary]["selected_ncomp"]
    null_egfp = models["training_mean_null"]["egfp"]["rmse"]
    primary_egfp = metric(models, primary, selected, "egfp")["rmse"]
    passed = primary_egfp <= null_egfp

    model = {"schema_version": 1, "name": criterion["model_name"],
             "feature_source": "rnafold_ensemble_features",
             "engine": criterion["feature_source"]["engine"],
             "parameter_file_sha256": criterion["feature_source"]["parameter_file_sha256"],
             "criterion_sha256": sha(args.config),
             "primary_arm": primary, "selected_ncomp": selected,
             "component": models["models"][primary]["components"][str(selected)],
             "arms": {arm: {"selected_ncomp": models["models"][arm]["selected_ncomp"],
                            "component": models["models"][arm]["components"][str(models["models"][arm]["selected_ncomp"])]}
                      for arm in ("with_alo", "without_alo")},
             "units": {"GC": "percent", "energy_per_length": "kcal/mol per nucleotide",
                       "aup": "fraction", "alo": "natural log odds", "target": "hours"},
             "is_published_strand": False,
             "naming_rule": criterion["naming_rule"],
             "independent_validation": False,
             "new_sequence_scoring_enabled": False, "stage3_ready": False}
    write(out/"calibration_model.json", model)

    cohorts = {}
    for arm in ("with_alo", "without_alo"):
        arm_selected = models["models"][arm]["selected_ncomp"]
        cohorts[arm] = {"selected_ncomp": arm_selected,
                        "loo_press": models["models"][arm]["loo_press"],
                        **{cohort: metric(models, arm, arm_selected, cohort)
                           for cohort in ("train", "train_loo", "egfp", "mev_exploratory")}}
    summary = {"model_name": criterion["model_name"], "is_published_strand": False,
               "feature_source_run": criterion["feature_source"]["reuse_run"],
               "records": {c: len(rows[c]) for c in COHORT_FILES},
               "runtime": runtime, "fits": fits,
               "deterministic_repeated_fit": True,
               "training_loo_rmse_hours": loo,
               "primary_arm": primary, "primary_arm_rule": criterion["primary_arm_rule"],
               "selected_ncomp": selected,
               "primary_egfp_rmse_hours": primary_egfp,
               "training_mean_null_egfp_rmse_hours": null_egfp,
               "training_mean_half_life_hours": models["training_mean_null"]["train_mean_half_life"],
               "arm_metrics": cohorts,
               "published_reference_points_not_bars":
                   criterion["acceptance_criterion"]["reference_points_not_bars"],
               "acceptance": {"bar": criterion["acceptance_criterion"]["primary_bar"],
                              "bar_passed": passed,
                              "outcome": "not_rejected" if passed else "rejected"},
               "no_claim_permitted": criterion["no_claim_permitted"],
               "new_sequence_scoring_enabled": False, "stage3_ready": False,
               "interpretation": "Separately named refit on RNAfold ensemble features. "
                                 "Held-out readout on 13 project-exposed eGFP records. "
                                 "Not published STRAND and not independent validation."}
    write(out/"summary.json", summary)
    artifacts = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob("*")) if p.is_file()}
    write(out/"manifest.json", {"run": stamp, "artifacts": artifacts})
    print(json.dumps({k: summary[k] for k in
                      ("model_name", "records", "runtime", "training_loo_rmse_hours", "primary_arm",
                       "selected_ncomp", "primary_egfp_rmse_hours",
                       "training_mean_null_egfp_rmse_hours", "acceptance")}, indent=2))


if __name__ == "__main__":
    main()
