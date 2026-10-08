"""Complete per-record and fixed-slice diagnostics on reused checkpoint validation."""

import statistics
from .reference_audit import require
from .scoring import structure_agreement
from .reference import digest

HEADS = ("baseline", "stack", "helix")
SEEDS = (20261006, 20261007, 20261008)
METRICS = ("pair_precision", "pair_recall", "pair_f1")


def source_group(record):
    identifier = record["id"]
    if "PDB_" in identifier:
        return "PDB-derived"
    if "RFA_" in identifier:
        return "Rfam-comparative"
    if "CRW_" in identifier:
        return "CRW-comparative"
    raise ValueError("Unknown frozen development provenance group")


def length_group(length):
    if not 1 <= length <= 1024:
        raise ValueError("Frozen diagnostic length outside exact sparse cohort")
    for lower, upper in ((1, 64), (65, 128), (129, 256), (257, 1024)):
        if lower <= length <= upper:
            return str(lower) + ".." + str(upper)


def analyze(records, components):
    require(
        len({record["id"] for record in records}) == len(records) and bool(records),
        "Validation record inventory differs",
    )
    inventory = {record["id"]: record for record in records}
    scores = {}
    rows = []
    require(len(components) == 9, "Expected all nine head/seed checkpoints")
    for component, predictions in components:
        key = (component["seed"], component["head"])
        require(
            key[0] in SEEDS and key[1] in HEADS and key not in scores,
            "Duplicate/unknown head-seed component",
        )
        require(
            len(predictions) == len(records)
            and {row["id"] for row in predictions} == set(inventory),
            "Prediction inventory differs",
        )
        by_id = {row["id"]: row for row in predictions}
        scores[key] = {}
        for record in records:
            prediction = by_id[record["id"]]
            require(
                prediction.get("status") == "ok"
                and prediction["sequence"] == record["sequence"],
                "Prediction sequence/status differs",
            )
            metrics = structure_agreement(prediction["structure"], record["structure"])
            scores[key][record["id"]] = metrics
            rows.append(
                {
                    "id": record["id"],
                    "sequence_sha256": digest(record["sequence"].encode()),
                    "length": len(record["sequence"]),
                    "reference_kind": record["reference_kind"],
                    "source_group": source_group(record),
                    "length_group": length_group(len(record["sequence"])),
                    "model_seed": key[0],
                    "head": key[1],
                    **{metric: metrics[metric] for metric in METRICS},
                }
            )
        require(
            statistics.mean(scores[key][record["id"]]["pair_f1"] for record in records)
            == component["selected_validation_pair_f1"]
            or abs(
                statistics.mean(
                    scores[key][record["id"]]["pair_f1"] for record in records
                )
                - component["selected_validation_pair_f1"]
            )
            < 1e-15,
            "Selected checkpoint score differs",
        )
    require(
        set(scores) == {(seed, head) for seed in SEEDS for head in HEADS},
        "Missing head-seed fit",
    )
    slices = []
    definitions = [("all", "all", records)]
    for dimension, groups in [
        ("source_group", ("PDB-derived", "Rfam-comparative", "CRW-comparative")),
        ("length_group", ("1..64", "65..128", "129..256", "257..1024")),
        ("reference_kind", ("experimental", "computational")),
    ]:
        for group in groups:
            definitions.append(
                (
                    dimension,
                    group,
                    [
                        record
                        for record in records
                        if (
                            source_group(record)
                            if dimension == "source_group"
                            else length_group(len(record["sequence"]))
                            if dimension == "length_group"
                            else record["reference_kind"]
                        )
                        == group
                    ],
                )
            )
    for dimension, group, selected in definitions:
        for seed in SEEDS:
            for head in HEADS:
                slices.append(
                    {
                        "dimension": dimension,
                        "group": group,
                        "model_seed": seed,
                        "head": head,
                        "planned_records": len(selected),
                        "measured_records": len(selected),
                        **{
                            metric: statistics.mean(
                                scores[(seed, head)][record["id"]][metric]
                                for record in selected
                            )
                            if selected
                            else None
                            for metric in METRICS
                        },
                    }
                )
    per_record = []
    for record in records:
        values = {
            head: statistics.mean(
                scores[(seed, head)][record["id"]]["pair_f1"] for seed in SEEDS
            )
            for head in HEADS
        }
        per_record.append(
            {
                "id": record["id"],
                "length": len(record["sequence"]),
                "source_group": source_group(record),
                "reference_kind": record["reference_kind"],
                "baseline_mean_f1": values["baseline"],
                "stack_mean_f1": values["stack"],
                "helix_mean_f1": values["helix"],
                "helix_minus_baseline_mean_f1": values["helix"] - values["baseline"],
                "helix_minus_stack_mean_f1": values["helix"] - values["stack"],
            }
        )
    return {
        "records": rows,
        "slices": slices,
        "per_record_mean_across_model_seeds": per_record,
        "record_count": len(records),
        "planned_checkpoint_record_predictions": 9 * len(records),
        "measured_checkpoint_record_predictions": len(rows),
        "accuracy_scope": "previously_exposed_development_validation_only",
        "new_predictions_computed": False,
        "test_evaluated": False,
        "checkpoint_selected": False,
        "limitations": [
            "Reused selected checkpoints and development labels; slices are descriptive error diagnostics after exposure, not independent tests.",
            "PDB-derived processed annotations retain their source reference-kind tag; this is not a new experimental assay.",
            "Three model initialization seeds share each record. Spread or mean across them does not estimate independent biological uncertainty.",
            "Length bins are fixed and empty bins retain a zero denominator/unknown mean. No new RNA family independence is inferred from source groups.",
            "Every record and all nine fitted checkpoints remain present; regressions and poor slices are not filtered out.",
        ],
    }
