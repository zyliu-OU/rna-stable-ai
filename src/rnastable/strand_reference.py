"""Reference-only STRAND score replay; new folding features remain gated."""
import hashlib
import json
import math

from .component_integration import strand_alo

FEATURE_ORDER = ["energy_per_length", "GC", "aup", "alo"]


def reference_record(row, cohort):
    length = int(row["seq_len"] if "seq_len" in row else row["length"])
    sequence = row["sequence"]
    probabilities = json.loads(row["bpp_per_pos"])
    if len(sequence) != length or len(probabilities) != length:
        raise ValueError("Reference sequence/probability length mismatch")
    if set(sequence)-set("ACGU"):
        raise ValueError("Canonical RNA reference required")
    values = {"energy_per_length": float(row["energy"])/length,
              "GC": float(row["GC"]), "aup": float(row["aup"]),
              "alo": strand_alo(probabilities)}
    if not all(math.isfinite(x) for x in values.values()):
        raise ValueError("Nonfinite reference feature")
    if not 0 <= values["GC"] <= 100 or not 0 <= values["aup"] <= 1:
        raise ValueError("Invalid reference feature units/range")
    return {"name":row["name"], "cohort":cohort,
            "input_sha256":hashlib.sha256(sequence.encode()).hexdigest(),
            "feature_source":"released_LinearPartition_features", "features":values,
            "observed_half_life":float(row["in_solution_half_life"])}


def feature_identity(record):
    fields = {k:record[k] for k in ("name","cohort","input_sha256","feature_source","features")}
    return hashlib.sha256(json.dumps(fields,sort_keys=True,allow_nan=False).encode()).hexdigest()


def linear_prediction(component, features):
    """Raw-unit coefficient evaluation for audited exports and diagnostics."""
    names = component["feature_order"]
    if set(features) != set(names):
        raise ValueError("Feature names do not match the fitted model")
    if not all(type(x) in (int,float) and math.isfinite(x) for x in features.values()):
        raise ValueError("Finite numeric features required")
    return component["intercept"]+sum(component["coefficients"][k]*features[k] for k in names)


def replay_reference(model, record):
    if model.get("schema_version") != 1 or model.get("new_sequence_scoring_enabled") is not False:
        raise ValueError("Reference-only model contract required")
    if record.get("feature_source") != "released_LinearPartition_features":
        raise ValueError("RNAfold-derived or unknown features require compatibility/calibration review")
    identity = feature_identity(record)
    if identity not in model["allowed_reference_feature_identities"]:
        raise ValueError("Reference identity/feature values are not in the frozen inventory")
    return {"name":record["name"], "input_sha256":record["input_sha256"],
            "feature_identity":identity,
            "predicted_half_life":linear_prediction(model["component"],record["features"]),
            "units":"hours", "interpretation":"released-reference model replay only",
            "independent_validation":False}
