#!/usr/bin/env python3
"""Score the PERSIST-seq designed constructs with this project's frozen objective.

The earlier mRNAutilus comparison tested only in-solution half-life, which is
this project's training domain and not theirs. Leppek et al. 2022's
Supplementary Data 1 carries BOTH an in-solution and an in-cell half-life for
the SAME 191 designed constructs, with declared 5'UTR/CDS/3'UTR boundaries, so
the one-sided test can be replaced by a symmetric 2x2.

This script produces this project's half of that table. mRNAutilus's half is
produced in its own isolated environment and merged by
`scripts/build_two_axis_comparison.py`, because mRNAutilus needs torch,
flash-attn and a 1.78 GB checkpoint that this project neither depends on nor
redistributes.

The protocol, the metrics, the expected pattern and the falsification criterion
were declared in `configs/two_axis_comparison_v1_2026-10-20.json` BEFORE this
script was run. Nothing is refitted: the frozen coefficients are applied exactly
as recorded, and no in-cell label touches any coefficient.

The source archive is not redistributed. Pass its path; the script verifies both
recorded hashes before reading a row.

Usage:
    python scripts/run_two_axis_comparison.py --archive /path/to/MOESM4.zip
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
# ensemble_worker is called directly rather than via fold_fixed_input: that path
# builds a Transcript, which validates its CDS as a reading frame. These are full
# mRNAs whose declared CDS is followed by constant regions and a barcode, and the
# three calibration features need no CDS annotation at all.

PROTOCOL = ROOT / "configs/two_axis_comparison_v1_2026-10-20.json"
CALIBRATION = ROOT / "results/strand_rnafold_calibration_runs/20261019T174049.053308Z"
TABLE = "Supplementary Data 1 - Attributes for pooled 233 sequences.xlsx"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
BINS = ((1.00, 1.10), (1.10, 1.25), (1.25, 1.50), (1.50, 2.00), (2.00, math.inf))
# The pooled library uses TWO constant-region layouts. Most constructs interleave
# the barcode between the CDS and the 3'UTR; the 24 "CDS (Nluc) variants" place
# the 3'UTR directly after the CDS and push the constant regions and barcode to
# the very end. Both are tried and the one that reconstructs the RNA sequence
# exactly is accepted, so no record is dropped for being in the other layout.
LAYOUTS = (
    ("Sequence 5 UTR", "Sequence CDS", "Sequence Constant1", "Sequence Barcode",
     "Sequence Constant2", "Sequence 3 UTR", "Sequence Constant3"),
    ("Sequence 5 UTR", "Sequence CDS", "Sequence 3 UTR", "Sequence Constant1",
     "Sequence Barcode", "Sequence Constant2", "Sequence Constant3"),
)


def read_table(archive_path):
    """Read Supplementary Data 1 out of the zip without extracting it to disk.

    Third-party downloaded data: parsed with the standard library, never
    executed, and no spreadsheet package is introduced to read it.
    """
    with zipfile.ZipFile(archive_path) as outer:
        member = next(n for n in outer.namelist()
                      if n.endswith(TABLE) and not n.startswith("__MACOSX"))
        digest = hashlib.sha256(outer.read(member)).hexdigest()
        with outer.open(member) as handle, zipfile.ZipFile(handle) as book:
            shared = []
            if "xl/sharedStrings.xml" in book.namelist():
                shared = ["".join(t.text or "" for t in item.iter(f"{NS}t")) for item in
                          ET.fromstring(book.read("xl/sharedStrings.xml")).iter(f"{NS}si")]
            sheet = ET.fromstring(book.read("xl/worksheets/sheet1.xml"))
            rows = []
            for row in sheet.iter(f"{NS}row"):
                cells = {}
                for cell in row.iter(f"{NS}c"):
                    value = cell.find(f"{NS}v")
                    text = value.text if value is not None else ""
                    column = "".join(c for c in (cell.get("r") or "") if c.isalpha())
                    cells[column] = (shared[int(text)] if cell.get("t") == "s" and text
                                     else text) or ""
                rows.append(cells)
    header = {letter: name for letter, name in rows[0].items() if name}
    records = []
    for row in rows[1:]:
        record = {name: row.get(letter, "").strip() for letter, name in header.items()}
        if record.get("Sequence ID"):
            records.append(record)
    return records, digest


def number(record, key):
    try:
        return float(record[key])
    except (KeyError, ValueError):
        return None


def spearman(xs, ys):
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
    if len(xs) < 3:
        return None
    return statistics.correlation(ranks(xs), ranks(ys))


def bin_key(low, high):
    return f"{low:.2f}-{high:.2f}" if high != math.inf else f"above_{low:.2f}"


def concordance(predicted, measured):
    out = {}
    for low, high in BINS:
        pairs = agree = 0
        for i in range(len(measured)):
            for j in range(i + 1, len(measured)):
                small, large = sorted((measured[i], measured[j]))
                if small <= 0:
                    continue
                if low <= large / small < high:
                    pairs += 1
                    agree += (predicted[i] < predicted[j]) == (measured[i] < measured[j])
        out[bin_key(low, high)] = {"pairs": pairs,
                                   "concordance": agree / pairs if pairs else None}
    return out


def fold_one(payload):
    import subprocess

    index, sequence = payload
    try:
        done = subprocess.run(
            [sys.executable, "-m", "rnastable.ensemble_worker"],
            input=json.dumps({"sequence": sequence, "temperature": 37.0}),
            text=True, capture_output=True, timeout=600, check=True,
            cwd=str(ROOT / "src"))
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return index, None
    result = json.loads(done.stdout)
    if result.get("status") != "ok":
        return index, None
    candidates = result["feature_candidates"]
    return index, {"energy_per_length": candidates["ensemble_energy_per_nt"],
                   "GC": candidates["gc_fraction"] * 100,
                   "aup": candidates["aup"],
                   "gc_fraction": candidates["gc_fraction"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--archive", required=True,
                        help="path to the downloaded MOESM4 supplementary zip")
    parser.add_argument("--jobs", type=int, default=24)
    parser.add_argument("--out", default="results/two_axis_comparison_runs")
    args = parser.parse_args(argv)

    protocol = json.loads(PROTOCOL.read_text())
    declared = protocol["test_set"]
    archive = Path(args.archive)
    archive_digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if archive_digest != declared["archive_sha256"]:
        raise SystemExit(f"archive sha256 {archive_digest} does not match the protocol")

    records, table_digest = read_table(archive)
    if table_digest != declared["table_sha256"]:
        raise SystemExit(f"table sha256 {table_digest} does not match the protocol")
    if len(records) != declared["records_total"]:
        raise SystemExit(f"{len(records)} records, protocol declares "
                         f"{declared['records_total']}")

    model = json.loads((CALIBRATION / "calibration_model.json").read_text())
    arm = model["component"]
    train = list(csv.DictReader((CALIBRATION / "features/train_features.csv").open()))
    domain = {f: {"min": min(float(r[f]) for r in train), "max": max(float(r[f]) for r in train)}
              for f in ("energy_per_length", "GC", "aup")}
    training_values = {round(float(r["in_solution_half_life"]), 4) for r in train}

    # Both labels, all three declared segments, and a reconstruction that matches.
    candidates, dropped = [], {"missing_label": 0, "missing_segment": 0,
                               "reconstruction_mismatch": 0, "in_training_set": 0}
    for record in records:
        in_cell = number(record, "In-cell half-life")
        in_solution = number(record, "In-solution half-life")
        if in_cell is None or in_solution is None:
            dropped["missing_label"] += 1
            continue
        if not all(record.get(s) for s in ("Sequence 5 UTR", "Sequence CDS", "Sequence 3 UTR")):
            dropped["missing_segment"] += 1
            continue
        rna = record["RNA sequence"].strip().upper().replace("U", "T")
        layout = next((i for i, order in enumerate(LAYOUTS)
                       if "GGG" + "".join(record.get(s, "") for s in order).upper() == rna),
                      None)
        if layout is None:
            dropped["reconstruction_mismatch"] += 1
            continue
        if round(in_solution, 4) in training_values:
            dropped["in_training_set"] += 1
            continue
        candidates.append({
            "sequence_id": record["Sequence ID"],
            "name": record["Human-readable name"],
            "group": record.get("Group", ""),
            "length_nt": len(rna),
            "constant_region_layout": layout,
            "utr5_len": 3 + len(record["Sequence 5 UTR"]),
            "cds_len": len(record["Sequence CDS"]),
            "measured_in_cell_hours": in_cell,
            "measured_in_solution_hours": in_solution,
            "sequence_dna": rna,
            "baseline_eternafold_sup": number(record, "SUP EternaFold"),
        })

    print(f"records {len(records)}  dropped {dropped}  test set {len(candidates)}", flush=True)
    if len(candidates) != declared["declared_test_set_size"]:
        raise SystemExit(f"test set is {len(candidates)}, protocol declares "
                         f"{declared['declared_test_set_size']}")

    print(f"folding {len(candidates)} constructs on {args.jobs} workers...", flush=True)
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        for index, features in pool.map(
                fold_one, [(i, c["sequence_dna"].replace("T", "U"))
                       for i, c in enumerate(candidates)]):
            candidates[index]["features"] = features
    failed = [c["sequence_id"] for c in candidates if not c.get("features")]
    if failed:
        raise SystemExit(f"folding failed for {len(failed)}: {failed[:5]}")

    for entry in candidates:
        features = entry["features"]
        entry["predicted_hours"] = arm["intercept"] + sum(
            arm["coefficients"][f] * features[f] for f in arm["feature_order"])
        entry["features_outside_training_range"] = sorted(
            f for f in domain
            if not domain[f]["min"] <= features[f] <= domain[f]["max"])

    predicted = [e["predicted_hours"] for e in candidates]
    in_cell = [e["measured_in_cell_hours"] for e in candidates]
    in_solution = [e["measured_in_solution_hours"] for e in candidates]
    gc = [e["features"]["gc_fraction"] for e in candidates]
    # per-nucleotide EternaFold: the raw column is a sum over nucleotides and so
    # encodes length, the post-hoc correction recorded in external_validation_leppek_v1
    eterna = [-e["baseline_eternafold_sup"] / e["length_nt"]
              if e["baseline_eternafold_sup"] is not None else None for e in candidates]
    have_eterna = all(v is not None for v in eterna)

    summary = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": protocol["purpose"],
        "protocol": str(PROTOCOL.relative_to(ROOT)),
        "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
        "source": {"doi": protocol["test_set"]["doi"],
                   "archive_sha256": archive_digest, "table_sha256": table_digest,
                   "not_redistributed": protocol["test_set"]["not_redistributed"]},
        "counts": {"records": len(records), "dropped": dropped,
                   "test_set": len(candidates)},
        "calibration_run": str(CALIBRATION.relative_to(ROOT)),
        "refitting_performed": "none",
        "measured_axes": {
            "spearman_between_the_two_measured_axes": spearman(in_cell, in_solution),
            "note": "This bounds how well any single predictor could rank both axes at "
                    "once. If it is low, no predictor can win both columns.",
            "in_cell_range_hours": [min(in_cell), max(in_cell)],
            "in_solution_range_hours": [min(in_solution), max(in_solution)],
        },
        "ours": {
            "spearman_vs_in_solution": spearman(predicted, in_solution),
            "spearman_vs_in_cell": spearman(predicted, in_cell),
            "concordance_vs_in_solution": concordance(predicted, in_solution),
            "concordance_vs_in_cell": concordance(predicted, in_cell),
            "correlation_with_transcript_gc": statistics.correlation(gc, predicted),
            "records_extrapolating_on_any_feature": sum(
                1 for e in candidates if e["features_outside_training_range"]),
        },
        "free_eternafold_per_nucleotide": {
            "spearman_vs_in_solution": spearman(eterna, in_solution) if have_eterna else None,
            "spearman_vs_in_cell": spearman(eterna, in_cell) if have_eterna else None,
        } if have_eterna else {"available": False},
        "gc_alone": {
            "spearman_vs_in_solution": spearman(gc, in_solution),
            "spearman_vs_in_cell": spearman(gc, in_cell),
        },
        "their_side": "not in this artifact; produced in the isolated mRNAutilus "
                      "environment and merged by scripts/build_two_axis_comparison.py",
        "what_this_cannot_establish": protocol["what_this_cannot_establish"],
        "rows": [{k: v for k, v in e.items() if k != "sequence_dna"} for e in candidates],
    }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%f") + "Z"
    out = ROOT / args.out / stamp
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    with (out / "test_set.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sequence_id", "utr5_len", "cds_len", "length_nt",
                         "measured_in_cell_hours", "measured_in_solution_hours",
                         "sequence_rna"])
        for entry in candidates:
            writer.writerow([entry["sequence_id"], entry["utr5_len"], entry["cds_len"],
                             entry["length_nt"], entry["measured_in_cell_hours"],
                             entry["measured_in_solution_hours"],
                             entry["sequence_dna"].replace("T", "U")])
    print(f"wrote {out / 'summary.json'}")
    print(f"wrote {out / 'test_set.csv'}  (input for the mRNAutilus side)")
    print(f"\nmeasured axes agree at Spearman "
          f"{summary['measured_axes']['spearman_between_the_two_measured_axes']:+.4f}")
    print(f"ours vs in-solution  {summary['ours']['spearman_vs_in_solution']:+.4f}")
    print(f"ours vs in-cell      {summary['ours']['spearman_vs_in_cell']:+.4f}")
    if have_eterna:
        print(f"free EternaFold/nt vs in-solution "
              f"{summary['free_eternafold_per_nucleotide']['spearman_vs_in_solution']:+.4f}")
        print(f"free EternaFold/nt vs in-cell     "
              f"{summary['free_eternafold_per_nucleotide']['spearman_vs_in_cell']:+.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
