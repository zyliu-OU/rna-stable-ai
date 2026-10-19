"""Prespecified RNAfold-vs-LinearPartition feature agreement for STRAND.

Engine agreement only. Nothing here predicts stability, half-life or
expression, and passing the criterion does not enable new-sequence scoring.
"""
import math

from .component_integration import strand_alo
from .strand_reference import FEATURE_ORDER, linear_prediction


def alo_transform(name):
    """Return the prespecified positional-probability transform by name.

    Released LinearPartition arrays saturate strand_alo's log odds at both
    ends (exact zeros, and sums at or above one). floor_t and two_sided_t test
    whether reproducing that saturation on RNAfold probabilities, rather than a
    different ALO formula, accounts for the gap.
    """
    if name == "identity":
        return lambda values: list(values)
    kind, _, raw = name.rpartition("_")
    threshold = float(raw)
    if kind not in ("floor", "two_sided") or not 0 < threshold < 0.5:
        raise ValueError(f"Unknown ALO transform: {name}")
    def transform(values):
        out = []
        for x in values:
            if x < threshold:
                out.append(0.0)
            elif kind == "two_sided" and x > 1-threshold:
                out.append(1.0)
            else:
                out.append(x)
        return out
    return transform


def released_decimals(text):
    """Decimal places carried by a released numeric string."""
    body = text.strip().split("e")[0].split("E")[0]
    return len(body.split(".")[1]) if "." in body else 0


def rounding_half_widths(raw_row, length):
    """Half-width of the released rounding interval per compared feature.

    The released validation table reports GC, aup and energy to about two
    decimals, so it cannot evidence agreement finer than its own rounding. ALO
    is recomputed here from the full released probability array, so it is exact.
    """
    if length <= 0:
        raise ValueError("Positive length required")
    energy = 0.5*10**(-released_decimals(raw_row["energy"]))
    return {"energy_per_length": energy/length,
            "GC": 0.5*10**(-released_decimals(raw_row["GC"])),
            "aup": 0.5*10**(-released_decimals(raw_row["aup"])),
            "alo": 0.0}


def quantile(values, probability):
    """Linear-interpolated quantile at position (n-1)*probability."""
    ordered = sorted(values)
    if not ordered or not 0 <= probability <= 1:
        raise ValueError("Non-empty values and probability in [0,1] required")
    position = (len(ordered)-1)*probability
    low = math.floor(position)
    high = min(low+1, len(ordered)-1)
    return ordered[low]+(ordered[high]-ordered[low])*(position-low)


def feature_tolerances(records, fraction):
    """fraction * interquartile range of each released reference feature."""
    if not 0 < fraction < 1:
        raise ValueError("Tolerance fraction must lie in (0,1)")
    tolerances = {}
    for name in FEATURE_ORDER:
        values = [r["features"][name] for r in records]
        spread = quantile(values, 0.75)-quantile(values, 0.25)
        if not math.isfinite(spread) or spread <= 0:
            raise ValueError(f"Degenerate reference spread for {name}")
        tolerances[name] = fraction*spread
    return tolerances


def substituted_features(folding, energy_hypothesis, transform_name):
    """RNAfold features under one grid cell.

    The frozen criterion applies the transform to ALO only; aup stays the
    untransformed ensemble mean, as specified.
    """
    candidates = folding["feature_candidates"]
    if energy_hypothesis not in ("mfe_energy_per_nt", "ensemble_energy_per_nt"):
        raise ValueError(f"Unknown energy hypothesis: {energy_hypothesis}")
    paired = alo_transform(transform_name)(folding["paired_probability_per_position"])
    values = {"energy_per_length": candidates[energy_hypothesis],
              "GC": candidates["gc_fraction"]*100,
              "aup": candidates["aup"],
              "alo": strand_alo(paired)}
    if not all(math.isfinite(x) for x in values.values()):
        raise ValueError("Nonfinite substituted feature")
    return values


def feature_deltas(reference, substituted, half_widths):
    """Signed differences and rounding-excess magnitudes per feature."""
    if set(reference) != set(FEATURE_ORDER) or set(substituted) != set(FEATURE_ORDER):
        raise ValueError("Both feature sets must carry the released feature order")
    out = {}
    for name in FEATURE_ORDER:
        delta = substituted[name]-reference[name]
        out[name] = {"delta": delta,
                     "released_rounding_half_width": half_widths[name],
                     "excess_over_rounding": max(0.0, abs(delta)-half_widths[name])}
    return out


def select_cell(selection_rows, energy_hypotheses, alo_transforms):
    """Apply the frozen selection rule to the burned selection set only."""
    if not selection_rows:
        raise ValueError("Selection set required")
    energy = min(energy_hypotheses,
                 key=lambda name: max(abs(row["energy"][name]) for row in selection_rows))
    def key(index_name):
        index, name = index_name
        worst = max(abs(row["alo"][name]) for row in selection_rows)
        kind = "identity" if name == "identity" else name.rpartition("_")[0]
        return (worst, 0 if name == "identity" else 1,
                0.0 if name == "identity" else float(name.rpartition("_")[2]),
                0 if kind in ("identity", "floor") else 1, index)
    transform = min(enumerate(alo_transforms), key=key)[1]
    return {"energy_hypothesis": energy, "alo_transform": transform}


def summarize(deltas, tolerances):
    """Median, 95th-percentile and max rounding-excess per feature, with passes."""
    out = {}
    for name in FEATURE_ORDER:
        excess = [d[name]["excess_over_rounding"] for d in deltas]
        worst = max(excess)
        out[name] = {"n": len(excess), "median_excess": quantile(excess, 0.5),
                     "p95_excess": quantile(excess, 0.95), "max_excess": worst,
                     "tolerance": tolerances[name], "passes": worst <= tolerances[name]}
    return out


def output_differences(component, reference_features, substituted, reference_prediction):
    """Predicted half-life shift caused by substituting features, in hours."""
    names = component["feature_order"]
    reference_check = linear_prediction(component, {k: reference_features[k] for k in names})
    substituted_prediction = linear_prediction(component, {k: substituted[k] for k in names})
    return {"reference_prediction_hours": reference_check,
            "substituted_prediction_hours": substituted_prediction,
            "difference_hours": substituted_prediction-reference_check,
            "frozen_replay_consistent": reference_prediction is None
            or abs(reference_check-reference_prediction) <= 1e-10}


def decide(feature_summary, output_max_difference, output_tolerance):
    """Frozen decision rules; feature agreement alone licenses unchanged STRAND."""
    feature_level = all(feature_summary[name]["passes"] for name in FEATURE_ORDER)
    output_level = output_max_difference <= output_tolerance
    if feature_level:
        outcome = "feature_level_compatible"
    elif output_level:
        outcome = "output_level_equivalent_separately_named_calibration_required"
    else:
        outcome = "rejected"
    return {"feature_level_compatible": feature_level,
            "output_level_equivalent": output_level,
            "outcome": outcome,
            "unchanged_published_strand_applicable": feature_level,
            "new_sequence_scoring_enabled": False,
            "stage3_ready": False,
            "note": "Label-free engine agreement. No stability, translation or "
                    "expression claim, and no Stage 2 gate progress, follows from this."}
