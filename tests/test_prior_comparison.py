import json
from pathlib import Path
from rnastable.native_journal import atomic_json
from rnastable.prior_comparison import compare_studies
from rnastable.reference import digest

POLICIES = ("random_pool", "compatibility_only", "checkpoint_prior")


def study(tmp_path, name, model_seed, features):
    run = tmp_path / name
    run.mkdir()
    atomic_json(run / "manifest.json", {"fixture": name})
    components = []
    config = {
        "seed": 7,
        "steps": 8,
        "pool_size": 16,
        "max_mutations": 16,
        "beam_size": 100,
        "timeout_seconds": 30,
        "finalist_timeout_seconds": 300 if features == "local_helix_context_v1" else 30,
        "memory_limit_gib": 4,
        "min_improvement_kcal_mol": 0.1,
        "temperature_c": 37,
        "preserve_protein": False,
        "protected_positions": [1, 2, 3],
    }
    for length in (1000, 5000, 10000):
        for seed in (20261006, 20261007):
            child = run / f"{length}_{seed}"
            child.mkdir()
            sequence = "G" + "A" * (length - 2) + "C"
            (child / "input.fasta").write_text(f">synthetic_{length}\n{sequence}\n")
            atomic_json(
                child / "source_summary.json",
                {"config": {"seed": model_seed, "pair_features": features}},
            )
            atomic_json(
                child / "manifest.json",
                {
                    "config": {**config, "seed": seed},
                    "checkpoint_sha256": name,
                    "fixture": True,
                },
            )
            rows = []
            for policy in POLICIES:
                arm = child / policy
                arm.mkdir()
                search = {
                    "status": "completed",
                    "sequence": sequence,
                    "baseline": {
                        "status": "ok",
                        "mfe_kcal_mol": -10.0,
                        "structure": "." * length,
                    },
                    "best": {"mfe_kcal_mol": -12.0},
                    "history": [
                        {
                            "step": 1,
                            "pool": [sequence],
                            "selected_index": 0,
                            "accepted": True,
                            "fold": {
                                "status": "ok",
                                "mfe_kcal_mol": -12.0,
                                "structure": "." * length,
                            },
                        }
                    ],
                }
                delta = (
                    -3.0
                    if features == "local_helix_context_v1"
                    and policy == "checkpoint_prior"
                    else -1.0
                )
                row = {
                    "policy": policy,
                    "candidate_vienna_delta_kcal_mol": delta,
                    "selected_vienna_delta_kcal_mol": delta,
                    "selection_source": "finalist",
                    "selection_reason": "confirmed_improvement",
                    "selected_mutations": 0,
                }
                atomic_json(arm / "result.json", {"search": search, "row": row})
                rows.append(row)
            summary = {
                "run_dir": str(child),
                "input_id": "synthetic_" + str(length),
                "seed": seed,
                "manifest_sha256": digest((child / "manifest.json").read_bytes()),
                "rows": rows,
            }
            atomic_json(child / "summary.json", summary)
            components.append(
                {
                    "summary": str(child / "summary.json"),
                    "sha256": digest((child / "summary.json").read_bytes()),
                }
            )
    summary = {
        "complete": True,
        "run_dir": str(run),
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "test_accuracy_evaluated": False,
        "model_fitted": False,
        "components": components,
    }
    atomic_json(run / "summary.json", summary)
    return summary


def extension(tmp_path, stack):
    run = tmp_path / "extension"
    run.mkdir()
    arms = []
    rows = []
    for seed in (20261006, 20261007):
        sequence = "G" + "A" * 9998 + "C"
        for policy in POLICIES:
            arms.append(
                {
                    "seed": seed,
                    "policy": policy,
                    "input_sha256": digest(sequence.encode()),
                    "finalist_sha256": digest(sequence.encode()),
                }
            )
            rows.append(
                {
                    "input_id": "synthetic_10000",
                    "seed": seed,
                    "policy": policy,
                    "candidate_vienna_delta_kcal_mol": -2.0,
                    "selected_vienna_delta_kcal_mol": -2.0,
                    "selection_source": "finalist",
                    "selection_reason": "confirmed_improvement",
                    "selected_mutations": 0,
                }
            )
    atomic_json(
        run / "manifest.json",
        {
            "config": {"timeout_seconds": 300},
            "source_summary_sha256": digest(
                (Path(stack["run_dir"]) / "summary.json").read_bytes()
            ),
            "arms": arms,
        },
    )
    summary = {
        "complete": True,
        "run_dir": str(run),
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "test_accuracy_evaluated": False,
        "model_fitted": False,
        "new_search_performed": False,
        "rows": rows,
    }
    atomic_json(run / "summary.json", summary)
    return summary


def test_prior_comparison_uses_extended_stack_references_and_all_controls(tmp_path):
    stack = study(tmp_path, "stack", 20261006, "adjacent_stackability")
    helix = study(tmp_path, "helix", 20261007, "local_helix_context_v1")
    extra = extension(tmp_path, stack)
    result = compare_studies(stack, extra, [("helix7", helix)])
    assert (
        len(result["rows"]) == 36
        and len(result["paired_prior_differences"]) == 6
        and len(result["control_reproducibility_checks"]) == 12
    )
    tenk = [
        row
        for row in result["paired_prior_differences"]
        if row["input_id"] == "synthetic_10000"
    ]
    assert all(row["helix_minus_stack_selected_delta_kcal_mol"] == -1.0 for row in tenk)
    assert all(
        row["every_pool_decision_native_structure_and_energy_identical"]
        for row in result["control_reproducibility_checks"]
    )
    assert result["accuracy_evaluated"] is False


def test_prior_comparison_retains_unknown_reference_outcomes(tmp_path):
    stack = study(tmp_path, "stack", 20261006, "adjacent_stackability")
    helix = study(tmp_path, "helix", 20261007, "local_helix_context_v1")
    extra = extension(tmp_path, stack)
    path = Path(helix["components"][0]["summary"])
    component = json.loads(path.read_text())
    arm = path.parent / "checkpoint_prior/result.json"
    data = json.loads(arm.read_text())
    data["row"].update(
        candidate_vienna_delta_kcal_mol=None,
        selected_vienna_delta_kcal_mol=None,
        selection_reason="validation_failed",
    )
    atomic_json(arm, data)
    component["rows"][-1] = data["row"]
    atomic_json(path, component)
    helix["components"][0]["sha256"] = digest(path.read_bytes())
    atomic_json(Path(helix["run_dir"]) / "summary.json", helix)
    result = compare_studies(stack, extra, [("helix7", helix)])
    unknown = [
        row
        for row in result["paired_prior_differences"]
        if row["helix_selection_reason"] == "validation_failed"
    ]
    assert (
        len(unknown) == 1
        and unknown[0]["paired_reference_outcomes_known"] is False
        and unknown[0]["helix_minus_stack_selected_delta_kcal_mol"] is None
    )
