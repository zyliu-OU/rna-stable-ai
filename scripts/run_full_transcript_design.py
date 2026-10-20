#!/usr/bin/env python3
"""Score a whole-transcript design pool and ask whether it clears the resolvable threshold.

The synonymous-only design space produced a widest predicted stability
difference of 1.0617-fold, below even the 1.10-fold floor at which the objective
was measured to order at chance. Design-space v3 widens the domain to UTR
composition plus synonymous codons, with every length fixed, for exactly one
reason: to move differences into the regime where the objective has measured
resolution, 1.25-fold and above.

This builds the pool, assembles every member through
`transcript_assembly.assemble_designed`, folds it, applies
`strand_rnafold_calibration_v1`, and reports the fold-difference distribution
against the reference together with the coarse-filter verdict.

RiboNN is deliberately not run. It has no measured resolution in this project,
it is excluded from filtering by
`configs/coarse_filter_diversity_panel_v1_2026-10-20.json`, and designed UTRs
are further outside its endogenous-transcript domain than natural ones. Omitting
it keeps this run about the question it can answer.
"""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import csv
import hashlib
import json
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.transcript_assembly import assemble_designed
from rnastable.transcript_design import build_pool

SPEC = ROOT / "configs/full_transcript_design_space_v3_2026-10-20.json"
SELECTION = ROOT / "configs/coarse_filter_diversity_panel_v1_2026-10-20.json"
INPUTS = ROOT / "configs/transcript_inputs_v1_2026-10-19.json"
CALIBRATION = ROOT / "results/strand_rnafold_calibration_runs/20261019T174049.053308Z"


def fold_one(payload):
    import subprocess

    member, sequence = payload
    try:
        done = subprocess.run([sys.executable, "-m", "rnastable.ensemble_worker"],
                              input=json.dumps({"sequence": sequence, "temperature": 37.0}),
                              text=True, capture_output=True, timeout=600, check=True,
                              cwd=str(ROOT / "src"))
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return member, None
    result = json.loads(done.stdout)
    if result.get("status") != "ok":
        return member, None
    candidates = result["feature_candidates"]
    return member, {"energy_per_length": candidates["ensemble_energy_per_nt"],
                    "GC": candidates["gc_fraction"] * 100,
                    "aup": candidates["aup"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--jobs", type=int, default=24)
    parser.add_argument("--out", default="results/full_transcript_design_runs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    spec = json.loads(SPEC.read_text())
    selection = json.loads(SELECTION.read_text())
    floor = selection["resolution_floor"]
    chance, resolvable = floor["chance_floor"], floor["resolvable_threshold"]

    components = json.loads(INPUTS.read_text())["components"]
    utr5 = components["utr5"]["sequence_dna_uppercase"]
    utr3 = components["utr3"]["sequence_dna_uppercase"]
    cds = "".join((ROOT / "data/constructs/fluc_orf.txt").read_text().split())

    pool = build_pool(utr5, cds, utr3, size=args.size,
                      seed=spec["sampling"]["seed"],
                      max_homopolymer=spec["constraints"]["max_homopolymer_run"])
    orfs = {m["orf"] for m in pool["members"]}
    print(f"pool {pool['size']} members, {len(orfs)} distinct ORFs, "
          f"{pool['attempts']} attempts, rejected {pool['rejected']}", flush=True)
    if len(orfs) < pool["size"] * 0.9:
        raise SystemExit(f"Pool collapsed: only {len(orfs)} distinct ORFs for "
                         f"{pool['size']} members")

    jobs, members = [], []
    for member in pool["members"]:
        transcript, report = assemble_designed(
            member["utr5"], member["orf"], member["utr3"], INPUTS,
            f"FLUC-FULL-{member['member']:04d}",
            "whole-transcript design, v3 domain", "provisional; no measurement exists")
        if report.utrs_designed is not True or report.synonymous_verified is not True:
            raise SystemExit(f"Member {member['member']} failed verification")
        members.append({**{k: v for k, v in member.items() if k not in ("utr5", "utr3", "orf")},
                        "tx_id": transcript.tx_id,
                        "transcript_sha256_rna": report.transcript_sha256_rna,
                        "protein_sha256": report.protein_sha256,
                        "utr5_edits": report.utr5_edits, "utr3_edits": report.utr3_edits})
        jobs.append((member["member"], transcript.sequence))
    lengths = {m["transcript_length_nt"] for m in members}
    proteins = {m["protein_sha256"] for m in members}
    if len(lengths) != 1 or len(proteins) != 1:
        raise SystemExit("Members differ in length or protein")
    print(f"assembled {len(members)} transcripts, all {lengths.pop()} nt, one protein",
          flush=True)
    if args.dry_run:
        print("Dry run: nothing folded.", file=sys.stderr)
        return 0

    folds = {}
    with ProcessPoolExecutor(max_workers=args.jobs) as pool_exec:
        for done, (member, features) in enumerate(pool_exec.map(fold_one, jobs), 1):
            folds[member] = features
            if done % 50 == 0 or done == len(jobs):
                print(f"  folded {done}/{len(jobs)}", flush=True)

    model = json.loads((CALIBRATION / "calibration_model.json").read_text())["component"]
    train = list(csv.DictReader((CALIBRATION / "features/train_features.csv").open()))
    domain = {f: {"min": min(float(r[f]) for r in train), "max": max(float(r[f]) for r in train)}
              for f in ("energy_per_length", "GC", "aup")}
    for entry in members:
        features = folds.get(entry["member"])
        if not features:
            entry["stability"] = None
            continue
        outside = [f for f in model["feature_order"]
                   if not domain[f]["min"] <= features[f] <= domain[f]["max"]]
        entry["stability"] = {
            "predicted_in_solution_half_life_hours": model["intercept"] + sum(
                model["coefficients"][f] * features[f] for f in model["feature_order"]),
            "features": features, "features_outside_training_range": outside,
            "extrapolating": bool(outside),
        }

    scored = [m for m in members if m.get("stability")]
    reference = next(m for m in scored if m["is_reference"])
    reference_hours = reference["stability"]["predicted_in_solution_half_life_hours"]
    for entry in scored:
        hours = entry["stability"]["predicted_in_solution_half_life_hours"]
        fold = hours / reference_hours
        ratio = fold if fold >= 1 else 1 / fold
        entry["fold_vs_reference"] = fold
        entry["ratio_vs_reference"] = ratio
        entry["verdict"] = ("resolvably_better" if ratio >= resolvable and fold > 1
                            else "resolvably_worse" if ratio >= resolvable
                            else "unresolved")
    ratios = [m["ratio_vs_reference"] for m in scored if not m["is_reference"]]
    better = [m["member"] for m in scored if m["verdict"] == "resolvably_better"]
    worse = [m["member"] for m in scored if m["verdict"] == "resolvably_worse"]
    extrapolating = sum(1 for m in scored if m["stability"]["extrapolating"])

    payload = {
        "purpose": ("Does widening the design domain to UTR composition plus synonymous "
                    "codons move predicted differences into the regime the objective can "
                    "resolve?"),
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "design_space": str(SPEC.relative_to(ROOT)),
        "design_space_sha256": hashlib.sha256(SPEC.read_bytes()).hexdigest(),
        "selection_protocol": str(SELECTION.relative_to(ROOT)),
        "resolution_floor": {"chance_floor": chance, "resolvable_threshold": resolvable,
                             "applies_to": "stability only"},
        "ribonn_not_run": ("deliberate: no measured resolution in this project, excluded from "
                           "filtering, and designed UTRs are further outside its domain"),
        "pool": {"size": pool["size"], "distinct_orfs": len(orfs),
                 "attempts": pool["attempts"], "rejected": pool["rejected"],
                 "seed": pool["seed"], "editable": pool["editable"],
                 "substitutable_codons": pool["substitutable_codons"],
                 "reachable_gc_range": pool["reachable_gc_range"]},
        "assembly": {"transcript_length_nt": members[0]["transcript_length_nt"],
                     "one_protein_hash": True, "utrs_designed": True,
                     "utr5_edits_range": [min(m["utr5_edits"] for m in members),
                                          max(m["utr5_edits"] for m in members)],
                     "utr3_edits_range": [min(m["utr3_edits"] for m in members),
                                          max(m["utr3_edits"] for m in members)],
                     "codon_substitution_range": [min(m["substitution_count"] for m in members),
                                                  max(m["substitution_count"] for m in members)]},
        "gc": {
            "achieved_range": [min(m["transcript_gc_fraction"] for m in scored),
                               max(m["transcript_gc_fraction"] for m in scored)],
            "reference": reference["transcript_gc_fraction"],
            "calibration_training_range": [domain["GC"]["min"] / 100, domain["GC"]["max"] / 100],
            "members_in_calibration_domain": len(scored) - extrapolating,
            "members_extrapolating": extrapolating,
            "note": ("In the synonymous-only domain every member extrapolated on GC. "
                     "Designing the UTRs makes the calibration's fitted domain reachable."),
        },
        "stability_vs_reference": {
            "reference_hours": reference_hours,
            "widest_ratio": max(ratios), "median_ratio": statistics.median(ratios),
            "members_above_chance_floor": sum(1 for r in ratios if r >= chance),
            "members_above_resolvable_threshold": sum(1 for r in ratios if r >= resolvable),
            "resolvably_better": better, "resolvably_worse": worse,
            "unresolved": len(scored) - len(better) - len(worse),
        },
        "verdict": {
            "clears_the_chance_floor": max(ratios) >= chance,
            "clears_the_resolvable_threshold": max(ratios) >= resolvable,
            "finding": None,
        },
        "members": members,
        "no_claim": [
            "Nothing here is measured. No molecule in this project has been assayed.",
            "A designed-UTR member is a NEW construct and carries none of the supplied UTRs' "
            "provenance. The protein is preserved and verified; the UTRs are not the "
            "collaborator's.",
            "Reaching the calibration's GC domain makes its predictions in-domain, not correct.",
            "Widening the design space does not improve the objective's resolution; it only "
            "changes the size of the differences presented to it.",
            "The translation side was not scored and remains excluded from filtering.",
        ],
    }
    payload["verdict"]["finding"] = (
        f"The widest predicted difference from the reference is {max(ratios):.4f}-fold. "
        + ("This clears the 1.25-fold resolvable threshold, so the objective can distinguish "
           "at least some members from the reference for the first time in this project."
           if max(ratios) >= resolvable else
           f"This clears the {chance}-fold chance floor but not the {resolvable}-fold "
           "resolvable threshold, so differences remain unresolved."
           if max(ratios) >= chance else
           "This does not clear even the chance floor, so the widened domain did not move "
           "differences into a resolvable regime."))

    print(f"\nGC achieved {payload['gc']['achieved_range'][0]:.4f} .. "
          f"{payload['gc']['achieved_range'][1]:.4f}   reference "
          f"{reference['transcript_gc_fraction']:.4f}")
    print(f"  in calibration domain {payload['gc']['members_in_calibration_domain']}"
          f"/{len(scored)}  (was 0 in the synonymous-only domain)")
    print(f"\nstability vs reference ({reference_hours:.4f} h):")
    print(f"  widest ratio {max(ratios):.4f}x   median {statistics.median(ratios):.4f}x")
    print(f"  above chance floor {chance}x        "
          f"{payload['stability_vs_reference']['members_above_chance_floor']}")
    print(f"  above resolvable threshold {resolvable}x  "
          f"{payload['stability_vs_reference']['members_above_resolvable_threshold']}")
    print(f"  resolvably better {len(better)}   resolvably worse {len(worse)}   "
          f"unresolved {payload['stability_vs_reference']['unresolved']}")
    print(f"\n{payload['verdict']['finding']}")

    out = ROOT / args.out / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True, exist_ok=False)
    (out / "summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(f"\nWrote {out}/summary.json", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
