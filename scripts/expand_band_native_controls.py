#!/usr/bin/env python3
"""Evaluate the native controls across the full 2,000-2,999 nt band.

The frozen development selection holds exactly one record in this band, because
a fixed per-family cap stopped further selection, not because references were
unavailable. The census records 55 further eligible band records across RF02540
and RF02541. That cap existed to bound how much data a learned model could be
trained and evaluated on.

The learned model was retired on 2026-10-20. LinearFold and ViennaRNA have no
training set, so there is nothing for a per-family cap to protect against here:
evaluating them on more references is folding, not fitting. This script does
exactly that, giving the band the dispersion and family contrast a single record
cannot provide.

What this is NOT:

- It does not modify the frozen selection. That cohort stays exactly as it is,
  and this runs beside it as a separately named native-control band cohort.
- It fits nothing and trains nothing. No model is involved at any point.
- It does not make the references experimental. They remain computational Rfam
  consensus annotations, with every limitation that carries.
"""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import gzip
import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.folding import fold_sequence
from rnastable.pair_model import CANONICAL
from rnastable.pair_reference import validate_pairs
from rnastable.prospective_binding import bind_pair_reference, parse_stockholm
from rnastable.reference import digest
from evaluate_long_native_controls import CONFIG, METHODS, score

SEED = ROOT / "results/rfam_release_15_1_clan_source/Rfam.seed.gz"
CENSUS = ROOT / "results/stage2_band_coverage_census_runs/20261019T180243.655199Z"
BAND = (2000, 3000)
FAMILIES = ("RF02540", "RF02541")


def extract_families(families):
    """Pull the named family blocks out of the compressed Rfam seed."""
    wanted, found, block, accession = set(families), {}, [], None
    with gzip.open(SEED, "rt", encoding="latin-1") as handle:
        for line in handle:
            block.append(line)
            if line.startswith("#=GF AC"):
                accession = line.split()[-1].strip()
            elif line.startswith("//"):
                if accession in wanted:
                    found[accession] = "".join(block).encode()
                block, accession = [], None
                if len(found) == len(wanted):
                    break
    missing = wanted - set(found)
    if missing:
        raise SystemExit(f"Families not found in the seed: {sorted(missing)}")
    return found


def band_records(alignments, eligible_ids):
    """Bind pair references for eligible band records, skipping unusable ones."""
    records, skipped = [], Counter()
    for family, raw in alignments.items():
        alignment = parse_stockholm(raw, family)
        for identity, aligned in alignment["sequences"].items():
            record_id = f"{family}:{identity}"
            if record_id not in eligible_ids:
                continue
            sequence = aligned.replace("-", "").replace(".", "").upper().replace("T", "U")
            if not BAND[0] <= len(sequence) < BAND[1]:
                skipped["outside_band_after_degapping"] += 1
                continue
            try:
                bound = bind_pair_reference(
                    {"id": record_id, "family_id": family, "sequence": sequence,
                     "sequence_sha256": digest(sequence.encode())}, alignment)
                validate_pairs(bound["pairs"], len(bound["sequence"]))
            except Exception:
                skipped["binding_failed"] += 1
                continue
            legal = [(i, j) for i, j in bound["pairs"]
                     if j - i >= 4 and bound["sequence"][i] + bound["sequence"][j] in CANONICAL]
            if not legal:
                skipped["no_legal_canonical_pairs"] += 1
                continue
            records.append({"id": record_id, "family_id": family,
                            "sequence": bound["sequence"], "pairs": bound["pairs"],
                            "length_nt": len(bound["sequence"])})
    return records, dict(skipped)


def summarise(rows):
    by_family = defaultdict(list)
    for row in rows:
        by_family[row["family_id"]].append(row["pair_f1"])
    family_means = {k: statistics.fmean(v) for k, v in sorted(by_family.items())}
    values = [r["pair_f1"] for r in rows]
    return {
        "n": len(rows),
        "families": len(family_means),
        "mean_record_pair_f1": statistics.fmean(values),
        "median_pair_f1": statistics.median(values),
        # A single record carries no dispersion; reporting it is the point.
        "stdev_pair_f1": statistics.stdev(values) if len(values) > 1 else None,
        "min_pair_f1": min(values),
        "max_pair_f1": max(values),
        "family_means": family_means,
        "mean_family_pair_f1": statistics.fmean(family_means.values()),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--limit", type=int, default=0, help="cap records, for a smoke run")
    parser.add_argument("--out", default="results/band_native_control_runs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    census = json.loads((CENSUS / "band_records.json").read_text())
    eligible = {r["id"] for r in census
                if r.get("decision") == "fixed_family_cap" and r.get("reference_supported")}
    print(f"eligible band records recorded by the census: {len(eligible)}")

    records, skipped = band_records(extract_families(FAMILIES), eligible)
    records.sort(key=lambda r: r["id"])
    if args.limit:
        records = records[:args.limit]
    print(f"bound references: {len(records)}  skipped: {skipped}")
    if not records:
        raise SystemExit("No band references could be bound")

    rows, failures = [], Counter()
    for index, record in enumerate(records, 1):
        for method in METHODS:
            result = fold_sequence(ROOT, record["sequence"], CONFIG, method)
            metrics = score(result, record)
            if metrics is None:
                failures[method] += 1
                continue
            rows.append({"id": record["id"], "family_id": record["family_id"],
                         "length_nt": record["length_nt"], "method": method,
                         "pair_f1": metrics["pair_f1"],
                         "pair_precision": metrics["pair_precision"],
                         "pair_recall": metrics["pair_recall"]})
        print(f"  [{index}/{len(records)}] {record['id'][:44]} {record['length_nt']} nt", flush=True)

    per_method = {m: summarise([r for r in rows if r["method"] == m]) for m in METHODS
                  if any(r["method"] == m for r in rows)}
    payload = {
        "purpose": ("Native-control accuracy across the full 2,000-2,999 nt band, giving "
                    "the band the dispersion and family contrast a single record cannot."),
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "band": {"minimum_inclusive": BAND[0], "maximum_exclusive": BAND[1]},
        "families": list(FAMILIES),
        "model_fitted": False,
        "learned_model_involved": False,
        "frozen_selection_modified": False,
        "records_evaluated": len(records),
        "skipped": skipped,
        "fold_failures": dict(failures),
        "per_method": per_method,
        "rows": rows,
        "relation_to_the_frozen_cohort": (
            "The frozen development selection still holds exactly one band record and is "
            "unchanged. This is a separately named native-control band cohort evaluated "
            "beside it, not a replacement for it."),
        "why_the_cap_does_not_apply": (
            "The fixed per-family cap bounded how much data a learned model could be "
            "trained and evaluated on. LinearFold and ViennaRNA have no training set, so "
            "evaluating them on more references is folding rather than fitting."),
        "no_claim": [
            "The references remain computational Rfam consensus annotations, not "
            "experimental structures. Accuracy against them is not biological validation.",
            "Two families in one clan is broader than one record, and still narrow.",
            "No model was fitted and no learned component was involved.",
            "Satisfying a gate requirement is a gate-review judgement, not an output here.",
        ],
    }
    for method, stats in per_method.items():
        print(f"\n=== {method} (2,000-2,999 nt) ===")
        print(f"  n={stats['n']}  families={stats['families']}")
        print(f"  record F1 {stats['mean_record_pair_f1']:.4f}   family F1 "
              f"{stats['mean_family_pair_f1']:.4f}   median {stats['median_pair_f1']:.4f}")
        print(f"  stdev {stats['stdev_pair_f1']:.4f}   range "
              f"[{stats['min_pair_f1']:.4f}, {stats['max_pair_f1']:.4f}]")
        for family, mean in stats["family_means"].items():
            print(f"    {family}: {mean:.4f}")

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
