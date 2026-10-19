"""Build versioned score records binding component scores to their provenance.

Ingests the existing STRAND reference replay, the named RNAfold calibration and
the fixed RiboNN inference, and emits one fully bound record per scored
sequence plus an explicit exclusion for every component that did not score it.
Emits no composite score, selects no floor and selects no RiboNN task.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

from rnastable.score_records import (
    build_record, coding_annotation, coverage, exclusion_entry, score_entry,
    sequence_identity,
)
from rnastable.strand_reference import reference_record

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT/"configs/score_record_schema_v1_2026-10-19.json"
COMPONENTS = ("strand_reference_replay", "strand_rnafold_calibration_v1", "ribonn_released_task")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, obj):
    with Path(path).open("x") as f:
        f.write(json.dumps(obj, indent=2, allow_nan=False)+"\n")


def relative(path):
    return str(Path(path).resolve().relative_to(ROOT))


def source_for(schema, component):
    for entry in schema["ingested_sources"]:
        if entry["component"] == component:
            return entry
    raise ValueError(f"Schema does not declare source for {component}")


def load_strand_sequences(reference_run):
    """Released STRAND sequences and cohorts from the pinned upstream tables."""
    manifest = json.loads((reference_run/"source_manifest.json").read_text())
    files = {}
    for entry in manifest["files"]:
        if entry.get("component") != "strand":
            continue
        if sha(ROOT/entry["local_path"]) != entry["sha256"]:
            raise ValueError(f"Pinned source hash mismatch: {entry['upstream_path']}")
        files[entry["upstream_path"]] = ROOT/entry["local_path"]
    train = list(csv.DictReader(files["Data/nluc_cleaned_new_final.csv"].open(encoding="utf-8-sig")))
    validation = list(csv.DictReader(files["Data/validate_cleaned_new_final.csv"].open(encoding="utf-8-sig")))
    records = [(reference_record(r, "train"), r) for r in train]
    for row in validation:
        cohort = {"CDS (eGFP) variants": "egfp", "CDS (MEV) variants": "mev_exploratory"}[row["group"]]
        records.append((reference_record(row, cohort), row))
    return records


def strand_reference_scores(schema, reference_run):
    """Reference-only replay of the published model on released features."""
    source = source_for(schema, "strand_reference_replay")
    model = json.loads((reference_run/"reference_model.json").read_text())
    predictions = json.loads((reference_run/"python_reference_predictions.json").read_text())
    identity = {"model_name": model["name"],
                "reference_model_sha256": sha(reference_run/"reference_model.json"),
                "source_commit": model["source_commit"],
                "source_manifest_sha256": model["source_manifest_sha256"]}
    tool = {"engine": "LinearPartition (released feature extraction)",
            "engine_version": "unknown; released features consumed as published",
            "fitting_runtime_version": "R 4.5.3 / pls 2.8.5"}
    paths = [relative(reference_run/"python_reference_predictions.json"),
             relative(reference_run/"reference_model.json")]
    out = {}
    for row in predictions:
        out[row["input_sha256"]] = score_entry(
            ROOT, component="strand_reference_replay",
            score_name="predicted_in_solution_half_life",
            value=row["predicted_half_life"], units=source["units"],
            target_scale=source["target_scale"], model_identity=identity, tool_identity=tool,
            settings={"feature_source": source["feature_source"],
                      "selected_components": model["component"]["ncomp"],
                      "feature_order": model["component"]["feature_order"],
                      "new_sequence_scoring_enabled": False},
            raw_artifact_paths=paths, run=relative(reference_run),
            interpretation="Released-reference model replay only; reproduces published "
                           "arithmetic on released features.",
            independent_validation=False)
    return out


def calibration_scores(schema, calibration_run, by_name):
    """Primary arm of the separately named RNAfold calibration."""
    source = source_for(schema, "strand_rnafold_calibration_v1")
    model = json.loads((calibration_run/"calibration_model.json").read_text())
    summary = json.loads((calibration_run/"summary.json").read_text())
    arm, ncomp = model["primary_arm"], model["selected_ncomp"]
    identity = {"model_name": model["name"],
                "calibration_model_sha256": sha(calibration_run/"calibration_model.json"),
                "criterion_sha256": model["criterion_sha256"],
                "primary_arm": arm, "is_published_strand": False}
    tool = {"engine": "ViennaRNA", "engine_version": "2.7.2",
            "parameter_file_sha256": model["parameter_file_sha256"],
            "fitting_runtime_version": "R 4.5.3 / pls 2.8.5"}
    paths = [relative(calibration_run/"fit/r_predictions.csv"),
             relative(calibration_run/"calibration_model.json")]
    out = {}
    for row in csv.DictReader((calibration_run/"fit/r_predictions.csv").open()):
        if row["arm"] != arm or int(row["ncomp"]) != ncomp or row["cohort"] == "train_loo":
            continue
        record = by_name.get(row["name"])
        if record is None:
            raise ValueError(f"Calibration prediction for unknown sequence: {row['name']}")
        out[record["input_sha256"]] = score_entry(
            ROOT, component="strand_rnafold_calibration_v1",
            score_name="predicted_in_solution_half_life",
            value=float(row["prediction"]), units=source["units"],
            target_scale=source["target_scale"], model_identity=identity, tool_identity=tool,
            settings={"feature_source": source["feature_source"],
                      "selected_components": ncomp,
                      "feature_order": model["component"]["feature_order"],
                      "energy_feature": "ensemble_energy_per_nt", "alo_transform": "identity",
                      "held_out_cohort_rmse_hours": summary["primary_egfp_rmse_hours"],
                      "new_sequence_scoring_enabled": False},
            raw_artifact_paths=paths, run=relative(calibration_run),
            interpretation="Separately named refit on RNAfold ensemble features; not published "
                           "STRAND; no independent biological validation.",
            independent_validation=False)
    return out


def ribonn_entries(schema, ribonn_run):
    """Fixed-input released-task scores and the run's explicit exclusions."""
    source = source_for(schema, "ribonn_released_task")
    protocol = json.loads((ribonn_run/"protocol.json").read_text())
    weights = json.loads((ribonn_run/"weight_manifest.json").read_text())
    sources = json.loads((ribonn_run/"source_manifest.json").read_text())
    checkpoints = json.loads((ribonn_run/"checkpoint_inventory.json").read_text())
    joined = json.loads((ribonn_run/"joined_predictions.json").read_text())
    inventory = {row["input_sha256"]: row for row in
                 json.loads((ribonn_run/"input_inventory.json").read_text())}
    commit = {entry["commit"] for entry in sources["files"] if entry.get("component") == "ribonn"}
    if len(commit) != 1:
        raise ValueError("Ambiguous RiboNN source commit")
    identity = {"model_name": "RiboNN released human checkpoints",
                "source_commit": commit.pop(),
                "weight_archive_sha256": weights["sha256"],
                "checkpoint_count_version": f"{len(checkpoints)} selected checkpoints",
                "checkpoint_sha256_list_sha256":
                    hashlib.sha256(json.dumps([c["sha256"] for c in checkpoints],
                                              sort_keys=True).encode()).hexdigest()}
    tool = {"framework": "PyTorch", "framework_version": "1.13.1 CPU",
            "python_version": "3.10.13",
            "inference_run_manifest_sha256": sha(ribonn_run/"manifest.json")}
    paths = [relative(ribonn_run/"joined_predictions.json"),
             relative(ribonn_run/"inference_0/raw_fold_predictions.tsv"),
             relative(ribonn_run/"inference_1/raw_fold_predictions.tsv"),
             relative(ribonn_run/"checkpoint_inventory.json")]
    settings = {"species": protocol["species"], "score_column": protocol["score_column"],
                "task_selection": "demonstration_only_not_assay_selected",
                "task_choice_note": protocol["task_choice"],
                "checkpoint_selection": protocol["checkpoint_selection"],
                "folds": protocol["expected_folds"], "top_k_per_fold": protocol["top_k_per_fold"],
                "cell_free_calibrated": False, "candidate_design_enabled": False}
    scores, exclusions, annotations = {}, {}, {}
    for row in joined:
        key = row["input_sha256"]
        inventory_row = inventory[key]
        annotations[key] = (inventory_row["sequence"], inventory_row["cds_start"],
                            inventory_row["cds_end"])
        if row["status"] != "ok":
            exclusions[key] = exclusion_entry(
                component="ribonn_released_task",
                reason=row.get("reason") or row["status"], run=relative(ribonn_run))
            continue
        scores[key] = score_entry(
            ROOT, component="ribonn_released_task", score_name=row["score_column"],
            value=row["mean_score"], units=source["units"], target_scale=source["target_scale"],
            model_identity=identity, tool_identity=tool,
            settings=dict(settings, fold_scores=row["fold_scores"],
                          aggregation="mean over released per-fold checkpoint predictions"),
            raw_artifact_paths=paths, run=relative(ribonn_run),
            interpretation=row["interpretation"],
            independent_validation=False)
    return scores, exclusions, annotations


def ribonn_task_inventory(ribonn_run, schema):
    """Every released output task, with the evidence that is actually local."""
    header = (ribonn_run/"inference_0/raw_fold_predictions.tsv").open().readline().rstrip("\n").split("\t")
    tasks = [name for name in header if name.startswith("predicted_TE_")]
    checkpoints = json.loads((ribonn_run/"checkpoint_inventory.json").read_text())
    scores = [c["validation_r2"] for c in checkpoints]
    return {"released_task_count": len(tasks), "tasks": tasks,
            "task_context": "All released human output tasks are cell-type or tissue "
                            "translational-efficiency tasks.",
            "cell_free_task_present": False,
            "per_task_released_accuracy_available_locally": False,
            "available_evidence": {
                "granularity": "per selected checkpoint, not per task",
                "metric": "released validation R2",
                "checkpoints": len(checkpoints),
                "min": min(scores), "max": max(scores)},
            "selection_status": schema["ribonn_task_selection"]["status"],
            "blockers": schema["ribonn_task_selection"]["blockers_recorded_2026-10-19"],
            "required_for_selection": schema["ribonn_task_selection"]["required_for_selection"],
            "interim_rule": schema["ribonn_task_selection"]["interim_rule"]}


def verify(run):
    """Re-check stored artifact hashes and replay coverage from stored records."""
    manifest = json.loads((run/"manifest.json").read_text())
    for name, expected in manifest["artifacts"].items():
        path = run/name
        if not path.resolve().is_relative_to(run.resolve()) or sha(path) != expected:
            raise ValueError(f"Artifact checksum mismatch: {name}")
    records = json.loads((run/"score_records.json").read_text())
    summary = json.loads((run/"summary.json").read_text())
    replayed = coverage(records, list(COMPONENTS))
    if replayed != summary["coverage"]:
        raise ValueError("Stored coverage does not replay from stored records")
    if any(record["composite_score"] is not None for record in records):
        raise ValueError("A stored record carries a composite score")
    result = {"artifacts_verified": len(manifest["artifacts"]),
              "records": len(records), "coverage": replayed,
              "ribonn_task_selection": summary["ribonn_task_selection_status"],
              "floors": summary["floor_status"],
              "mode": "artifact and stored-record audit; no new scoring"}
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
    schema = json.loads(args.config.read_text())
    if (schema["new_sequence_scoring_enabled"] or schema["stage3_ready"]
            or schema["expression_candidate_design_enabled"]
            or schema["composite_prohibition"]["composite_score_permitted"]):
        raise ValueError("Provenance binding only")
    for side in ("stability_floor", "translation_floor"):
        if schema["floor_selection"][side]["value"] is not None:
            raise ValueError(f"{side} must stay unselected in this schema")

    reference_run = ROOT/source_for(schema, "strand_reference_replay")["run"]
    calibration_run = ROOT/source_for(schema, "strand_rnafold_calibration_v1")["run"]
    ribonn_run = ROOT/source_for(schema, "ribonn_released_task")["run"]

    strand = load_strand_sequences(reference_run)
    by_name = {record["name"]: record for record, _ in strand}
    reference = strand_reference_scores(schema, reference_run)
    calibration = calibration_scores(schema, calibration_run, by_name)
    ribonn, ribonn_excluded, ribonn_annotation = ribonn_entries(schema, ribonn_run)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out = ROOT/"results/score_record_runs"/stamp
    out.mkdir(parents=True, exist_ok=False)
    print(out, flush=True)
    write(out/"protocol.json", schema)

    records = []
    for record, row in strand:
        key = record["input_sha256"]
        identity = sequence_identity(row["sequence"])
        if identity["sha256"] != key:
            raise ValueError(f"Sequence identity mismatch for {record['name']}")
        annotation = coding_annotation(
            identity["length"],
            absent_reason="Released STRAND tables give UTR5/CDS/UTR3 descriptions and types "
                          f"(UTR5 {row['UTR5_description']!r}, CDS {row['CDS_description']!r}, "
                          f"UTR3 {row['UTR3_description']!r}) but no numeric coding boundaries.")
        scores = [entry for entry in (reference.get(key), calibration.get(key)) if entry]
        exclusions = [exclusion_entry(
            component="ribonn_released_task",
            reason="No numeric coding boundaries available for this released sequence; RiboNN "
                   "requires utr5_size and cds_size. Deriving boundaries would be new annotation "
                   "needing its own provenance and validation.",
            run=relative(ribonn_run))]
        for component in ("strand_reference_replay", "strand_rnafold_calibration_v1"):
            if not any(entry["component"] == component for entry in scores):
                exclusions.append(exclusion_entry(
                    component=component, reason="No stored prediction for this sequence",
                    run=relative(reference_run if component == "strand_reference_replay"
                                 else calibration_run)))
        records.append(dict(build_record(identity, annotation, scores, exclusions, COMPONENTS),
                            cohort=record["cohort"], released_name=record["name"],
                            observed_half_life_hours=record["observed_half_life"]))

    for key, (sequence, cds_start, cds_end) in ribonn_annotation.items():
        identity = sequence_identity(sequence)
        if identity["sha256"] != key:
            raise ValueError("RiboNN input identity mismatch")
        annotation = coding_annotation(identity["length"], int(cds_start), int(cds_end))
        scores = [entry for entry in (ribonn.get(key),) if entry]
        exclusions = [entry for entry in (ribonn_excluded.get(key),) if entry]
        for component in ("strand_reference_replay", "strand_rnafold_calibration_v1"):
            exclusions.append(exclusion_entry(
                component=component,
                reason="Synthetic fixed RiboNN mechanics input; not a released STRAND reference "
                       "record and not folded for calibration features.",
                run=relative(reference_run if component == "strand_reference_replay"
                             else calibration_run)))
        records.append(dict(build_record(identity, annotation, scores, exclusions, COMPONENTS),
                            cohort="ribonn_fixed_synthetic", released_name=None,
                            observed_half_life_hours=None))

    write(out/"score_records.json", records)
    tasks = ribonn_task_inventory(ribonn_run, schema)
    write(out/"ribonn_task_inventory.json", tasks)

    implementations = [Path(__file__), ROOT/"src/rnastable/score_records.py",
                       ROOT/"src/rnastable/strand_reference.py"]
    identities = {}
    for path in implementations:
        target = out/"source"/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        identities[str(path.relative_to(ROOT))] = sha(path)
    write(out/"identity.json",
          {"implementation": identities, "schema_sha256": sha(args.config),
           "ingested_runs": {
               "strand_reference_replay": {"run": relative(reference_run),
                                           "manifest_sha256": sha(reference_run/"manifest.json")},
               "strand_rnafold_calibration_v1": {"run": relative(calibration_run),
                                                 "manifest_sha256": sha(calibration_run/"manifest.json")},
               "ribonn_released_task": {"run": relative(ribonn_run),
                                        "manifest_sha256": sha(ribonn_run/"manifest.json")}}})

    counts = coverage(records, list(COMPONENTS))
    summary = {"schema_version": 1, "schema_sha256": sha(args.config),
               "records": len(records), "coverage": counts,
               "cohorts": {c: sum(1 for r in records if r["cohort"] == c)
                           for c in sorted({r["cohort"] for r in records})},
               "records_with_numeric_annotation":
                   sum(1 for r in records if r["annotation"]["numeric_boundaries_available"]),
               "composite_score_emitted": False,
               "composite_blocked_reason": schema["composite_prohibition"]["reason"],
               "ribonn_task_selection_status": tasks["selection_status"],
               "ribonn_task_blockers": tasks["blockers"],
               "released_task_count": tasks["released_task_count"],
               "cell_free_task_present": tasks["cell_free_task_present"],
               "floor_status": {side: schema["floor_selection"][side]["status"]
                                for side in ("stability_floor", "translation_floor")},
               "floor_required_evidence": schema["floor_selection"]["required_for_selection"],
               "no_claim_permitted": schema["no_claim_permitted"],
               "new_sequence_scoring_enabled": False, "stage3_ready": False,
               "interpretation": "Provenance binding inventory. No score here is validated and "
                                 "no component pair is jointly available."}
    write(out/"summary.json", summary)
    artifacts = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob("*")) if p.is_file()}
    write(out/"manifest.json", {"run": stamp, "artifacts": artifacts})
    print(json.dumps({k: summary[k] for k in
                      ("records", "coverage", "cohorts", "records_with_numeric_annotation",
                       "ribonn_task_selection_status", "released_task_count",
                       "cell_free_task_present", "floor_status")}, indent=2))


if __name__ == "__main__":
    main()
