"""Decide RNAfold-vs-LinearPartition STRAND feature agreement under a frozen criterion.

Folds every released reference sequence once, selects a single grid cell on the
already-burned six-sequence panel, then scores that cell and the prespecified
identity null once on the held-out records. Engine agreement only: no stability
prediction, no new-sequence scoring and no Stage 2 gate progress.
"""
import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

from rnastable.component_integration import fold_fixed_input
from rnastable.strand_agreement import (
    decide, feature_deltas, feature_tolerances, output_differences,
    quantile, rounding_half_widths, select_cell, substituted_features, summarize,
)
from rnastable.strand_reference import FEATURE_ORDER, reference_record

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT/"configs/strand_rnafold_agreement_criterion_v1_2026-10-19.json"


@dataclass(frozen=True)
class FixedSequence:
    tx_id: str
    sequence: str

    @property
    def sha256(self):
        return hashlib.sha256(self.sequence.encode()).hexdigest()

    @property
    def identity_sha256(self):
        return hashlib.sha256(f"{self.tx_id}:{self.sequence}".encode()).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, obj):
    with Path(path).open("x") as f:
        f.write(json.dumps(obj, indent=2, allow_nan=False)+"\n")


def load_references(criterion):
    """Rebuild the frozen 91-record inventory from pinned upstream sources."""
    run = ROOT/criterion["reference_run"]
    manifest = json.loads((run/"source_manifest.json").read_text())
    files = {}
    for entry in manifest["files"]:
        if entry.get("component") != "strand":
            continue
        if sha(ROOT/entry["local_path"]) != entry["sha256"]:
            raise ValueError(f"Pinned source hash mismatch: {entry['upstream_path']}")
        if entry["commit"] != criterion["source_commit"]:
            raise ValueError("STRAND source commit mismatch")
        files[entry["upstream_path"]] = ROOT/entry["local_path"]
    raw_train = list(csv.DictReader(files["Data/nluc_cleaned_new_final.csv"].open(encoding="utf-8-sig")))
    raw_validation = list(csv.DictReader(files["Data/validate_cleaned_new_final.csv"].open(encoding="utf-8-sig")))
    records = [reference_record(r, "train") for r in raw_train]
    for row in raw_validation:
        cohort = {"CDS (eGFP) variants": "egfp", "CDS (MEV) variants": "mev_exploratory"}[row["group"]]
        records.append(reference_record(row, cohort))
    raw = {r["name"]: r for r in raw_train+raw_validation}
    counts = {c: sum(r["cohort"] == c for r in records) for c in ("train", "egfp", "mev_exploratory")}
    if counts != {"train": 69, "egfp": 13, "mev_exploratory": 9} or len(raw) != len(records):
        raise ValueError("Unexpected cohort inventory or duplicate reference IDs")
    return records, raw


def cohort_summary(rows, key):
    out = {}
    for row in rows:
        out.setdefault(row[key], 0)
        out[row[key]] += 1
    return dict(sorted(out.items()))


def verify(run):
    """Re-check stored artifact hashes and replay the decision from stored folds."""
    manifest = json.loads((run/"manifest.json").read_text())
    for relative, expected in manifest["artifacts"].items():
        path = run/relative
        if not path.resolve().is_relative_to(run.resolve()) or sha(path) != expected:
            raise ValueError(f"Artifact checksum mismatch: {relative}")
    agreement = json.loads((run/"agreement.json").read_text())
    criterion = json.loads((run/"protocol.json").read_text())
    replayed = decide(agreement["selected"]["evaluation_feature_summary"],
                      agreement["selected"]["evaluation_output"]["with_alo"]["max_abs_difference_hours"],
                      criterion["tolerances"]["output_absolute_hours"])
    if replayed != agreement["decision"]:
        raise ValueError("Stored decision does not replay from stored summaries")
    result = {"artifacts_verified": len(manifest["artifacts"]),
              "criterion_sha256": json.loads((run/"identity.json").read_text())["criterion_sha256"],
              "selected_cell": {k: agreement["selected"][k] for k in ("energy_hypothesis", "alo_transform")},
              "decision": agreement["decision"]["outcome"],
              "mode": "artifact and stored-fold audit; no new folding"}
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
    if criterion["new_sequence_scoring_enabled"] or criterion["stage3_ready"]:
        raise ValueError("Engine-agreement audit only")
    if not criterion["hypothesis_grid"]["closed"]:
        raise ValueError("Hypothesis grid must be closed before evaluation")

    records, raw = load_references(criterion)
    reference_run = ROOT/criterion["reference_run"]
    model = json.loads((reference_run/"reference_model.json").read_text())
    if sha(reference_run/"reference_model.json") != criterion["reference_model_sha256"]:
        raise ValueError("Frozen reference model hash mismatch")
    if model["new_sequence_scoring_enabled"] is not False:
        raise ValueError("Reference-only model contract required")
    without_alo = json.loads((reference_run/"fit/r_models.json").read_text())["models"]["without_alo"]
    without_component = without_alo["components"][str(without_alo["selected_ncomp"])]
    frozen_predictions = {r["name"]: r["predicted_half_life"]
                          for r in json.loads((reference_run/"python_reference_predictions.json").read_text())}

    selection_names = list(criterion["cohort_split"]["selection_set"])
    if len(set(selection_names)) != len(selection_names) or not set(selection_names) <= set(raw):
        raise ValueError("Selection set must be distinct released record IDs")
    energies = criterion["hypothesis_grid"]["energy_hypotheses"]
    transforms = criterion["hypothesis_grid"]["alo_transforms"]
    tolerances = feature_tolerances(records, criterion["tolerances"]["feature_relative_iqr_fraction"])

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out = ROOT/"results/strand_rnafold_agreement_runs"/stamp
    out.mkdir(parents=True, exist_ok=False)
    print(out, flush=True)
    write(out/"protocol.json", criterion)
    write(out/"feature_tolerances.json",
          {"rule": criterion["tolerances"]["feature_tolerance_rule"],
           "interquartile_fraction": criterion["tolerances"]["feature_relative_iqr_fraction"],
           "tolerances": tolerances})

    implementations = [Path(__file__), ROOT/"src/rnastable/strand_agreement.py",
                       ROOT/"src/rnastable/strand_reference.py",
                       ROOT/"src/rnastable/component_integration.py",
                       ROOT/"src/rnastable/ensemble_worker.py"]
    identities = {}
    for path in implementations:
        target = out/"source"/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        identities[str(path.relative_to(ROOT))] = sha(path)
    write(out/"identity.json",
          {"implementation": identities, "criterion_sha256": sha(args.config),
           "reference_model_sha256": criterion["reference_model_sha256"],
           "source_manifest_sha256": sha(reference_run/"source_manifest.json")})

    folds = out/"folds"
    folds.mkdir()
    rows = []
    engine = None
    for index, record in enumerate(records):
        name = record["name"]
        sequence = FixedSequence(name, raw[name]["sequence"])
        if sequence.sha256 != record["input_sha256"]:
            raise ValueError(f"Sequence identity mismatch for {name}")
        folding = fold_fixed_input(sequence, criterion["substitute_engine"].get("timeout_seconds", 600),
                                   criterion["substitute_engine"]["temperature_c"])
        write(folds/f"{name}.json", folding)
        if folding["status"] != "ok":
            raise ValueError(f"Folding failed for {name}: {folding.get('reason')}")
        settings = folding["settings"]
        expected = criterion["substitute_engine"]
        if (settings["dangles"] != expected["dangles"]
                or settings["parameter_set"] != expected["parameter_set"]
                or settings["temperature_c"] != expected["temperature_c"]
                or folding["tool"] != expected["tool"]):
            raise ValueError(f"Substitute engine settings do not match the frozen criterion for {name}")
        current = {"tool": folding["tool"], "version": folding["version"],
                   "parameter_file_sha256": settings["parameter_file_sha256"],
                   "temperature_c": settings["temperature_c"], "dangles": settings["dangles"]}
        if engine is None:
            engine = current
        elif engine != current:
            raise ValueError("Folding engine identity changed mid-run")
        length = len(sequence.sequence)
        half_widths = rounding_half_widths(raw[name], length)
        row = {"name": name, "cohort": record["cohort"], "length": length,
               "input_sha256": record["input_sha256"],
               "in_selection_set": name in selection_names,
               "released_zero_positions": sum(1 for x in json.loads(raw[name]["bpp_per_pos"]) if x <= 0),
               "released_at_or_above_one_positions": sum(1 for x in json.loads(raw[name]["bpp_per_pos"]) if x >= 1),
               "rnafold_zero_positions": sum(1 for x in folding["paired_probability_per_position"] if x <= 0),
               "rnafold_at_or_above_one_positions": sum(1 for x in folding["paired_probability_per_position"] if x >= 1),
               "reference_features": record["features"], "rounding_half_widths": half_widths,
               "substituted": {}, "energy": {}, "alo": {}}
        for energy in energies:
            for transform in transforms:
                values = substituted_features(folding, energy, transform)
                deltas = feature_deltas(record["features"], values, half_widths)
                row["substituted"][f"{energy}|{transform}"] = {"features": values, "deltas": deltas}
                row["energy"][energy] = deltas["energy_per_length"]["excess_over_rounding"]
                row["alo"][transform] = deltas["alo"]["excess_over_rounding"]
        rows.append(row)
        print(f"folded {index+1}/{len(records)} {name} {length}nt", flush=True)

    selection_rows = [r for r in rows if r["in_selection_set"]]
    evaluation_rows = [r for r in rows if not r["in_selection_set"]]
    if len(selection_rows) != len(selection_names) or not evaluation_rows:
        raise ValueError("Cohort split did not resolve")
    selected = select_cell(selection_rows, energies, transforms)

    def score(energy, transform, subset):
        key = f"{energy}|{transform}"
        deltas = [r["substituted"][key]["deltas"] for r in subset]
        feature_summary = summarize(deltas, tolerances)
        outputs = {}
        for arm, component in (("with_alo", model["component"]), ("without_alo", without_component)):
            per_row = []
            for r in subset:
                diff = output_differences(component, r["reference_features"],
                                          r["substituted"][key]["features"],
                                          frozen_predictions.get(r["name"]) if arm == "with_alo" else None)
                per_row.append(dict(diff, name=r["name"]))
            if arm == "with_alo" and not all(x["frozen_replay_consistent"] for x in per_row):
                raise ValueError("Reference-feature arithmetic does not match the frozen replay")
            outputs[arm] = {"max_abs_difference_hours": max(abs(x["difference_hours"]) for x in per_row),
                            "median_abs_difference_hours":
                                quantile([abs(x["difference_hours"]) for x in per_row], 0.5),
                            "feature_order": component["feature_order"], "per_record": per_row}
        return feature_summary, outputs

    selection_summary, selection_outputs = score(selected["energy_hypothesis"], selected["alo_transform"], selection_rows)
    evaluation_summary, evaluation_outputs = score(selected["energy_hypothesis"], selected["alo_transform"], evaluation_rows)
    null_summary, null_outputs = score(selected["energy_hypothesis"], "identity", evaluation_rows)
    selection_unstable = (evaluation_summary["alo"]["max_excess"] > null_summary["alo"]["max_excess"])

    by_length = {}
    for row in evaluation_rows:
        key = f"{selected['energy_hypothesis']}|{selected['alo_transform']}"
        bucket = by_length.setdefault(str(row["length"]), {"n": 0, "max_alo_excess": 0.0, "max_aup_excess": 0.0})
        bucket["n"] += 1
        for feature, field in (("alo", "max_alo_excess"), ("aup", "max_aup_excess")):
            bucket[field] = max(bucket[field], row["substituted"][key]["deltas"][feature]["excess_over_rounding"])

    decision = decide(evaluation_summary, evaluation_outputs["with_alo"]["max_abs_difference_hours"],
                      criterion["tolerances"]["output_absolute_hours"])
    write(out/"agreement.json", {
        "original_engine": criterion["original_engine"], "substitute_engine_identity": engine,
        "selection_set_size": len(selection_rows), "evaluation_set_size": len(evaluation_rows),
        "evaluation_cohorts": cohort_summary(evaluation_rows, "cohort"),
        "feature_tolerances": tolerances,
        "selected": dict(selected,
                         selection_feature_summary=selection_summary, selection_output=selection_outputs,
                         evaluation_feature_summary=evaluation_summary, evaluation_output=evaluation_outputs),
        "identity_null": {"alo_transform": "identity", "evaluation_feature_summary": null_summary,
                          "evaluation_output": null_outputs},
        "selection_unstable": selection_unstable,
        "evaluation_by_length": by_length,
        "decision": decision})
    write(out/"per_record_features.json", [
        {k: r[k] for k in ("name", "cohort", "length", "input_sha256", "in_selection_set",
                           "released_zero_positions", "released_at_or_above_one_positions",
                           "rnafold_zero_positions", "rnafold_at_or_above_one_positions",
                           "reference_features", "rounding_half_widths", "substituted")}
        for r in rows])

    summary = {"records_folded": len(rows), "selection_set_size": len(selection_rows),
               "evaluation_set_size": len(evaluation_rows),
               "selected_energy_hypothesis": selected["energy_hypothesis"],
               "selected_alo_transform": selected["alo_transform"],
               "selection_unstable": selection_unstable,
               "feature_passes": {k: evaluation_summary[k]["passes"] for k in FEATURE_ORDER},
               "evaluation_max_output_difference_hours":
                   evaluation_outputs["with_alo"]["max_abs_difference_hours"],
               "output_tolerance_hours": criterion["tolerances"]["output_absolute_hours"],
               "decision": decision, "engine": engine,
               "new_sequence_scoring_enabled": False, "stage3_ready": False,
               "interpretation": "Label-free engine agreement on released reference sequences. "
                                 "Not a stability, translation or expression result."}
    write(out/"summary.json", summary)
    artifacts = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob("*")) if p.is_file()}
    write(out/"manifest.json", {"run": stamp, "artifacts": artifacts})
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
