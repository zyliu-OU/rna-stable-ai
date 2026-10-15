#!/usr/bin/env python3
"""Freeze a bounded longer training-only annotation cohort for sampled supervision."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp, publish
from rnastable.exposures import record_exposure
from rnastable.long_training_data import import_long_training
from rnastable.native_journal import atomic_json
from rnastable.population_sampling import PairPopulation
from rnastable.reference_audit import require
from rnastable.exposures import read_exposure, exposure_records
from rnastable.reference import digest
from train_sampled_comparative_development import frozen_inputs


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(
        summary == json.loads((run / "summary.json").read_text()),
        "Retained availability summary differs",
    )
    require(
        summary["complete"] is True
        and summary["model_fitted"] is False
        and summary["holdout_sources_read"] is False
        and summary["test_sources_read"] is False,
        "Availability interpretation changed",
    )
    require(
        digest((run / "manifest.json").read_bytes()) == summary["manifest_sha256"],
        "Availability manifest changed",
    )
    manifest = json.loads((run / "manifest.json").read_text())
    require(manifest["run_dir"] == str(run), "Run identity differs")
    for name, key in [
        ("source_summary.json", "source_summary_sha256"),
        ("import.json", "import_sha256"),
        ("extra_training.json", "extra_training_sha256"),
    ]:
        require(
            digest((run / name).read_bytes()) == manifest[key],
            "Availability source changed: " + name,
        )
    data, source, snapshots, splits = frozen_inputs(run / "source_summary.json")
    records, imported = import_long_training(ROOT / "external/EternaFold", splits)
    require(
        imported == json.loads((run / "import.json").read_text()),
        "Training-only inventory replay differs",
    )
    require(
        records == json.loads((run / "extra_training.json").read_text())["records"],
        "Selected training records differ",
    )
    require(
        summary["availability"] == imported["availability"]
        and summary["maximum_raw_crw_training_length"]
        == imported["maximum_raw_training_length"]
        and summary["training_crw_member_count"] == imported["training_member_count"],
        "Availability counts differ",
    )
    rows = []
    for record in records:
        population = PairPopulation(record)
        rows.append(
            {
                "id": record["id"],
                "length": len(record["sequence"]),
                "rna_type": record["rna_type"],
                "population_positive": population.positive_count,
                "population_negative": population.negative_count,
                "excluded_contacts": population.excluded,
            }
        )
    require(
        rows == summary["rows"]
        and summary["extra_training"] == str(run / "extra_training.json"),
        "Population inventory differs",
    )
    event = manifest["exposure_event"]
    if records:
        path = Path(event["path"])
        require(
            path.resolve().parent == (run / "exposures").resolve()
            and digest(path.read_bytes()) == event["sha256"],
            "Exposure changed",
        )
        data = read_exposure(path)
        require(
            data["stage"] == "training_started"
            and data["records"]
            == exposure_records(records, str(run) + " training_started"),
            "Exposure records differ",
        )
    else:
        require(
            event is None and not list((run / "exposures").glob("*.json")),
            "Empty availability result must not invent exposure",
        )
    print(
        "Longer training availability audit passed: fixed1025–4096nt range; training sources only; no fitting or new validation/test."
    )
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        return audit(ROOT / "results/long_population_training_data_summary.json")
    source_bytes, source, snapshots, splits = frozen_inputs(
        ROOT / "results/exact_comparative_development_summary.json"
    )
    records, imported = import_long_training(ROOT / "external/EternaFold", splits)
    run = ROOT / "results/long_population_training_data_runs" / timestamp()
    run.mkdir(parents=True)
    atomic_json(
        run / "extra_training.json",
        {
            "schema_version": 1,
            "dataset_id": "longer_crw_training_only",
            "records": records,
        },
    )
    atomic_json(run / "import.json", imported)
    (run / "source_summary.json").write_bytes(source_bytes)
    event = record_exposure(run, "training_started", records) if records else None
    rows = []
    for record in records:
        population = PairPopulation(record)
        rows.append(
            {
                "id": record["id"],
                "length": len(record["sequence"]),
                "rna_type": record["rna_type"],
                "population_positive": population.positive_count,
                "population_negative": population.negative_count,
                "excluded_contacts": population.excluded,
            }
        )
    manifest = {
        "run_dir": str(run),
        "source_summary_sha256": digest(source_bytes),
        "import_sha256": digest((run / "import.json").read_bytes()),
        "extra_training_sha256": digest((run / "extra_training.json").read_bytes()),
        "exposure_event": event,
        "policy": imported["policy"],
    }
    atomic_json(run / "manifest.json", manifest)
    summary = {
        "complete": True,
        "run_dir": str(run),
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "holdout_sources_read": False,
        "test_sources_read": False,
        "model_fitted": False,
        "availability": imported["availability"],
        "maximum_raw_crw_training_length": imported["maximum_raw_training_length"],
        "training_crw_member_count": imported["training_member_count"],
        "rows": rows,
        "extra_training": str(run / "extra_training.json"),
        "limitations": [
            "Additional upstream training annotations only; the existing validation cohort remains unchanged.",
            "Processed comparative annotations are not new experimental measurements.",
            "Sequence/accession separation does not establish family/clan independence or generalization.",
        ],
    }
    atomic_json(run / "summary.json", summary)
    report = [
        "# Longer training-only comparative annotation cohort",
        "",
        imported["policy"],
        "",
        "| ID | Length | RNA type | Positive legal pairs | Full negative population |",
        "|---|---:|---|---:|---:|",
    ]
    for row in rows:
        report.append(
            f"| {row['id']} | {row['length']} | {row['rna_type']} | {row['population_positive']} | {row['population_negative']} |"
        )
    report += [
        "",
        f"Availability: {imported['availability']}. Inspected {imported['training_member_count']} CRW training members; maximum raw annotation length {imported['maximum_raw_training_length']}nt. Fixed requested range {imported['minimum']}–{imported['maximum']}nt. No fit or new validation labels.",
        "",
        *summary["limitations"],
    ]
    publish(
        ROOT,
        "long_population_training_data",
        summary,
        rows,
        [
            "id",
            "length",
            "rna_type",
            "population_positive",
            "population_negative",
            "excluded_contacts",
        ],
        "\n".join(report) + "\n",
    )
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    main()
