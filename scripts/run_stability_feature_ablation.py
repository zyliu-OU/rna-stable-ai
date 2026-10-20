#!/usr/bin/env python3
"""Is GC load-bearing, can the model order similar sequences, is the refit worth keeping?

Three questions in one run, all on the Leppek Fig_S8a records, all fitted on the
69 rows the calibration was trained on and scored once on the 123 held-out rows:

  A  ablation: drop each feature in turn and measure the held-out cost. GC is
     the one that matters, because m1-pseudouridine rescales its slope, it is one
     of only three inputs, and this project's construct extrapolates on it.
  B  fine ordering: pairwise concordance binned by how much two records actually
     differ. The design space produces 3 to 8 percent differences, so the
     narrowest bin is the one that decides whether synonymous ranking is possible.
  C  combination: does adding a free per-nucleotide EternaFold score beat both it
     and the refit?

Criteria are declared in `configs/stability_feature_ablation_v1_2026-10-20.json`
before any of these numbers existed. Every model is ordinary least squares so the
ablation is internally comparable; the frozen one-component PLS model is scored
alongside as a labelled reference, not as a variant, because it was fitted in R
and cannot be reproduced exactly here.
"""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import csv
import hashlib
import itertools
import json
import math
import statistics
import sys
import zipfile
import xml.etree.ElementTree as ET
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

PROTOCOL = ROOT / "configs/stability_feature_ablation_v1_2026-10-20.json"
CALIBRATION = ROOT / "results/strand_rnafold_calibration_runs/20261019T174049.053308Z"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
BASE = ("energy_per_length", "GC", "aup")
VARIANTS = {
    "full": ["energy_per_length", "GC", "aup"],
    "without_gc": ["energy_per_length", "aup"],
    "without_aup": ["energy_per_length", "GC"],
    "without_energy": ["GC", "aup"],
    "energy_only": ["energy_per_length"],
    "gc_only": ["GC"],
    "aup_only": ["aup"],
    "eternafold_only": ["eternafold_per_nt"],
    "full_plus_eternafold": ["energy_per_length", "GC", "aup", "eternafold_per_nt"],
}
BINS = ((1.00, 1.10), (1.10, 1.25), (1.25, 1.50), (1.50, 2.00), (2.00, math.inf))


def read_sheet(path, sheet):
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        targets = {r.get("Id"): r.get("Target") for r in
                   ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))}
        member = None
        for entry in workbook.iter(f"{NS}sheet"):
            if entry.get("name") == sheet:
                member = "xl/" + targets[entry.get(f"{REL}id")].lstrip("/").replace("xl/", "")
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            for item in ET.fromstring(archive.read("xl/sharedStrings.xml")).iter(f"{NS}si"):
                shared.append("".join(t.text or "" for t in item.iter(f"{NS}t")))

        def value(cell):
            node = cell.find(f"{NS}v")
            text = node.text if node is not None else ""
            if cell.get("t") == "s" and text:
                text = shared[int(text)]
            return text or ""

        rows = []
        for row in ET.fromstring(archive.read(member)).iter(f"{NS}row"):
            slots = {}
            for cell in row.iter(f"{NS}c"):
                column = "".join(ch for ch in (cell.get("r") or "") if ch.isalpha())
                slots[column] = value(cell)
            rows.append([slots[k] for k in sorted(slots, key=lambda k: (len(k), k))])
    header = rows[0]
    return [dict(zip(header, r)) for r in rows[1:] if any(r)]


def fold_one(payload):
    import json as _json
    import subprocess

    index, sequence = payload
    try:
        done = subprocess.run([sys.executable, "-m", "rnastable.ensemble_worker"],
                              input=_json.dumps({"sequence": sequence, "temperature": 37.0}),
                              text=True, capture_output=True, timeout=300, check=True,
                              cwd=str(ROOT / "src"))
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return index, None
    result = _json.loads(done.stdout)
    if result.get("status") != "ok":
        return index, None
    candidates = result["feature_candidates"]
    return index, {"energy_per_length": candidates["ensemble_energy_per_nt"],
                   "GC": candidates["gc_fraction"] * 100,
                   "aup": candidates["aup"]}


def fit_ols(rows, names):
    """Least squares with an intercept, solved by Gaussian elimination."""
    design = [[1.0] + [r["features"][n] for n in names] for r in rows]
    target = [r["measured_hours"] for r in rows]
    width = len(names) + 1
    normal = [[sum(design[k][i] * design[k][j] for k in range(len(rows)))
               for j in range(width)] + [sum(design[k][i] * target[k] for k in range(len(rows)))]
              for i in range(width)]
    for col in range(width):
        pivot = max(range(col, width), key=lambda r: abs(normal[r][col]))
        if abs(normal[pivot][col]) < 1e-12:
            raise SystemExit(f"Singular design for {names}")
        normal[col], normal[pivot] = normal[pivot], normal[col]
        scale = normal[col][col]
        normal[col] = [v / scale for v in normal[col]]
        for other in range(width):
            if other == col:
                continue
            factor = normal[other][col]
            normal[other] = [a - factor * b for a, b in zip(normal[other], normal[col])]
    coefficients = [row[-1] for row in normal]
    return {"intercept": coefficients[0],
            "coefficients": dict(zip(names, coefficients[1:])), "features": list(names)}


def predict(model, row):
    return model["intercept"] + sum(
        model["coefficients"][n] * row["features"][n] for n in model["features"])


def spearman(xs, ys):
    def ranks(values):
        order = sorted(range(len(values)), key=lambda i: values[i])
        out = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            shared = (i + j) / 2 + 1
            for k in range(i, j + 1):
                out[order[k]] = shared
            i = j + 1
        return out
    if len(xs) < 3 or len(set(xs)) < 2 or len(set(ys)) < 2:
        return None
    return statistics.correlation(ranks(xs), ranks(ys))


def concordance(predicted, measured):
    """Fraction of pairs ordered correctly, binned by the measured fold difference."""
    bins = {f"{lo:.2f}-{hi:.2f}" if hi != math.inf else f"above_{lo:.2f}":
            {"pairs": 0, "concordant": 0} for lo, hi in BINS}
    for i, j in itertools.combinations(range(len(measured)), 2):
        low, high = sorted((measured[i], measured[j]))
        if low <= 0:
            continue
        fold = high / low
        for lo, hi in BINS:
            if lo <= fold < hi:
                key = f"{lo:.2f}-{hi:.2f}" if hi != math.inf else f"above_{lo:.2f}"
                bins[key]["pairs"] += 1
                same = (predicted[i] < predicted[j]) == (measured[i] < measured[j])
                bins[key]["concordant"] += 1 if same else 0
                break
    for stats in bins.values():
        stats["concordance"] = (stats["concordant"] / stats["pairs"]) if stats["pairs"] else None
    return bins


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--workbook", required=True)
    parser.add_argument("--jobs", type=int, default=24)
    parser.add_argument("--out", default="results/stability_ablation_runs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    protocol = json.loads(PROTOCOL.read_text())
    digest = hashlib.sha256(Path(args.workbook).read_bytes()).hexdigest()
    if digest != protocol["data"]["workbook_sha256"]:
        raise SystemExit(f"Workbook hash mismatch; observed {digest}")
    print(f"workbook hash verified: {digest[:16]}…", flush=True)

    train = list(csv.DictReader((CALIBRATION / "features/train_features.csv").open()))
    training_half_lives = {round(float(r["in_solution_half_life"]), 6) for r in train}
    rows = []
    for record in read_sheet(args.workbook, protocol["data"]["sheet"]):
        if not record.get("RNA_sequence") or not record.get("half_life"):
            continue
        eternafold = record.get("SUP EternaFold FULL")
        sequence = record["RNA_sequence"].strip().upper().replace("T", "U")
        rows.append({
            "name": record["Human readable name"],
            "sequence": sequence,
            "length_nt": len(sequence),
            "measured_hours": float(record["half_life"]),
            "eternafold_sum": float(eternafold) if eternafold else None,
        })
    fit_rows = [r for r in rows if round(r["measured_hours"], 6) in training_half_lives]
    held_rows = [r for r in rows if round(r["measured_hours"], 6) not in training_half_lives]
    print(f"rows {len(rows)}  fit {len(fit_rows)}  held out {len(held_rows)}", flush=True)
    if (len(fit_rows), len(held_rows)) != (69, 123):
        raise SystemExit("Split differs from the declared 69 / 123")
    if args.dry_run:
        print("Dry run: split verified, nothing folded.", file=sys.stderr)
        return 0

    jobs = [(i, r["sequence"]) for i, r in enumerate(rows)]
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        for done, (index, features) in enumerate(pool.map(fold_one, jobs), 1):
            rows[index]["features"] = features
            if done % 60 == 0 or done == len(jobs):
                print(f"  folded {done}/{len(jobs)}", flush=True)
    for row in rows:
        if row["features"] and row["eternafold_sum"] is not None:
            row["features"]["eternafold_per_nt"] = row["eternafold_sum"] / row["length_nt"]

    def usable(group, names):
        return [r for r in group
                if r.get("features") and all(n in r["features"] for n in names)]

    # Provenance check: do recomputed features match the frozen training table?
    recomputed = {round(r["measured_hours"], 6): r["features"] for r in fit_rows
                  if r.get("features")}
    deltas = {name: [] for name in BASE}
    for record in train:
        key = round(float(record["in_solution_half_life"]), 6)
        if key in recomputed:
            for name in BASE:
                deltas[name].append(abs(float(record[name]) - recomputed[key][name]))
    provenance = {name: {"n": len(values), "max_absolute_difference": max(values) if values else None,
                         "median_absolute_difference": statistics.median(values) if values else None}
                  for name, values in deltas.items()}

    results = {}
    for label, names in VARIANTS.items():
        fit_set, held_set = usable(fit_rows, names), usable(held_rows, names)
        model = fit_ols(fit_set, names)
        held_predicted = [predict(model, r) for r in held_set]
        held_measured = [r["measured_hours"] for r in held_set]
        fit_predicted = [predict(model, r) for r in fit_set]
        results[label] = {
            "features": names,
            "model": model,
            "fit_n": len(fit_set),
            "held_out_n": len(held_set),
            "held_out_spearman": spearman(held_predicted, held_measured),
            "held_out_pearson_log": spearman(held_predicted, held_measured) and statistics.correlation(
                [math.log(max(p, 1e-6)) for p in held_predicted],
                [math.log(m) for m in held_measured]),
            "held_out_mae_hours": statistics.fmean(
                abs(p - m) for p, m in zip(held_predicted, held_measured)),
            "fit_spearman_upper_bound": spearman(
                fit_predicted, [r["measured_hours"] for r in fit_set]),
        }
        print(f"  {label:<22} held-out rho {results[label]['held_out_spearman']:+.4f}  "
              f"MAE {results[label]['held_out_mae_hours']:.3f} h  "
              f"(fit rho {results[label]['fit_spearman_upper_bound']:+.4f})", flush=True)

    # The frozen PLS model, scored as a labelled reference rather than a variant.
    frozen = json.loads((CALIBRATION / "calibration_model.json").read_text())["component"]
    frozen_set = usable(held_rows, BASE)
    frozen_predicted = [frozen["intercept"] + sum(
        frozen["coefficients"][n] * r["features"][n] for n in frozen["feature_order"])
        for r in frozen_set]
    frozen_measured = [r["measured_hours"] for r in frozen_set]
    frozen_reference = {
        "note": "frozen one-component PLS fitted in R; a labelled reference, not an OLS variant",
        "held_out_n": len(frozen_set),
        "held_out_spearman": spearman(frozen_predicted, frozen_measured),
        "held_out_mae_hours": statistics.fmean(
            abs(p - m) for p, m in zip(frozen_predicted, frozen_measured)),
    }

    criteria = protocol["declared_criteria"]
    gc_delta = results["without_gc"]["held_out_spearman"] - results["full"]["held_out_spearman"]
    if abs(gc_delta) <= 0.05:
        gc_verdict = "not_load_bearing"
    elif gc_delta < -0.10:
        gc_verdict = "load_bearing"
    else:
        gc_verdict = "ambiguous"

    bands = concordance(
        [predict(results["full"]["model"], r) for r in usable(held_rows, BASE)],
        [r["measured_hours"] for r in usable(held_rows, BASE)])
    narrow = bands["1.00-1.10"]["concordance"]
    if narrow is None:
        ordering_verdict = "undetermined"
    elif narrow <= 0.55:
        ordering_verdict = "cannot_order_similar"
    elif narrow >= 0.65:
        ordering_verdict = "can_order_similar"
    else:
        ordering_verdict = "ambiguous"

    best_single = max(results["full"]["held_out_spearman"],
                      results["eternafold_only"]["held_out_spearman"])
    combination_gain = results["full_plus_eternafold"]["held_out_spearman"] - best_single
    if combination_gain >= 0.05:
        combination_verdict = "combination_has_value"
    elif abs(results["eternafold_only"]["held_out_spearman"]
             - results["full"]["held_out_spearman"]) <= 0.05:
        combination_verdict = "prefer_the_free_predictor"
    else:
        combination_verdict = "keep_the_refit_no_combination_gain"

    quartile_spearman = {}
    scored = sorted(usable(held_rows, BASE), key=lambda r: r["measured_hours"])
    size = max(1, len(scored) // 4)
    for index in range(4):
        chunk = scored[index * size:(index + 1) * size] if index < 3 else scored[3 * size:]
        quartile_spearman[f"q{index + 1}"] = {
            "n": len(chunk),
            "measured_range": [chunk[0]["measured_hours"], chunk[-1]["measured_hours"]],
            "spearman": spearman([predict(results["full"]["model"], r) for r in chunk],
                                 [r["measured_hours"] for r in chunk]),
        }

    payload = {
        "purpose": protocol["purpose"],
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": str(PROTOCOL.relative_to(ROOT)),
        "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
        "workbook_hash_verified": True,
        "counts": {"rows": len(rows), "fit": len(fit_rows), "held_out": len(held_rows)},
        "estimator": protocol["estimator"],
        "feature_provenance_check": provenance,
        "variants": results,
        "frozen_pls_reference": frozen_reference,
        "A_gc_ablation": {
            "full_spearman": results["full"]["held_out_spearman"],
            "without_gc_spearman": results["without_gc"]["held_out_spearman"],
            "delta": gc_delta,
            "verdict": gc_verdict,
            "criteria": criteria["A_gc_ablation"],
        },
        "B_fine_ordering": {
            "pairwise_concordance_by_measured_fold_difference": bands,
            "narrowest_bin_concordance": narrow,
            "verdict": ordering_verdict,
            "spearman_within_measured_quartiles": quartile_spearman,
            "criteria": criteria["B_fine_ordering"],
            "why_the_narrowest_bin_matters": (
                "This project's design space produces differences of 3 to 8 percent, which "
                "fall inside the 1.00 to 1.10 bin. Chance is 0.50."),
        },
        "C_combination": {
            "full_spearman": results["full"]["held_out_spearman"],
            "eternafold_only_spearman": results["eternafold_only"]["held_out_spearman"],
            "combined_spearman": results["full_plus_eternafold"]["held_out_spearman"],
            "gain_over_best_single": combination_gain,
            "verdict": combination_verdict,
            "criteria": criteria["C_combination"],
        },
        "what_this_cannot_establish": protocol["what_this_cannot_establish"],
        "no_claim": [
            "These are rank statistics on 123 records, not a demonstration of absolute accuracy.",
            "A better-performing variant does not become the project default here; that is a "
            "gate decision.",
            "Every model was fitted on the 69 fit rows only and the held-out rows were scored "
            "once per model, so no variant was selected using them.",
            "The frozen PLS model is reported as a labelled reference; OLS results do not "
            "transfer to it.",
            "Nothing here touches the translation side, in-cell stability, or this project's "
            "own 1811 nt construct.",
        ],
    }

    print("\n=== A: is GC load-bearing? ===")
    print(f"  full {results['full']['held_out_spearman']:+.4f}  without_gc "
          f"{results['without_gc']['held_out_spearman']:+.4f}  delta {gc_delta:+.4f}"
          f"  -> {gc_verdict.upper()}")
    print("=== B: can it order similar sequences? ===")
    for key, stats in bands.items():
        if stats["pairs"]:
            print(f"  measured fold {key:<12} pairs {stats['pairs']:>6}  "
                  f"concordance {stats['concordance']:.4f}")
    print(f"  -> {ordering_verdict.upper()}  (chance is 0.5000)")
    print("  Spearman within measured quartiles: " + "  ".join(
        f"{k} {v['spearman']:+.3f}" if v["spearman"] is not None else f"{k} n/a"
        for k, v in quartile_spearman.items()))
    print("=== C: does the refit earn its keep? ===")
    print(f"  full {results['full']['held_out_spearman']:+.4f}  eternafold_only "
          f"{results['eternafold_only']['held_out_spearman']:+.4f}  combined "
          f"{results['full_plus_eternafold']['held_out_spearman']:+.4f}  "
          f"gain {combination_gain:+.4f}  -> {combination_verdict.upper()}")
    print("=== feature provenance against the frozen training table ===")
    for name, stats in provenance.items():
        print(f"  {name:<18} n={stats['n']}  max |diff| "
              f"{stats['max_absolute_difference']:.6g}")

    if args.dry_run:
        return 0
    out = ROOT / args.out / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True, exist_ok=False)
    (out / "summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(f"\nWrote {out}/summary.json", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
