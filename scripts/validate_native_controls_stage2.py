#!/usr/bin/env python3
"""Validate the native controls the project relies on, under the Stage 2 scope.

Gate v4 amended requirement 4 to concern the accuracy of the native controls —
LinearFold and ViennaRNA — rather than the learned pair model, which was retired
on 2026-10-20. This produces that evidence from saved predictions, by band,
family and clan, across every cohort available, with the baseline gaps stated.

No new inference is performed and no model is fitted. Every number here comes
from predictions already frozen in earlier runs.

Why separation is different for a thermodynamic folder. The requirement for
sequence-, family- and clan-separated validation exists to stop a learned model
being evaluated on data it was exposed to during training. LinearFold and
ViennaRNA have no training set: both are Turner-model thermodynamic folders
whose parameters come from published optical-melting measurements, not from
these references. There is therefore no exposure to separate from, and the
separation requirement is satisfied by construction rather than by partitioning.
That argument applies ONLY to the native controls. It would not apply to any
learned component, and it is not a claim that the cohorts are large or diverse.
"""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

LONG_NATIVE = ROOT / "results/long_native_controls_runs/20261017T034318.804594Z/rows.json"
SHORT_EVAL = ROOT / "results/bprna_five_clan_feasibility_evaluation_runs/20261017T191445.852927Z"
SHORT_REFS = ROOT / "results/bprna_five_clan_reference_screen_runs/20261017T191404.643416Z/references.json"
STRUCTURE = ROOT / "results/raw_structure_feasibility_runs/20261015T025936.192087Z/summary.json"
CLAN_SOURCE = ROOT / "results/band_clan_availability_runs/20261019T185713.116447Z/summary.json"
CENSUS = ROOT / "results/stage2_band_coverage_census_runs/20261019T180243.655199Z/summary.json"
GATE = ROOT / "configs/stage2_to_stage3_gate_v4_2026-10-20.json"
METHODS = ("LinearFold", "ViennaRNA")
BANDS = (("1_999", 1, 1000), ("1000_1999", 1000, 2000), ("2000_2999", 2000, 3000))


def family_to_clan():
    """Family to clan mapping, as recorded by the band availability audit."""
    data = json.loads(CLAN_SOURCE.read_text())
    mapping = {family: entry.get("clan_id")
               for family, entry in data.get("rfam", {}).get("band_families", {}).items()}
    for record in json.loads(SHORT_REFS.read_text()):
        if record.get("clan_id"):
            mapping.setdefault(record["family_id"], record["clan_id"])
    # The census records selected families and clans per band. Where a band
    # resolves to exactly one clan, every family selected in it belongs to that
    # clan; where it does not, no assignment is inferred rather than guessed.
    for band in json.loads(CENSUS.read_text()).get("coverage_by_band", {}).values():
        band_clans = band.get("selected_clans") or []
        if len(band_clans) == 1:
            for family in band.get("selected_families") or []:
                mapping.setdefault(family, band_clans[0])
    return {k: v for k, v in mapping.items() if v}


def summarise(rows, clans):
    """Aggregate pair F1 by record, family, clan and length band.

    Family and clan means are reported beside the record mean because a record
    mean is dominated by whichever family contributes most records, which on
    these small cohorts is a real distortion rather than a technicality.
    """
    if not rows:
        return None
    by_family, by_clan, by_band = defaultdict(list), defaultdict(list), defaultdict(list)
    for row in rows:
        by_family[row["family_id"]].append(row["pair_f1"])
        by_clan[clans.get(row["family_id"]) or "unmapped"].append(row["pair_f1"])
        for name, low, high in BANDS:
            if low <= row["length_nt"] < high:
                by_band[name].append(row["pair_f1"])
    family_means = {k: statistics.fmean(v) for k, v in sorted(by_family.items())}
    clan_means = {k: statistics.fmean(v) for k, v in sorted(by_clan.items())}
    return {
        "n": len(rows),
        "mean_record_pair_f1": statistics.fmean(r["pair_f1"] for r in rows),
        "families": len(family_means),
        "clans": len([k for k in clan_means if k != "unmapped"]),
        "family_means": family_means,
        "mean_family_pair_f1": statistics.fmean(family_means.values()),
        "clan_means": clan_means,
        "mean_clan_pair_f1": statistics.fmean(clan_means.values()),
        "bands": {name: {"n": len(by_band.get(name, [])),
                         "mean_pair_f1": statistics.fmean(by_band[name]) if by_band.get(name) else None}
                  for name, _, _ in BANDS},
    }


def long_rows(method, clans):
    rows = []
    for row in json.loads(LONG_NATIVE.read_text()):
        if row["method"] != method or row["metrics"] is None:
            continue
        if not 1 <= row["length_nt"] < 3000:
            continue
        rows.append({"id": row["id"], "family_id": row["family_id"],
                     "length_nt": row["length_nt"], "pair_f1": row["metrics"]["pair_f1"]})
    return rows


def short_rows(method):
    """Score saved short-cohort predictions against their frozen references."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from evaluate_bprna_five_clan_feasibility import score_rows
    references = json.loads(SHORT_REFS.read_text())
    predictions = json.loads((SHORT_EVAL / f"{method}_predictions.json").read_text())
    scored = score_rows(predictions, references)
    reference_by_id = {r["id"]: r for r in references}
    rows = []
    for entry in scored.get("rows", scored if isinstance(scored, list) else []):
        reference = reference_by_id.get(entry.get("id"))
        if reference is None or entry.get("pair_f1") is None:
            continue
        rows.append({"id": entry["id"], "family_id": reference["family_id"],
                     "length_nt": len(reference["sequence"]), "pair_f1": entry["pair_f1"]})
    return rows, scored


def structure_aggregate(method):
    data = json.loads(STRUCTURE.read_text())
    for entry in data["aggregates"]:
        if entry["method"] == method:
            return {"n": entry["measured_inputs"], "mean_pair_f1": entry["mean_pair_f1"],
                    "mean_pair_precision": entry["mean_pair_precision"],
                    "mean_pair_recall": entry["mean_pair_recall"]}
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", default="results/native_control_validation")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    clans = family_to_clan()
    gate = json.loads(GATE.read_text())
    cohorts = {}
    for method in METHODS:
        rows_long = long_rows(method, clans)
        rows_short, _ = short_rows(method)
        cohorts[method] = {
            "long_rfam_consensus": summarise(rows_long, clans),
            "short_bprna_five_clan": summarise(rows_short, clans),
            "structure_derived": structure_aggregate(method),
        }

    payload = {
        "purpose": ("Evidence for gate v4 requirement 4: accuracy of the native controls "
                    "the project relies on, by band, family and clan."),
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "methods": list(METHODS),
        "no_new_inference": True,
        "model_fitted": False,
        "cohorts": cohorts,
        "separation_argument": {
            "claim": ("Sequence-, family- and clan-separated validation is satisfied by "
                      "construction for these controls."),
            "reason": ("LinearFold and ViennaRNA are Turner-model thermodynamic folders with "
                       "no training set. Their parameters come from published optical-melting "
                       "measurements, not from these references, so there is no exposure to "
                       "separate from."),
            "scope_limit": ("Applies ONLY to the native controls. It would not apply to any "
                            "learned component, and it is not a claim that the cohorts are "
                            "large, diverse or representative."),
        },
        "baseline_gaps": [
            "Every long in-scope reference is a computational Rfam consensus, not an "
            "experimental structure. Accuracy against consensus annotation is not accuracy "
            "against measured structure.",
            "The long in-scope cohort is 6 records across 3 families and 2 clans. That is a "
            "small and narrow basis for any accuracy statement.",
            "The 2,000-2,999 nt band holds exactly one record, so its per-band figure carries "
            "no dispersion and no family or clan contrast. Gate v3 accepted this as a "
            "documented limitation; any statement spanning that band must carry it.",
            "No native experimental-structure control exists for the 2,000-2,999 nt band.",
            "The structure-derived cohort is a six-family feasibility set whose own run "
            "records broad_validation_gate_satisfied false and independence_certified false. "
            "It is not independent biological validation.",
        ],
        "claimed_length_range": gate["claimed_length_range"],
        "no_claim": [
            "No new inference was performed and no model was fitted.",
            "Accuracy against computational consensus references is not biological validation.",
            "This does not establish any stability, translation or expression benefit.",
            "Satisfying a requirement is a gate-review judgement, not an output of this script.",
        ],
    }

    for method in METHODS:
        print(f"\n=== {method} ===")
        for name, value in cohorts[method].items():
            if value is None:
                print(f"  {name:24s} (no data)")
            elif "mean_record_pair_f1" in value:
                print(f"  {name:24s} n={value['n']:3d}  record F1 {value['mean_record_pair_f1']:.4f}"
                      f"  family F1 {value['mean_family_pair_f1']:.4f}"
                      f"  clan F1 {value['mean_clan_pair_f1']:.4f}"
                      f"  ({value['families']} fam, {value['clans']} clan)")
                for band, stats in value["bands"].items():
                    if stats["n"]:
                        print(f"      band {band:10s} n={stats['n']:2d}  F1 {stats['mean_pair_f1']:.4f}")
            else:
                print(f"  {name:24s} n={value['n']:3d}  F1 {value['mean_pair_f1']:.4f}")

    if args.dry_run:
        print("\nDry run: nothing written.", file=sys.stderr)
        return 0
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    target = out / "native_control_validation.json"
    if target.exists():
        raise SystemExit(f"{target} already exists; remove it deliberately.")
    target.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(f"\nWrote {target}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
