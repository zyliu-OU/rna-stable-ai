#!/usr/bin/env python3
"""The end-to-end design workflow, run on predicted quantities only.

The user stated on 2026-10-20 that no experimental data exists yet and asked for
the whole workflow to be built now, to be verified and improved later. Gate v6
records that decision and opens `new_sequence_scoring_enabled` and
`expression_candidate_design_enabled` for exactly that purpose.

Stages:

  1. pool        windowed synonymous variants of the recorded Fluc ORF
  2. assemble    5'UTR + variant CDS + 3'UTR, through assemble_variant, which
                 still hash-verifies the reference and requires synonymy
  3. fold        ViennaRNA ensemble fold, the SAME settings as the frozen
                 reference record, in parallel isolated workers
  4. stability   strand_rnafold_calibration_v1 -> predicted in-solution
                 half-life in hours, with extrapolation flagged per member
  5. translation RiboNN released predicted_TE_A549, through the existing
                 verified inference driver
  6. select      Pareto front over the two objectives, then the panel subset
                 that maximises dominated hypervolume
  7. bo replay   qLogNEHVI run sequentially over the pool with the precomputed
                 objectives as an oracle, against a random baseline, to show
                 what the optimizer would buy when scoring is expensive

What this is not. Every value is a PREDICTION from an unvalidated model on a
quantity the planned assay does not measure. There is no measurement of any
construct in this project. A selected panel ILLUSTRATES THE PIPELINE; it is not
a recommendation to synthesise or assay anything, and the panel size is a
declared placeholder because the collaborator has not stated the assay's
capacity. No composite score is emitted at any stage.
"""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import csv
import hashlib
import json
import random
import statistics
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.component_integration import fold_fixed_input
from rnastable.pareto import hypervolume_2d, non_dominated_indices
from rnastable.synonymous_window import build_pool
from rnastable.transcript_assembly import assemble_variant

GATE = ROOT / "configs/stage2_to_stage3_gate_v6_2026-10-20.json"
SPEC = ROOT / "configs/synonymous_window_design_space_v2_2026-10-20.json"
FORMULATION = ROOT / "configs/pareto_objective_formulation_v1_2026-10-20.json"
INPUTS = ROOT / "configs/transcript_inputs_v1_2026-10-19.json"
CALIBRATION = ROOT / "results/strand_rnafold_calibration_runs/20261019T174049.053308Z"
RIBONN_BASE = ROOT / "configs/ribonn_reference_inference_v2_2026-10-19.json"
OBJECTIVES = ("predicted_in_solution_half_life_hours", "predicted_TE_A549")
# A placeholder, and labelled as one everywhere it appears. The collaborator has
# not stated how many constructs the assay can carry.
DEFAULT_PANEL = 12


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require_open_gate():
    gate = json.loads(GATE.read_text())
    switches = gate["switches_opened_here"]
    for name in ("new_sequence_scoring_enabled", "expression_candidate_design_enabled"):
        if not switches.get(name, {}).get("now"):
            raise SystemExit(f"{GATE.name} does not record {name} as open")
    return gate


def calibration_model():
    model = json.loads((CALIBRATION / "calibration_model.json").read_text())
    rows = list(csv.DictReader((CALIBRATION / "features/train_features.csv").open()))
    domain = {feature: {"min": min(float(r[feature]) for r in rows),
                        "max": max(float(r[feature]) for r in rows)}
              for feature in ("energy_per_length", "GC", "aup")}
    return model, model["component"], domain


def fold_one(payload):
    """Fold one assembled transcript in an isolated worker.

    The worker already emits the calibration's three feature candidates, so
    they are taken from it rather than recomputed, and the energy hypothesis
    stays the `ensemble_energy_per_nt` the frozen agreement criterion selected.
    """
    from rnastable.component_integration import Transcript

    member, tx_id, sequence, cds_start, cds_end, timeout, temperature = payload
    record = Transcript(tx_id=tx_id, sequence=sequence, cds_start=cds_start,
                        cds_end=cds_end, provenance="design pool member",
                        assay_context="provisional; no measurement exists")
    result = fold_fixed_input(record, timeout=timeout, temperature=temperature)
    if result.get("status") != "ok":
        return {"member": member, "tx_id": tx_id, "status": result.get("status", "error"),
                "reason": result.get("reason"), "fold": None}
    candidates = result["feature_candidates"]
    return {
        "member": member,
        "tx_id": tx_id,
        "status": "ok",
        "fold": {
            "mfe_kcal_mol": result["mfe_kcal_mol"],
            "ensemble_free_energy_kcal_mol": result["ensemble_free_energy_kcal_mol"],
            "ensemble_free_energy_per_nt_kcal_mol": candidates["ensemble_energy_per_nt"],
            "mean_unpaired_probability": candidates["aup"],
            "gc_fraction": candidates["gc_fraction"],
            "strand_alo": candidates["alo"],
            "runtime_seconds": result.get("runtime_seconds"),
            "tool": result["tool"],
            "version": result["version"],
            "settings": result["settings"],
        },
    }


def design_features(members, window_indices):
    """Binary substituted/not per window position, scaled to [0, 1].

    The optimizer domain is the edit pattern itself, not a hand-made summary,
    so the representation is one coordinate per substitutable position. A
    summary such as edit count would hide which positions were changed, which
    is the thing being chosen.
    """
    positions = sorted(window_indices)
    rows = []
    for member in members:
        substituted = set(member["substituted_codon_indices"])
        rows.append([1.0 if i in substituted else 0.0 for i in positions])
    return rows, positions


def bo_replay(features, objectives, budget, seed, reference_point):
    """Sequential qLogNEHVI over the pool, with the pool's values as an oracle.

    Not a claim about the optimizer's value on the real problem. It answers one
    question: if each member cost a fold and a RiboNN pass, how much of the
    exhaustively computed front would the optimizer have recovered inside a
    budget, against spending that budget at random.
    """
    from rnastable.multi_objective_bo import select_next_pareto

    unique = {}
    for index, row in enumerate(features):
        unique.setdefault(tuple(row), index)
    pool_ids = sorted(unique.values())
    if len(pool_ids) < budget + 3:
        return None
    pool_features = [features[i] for i in pool_ids]
    feasible = [True] * len(pool_features)
    initial = [0, len(pool_ids) // 2, len(pool_ids) - 1]
    observed = {i: tuple(objectives[pool_ids[i]]) for i in initial}
    history = list(initial)
    while len(history) < budget:
        index, _ = select_next_pareto(pool_features, observed, feasible, seed, reference_point)
        observed[index] = tuple(objectives[pool_ids[index]])
        history.append(index)
    chosen = [pool_ids[i] for i in history]
    rng = random.Random(seed)
    random_ids = rng.sample(pool_ids, budget)
    true_front = set(non_dominated_indices([tuple(row) for row in objectives]))
    return {
        "budget": budget,
        "pool_size_unique_representations": len(pool_ids),
        "selected_members": chosen,
        "hypervolume": hypervolume_2d([objectives[i] for i in chosen], reference_point),
        "front_members_found": len(set(chosen) & true_front),
        "random_members": random_ids,
        "random_hypervolume": hypervolume_2d([objectives[i] for i in random_ids], reference_point),
        "random_front_members_found": len(set(random_ids) & true_front),
        "exhaustive_hypervolume": hypervolume_2d(
            [tuple(row) for row in objectives], reference_point),
        "true_front_size": len(true_front),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--spec", default=None,
                        help="design-space config; defaults to the current version")
    parser.add_argument("--gc-mode", choices=("free", "neutral"), default="neutral")
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--jobs", type=int, default=24)
    parser.add_argument("--panel", type=int, default=DEFAULT_PANEL)
    parser.add_argument("--bo-budget", type=int, default=24)
    parser.add_argument("--fold-timeout", type=int, default=300)
    parser.add_argument("--skip-ribonn", action="store_true",
                        help="stop after the stability side, for a quick mechanics check")
    parser.add_argument("--out", default="results/design_workflow_runs")
    args = parser.parse_args(argv)

    require_open_gate()
    spec_path = ROOT / args.spec if args.spec else SPEC
    spec = json.loads(spec_path.read_text())
    window_codons = spec["window"]["codons"]
    out = ROOT / args.out / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True, exist_ok=False)
    print(out, flush=True)

    # --- 1. pool -----------------------------------------------------------
    cds = "".join((ROOT / spec["reference"]["orf"]).read_text().split())
    pool = build_pool(cds, window_codons=window_codons, size=args.size,
                      seed=spec["sampling"]["seed"],
                      max_homopolymer=spec["constraints"]["max_homopolymer_run"],
                      gc_mode=args.gc_mode)
    print(f"1. pool: {pool['size']} members, gc_mode={args.gc_mode}, "
          f"{pool['substitutable_positions']} substitutable positions", flush=True)

    # --- 2. assemble -------------------------------------------------------
    members, jobs = [], []
    for member in pool["members"]:
        orf = "".join(member["codons"])
        tx_id = f"FLUC-DESIGN-{args.gc_mode[:3].upper()}-{member['member']:04d}"
        record, report = assemble_variant(orf, INPUTS, tx_id, "design pool member",
                                          "provisional; no measurement exists")
        if report.synonymous_verified is not True:
            raise SystemExit(f"Member {member['member']} failed synonymy verification")
        members.append({
            "member": member["member"], "tx_id": tx_id, "is_reference": member["is_reference"],
            "orf": orf, "orf_sha256": member["orf_sha256"],
            "substituted_codon_indices": member["substituted_codon_indices"],
            "substitution_count": member["substitution_count"],
            "window_gc_fraction": member["window_gc_fraction"],
            "orf_gc_fraction": member["orf_gc_fraction"],
            "transcript_length_nt": report.transcript_length_nt,
            "transcript_sha256_rna": report.transcript_sha256_rna,
            "reference_cds_sha256_dna_uppercase": report.reference_cds_sha256_dna_uppercase,
            "protein_sha256": report.protein_sha256,
        })
        jobs.append((member["member"], tx_id, record.sequence, record.cds_start,
                     record.cds_end, args.fold_timeout, 37.0))
    lengths = {m["transcript_length_nt"] for m in members}
    proteins = {m["protein_sha256"] for m in members}
    if len(lengths) != 1 or len(proteins) != 1:
        raise SystemExit("Assembled variants differ in length or protein; refusing to continue")
    print(f"2. assembled: {len(members)} transcripts, all {lengths.pop()} nt, "
          f"one protein hash", flush=True)
    (out / "pool.json").write_text(json.dumps(
        {"gc_mode": args.gc_mode, "window_codon_indices": pool["window_codon_indices"],
         "members": members}, indent=2, sort_keys=True))

    # --- 3. fold -----------------------------------------------------------
    folds = {}
    with ProcessPoolExecutor(max_workers=args.jobs) as executor:
        for done, result in enumerate(executor.map(fold_one, jobs), 1):
            folds[result["member"]] = result
            if done % 50 == 0 or done == len(jobs):
                print(f"3. folded {done}/{len(jobs)}", flush=True)
    failed = [m for m, r in folds.items() if r["status"] != "ok"]
    print(f"3. folds ok: {len(folds) - len(failed)}/{len(folds)}", flush=True)

    # --- 4. stability ------------------------------------------------------
    model, arm, domain = calibration_model()
    for entry in members:
        fold = folds[entry["member"]]
        if fold["status"] != "ok":
            entry["stability"] = None
            continue
        # GC is whole-transcript GC in percent, the form the calibration was
        # fitted on, not the ORF's GC.
        features = {
            "energy_per_length": fold["fold"]["ensemble_free_energy_per_nt_kcal_mol"],
            "GC": fold["fold"]["gc_fraction"] * 100,
            "aup": fold["fold"]["mean_unpaired_probability"],
        }
        outside = [f for f in arm["feature_order"]
                   if not domain[f]["min"] <= features[f] <= domain[f]["max"]]
        entry["stability"] = {
            "predicted_in_solution_half_life_hours": arm["intercept"] + sum(
                arm["coefficients"][f] * features[f] for f in arm["feature_order"]),
            "features": features,
            "features_outside_training_range": outside,
            "extrapolating": bool(outside),
        }
    scored = [m for m in members if m.get("stability")]
    print(f"4. stability: {len(scored)} predicted; extrapolating "
          f"{sum(1 for m in scored if m['stability']['extrapolating'])}", flush=True)

    if args.skip_ribonn:
        (out / "summary.json").write_text(json.dumps(
            {"stage_reached": "stability", "members": len(members),
             "folds_ok": len(folds) - len(failed)}, indent=2, sort_keys=True))
        print("\nStopped after the stability side (--skip-ribonn).", flush=True)
        return 0

    # --- 5. translation ----------------------------------------------------
    ribonn_config = json.loads(RIBONN_BASE.read_text())
    ribonn_config.pop("reference_transcript", None)
    ribonn_config.update({
        "purpose": ("Score a windowed synonymous design pool with the selected A549 task, "
                    "under gate v6. Predictions only; no measurement exists."),
        "candidate_design_enabled": True,
        "stage3_ready": True,
        "authorizing_gate": str(GATE.relative_to(ROOT)),
        "design_pool": {
            "pool_file": str((out / "pool.json").relative_to(ROOT)),
            "inputs_config": str(INPUTS.relative_to(ROOT)),
            "tx_id_prefix": f"FLUC-DESIGN-{args.gc_mode[:3].upper()}-{{member:04d}}",
            "provenance": "design pool member",
            "assay_context": "provisional; no measurement exists",
            "include_poly_a": False,
            "reference_component": "cds",
        },
    })
    config_path = out / "ribonn_design_pool_config.json"
    config_path.write_text(json.dumps(ribonn_config, indent=2, sort_keys=True))
    print("5. translation: running the RiboNN driver", flush=True)
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_ribonn_fixed_inference.py"),
         "--config", str(config_path)],
        capture_output=True, text=True)
    (out / "ribonn_driver.log").write_text(completed.stdout + completed.stderr)
    if completed.returncode:
        raise SystemExit(f"RiboNN driver failed; see {out / 'ribonn_driver.log'}")
    ribonn_run = Path(completed.stdout.strip().splitlines()[0])
    predictions = {row["tx_id"]: row for row in json.loads(
        (ribonn_run / "joined_predictions.json").read_text())}
    ribonn_summary = json.loads((ribonn_run / "summary.json").read_text())
    for entry in members:
        row = predictions.get(entry["tx_id"])
        entry["translation"] = None if row is None or row.get("mean_score") is None else {
            "score_name": row["score_column"],
            "value": float(row["mean_score"]),
            "fold_scores": row["fold_scores"],
        }
    print(f"5. translation: {sum(1 for m in members if m['translation'])} scored", flush=True)

    # --- 6. select ---------------------------------------------------------
    complete = [m for m in members if m.get("stability") and m.get("translation")]
    objectives = [(m["stability"]["predicted_in_solution_half_life_hours"],
                   m["translation"]["value"]) for m in complete]
    front_local = non_dominated_indices(objectives)
    front = [complete[i]["member"] for i in front_local]
    # A reference point declared from this pool's own minima. It is comparable
    # WITHIN this run only; no reference point exists on the real scales.
    reference_point = (min(o[0] for o in objectives) - 1e-9,
                       min(o[1] for o in objectives) - 1e-9)

    from botorch.utils.multi_objective.hypervolume import get_hypervolume_maximizing_subset
    import torch

    panel_size = min(args.panel, len(front_local))
    # Greedy and provably bounded, because hypervolume is submodular. Not an
    # optimisation over the pool: the pool is already scored exhaustively here.
    _, panel_local = get_hypervolume_maximizing_subset(
        n=panel_size, Y=torch.tensor(objectives, dtype=torch.double),
        ref_point=torch.tensor(reference_point, dtype=torch.double))
    panel = [complete[int(i)]["member"] for i in panel_local]
    print(f"6. select: front {len(front)} of {len(complete)}; "
          f"panel {len(panel)} (placeholder size {args.panel})", flush=True)

    # --- 7. bo replay ------------------------------------------------------
    features, positions = design_features(complete, pool["window_codon_indices"])
    replay = bo_replay(features, objectives, args.bo_budget,
                       spec["sampling"]["seed"], reference_point)
    if replay:
        print(f"7. bo replay: budget {replay['budget']}  "
              f"hv {replay['hypervolume']:.6g} vs random {replay['random_hypervolume']:.6g}  "
              f"front found {replay['front_members_found']}/{replay['true_front_size']} "
              f"vs random {replay['random_front_members_found']}", flush=True)

    payload = {
        "purpose": ("End-to-end design workflow on predicted quantities. No experimental "
                    "measurement of any construct exists in this project."),
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "gate": str(GATE.relative_to(ROOT)),
        "gate_sha256": sha(GATE),
        "design_space": str(spec_path.relative_to(ROOT)),
        "design_space_sha256": sha(spec_path),
        "design_space_window_codons": window_codons,
        "formulation": str(FORMULATION.relative_to(ROOT)),
        "gc_mode": args.gc_mode,
        "pool": {"size": pool["size"], "window_codons": window_codons,
                 "substitutable_positions": pool["substitutable_positions"],
                 "seed": spec["sampling"]["seed"],
                 "window_codon_indices": pool["window_codon_indices"]},
        "assembly": {
            "transcript_length_nt": members[0]["transcript_length_nt"],
            "protein_sha256": members[0]["protein_sha256"],
            "reference_cds_sha256_dna_uppercase":
                members[0]["reference_cds_sha256_dna_uppercase"],
            "synonymy_verified_on_every_member": True,
            "poly_a_included": False,
        },
        "folding": {
            "tool": "ViennaRNA", "ok": len(folds) - len(failed), "failed": failed,
            "settings_source": "same as the frozen reference record; span policy provisional",
            "mean_runtime_seconds": statistics.fmean(
                f["fold"]["runtime_seconds"] for f in folds.values()
                if f["status"] == "ok" and f["fold"]["runtime_seconds"]),
        },
        "stability": {
            "model": model["name"], "arm": model["primary_arm"],
            "calibration_run": str(CALIBRATION.relative_to(ROOT)),
            "scored": len(scored),
            "extrapolating": sum(1 for m in scored if m["stability"]["extrapolating"]),
            "hours_range": [min(m["stability"]["predicted_in_solution_half_life_hours"]
                                for m in scored),
                            max(m["stability"]["predicted_in_solution_half_life_hours"]
                                for m in scored)],
        },
        "translation": {
            "run": str(ribonn_run.relative_to(ROOT)),
            "score_column": ribonn_summary["score_column"],
            "checkpoints": ribonn_summary["selected_models"],
            "scored": sum(1 for m in members if m["translation"]),
            "value_range": [min(m["translation"]["value"] for m in complete),
                            max(m["translation"]["value"] for m in complete)],
        },
        "selection": {
            "objectives": list(OBJECTIVES),
            "directions": ["maximize", "maximize"],
            "composite_score_emitted": False,
            "complete_members": len(complete),
            "pareto_front_members": front,
            "pareto_front_size": len(front),
            "panel_members": panel,
            "panel_size_requested": args.panel,
            "panel_size_is_a_placeholder": True,
            "panel_rule": "subset of the given size maximising dominated hypervolume",
            "reference_point": list(reference_point),
            "reference_point_scope": ("declared from this pool's own minima; comparable "
                                      "WITHIN this run only. No reference point exists on "
                                      "the real scales."),
            "hypervolume_exhaustive": hypervolume_2d(objectives, reference_point),
        },
        "bo_replay": replay,
        "bo_replay_meaning": (
            "Every member here was scored exhaustively, so the Pareto front is already "
            "known and Bayesian optimisation is not needed to find it. The replay answers "
            "a different question: if each member cost a fold and a RiboNN pass, how much "
            "of the front would qLogNEHVI have recovered inside a budget, against spending "
            "that budget at random. That is the regime BO is for, and the regime a real "
            "campaign with a larger space would be in."),
        "design_feature_representation": {
            "coordinates": len(positions),
            "positions": positions,
            "encoding": "1.0 if that window codon is substituted, else 0.0",
            "why": ("The domain is the edit pattern. A summary such as edit count would "
                    "hide which positions changed, which is the thing being chosen."),
        },
        "what_must_not_be_claimed": json.loads(GATE.read_text())["what_must_not_be_claimed"],
        "no_claim": [
            "Every value here is a PREDICTION from an unvalidated model, on a quantity the "
            "planned assay does not measure. No construct in this project has been measured.",
            "The selected panel ILLUSTRATES THE PIPELINE. It is not a recommendation to "
            "synthesise or assay anything, and it is not known to beat the reference.",
            "The panel size is a declared placeholder; the assay's capacity is unknown.",
            "No composite score was emitted at any stage.",
            "The base-pair span policy is unresolved. The folding settings were reused from "
            "the frozen reference record for comparability, which is a provisional "
            "convention, not a resolution.",
            "Every uridine in the real molecules is N1-methylpseudouridine, which neither "
            "the folding engine nor the calibration nor RiboNN represents.",
            "The stability side predicts in-solution half-life in buffer; the assay measures "
            "in-cell decay by RT-qPCR. They are different quantities.",
        ],
    }
    (out / "summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    (out / "scored_members.json").write_text(json.dumps(members, indent=2, sort_keys=True))
    (out / "folds.json").write_text(json.dumps(folds, indent=2, sort_keys=True))
    print(f"\nWrote {out}/summary.json", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
