#!/usr/bin/env python3
"""Diagnose how base-pair span affects agreement with released LinearPartition features.

The STRAND reference features were produced by LinearPartition. This project
substitutes ViennaRNA, which folds with `max_bp_span: -1` (unlimited) by
default. That default was inherited rather than chosen, and a separate finding
showed it can dominate a region's computed accessibility on long transcripts.

This script asks whether the default is defensible: for several span values, it
refolds the STRAND selection-set records and measures how far the resulting
features sit from the released LinearPartition values.

Cohort. Selection-set records only. `configs/strand_rnafold_agreement_criterion_v1`
records those six as burned — their RNAfold differences were visible to the
author when the criterion was frozen, so they carry no confirmatory weight. The
blinded 85-record evaluation set is deliberately NOT touched, so nothing here can
contaminate the set any real decision must rest on.

This is a diagnostic. It selects nothing, freezes nothing, and satisfies no gate.
"""
import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path

import RNA

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "results/four_component_source_runs/20261019T040820.389955Z/strand/Data"
INVENTORY = (ROOT / "results/strand_reference_reproduction_runs"
             / "20261019T042427.196161Z/reference_inventory.json")
SELECTION_SET = ["X320004D1", "X310336T3", "X310003T1",
                 "X130010D1", "X130002D1", "X130006D1"]
# Tolerances as frozen in configs/strand_rnafold_agreement_criterion_v1.
TOLERANCES = {
    "energy_per_length": 0.005548940468588457,
    "aup": 0.002807531325000001,
    "alo": 0.05132036110543378,
}


def load_sequences(names):
    found = {}
    for filename in ("nluc_cleaned_new_final.csv", "validate_cleaned_new_final.csv"):
        with (DATA / filename).open(encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                name = row.get("name")
                if name in names and name not in found:
                    found[name] = row["sequence"].strip().upper().replace("T", "U")
    missing = set(names) - set(found)
    if missing:
        raise SystemExit(f"Sequences not found for: {sorted(missing)}")
    return found


def average_log_odds(paired, epsilon):
    """Mean log odds of the positional paired probability.

    The epsilon is explicit because this feature is dominated by the handful of
    positions with near-zero probability: the clipping convention moves it by
    more than the agreement tolerance even when the folding is identical.
    """
    clipped = [min(1 - epsilon, max(epsilon, value)) for value in paired]
    return statistics.fmean(math.log(x / (1 - x)) for x in clipped)


def fold_features(sequence, span, epsilon):
    RNA.params_load_RNA_Turner2004()
    model = RNA.md()
    model.temperature = 37.0
    model.dangles = 2
    model.compute_bpp = 1
    model.max_bp_span = span
    model.min_loop_size = 3
    compound = RNA.fold_compound(sequence, model)
    _, mfe = compound.mfe()
    compound.exp_params_rescale(mfe)
    _, ensemble = compound.pf()
    bpp = compound.bpp()
    length = len(sequence)
    paired = [0.0] * length
    for i in range(1, length + 1):
        for j in range(i + 1, length + 1):
            probability = bpp[i][j]
            if probability > 0:
                paired[i - 1] += probability
                paired[j - 1] += probability
    paired = [min(1.0, max(0.0, value)) for value in paired]
    return {
        "energy_per_length": ensemble / length,
        "aup": statistics.fmean(1 - value for value in paired),
        "alo": average_log_odds(paired, epsilon),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--spans", default="-1,800,600,400,300,200,150,100")
    parser.add_argument("--epsilon", type=float, default=1e-5,
                        help="alo clipping bound; 1e-5 is the transform the frozen "
                             "criterion selected")
    parser.add_argument("--out", default=str(ROOT / "results/bp_span_policy"
                                             / "span_vs_linearpartition_agreement.json"))
    args = parser.parse_args(argv)

    sequences = load_sequences(SELECTION_SET)
    released = {row["name"]: row for row in json.loads(INVENTORY.read_text())}
    spans = [int(value) for value in args.spans.split(",")]

    by_span = {}
    print(f"{'span':>10} {'within tol':>12}  "
          f"{'mean|d| epl':>12} {'mean|d| aup':>12} {'mean|d| alo':>12}")
    for span in spans:
        within = 0
        deltas = {key: [] for key in TOLERANCES}
        for name, sequence in sequences.items():
            computed = fold_features(sequence, span, args.epsilon)
            reference = released[name]["features"]
            for key, tolerance in TOLERANCES.items():
                delta = abs(computed[key] - reference[key])
                deltas[key].append(delta)
                within += delta <= tolerance
        by_span[str(span)] = {
            "within_tolerance": within,
            "of": len(sequences) * len(TOLERANCES),
            **{f"mean_abs_{key}": statistics.fmean(values)
               for key, values in deltas.items()},
        }
        label = "unlimited" if span == -1 else str(span)
        print(f"{label:>10} {within:>8}/{len(sequences) * 3:<3} "
              f"{statistics.fmean(deltas['energy_per_length']):12.6f} "
              f"{statistics.fmean(deltas['aup']):12.6f} "
              f"{statistics.fmean(deltas['alo']):12.6f}")

    payload = {
        "purpose": "Does bounding the base-pair span improve agreement with released "
                   "LinearPartition features?",
        "cohort_note": "Selection set only; recorded as burned by the frozen criterion. "
                       "The blinded 85-record evaluation set was NOT touched.",
        "selection_set": SELECTION_SET,
        "alo_clipping_epsilon": args.epsilon,
        "tolerances": TOLERANCES,
        "by_span": by_span,
        "no_claim": [
            "A diagnostic on burned records. It selects nothing and freezes nothing.",
            "No determination is made about which span is physically correct.",
        ],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(f"\nWrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
