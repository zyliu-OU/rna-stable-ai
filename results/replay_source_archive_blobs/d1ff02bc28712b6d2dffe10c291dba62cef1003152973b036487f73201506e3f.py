"""Descriptive paired comparison of frozen native prior studies and extended references."""

import json
from pathlib import Path
from .reference import digest
from .reference_audit import require
from .sequences import read_fasta

POLICIES = ("random_pool", "compatibility_only", "checkpoint_prior")
SEARCH_KEYS = (
    "steps",
    "pool_size",
    "max_mutations",
    "beam_size",
    "timeout_seconds",
    "memory_limit_gib",
    "min_improvement_kcal_mol",
    "temperature_c",
    "preserve_protein",
    "protected_positions",
)


def control_trace(search):
    return {
        "status": search["status"],
        "sequence": search["sequence"],
        "baseline": {
            key: search["baseline"].get(key)
            for key in ("status", "mfe_kcal_mol", "structure")
        },
        "history": [
            {
                **{
                    key: row.get(key)
                    for key in ("step", "pool", "selected_index", "accepted")
                },
                "fold": {
                    key: row.get("fold", {}).get(key)
                    for key in ("status", "mfe_kcal_mol", "structure")
                },
            }
            for row in search["history"]
        ],
    }


def difference(first, second):
    return first - second if first is not None and second is not None else None


def inventory(summary, label):
    require(
        summary["complete"] is True
        and summary["test_accuracy_evaluated"] is False
        and summary["model_fitted"] is False,
        "Expected completed native-only study",
    )
    run = Path(summary["run_dir"])
    require(
        summary == json.loads((run / "summary.json").read_text()),
        "Retained study differs",
    )
    require(
        digest((run / "manifest.json").read_bytes()) == summary["manifest_sha256"],
        "Study manifest changed",
    )
    records = {}
    rows = []
    model_identity = None
    search_config = None
    for item in summary["components"]:
        path = Path(item["summary"])
        require(digest(path.read_bytes()) == item["sha256"], "Component changed")
        component = json.loads(path.read_text())
        child = Path(component["run_dir"])
        manifest = json.loads((child / "manifest.json").read_text())
        require(
            digest((child / "manifest.json").read_bytes())
            == component["manifest_sha256"],
            "Child manifest changed",
        )
        config = manifest["config"]
        base = {key: config[key] for key in SEARCH_KEYS}
        if search_config is None:
            search_config = base
        require(search_config == base, "Search settings differ within study")
        source = json.loads((child / "source_summary.json").read_text())
        identity = {
            "label": label,
            "model_seed": source["config"]["seed"],
            "pair_features": source["config"].get("pair_features"),
            "checkpoint_sha256": manifest["checkpoint_sha256"],
        }
        if model_identity is None:
            model_identity = identity
        require(identity == model_identity, "Study checkpoint differs")
        record = read_fasta(child / "input.fasta")[0]
        key = (component["input_id"], component["seed"])
        require(key not in records, "Duplicate input/seed")
        require(
            record[0] == key[0] and len(record[1]) == int(key[0].split("_")[-1]),
            "Input identity/length differs",
        )
        arms = {
            policy: json.loads((child / policy / "result.json").read_text())
            for policy in POLICIES
        }
        require(
            [arm["row"] for arm in arms.values()] == component["rows"],
            "Component arm rows differ",
        )
        records[key] = {
            "input_sha256": digest(record[1].encode()),
            "config": base,
            "arms": arms,
            "reference_timeout_seconds": config["finalist_timeout_seconds"],
        }
        rows.extend(
            {
                "model": label,
                "model_seed": identity["model_seed"],
                "input_id": key[0],
                "search_seed": key[1],
                **arm["row"],
                "finalist_sha256": digest(arm["search"]["sequence"].encode()),
                "reference_timeout_seconds": config["finalist_timeout_seconds"],
                "reference_source": "original_study",
            }
            for arm in arms.values()
        )
    expected = {
        (f"synthetic_{length}", seed)
        for length in (1000, 5000, 10000)
        for seed in (20261006, 20261007)
    }
    require(set(records) == expected, "Fixed paired native study plan differs")
    require(len(rows) == 18, "Native trajectory inventory differs")
    return model_identity, records, rows


def compare_studies(stack, extension, helix_studies):
    stack_identity, stack_records, stack_rows = inventory(stack, "stack_seed20261006")
    require(
        stack_identity["pair_features"] == "adjacent_stackability"
        and stack_identity["model_seed"] == 20261006,
        "Expected stack control source",
    )
    require(
        extension["complete"] is True
        and extension["test_accuracy_evaluated"] is False
        and extension["model_fitted"] is False
        and extension["new_search_performed"] is False,
        "Reference extension scope differs",
    )
    extension_run = Path(extension["run_dir"])
    require(
        extension == json.loads((extension_run / "summary.json").read_text())
        and digest((extension_run / "manifest.json").read_bytes())
        == extension["manifest_sha256"],
        "Extension binding differs",
    )
    extension_manifest = json.loads((extension_run / "manifest.json").read_text())
    require(
        extension_manifest["source_summary_sha256"]
        == digest((Path(stack["run_dir"]) / "summary.json").read_bytes()),
        "Extension belongs to another study",
    )
    require(
        extension_manifest["config"]["timeout_seconds"] == 300,
        "Extended reference budget differs",
    )
    extended = {
        (row["input_id"], row["seed"], row["policy"]): row for row in extension["rows"]
    }
    require(
        len(extended) == len(extension["rows"]) == 6,
        "Extended reference inventory differs",
    )
    arm_bindings = {
        (arm["seed"], arm["policy"]): arm for arm in extension_manifest["arms"]
    }
    for row in stack_rows:
        if row["input_id"] != "synthetic_10000":
            continue
        key = (row["input_id"], row["search_seed"], row["policy"])
        require(key in extended, "Missing extended reference")
        extra = extended[key]
        binding = arm_bindings[(row["search_seed"], row["policy"])]
        require(
            row["finalist_sha256"] == binding["finalist_sha256"]
            and stack_records[key[:2]]["input_sha256"] == binding["input_sha256"],
            "Extended finalist/input differs",
        )
        for name in (
            "candidate_vienna_delta_kcal_mol",
            "selected_vienna_delta_kcal_mol",
            "selection_source",
            "selection_reason",
            "selected_mutations",
        ):
            row[name] = extra[name]
        row["reference_timeout_seconds"] = 300
        row["reference_source"] = "separate_frozen_finalist_extension"
    all_rows = list(stack_rows)
    identities = [stack_identity]
    paired = []
    control_checks = []
    for label, summary in helix_studies:
        identity, records, rows = inventory(summary, label)
        require(
            identity["pair_features"] == "local_helix_context_v1",
            "Expected helix feature model",
        )
        identities.append(identity)
        for key, record in records.items():
            require(
                record["input_sha256"] == stack_records[key]["input_sha256"]
                and record["config"] == stack_records[key]["config"],
                "Paired input/search configuration differs",
            )
            require(
                record["reference_timeout_seconds"] == 300,
                "Helix reference budget differs",
            )
            for policy in ("random_pool", "compatibility_only"):
                old = stack_records[key]["arms"][policy]["search"]
                new = record["arms"][policy]["search"]
                require(
                    control_trace(old) == control_trace(new),
                    "Model-independent control trajectory differs",
                )
                control_checks.append(
                    {
                        "model": label,
                        "input_id": key[0],
                        "search_seed": key[1],
                        "policy": policy,
                        "finalist_and_linearfold_energy_identical": True,
                        "every_pool_decision_native_structure_and_energy_identical": True,
                    }
                )
        lookup = {
            (row["input_id"], row["search_seed"], row["policy"]): row for row in rows
        }
        stack_lookup = {
            (row["input_id"], row["search_seed"], row["policy"]): row
            for row in stack_rows
        }
        for key in sorted(records):
            old = stack_lookup[(*key, "checkpoint_prior")]
            new = lookup[(*key, "checkpoint_prior")]
            known = (
                new["candidate_vienna_delta_kcal_mol"] is not None
                and old["candidate_vienna_delta_kcal_mol"] is not None
            )
            paired.append(
                {
                    "model": label,
                    "model_seed": identity["model_seed"],
                    "input_id": key[0],
                    "search_seed": key[1],
                    "stack_selected_delta_kcal_mol": old[
                        "selected_vienna_delta_kcal_mol"
                    ],
                    "helix_selected_delta_kcal_mol": new[
                        "selected_vienna_delta_kcal_mol"
                    ],
                    "helix_minus_stack_selected_delta_kcal_mol": difference(
                        new["selected_vienna_delta_kcal_mol"],
                        old["selected_vienna_delta_kcal_mol"],
                    )
                    if known
                    else None,
                    "helix_minus_compatibility_selected_delta_kcal_mol": difference(
                        new["selected_vienna_delta_kcal_mol"],
                        lookup[(*key, "compatibility_only")][
                            "selected_vienna_delta_kcal_mol"
                        ],
                    )
                    if known
                    and lookup[(*key, "compatibility_only")][
                        "candidate_vienna_delta_kcal_mol"
                    ]
                    is not None
                    else None,
                    "paired_reference_outcomes_known": known,
                    "stack_selection_reason": old["selection_reason"],
                    "helix_selection_reason": new["selection_reason"],
                    "interpretation": "Negative difference means lower native selected energy; descriptive shared-input result.",
                }
            )
        all_rows.extend(rows)
    return {
        "model_identities": identities,
        "rows": all_rows,
        "paired_prior_differences": paired,
        "control_reproducibility_checks": control_checks,
        "accuracy_evaluated": False,
        "test_evaluated": False,
        "model_fitted": False,
        "limitations": [
            "Previously exposed synthetic inputs; model/search seeds share sequences and are not independent biological samples.",
            "Native selected energy is not labelled structure accuracy, biological stability, retained function or generalization.",
            "All10000nt stack reference outcomes use the separately budgeted300-second frozen-finalist extension.1000/5000nt stack references used30 seconds and completed; helix studies used300 seconds for every length.",
            "Matched successful outcomes do not imply equal runtime/cost. Extra reference requests and repeated controls retain separate budgets.",
            "No best model/checkpoint/search seed is selected or deployed from this comparison. All outcomes, including inferior priors and input retention, remain reported.",
        ],
    }
