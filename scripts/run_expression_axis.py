#!/usr/bin/env python3
"""Characterise the EXPRESSION axis on the 24 unexposed CDS designs.

The expression axis has never been measured in this project. Gate v16 prohibits
presenting in-cell stability as a validated expression proxy, and it rests that
prohibition on 6 paired constructs. Supplementary Data 6 carries 24 constructs
with measured Nluc/Fluc protein output at two time points, 4 replicates each,
with standard deviations, and matched in-cell half-life. This runs the primary
test on 24 instead of 6.

The construct set is unusually clean for this project: constant 883 nt, constant
53 nt and 209 nt UTRs, one 207 aa protein across all 24, and zero overlap with
Supplementary Data 1, so it is unexposed to every fit and screen here. Constant
length makes a length artifact structurally impossible, which neither the
two-axis set nor the in-cell screen could claim.

One source defect is enforced against rather than worked around: the 'Sequence'
column is exactly permuted against 'sequence_with_UTRs' for 5 of the 24 rows, in
a 2-cycle and a 3-cycle. Because every design is synonymous, all 5 still
translate to the right protein, so a protein check does not catch it. Features
come from sequence_with_UTRs only, and the permutation is re-detected at read
time and recorded.

NOTHING is fitted and no split is made. n=24 supports neither; gate v15 measured
that 105 records support about one feature. This is a characterisation.

Protocol, hashed before any relationship was computed:
    configs/expression_axis_v1_2026-10-21.json

Usage:
    python scripts/run_expression_axis.py --archive /path/to/MOESM4.zip
"""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_two_axis_comparison import CALIBRATION, fold_one, spearman  # noqa: E402

PROTOCOL = ROOT / "configs/expression_axis_v1_2026-10-21.json"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
ARCHIVE_SHA256 = "849ed7b49198c5b97049fec8d3636deea8812db4dd45ce0bcc448297703511c2"
DATA6 = "Data 6 - Attributes for 24 CDS designs"
DATA5 = "Data 5 - Significance tests for 24 CDS designs"

# Enforced layout of sequence_with_UTRs. Verified for all 24 before the protocol
# was declared; re-enforced here so a changed source cannot pass silently.
FULL_LEN = 883
UTR5_LEN = 53
CDS_LEN = 621
CDS_START, CDS_END = UTR5_LEN, UTR5_LEN + CDS_LEN
STOPS = {"UAA", "UAG", "UGA"}


def read_sheet(archive_path, want, sheet="xl/worksheets/sheet1.xml"):
    """Read one supplementary sheet out of the zip with the standard library only.

    Third-party downloaded data: parsed, never executed, and no spreadsheet
    package is introduced to read it. Mirrors run_two_axis_comparison.read_table.
    """
    with zipfile.ZipFile(archive_path) as outer:
        member = next(n for n in outer.namelist()
                      if want in n and n.endswith(".xlsx") and not n.startswith("__MACOSX"))
        digest = hashlib.sha256(outer.read(member)).hexdigest()
        with outer.open(member) as handle, zipfile.ZipFile(handle) as book:
            shared = []
            if "xl/sharedStrings.xml" in book.namelist():
                shared = ["".join(t.text or "" for t in item.iter(f"{NS}t")) for item in
                          ET.fromstring(book.read("xl/sharedStrings.xml")).iter(f"{NS}si")]
            rows = []
            for row in ET.fromstring(book.read(sheet)).iter(f"{NS}row"):
                cells = {}
                for cell in row.iter(f"{NS}c"):
                    value = cell.find(f"{NS}v")
                    text = value.text if value is not None else ""
                    column = "".join(c for c in (cell.get("r") or "") if c.isalpha())
                    cells[column] = (shared[int(text)] if cell.get("t") == "s" and text
                                     else text) or ""
                rows.append(cells)
    header = {letter: name for letter, name in rows[0].items() if name}
    records = [{name: row.get(letter, "").strip() for letter, name in header.items()}
               for row in rows[1:]]
    return member, digest, records


def number(record, field):
    try:
        return float(record[field])
    except (KeyError, TypeError, ValueError):
        return None


def translate(rna):
    bases = "UCAG"
    aas = "FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG"
    table = {}
    index = 0
    for first in bases:
        for second in bases:
            for third in bases:
                table[first + second + third] = aas[index]
                index += 1
    return "".join(table.get(rna[i:i + 3], "?") for i in range(0, len(rna) - 2, 3))


def integrity(records):
    """Re-detect the Sequence-column permutation; never trust that column.

    Reported rather than silently bypassed, because the same class of defect in
    this source - a column meaning something other than its obvious reading -
    produced the published +0.4190 error that gate v15 had to correct.
    """
    embedded = {r["Sequence ID"]: r["sequence_with_UTRs"].upper()[CDS_START:CDS_END]
                for r in records}
    column = {r["Sequence ID"]: r["Sequence"].upper() for r in records}
    mismatched, permutation = [], {}
    for key, cds in embedded.items():
        if cds == column[key]:
            continue
        mismatched.append(key)
        holder = [other for other, value in column.items() if value == cds]
        permutation[key] = holder[0] if len(holder) == 1 else None
    proteins = {translate(cds) for cds in embedded.values()}
    utr5 = {r["sequence_with_UTRs"].upper()[:UTR5_LEN] for r in records}
    utr3 = {r["sequence_with_UTRs"].upper()[CDS_END:] for r in records}
    return {
        "authoritative_field": "sequence_with_UTRs",
        "sequence_column_used_for_features": False,
        "rows": len(records),
        "sequence_column_mismatched_rows": sorted(mismatched),
        "sequence_column_mismatch_count": len(mismatched),
        "permutation_resolves_every_mismatch": all(permutation.values()) and bool(permutation),
        "permutation_map_mismatched_row_to_holder_of_its_cds": permutation,
        "protein_identical_across_all_rows": len(proteins) == 1,
        "distinct_proteins": len(proteins),
        "protein_length_aa": len(next(iter(proteins))),
        "note_on_why_a_protein_check_misses_this":
            "All 24 are synonymous designs of one protein, so a permuted assignment "
            "still translates correctly. Protein identity passes on every bad row.",
        "constant_utr5_len": UTR5_LEN if len(utr5) == 1 else None,
        "constant_utr3_len": len(next(iter(utr3))) if len(utr3) == 1 else None,
        "utr_features_have_zero_variance": len(utr5) == 1 and len(utr3) == 1,
        "all_full_length_equal": {len(r["sequence_with_UTRs"]) for r in records} == {FULL_LEN},
    }


def cv_analysis(entries):
    """Measured CV, and what it implies for resolution. No floor is frozen."""
    out = {}
    for label in ("6h", "24h"):
        values = [(e[f"nluc_fluc_{label}_mean"], e[f"nluc_fluc_{label}_sd"], e["replicates"])
                  for e in entries
                  if e[f"nluc_fluc_{label}_mean"] and e[f"nluc_fluc_{label}_sd"]]
        cvs = sorted(sd / mean for mean, sd, _ in values)
        replicates = sorted({n for _, _, n in values if n})
        median_cv = statistics.median(cvs)
        # ln(1 + CV) convention, matching src/rnastable/assay_power.py so the
        # number is comparable to the frozen power table.
        sigma = math.log(1 + median_cv)
        n = replicates[0] if len(replicates) == 1 else min(replicates)
        # Two-sided 0.05, 80 percent power, on the log scale, two groups of n.
        mde = math.exp(2.802 * sigma * math.sqrt(2.0 / n)) if n else None
        means = [mean for mean, _, _ in values]
        sds = [sd for _, sd, _ in values]
        pairs = resolvable = 0
        for i in range(len(means)):
            for j in range(i + 1, len(means)):
                pairs += 1
                spread = math.sqrt(sds[i] ** 2 + sds[j] ** 2) / math.sqrt(n) if n else 0.0
                if spread and abs(means[i] - means[j]) > 1.96 * spread:
                    resolvable += 1
        out[label] = {
            "constructs": len(values),
            "replicates_per_construct": replicates,
            "measured_cv": {"median": median_cv, "min": cvs[0], "max": cvs[-1]},
            "planning_bound_in_assay_definition_v3_and_v4": 0.20,
            "measured_cv_is_below_the_planning_bound": median_cv < 0.20,
            "minimum_detectable_fold_change_at_measured_cv": mde,
            "target_fold_change_in_assay_definition": 1.5,
            "target_is_detectable_at_this_cv_and_n": bool(mde and mde <= 1.5),
            "pairs": pairs,
            "resolvable_pairs": resolvable,
            "unresolvable_pairs": pairs - resolvable,
            "fraction_unresolvable": (pairs - resolvable) / pairs if pairs else None,
        }
    return out


def correlate(entries, predictor, declared):
    """One declared measurement: value beside the direction declared for it."""
    rows = [(e[predictor], e) for e in entries if e.get(predictor) is not None]
    out = {"declared_direction": declared, "constructs": len(rows)}
    for label, key in (("vs_half_life", "half_life"),
                       ("vs_expression_24h", "nluc_fluc_24h_mean"),
                       ("vs_expression_6h", "nluc_fluc_6h_mean")):
        usable = [(x, e[key]) for x, e in rows if e.get(key) is not None]
        out[label] = spearman([x for x, _ in usable], [y for _, y in usable]) if usable else None
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--out", default="results/expression_axis_runs")
    args = parser.parse_args(argv)

    declared = json.loads(PROTOCOL.read_text())
    protocol_hash = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    archive = Path(args.archive)
    archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
    if archive_hash != ARCHIVE_SHA256:
        raise SystemExit(f"archive sha256 {archive_hash} does not match the declared "
                         f"{ARCHIVE_SHA256}; refusing to read it")

    member6, digest6, rows6 = read_sheet(archive, DATA6)
    member5, digest5, rows5 = read_sheet(archive, DATA5)
    designs = [r for r in rows6 if r.get("Sequence ID")]
    tests = {r["name"]: r for r in rows5 if r.get("name")}
    print(f"designs {len(designs)}  significance rows {len(tests)}", flush=True)
    if len(designs) != 24:
        raise SystemExit(f"expected 24 designs, read {len(designs)}")

    checks = integrity(designs)
    print(f"integrity: Sequence column mismatches {checks['sequence_column_mismatch_count']} "
          f"of {checks['rows']}; permutation resolves them "
          f"{checks['permutation_resolves_every_mismatch']}; one protein "
          f"{checks['protein_identical_across_all_rows']}", flush=True)
    for guard, message in (
            (checks["all_full_length_equal"], "sequence_with_UTRs is not uniformly 883 nt"),
            (checks["protein_identical_across_all_rows"], "the 24 do not encode one protein"),
            (checks["utr_features_have_zero_variance"], "the UTRs are not constant")):
        if not guard:
            raise SystemExit(f"source layout changed: {message}; protocol does not apply")

    entries = []
    for record in designs:
        full = record["sequence_with_UTRs"].upper()
        cds = full[CDS_START:CDS_END]
        if cds[:3] != "AUG" or cds[-3:] not in STOPS:
            raise SystemExit(f"{record['Sequence ID']}: CDS at [{CDS_START}:{CDS_END}] is not "
                             "a clean ORF; the enforced layout does not hold")
        row = tests.get(record.get("Title", ""), {})
        entries.append({
            "sequence_id": record["Sequence ID"],
            "title": record.get("Title", ""),
            "category": record.get("Category", ""),
            "full_rna": full,
            "cds_rna": cds,
            "length_nt": len(full),
            "half_life": number(record, "half_life"),
            "half_life_err": number(record, "half_life_err"),
            "nluc_fluc_6h_mean": number(record, "Nluc_Fluc_6h_mean"),
            "nluc_fluc_6h_sd": number(record, "Nluc_Fluc_6h_sd"),
            "nluc_fluc_24h_mean": number(record, "Nluc_Fluc_24h_mean"),
            "nluc_fluc_24h_sd": number(record, "Nluc_Fluc_24h_sd"),
            "replicates": int(float(row["24h_n"])) if row.get("24h_n") else None,
            "source_p_value_24h": number(row, "24h_p_value") if row else None,
            "transcript_gc": (full.count("G") + full.count("C")) / len(full),
            "cds_gc": (cds.count("G") + cds.count("C")) / len(cds),
        })

    print(f"folding {len(entries)} full transcripts and {len(entries)} CDS regions "
          f"on {args.jobs} workers...", flush=True)
    jobs = ([(("full", i), e["full_rna"]) for i, e in enumerate(entries)]
            + [(("cds", i), e["cds_rna"]) for i, e in enumerate(entries)])
    folded = {}
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        for tag, features in pool.map(fold_one, jobs):
            folded[tag] = features
    missing = [tag for tag, features in folded.items() if not features]
    if missing:
        raise SystemExit(f"folding failed for {len(missing)}: {missing[:5]}")

    for index, entry in enumerate(entries):
        full, cds = folded[("full", index)], folded[("cds", index)]
        entry["aup"] = full["aup"]
        entry["energy_per_nt"] = full["energy_per_length"]
        entry["cds_aup"] = cds["aup"]
        entry["cds_energy_per_nt"] = cds["energy_per_length"]

    model = json.loads((CALIBRATION / "calibration_model.json").read_text())
    arm = model["component"]
    train = list(csv.DictReader((CALIBRATION / "features/train_features.csv").open()))
    domain = {f: {"min": min(float(r[f]) for r in train), "max": max(float(r[f]) for r in train)}
              for f in arm["feature_order"]}
    for index, entry in enumerate(entries):
        features = folded[("full", index)]
        entry["calibration_predicted_hours"] = arm["intercept"] + sum(
            arm["coefficients"][f] * features[f] for f in arm["feature_order"])
        entry["features_outside_training_range"] = sorted(
            f for f in domain if not domain[f]["min"] <= features[f] <= domain[f]["max"])

    primary = correlate(entries, "half_life", "POSITIVE")
    rho = primary["vs_expression_24h"]
    families = {}
    for name in sorted({e["category"] for e in entries}):
        members = [e for e in entries if e["category"] == name]
        if len(members) >= 4:
            families[name] = correlate(members, "half_life", "POSITIVE")
    signs = [v["vs_expression_24h"] for v in families.values()
             if v["vs_expression_24h"] is not None]
    reasons = []
    if rho is None or rho < 0.30:
        reasons.append(f"rho vs 24 h expression is {rho}, below the declared +0.30")
    if (primary["vs_expression_6h"] is not None and rho is not None
            and (primary["vs_expression_6h"] > 0) != (rho > 0)):
        reasons.append("the sign differs between the 6 h and 24 h labels")
    if signs and not (all(s > 0 for s in signs) or all(s < 0 for s in signs)):
        reasons.append("the sign reverses across design families with at least 4 members")

    exploratory = {
        "E1_frozen_calibration_on_an_unexposed_set":
            correlate(entries, "calibration_predicted_hours", "POSITIVE"),
        "E2_transcript_gc": correlate(entries, "transcript_gc", "POSITIVE"),
        "E2_cds_gc": correlate(entries, "cds_gc", "POSITIVE"),
        "E3_cds_aup": correlate(entries, "cds_aup", "NEGATIVE"),
        "E3_cds_energy_per_nt": correlate(entries, "cds_energy_per_nt", "NEGATIVE"),
        "E4_aup": correlate(entries, "aup", "NEGATIVE"),
        "E4_energy_per_nt": correlate(entries, "energy_per_nt", "NEGATIVE"),
    }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out = ROOT / args.out / stamp
    (out / "features").mkdir(parents=True, exist_ok=True)
    summary = {
        "protocol": {"file": str(PROTOCOL.relative_to(ROOT)), "sha256": protocol_hash,
                     "name": declared["name"]},
        "source": {"archive_sha256": archive_hash,
                   "members": [{"name": member6, "sha256": digest6},
                               {"name": member5, "sha256": digest5}]},
        "calibration_run": str(CALIBRATION.relative_to(ROOT)),
        "constructs": len(entries),
        "integrity": checks,
        "nothing_was_fitted": True,
        "no_train_test_split_was_made": True,
        "primary_confirmatory_test": {
            "question": declared["primary_confirmatory_test"]["question"],
            "predictor": "measured in-cell half_life",
            "label": "Nluc_Fluc_24h_mean",
            "declared_direction": "POSITIVE",
            "declared_threshold": 0.30,
            "spearman_vs_expression_24h": rho,
            "spearman_vs_expression_6h": primary["vs_expression_6h"],
            "stability_route_falsified": bool(reasons),
            "falsification_reasons": reasons,
            "verdict": (declared["primary_confirmatory_test"]["what_will_be_recorded_on_failure"]
                        if reasons else
                        declared["primary_confirmatory_test"]["what_will_be_recorded_on_success"]),
        },
        "family_stratified_primary_E5": families,
        "exploratory": exploratory,
        "measurement_error": cv_analysis(entries),
        "label_ranges": {
            "half_life_hours": [min(e["half_life"] for e in entries),
                                max(e["half_life"] for e in entries)],
            "nluc_fluc_24h": [min(e["nluc_fluc_24h_mean"] for e in entries),
                              max(e["nluc_fluc_24h_mean"] for e in entries)],
            "nluc_fluc_24h_fold_span": (max(e["nluc_fluc_24h_mean"] for e in entries)
                                        / min(e["nluc_fluc_24h_mean"] for e in entries)),
        },
        "extrapolation": {
            "constructs_outside_the_calibration_training_range": sum(
                1 for e in entries if e["features_outside_training_range"]),
            "features_involved": sorted({f for e in entries
                                         for f in e["features_outside_training_range"]}),
        },
        "limits_carried_from_the_protocol": declared["design_limits_declared_up_front"],
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    (out / "protocol.json").write_text(PROTOCOL.read_text())
    (out / "integrity.json").write_text(json.dumps(checks, indent=2, sort_keys=True) + "\n")
    columns = ["sequence_id", "title", "category", "length_nt", "half_life",
               "nluc_fluc_6h_mean", "nluc_fluc_6h_sd", "nluc_fluc_24h_mean",
               "nluc_fluc_24h_sd", "replicates", "transcript_gc", "cds_gc", "aup",
               "energy_per_nt", "cds_aup", "cds_energy_per_nt",
               "calibration_predicted_hours"]
    with (out / "features" / "designs.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(entries)

    print(f"\nPRIMARY  half-life vs 24 h expression: {rho:+.4f}  "
          f"(declared POSITIVE, threshold +0.30)")
    print(f"         half-life vs  6 h expression: {primary['vs_expression_6h']:+.4f}")
    print(f"         stability route falsified: {bool(reasons)}")
    for reason in reasons:
        print(f"           - {reason}")
    print("\nFAMILY (>=4 members), half-life vs 24 h expression:")
    for name, value in families.items():
        print(f"         {name:<14} n={value['constructs']:<3} "
              f"{value['vs_expression_24h']:+.4f}")
    print("\nEXPLORATORY                      vs half-life   vs 24h expr   declared")
    for name, value in exploratory.items():
        print(f"         {name:<32} {value['vs_half_life']:+.4f}       "
              f"{value['vs_expression_24h']:+.4f}     {value['declared_direction']}")
    print("\nMEASUREMENT ERROR")
    for label, value in summary["measurement_error"].items():
        print(f"         {label}: median CV {value['measured_cv']['median']:.4f} "
              f"(bound 0.20), n={value['replicates_per_construct']}, "
              f"MDE {value['minimum_detectable_fold_change_at_measured_cv']:.3f}x, "
              f"unresolvable {value['unresolvable_pairs']}/{value['pairs']}")
    print(f"\nwrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
