"""RiboNN checkpoint and output audit contracts, independent of its old runtime."""
import csv
import hashlib
import math
from pathlib import Path


def selected_checkpoints(rows, top_k=5):
    if type(top_k) is not int or top_k < 1:
        raise ValueError("Positive checkpoint budget required")
    selected = []
    if len({row["run_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate run IDs in checkpoint inventory")
    grouped = {}
    for row in rows:
        raw = row["params.test_fold"]
        fold_float = float(raw)
        if not math.isfinite(fold_float) or not fold_float.is_integer():
            raise ValueError("Noninteger test fold")
        fold = int(fold_float)
        score = float(row["metrics.val_r2"])
        if not math.isfinite(score):
            raise ValueError("Nonfinite checkpoint selection score")
        rid = row["run_id"]
        if not rid or any(x in rid for x in ["/","\\",".."]):
            raise ValueError("Unsafe checkpoint identity")
        grouped.setdefault(fold,[]).append((score,rid,row))
    for fold in sorted(grouped):
        ranked = sorted(grouped[fold],key=lambda row:-row[0])
        if len(ranked) < top_k:
            raise ValueError("Incomplete top-k checkpoint inventory")
        if len(ranked)>top_k and ranked[top_k-1][0]==ranked[top_k][0]:
            raise ValueError("Ambiguous validation-score tie at checkpoint boundary")
        # All tied selected values must also be rejected because the legacy
        # pandas quicksort order is not an explicitly stable selection rule.
        if len({row[0] for row in ranked[:top_k]})!=top_k:
            raise ValueError("Ambiguous selected checkpoint order")
        for score,rid,row in ranked[:top_k]:
            selected.append({"fold":fold,"run_id":rid,"validation_r2":score,
                             "selection":"released_top_k_by_validation_r2_descending"})
    if not selected:
        raise ValueError("Empty checkpoint inventory")
    return selected


def verify_weight_files(manifest, root):
    root = Path(root).resolve()
    for entry in manifest["files"]:
        path = (root/entry["path"]).resolve()
        if not path.is_relative_to(root) or path.stat().st_size != entry["bytes"]:
            raise ValueError("Weight file length/path mismatch")
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError("Weight file checksum mismatch")
    return len(manifest["files"])


def exact_prediction_replay(first, second, score_column):
    def indexed(rows):
        out = {}
        for row in rows:
            key = (row["tx_id"],int(row["fold"]))
            if key in out:
                raise ValueError("Duplicate prediction identity")
            score = float(row[score_column])
            if not math.isfinite(score):
                raise ValueError("Nonfinite prediction")
            out[key] = (row["tx_sequence"],score)
        return out
    a,b = indexed(first),indexed(second)
    if not a or a.keys()!=b.keys():
        raise ValueError("Prediction replay inventory mismatch")
    if any(a[k][0]!=b[k][0] for k in a):
        raise ValueError("Prediction replay sequence mismatch")
    error = max(abs(a[k][1]-b[k][1]) for k in a)
    if error != 0:
        raise ValueError(f"Nondeterministic prediction replay: {error}")
    return {"rows":len(a),"max_abs_difference":error,"bitwise_float_equal":True}
