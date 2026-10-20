#!/usr/bin/env python3
"""Select a panel by coarse filtering and diversity, not by ranking.

Gate v10 records that the stability objective's pairwise concordance is 0.5007
over 2958 held-out pairs for differences under 1.10-fold, which is chance, while
this project's design space produces differences of 3.2 to 8.4 percent. Choosing
the top of that ordering is choosing noise, so hypervolume-maximising selection
is replaced here by:

  1. a coarse filter against the reference, using only the resolution the
     objective has actually demonstrated, and
  2. a deterministic farthest-point traversal over the edit pattern, which uses
     no predicted values at all.

The filter applies to the STABILITY side only. RiboNN has never been evaluated
against any measurement in this project, so the translation score has no
measured resolution and every translation difference is treated as unresolved
regardless of size. That asymmetry is the easiest thing to get wrong here and is
enforced in code rather than left to the reader.

If nothing clears the resolvable threshold, that is the finding: the design
space lies inside the objective's noise floor. The run says so rather than
producing a ranking anyway.

Rules and thresholds are declared in
`configs/coarse_filter_diversity_panel_v1_2026-10-20.json`.
"""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import hashlib
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/coarse_filter_diversity_panel_v1_2026-10-20.json"
GATE = ROOT / "configs/stage2_to_stage3_gate_v10_2026-10-20.json"
HOURS = "predicted_in_solution_half_life_hours"


def classify(member, reference_hours, resolvable, chance_floor):
    """Coarse verdict against the reference, stability side only."""
    hours = member["stability"][HOURS]
    if hours <= 0 or reference_hours <= 0:
        return "unscored", None
    fold = hours / reference_hours
    ratio = fold if fold >= 1 else 1 / fold
    if ratio < chance_floor:
        band = "below_chance_floor"
    elif ratio < resolvable:
        band = "grey_band"
    else:
        band = "resolvable"
    if band != "resolvable":
        return "unresolved", {"fold_vs_reference": fold, "band": band}
    verdict = "resolvably_better" if fold > 1 else "resolvably_worse"
    return verdict, {"fold_vs_reference": fold, "band": band}


def hamming(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


def farthest_point(vectors, start_index, size):
    """Deterministic k-centre traversal; ties broken by lowest index."""
    chosen = [start_index]
    while len(chosen) < size:
        best, best_distance = None, -1
        for index in range(len(vectors)):
            if index in chosen:
                continue
            distance = min(hamming(vectors[index], vectors[c]) for c in chosen)
            if distance > best_distance:
                best, best_distance = index, distance
        if best is None:
            break
        chosen.append(best)
    return chosen


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--run", required=True,
                        help="a design_workflow_runs directory whose members are already scored")
    parser.add_argument("--panel", type=int, default=12)
    parser.add_argument("--out", default="results/coarse_filter_panel_runs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    protocol = json.loads(PROTOCOL.read_text())
    gate = json.loads(GATE.read_text())
    if "prohibition_added_here" not in gate:
        raise SystemExit(f"{GATE.name} does not carry the ranking prohibition")
    floor = protocol["resolution_floor"]
    resolvable, chance_floor = floor["resolvable_threshold"], floor["chance_floor"]

    source = ROOT / args.run
    summary = json.loads((source / "summary.json").read_text())
    members = json.loads((source / "scored_members.json").read_text())
    scored = [m for m in members if m.get("stability") and m.get("translation")]
    reference = next(m for m in scored if m["is_reference"])
    reference_hours = reference["stability"][HOURS]
    positions = sorted(summary["pool"]["window_codon_indices"])

    classified = {"resolvably_better": [], "resolvably_worse": [], "unresolved": []}
    detail = {}
    for member in scored:
        verdict, info = classify(member, reference_hours, resolvable, chance_floor)
        classified.setdefault(verdict, []).append(member["member"])
        detail[member["member"]] = {"verdict": verdict, **(info or {})}

    survivors = [m for m in scored
                 if detail[m["member"]]["verdict"] != "resolvably_worse"]
    vectors = [[1 if p in set(m["substituted_codon_indices"]) else 0 for p in positions]
               for m in survivors]
    reference_row = next(i for i, m in enumerate(survivors) if m["is_reference"])
    size = min(args.panel, len(survivors))
    chosen_rows = farthest_point(vectors, reference_row, size)
    panel = [survivors[i]["member"] for i in chosen_rows]
    panel_vectors = [vectors[i] for i in chosen_rows]
    pairwise = [hamming(panel_vectors[i], panel_vectors[j])
                for i in range(len(panel_vectors)) for j in range(i + 1, len(panel_vectors))]

    folds = [detail[m["member"]]["fold_vs_reference"] for m in scored
             if detail[m["member"]].get("fold_vs_reference")]
    translation = [m["translation"]["value"] for m in scored]
    reference_translation = reference["translation"]["value"]
    translation_folds = [v / reference_translation for v in translation if reference_translation]

    everything_unresolved = not (classified["resolvably_better"]
                                 or classified["resolvably_worse"])
    payload = {
        "purpose": protocol["purpose"],
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": str(PROTOCOL.relative_to(ROOT)),
        "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
        "gate": str(GATE.relative_to(ROOT)),
        "source_run": args.run,
        "pool": {"size": len(scored), "window_codons": summary["pool"]["window_codons"],
                 "gc_mode": summary["gc_mode"]},
        "selection_method": "coarse filter then deterministic farthest-point diversity",
        "ranking_used": False,
        "hypervolume_used": False,
        "resolution_floor_applied": {"chance_floor": chance_floor,
                                     "resolvable_threshold": resolvable,
                                     "applies_to": "stability only"},
        "reference": {"member": reference["member"],
                      "predicted_half_life_hours": reference_hours,
                      "predicted_translation": reference_translation},
        "stability_classification": {
            "resolvably_better": classified["resolvably_better"],
            "resolvably_worse": classified["resolvably_worse"],
            "unresolved_count": len(classified["unresolved"]),
            "widest_fold_difference_from_reference": max(folds) if folds else None,
            "narrowest_fold_difference_from_reference": min(folds) if folds else None,
            "everything_unresolved": everything_unresolved,
        },
        "translation_side": {
            "filter_applied": False,
            "why_not": protocol["the_translation_side_has_no_measured_resolution"]["consequence"],
            "widest_fold_difference_from_reference": max(translation_folds)
            if translation_folds else None,
            "members_exceeding_the_stability_chance_floor": sum(
                1 for f in translation_folds if max(f, 1 / f) >= chance_floor),
            "note": ("These counts are reported to show the trap, not to license it: the "
                     "stability floor was measured for a different model on a different "
                     "quantity and does not transfer to RiboNN."),
        },
        "panel": {
            "members": panel,
            "size": len(panel),
            "size_requested": args.panel,
            "size_is_a_placeholder": True,
            "reference_included": reference["member"] in panel,
            "minimum_pairwise_hamming": min(pairwise) if pairwise else None,
            "mean_pairwise_hamming": statistics.fmean(pairwise) if pairwise else None,
            "maximum_possible_hamming": len(positions),
            "selection_used_no_predicted_values": True,
        },
        "members": {str(m["member"]): {
            "verdict": detail[m["member"]]["verdict"],
            "fold_vs_reference": detail[m["member"]].get("fold_vs_reference"),
            "band": detail[m["member"]].get("band"),
            "predicted_half_life_hours": m["stability"][HOURS],
            "predicted_translation": m["translation"]["value"],
            "substitution_count": m["substitution_count"],
            "in_panel": m["member"] in panel,
        } for m in scored},
        "finding": (
            "The design space lies entirely inside the objective's noise floor: no member is "
            "resolvably better or worse than the reference on the stability side. The panel is "
            "therefore a diversity panel over ties, not a selection of better candidates."
            if everything_unresolved else
            "Some members are resolvably different from the reference on the stability side; "
            "see stability_classification."),
        "what_the_output_may_claim": protocol["what_the_output_may_claim"],
        "what_the_output_may_not_claim": protocol["what_the_output_may_not_claim"],
        "what_this_cannot_establish": protocol["what_this_cannot_establish"],
        "no_claim": [
            "The panel is NOT ranked. Members are ties unless explicitly classified resolvable.",
            "The translation score distinguishes no member from any other; it has no measured "
            "resolution in this project.",
            "No molecule in this project has been assayed.",
            "A diversity panel is the defensible choice given an objective that cannot rank; "
            "it is not evidence that diversity is the right criterion for a real campaign.",
        ],
    }

    print(f"source   {args.run}")
    print(f"pool     {len(scored)} scored members, window {payload['pool']['window_codons']} "
          f"codons, {payload['pool']['gc_mode']} mode")
    print(f"floor    chance {chance_floor}x, resolvable {resolvable}x, stability only")
    print(f"\nstability against the reference ({reference_hours:.4f} h):")
    print(f"  resolvably better  {len(classified['resolvably_better'])}")
    print(f"  resolvably worse   {len(classified['resolvably_worse'])}")
    print(f"  unresolved         {len(classified['unresolved'])}")
    print(f"  widest fold difference {max(folds):.4f}x  (resolvable needs {resolvable}x)")
    print(f"\ntranslation: filter NOT applied; widest fold difference "
          f"{max(translation_folds):.4f}x, "
          f"{payload['translation_side']['members_exceeding_the_stability_chance_floor']} "
          f"members exceed the stability chance floor and are STILL unresolved")
    print(f"\npanel {len(panel)} members: {panel}")
    print(f"  minimum pairwise Hamming {payload['panel']['minimum_pairwise_hamming']} "
          f"of {len(positions)} positions, mean "
          f"{payload['panel']['mean_pairwise_hamming']:.2f}")
    print(f"\n{payload['finding']}")

    if args.dry_run:
        print("\nDry run: nothing written.", file=sys.stderr)
        return 0
    out = ROOT / args.out / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True, exist_ok=False)
    (out / "summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(f"\nWrote {out}/summary.json", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
