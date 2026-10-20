#!/usr/bin/env python3
"""Test strand_rnafold_calibration_v1 against measured half-lives it never saw.

The calibration was fitted on 69 records that turn out to be rows of Leppek et
al. 2022's Supplementary Fig S8a. That sheet holds 192 records, so 123 of them
are genuinely held out: same measured quantity, same assay, same lab, and not in
the training set.

The protocol, the metrics, the expected direction and the falsification
criterion were declared in
`configs/external_validation_leppek_v1_2026-10-20.json` BEFORE this script was
run, so the result is able to fail. Nothing is refitted: the frozen coefficients
are applied exactly as recorded.

The source workbook is not redistributed. Pass its path; the script verifies the
recorded sha256 before reading a single row, so a different file cannot be
silently substituted.
"""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import csv
import hashlib
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
# The ensemble worker is called directly rather than through
# component_integration.fold_fixed_input, because that path builds a Transcript
# and a Transcript validates its CDS as a real reading frame. These records are
# full mRNAs with their own UTRs and the sheet gives no CDS boundaries, and the
# three calibration features need no CDS annotation at all. Inventing a CDS to
# satisfy a validator would be worse than not using it.

PROTOCOL = ROOT / "configs/external_validation_leppek_v1_2026-10-20.json"
CALIBRATION = ROOT / "results/strand_rnafold_calibration_runs/20261019T174049.053308Z"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def read_sheet(path, sheet):
    """Read one sheet of an xlsx with the standard library only.

    The workbook is third-party downloaded data, so it is parsed rather than
    executed and no spreadsheet library is introduced to read it.
    """
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        targets = {r.get("Id"): r.get("Target") for r in
                   ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))}
        member = None
        for entry in workbook.iter(f"{NS}sheet"):
            if entry.get("name") == sheet:
                member = "xl/" + targets[entry.get(f"{REL}id")].lstrip("/").replace("xl/", "")
        if member is None:
            raise SystemExit(f"Sheet {sheet!r} not found in {path}")
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in strings.iter(f"{NS}si"):
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


def calibration():
    model = json.loads((CALIBRATION / "calibration_model.json").read_text())
    arm = model["component"]
    train = list(csv.DictReader((CALIBRATION / "features/train_features.csv").open()))
    domain = {f: {"min": min(float(r[f]) for r in train), "max": max(float(r[f]) for r in train)}
              for f in ("energy_per_length", "GC", "aup")}
    half_lives = {round(float(r["in_solution_half_life"]), 6) for r in train}
    return model, arm, domain, half_lives, train


def spearman(xs, ys):
    """Rank correlation with average ranks for ties."""
    def ranks(values):
        order = sorted(range(len(values)), key=lambda i: values[i])
        result = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            shared = (i + j) / 2 + 1
            for k in range(i, j + 1):
                result[order[k]] = shared
            i = j + 1
        return result
    return pearson(ranks(xs), ranks(ys))


def pearson(xs, ys):
    if len(xs) < 3 or len(set(xs)) < 2 or len(set(ys)) < 2:
        return None
    return statistics.correlation(xs, ys)


def fold_one(payload):
    """Fold one sequence in the isolated ensemble worker, no CDS required."""
    import subprocess

    index, sequence = payload
    try:
        done = subprocess.run(
            [sys.executable, "-m", "rnastable.ensemble_worker"],
            input=json.dumps({"sequence": sequence, "temperature": 37.0}),
            text=True, capture_output=True, timeout=300, check=True,
            cwd=str(ROOT / "src"))
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return index, None
    result = json.loads(done.stdout)
    if result.get("status") != "ok":
        return index, None
    candidates = result["feature_candidates"]
    return index, {"energy_per_length": candidates["ensemble_energy_per_nt"],
                   "GC": candidates["gc_fraction"] * 100,
                   "aup": candidates["aup"]}


def metrics(rows, label):
    predicted = [r["predicted_hours"] for r in rows]
    measured = [r["measured_hours"] for r in rows]
    return {
        "label": label,
        "n": len(rows),
        "spearman": spearman(predicted, measured),
        "pearson_log": pearson([math.log(p) for p in predicted] if all(p > 0 for p in predicted)
                               else predicted, [math.log(m) for m in measured]),
        "mean_absolute_error_hours": statistics.fmean(
            abs(r["predicted_hours"] - r["measured_hours"]) for r in rows),
        "predicted_range": [min(predicted), max(predicted)],
        "measured_range": [min(measured), max(measured)],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--workbook", required=True,
                        help="path to the downloaded MOESM6 xlsx; its hash is verified")
    parser.add_argument("--jobs", type=int, default=24)
    parser.add_argument("--out", default="results/external_validation_leppek_runs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    protocol = json.loads(PROTOCOL.read_text())
    source = protocol["source"]
    digest = hashlib.sha256(Path(args.workbook).read_bytes()).hexdigest()
    if digest != source["file_sha256"]:
        raise SystemExit(f"Workbook hash mismatch.\n  expected {source['file_sha256']}\n"
                         f"  observed {digest}\nThis is a different file.")
    print(f"workbook hash verified: {digest[:16]}…", flush=True)

    rows = [r for r in read_sheet(args.workbook, source["sheet"])
            if r.get("RNA_sequence") and r.get("half_life")]
    if len(rows) != source["rows_with_sequence_and_half_life"]:
        raise SystemExit(f"Expected {source['rows_with_sequence_and_half_life']} usable rows, "
                         f"found {len(rows)}")

    model, arm, domain, training_half_lives, train = calibration()
    held, used = [], []
    for row in rows:
        entry = {
            "name": row["Human readable name"],
            "experiment": row.get("Expt type", ""),
            "sequence": row["RNA_sequence"].strip().upper().replace("T", "U"),
            "measured_hours": float(row["half_life"]),
            "measured_error_hours": float(row["half_life_err"]) if row.get("half_life_err") else None,
            "length_nt": len(row["RNA_sequence"].strip()),
            "baselines": {name: float(row[name]) for name in
                          protocol["declared_criteria"]["baseline_comparison"]["baselines"]
                          if row.get(name) not in (None, "")},
        }
        (used if round(entry["measured_hours"], 6) in training_half_lives else held).append(entry)
    print(f"rows {len(rows)}  training overlap {len(used)}  held out {len(held)}", flush=True)
    if len(held) != protocol["held_out_set"]["n"]:
        raise SystemExit(f"Expected {protocol['held_out_set']['n']} held-out records, "
                         f"found {len(held)}")
    if args.dry_run:
        print("Dry run: no folding, nothing written.", file=sys.stderr)
        return 0

    for label, group in (("held-out", held), ("training", used)):
        jobs = [(i, e["sequence"]) for i, e in enumerate(group)]
        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            for done, (index, features) in enumerate(pool.map(fold_one, jobs), 1):
                group[index]["features"] = features
                if done % 40 == 0 or done == len(jobs):
                    print(f"  folded {label} {done}/{len(jobs)}", flush=True)

    for group in (held, used):
        for entry in group:
            if not entry.get("features"):
                entry["predicted_hours"] = None
                continue
            features = entry["features"]
            entry["predicted_hours"] = arm["intercept"] + sum(
                arm["coefficients"][f] * features[f] for f in arm["feature_order"])
            entry["features_outside_training_range"] = [
                f for f in arm["feature_order"]
                if not domain[f]["min"] <= features[f] <= domain[f]["max"]]

    scored = [e for e in held if e.get("predicted_hours") is not None]
    in_domain = [e for e in scored if not e["features_outside_training_range"]]
    train_scored = [e for e in used if e.get("predicted_hours") is not None]

    # POST-HOC CORRECTION, disclosed rather than applied silently. The declared
    # protocol compared the paper's predictor columns raw. Those columns are SUMS
    # over nucleotides: on these records they correlate with sequence length at
    # Spearman +0.94 to +0.98, so raw they encode length rather than degradation
    # rate, and comparing them raw against half-life misuses the column. Both the
    # declared raw comparison and a per-nucleotide one are reported. The
    # justification is mechanical -- a sum over a variable-length sequence -- not
    # that the normalised figures flatter or disfavour this project.
    baseline_names = protocol["declared_criteria"]["baseline_comparison"]["baselines"]
    lengths = [e["length_nt"] for e in scored]
    measured = [e["measured_hours"] for e in scored]
    baseline_metrics = {}
    for name in baseline_names:
        rows_with = [e for e in scored if name in e["baselines"]]
        if len(rows_with) < 3:
            continue
        raw = [e["baselines"][name] for e in rows_with]
        per_nt = [e["baselines"][name] / e["length_nt"] for e in rows_with]
        target = [e["measured_hours"] for e in rows_with]
        rho_raw = spearman(raw, target)
        rho_per = spearman(per_nt, target)
        baseline_metrics[name] = {
            "n": len(rows_with),
            "spearman_raw_as_declared": rho_raw,
            "spearman_raw_vs_length": spearman(raw, [e["length_nt"] for e in rows_with]),
            "spearman_per_nucleotide": rho_per,
            "absolute_spearman": abs(rho_per) if rho_per is not None else None,
            "statistic_used_for_ranking": "per-nucleotide, see the post-hoc correction note",
        }
    length_confound = {
        "spearman_length_vs_measured_half_life": spearman(lengths, measured),
        "note": ("Length itself barely tracks half-life on these records, so length is not a "
                 "confound in this project's prediction; it is a confound only in the "
                 "paper's summed columns."),
    }

    calibration_metrics = metrics(scored, "held_out_all")
    ours = abs(calibration_metrics["spearman"]) if calibration_metrics["spearman"] else 0.0
    beaten_by = [n for n, m in baseline_metrics.items()
                 if m["absolute_spearman"] and m["absolute_spearman"] > ours]

    payload = {
        "purpose": protocol["purpose"],
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": str(PROTOCOL.relative_to(ROOT)),
        "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
        "source": {k: source[k] for k in ("doi", "sheet", "file_sha256", "measured_quantity")},
        "workbook_hash_verified": True,
        "refitting_performed": False,
        "counts": {"sheet_rows": len(rows), "training_overlap": len(used),
                   "held_out": len(held), "held_out_scored": len(scored),
                   "held_out_in_domain": len(in_domain)},
        "primary": calibration_metrics,
        "held_out_in_domain_only": metrics(in_domain, "held_out_in_domain") if len(in_domain) > 2 else None,
        "training_subset_upper_bound": metrics(train_scored, "training_subset") if train_scored else None,
        "baselines_on_the_same_records": baseline_metrics,
        "baseline_post_hoc_correction": {
            "what_was_declared": "compare the paper's predictor columns raw",
            "what_was_wrong": ("those columns are sums over nucleotides and correlate with "
                               "sequence length at Spearman +0.94 to +0.98 on these records, "
                               "so raw they encode length rather than degradation rate"),
            "what_was_changed": "a per-nucleotide comparison is reported beside the declared raw one",
            "when": "AFTER the primary result was computed; disclosed, not applied silently",
            "justification": "mechanical, a sum over a variable-length sequence",
            "effect_on_the_primary_metric": "none; this project's own prediction was not touched",
        },
        "length_confound_check": length_confound,
        "baselines_beating_the_calibration": beaten_by,
        "verdict": {
            "declared_falsification": protocol["declared_criteria"]["falsification"],
            "declared_weak_threshold": protocol["declared_criteria"]["weak_transfer_threshold"],
            "spearman": calibration_metrics["spearman"],
            "transfers": (calibration_metrics["spearman"] or 0) > 0.3,
            "falsified": (calibration_metrics["spearman"] or 0) <= 0,
            "adds_nothing_over_published_baselines": len(beaten_by) == len(baseline_metrics)
                                                     and bool(baseline_metrics),
        },
        "rows": [{k: v for k, v in e.items() if k != "sequence"} for e in held],
        "what_this_cannot_establish": protocol["what_this_cannot_establish"],
        "no_claim": [
            "A correlation is not a calibration. No absolute accuracy is established.",
            "The held-out records are a different reporter and a wider length and half-life "
            "range than the training subset, so model failure and distribution shift cannot "
            "be separated with this data alone.",
            "The training-subset figures are an upper bound on what the model can do, not a "
            "result; the model was fitted on those records.",
            "This says nothing about the translation side, about in-cell stability, or about "
            "the project's own 1811 nt construct, which lies outside this dataset's ranges.",
        ],
    }

    print(f"\n=== held out, all {calibration_metrics['n']} ===")
    print(f"  Spearman {calibration_metrics['spearman']:+.4f}   "
          f"Pearson(log) {calibration_metrics['pearson_log']:+.4f}   "
          f"MAE {calibration_metrics['mean_absolute_error_hours']:.3f} h")
    if payload["held_out_in_domain_only"]:
        d = payload["held_out_in_domain_only"]
        print(f"=== held out, in-domain {d['n']} ===")
        print(f"  Spearman {d['spearman']:+.4f}   Pearson(log) {d['pearson_log']:+.4f}   "
              f"MAE {d['mean_absolute_error_hours']:.3f} h")
    if payload["training_subset_upper_bound"]:
        t = payload["training_subset_upper_bound"]
        print(f"=== training subset {t['n']} (upper bound, not a result) ===")
        print(f"  Spearman {t['spearman']:+.4f}   MAE {t['mean_absolute_error_hours']:.3f} h")
    print(f"  length vs measured half-life: rho "
          f"{length_confound['spearman_length_vs_measured_half_life']:+.4f}")
    print("=== the paper's own predictors, same held-out records ===")
    for name, m in baseline_metrics.items():
        print(f"  {name:<26} n={m['n']:<4} raw {m['spearman_raw_as_declared']:+.4f} "
              f"(vs length {m['spearman_raw_vs_length']:+.4f})   "
              f"per-nt {m['spearman_per_nucleotide']:+.4f}  |rho| {m['absolute_spearman']:.4f}")
    print(f"\ntransfers (rho > 0.3): {payload['verdict']['transfers']}   "
          f"falsified (rho <= 0): {payload['verdict']['falsified']}   "
          f"beaten by all baselines: {payload['verdict']['adds_nothing_over_published_baselines']}")

    out = ROOT / args.out / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True, exist_ok=False)
    (out / "summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(f"\nWrote {out}/summary.json", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
