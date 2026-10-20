#!/usr/bin/env python3
"""Does N1-methylpseudouridine change how sequence features map to ribosome load?

The project's ranking argument needs the modification's effect to be
sequence-independent, so that predictions made on the unmodified sequence still
order the modified molecules. An earlier check used pseudouridine on six
constructs and found the effect construct-dependent on expression; that is a
different nucleoside and a tiny sample.

Sample et al. 2019 measured a random 50-mer 5' UTR library under unmodified and
m1-pseudouridine conditions, two replicate arms each, about 330,000 sequences
per arm. The arms share no sequences and their ribosome-load scales differ, so
this compares the SHAPE of the sequence-to-ribosome-load mapping rather than any
value: for three features declared in advance, is the slope the same under m1psi
as unmodified, judged against how much that slope moves between replicates of
the same condition?

Criteria, features, preprocessing and the decision rule are declared in
`configs/m1pseudouridine_feature_slope_check_v1_2026-10-20.json`, written before
any feature-to-ribosome-load relationship was computed. Per-file hashes are
verified before a row is read. The source is not redistributed.
"""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import csv
import gzip
import hashlib
import json
import math
import random
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/m1pseudouridine_feature_slope_check_v1_2026-10-20.json"
SUFFIX = "ATGGGCGAA"
UTR_LENGTH = 50


def detect_convention(path, probe=20000):
    """Decide per FILE whether the constant suffix is present.

    CORRECTION to the declared preprocessing, disclosed in the artifact. The
    protocol tied the suffix trim to the m1-pseudouridine condition. It is
    actually a per-file export convention: unmod_2 carries the same 9-nt suffix
    as m1pseudo_1, while m1pseudo_2 is a different library of 54 nt with no
    constant suffix. Detecting it per file rather than per condition is a
    mechanical fix, decided from the observed suffix frequency and not from any
    feature-to-ribosome-load relationship.
    """
    lengths, suffixed, seen = {}, 0, 0
    with gzip.open(path, "rt") as handle:
        for row in csv.DictReader(handle):
            utr = (row.get("utr") or "").strip().upper()
            if not utr:
                continue
            lengths[len(utr)] = lengths.get(len(utr), 0) + 1
            suffixed += utr.endswith(SUFFIX)
            seen += 1
            if seen >= probe:
                break
    rate = suffixed / seen if seen else 0.0
    modal = max(lengths, key=lengths.get) if lengths else 0
    trim = rate >= 0.99 and modal - len(SUFFIX) == UTR_LENGTH
    return {"modal_length": modal, "suffix_rate": rate, "trim_suffix": trim,
            "usable": UTR_LENGTH == (modal - len(SUFFIX) if trim else modal)}


def load_arm(path, trim_suffix):
    """Read one arm, applying the declared preprocessing and counting exclusions."""
    rows, excluded = [], {"suffix_missing": 0, "wrong_length": 0, "alphabet": 0,
                          "no_ribosome_load": 0}
    with gzip.open(path, "rt") as handle:
        for record in csv.DictReader(handle):
            utr = (record.get("utr") or "").strip().upper()
            load = record.get("rl")
            depth = record.get("total_reads") or record.get("total") or "0"
            if not utr or load in (None, "", "nan", "NA"):
                excluded["no_ribosome_load"] += 1
                continue
            if trim_suffix:
                if not utr.endswith(SUFFIX):
                    excluded["suffix_missing"] += 1
                    continue
                utr = utr[: -len(SUFFIX)]
            if len(utr) != UTR_LENGTH:
                excluded["wrong_length"] += 1
                continue
            if set(utr) - set("ACGT"):
                excluded["alphabet"] += 1
                continue
            try:
                rows.append((utr, float(load), float(depth)))
            except ValueError:
                excluded["no_ribosome_load"] += 1
    return rows, excluded


def features(utr, fold):
    """The three features declared in advance."""
    rna = utr.replace("T", "U")
    out_of_frame = any(utr[i:i + 3] == "ATG" and (UTR_LENGTH - i) % 3 != 0
                       for i in range(UTR_LENGTH - 2))
    return {
        "out_of_frame_uaug": 1.0 if out_of_frame else 0.0,
        "gc_fraction": (utr.count("G") + utr.count("C")) / UTR_LENGTH,
        "vienna_mfe": fold(rna),
    }


def ols(xs, ys):
    """Slope, its standard error, and n, for a simple regression."""
    n = len(xs)
    mean_x, mean_y = statistics.fmean(xs), statistics.fmean(ys)
    sxx = sum((x - mean_x) ** 2 for x in xs)
    if not sxx:
        return {"slope": None, "standard_error": None, "n": n}
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / sxx
    intercept = mean_y - slope * mean_x
    residual = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    se = math.sqrt(residual / (n - 2) / sxx) if n > 2 else None
    return {"slope": slope, "standard_error": se, "n": n}


def group_difference(flags, ys):
    """Difference in mean between the two groups of a binary feature."""
    present = [y for f, y in zip(flags, ys) if f > 0.5]
    absent = [y for f, y in zip(flags, ys) if f <= 0.5]
    if len(present) < 3 or len(absent) < 3:
        return {"slope": None, "standard_error": None, "n": len(ys)}
    se = math.sqrt(statistics.variance(present) / len(present)
                   + statistics.variance(absent) / len(absent))
    return {"slope": statistics.fmean(present) - statistics.fmean(absent),
            "standard_error": se, "n": len(ys),
            "n_present": len(present), "n_absent": len(absent)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--data-dir", required=True,
                        help="directory holding the four downloaded GEO csv.gz files")
    parser.add_argument("--out", default="results/m1pseudouridine_slope_runs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    protocol = json.loads(PROTOCOL.read_text())
    pre = protocol["preprocessing"]
    size, seed = pre["subsample_size"], pre["seed"]
    local = {"unmod_1": "unmod_1.csv.gz", "unmod_2": "unmod_2.csv.gz",
             "m1pseudo_1": "m1pseudo_1.csv.gz", "m1pseudo_2": "m1pseudo_2.csv.gz"}

    paths = {}
    for arm, declared in protocol["source"]["files"].items():
        path = Path(args.data_dir) / local[arm]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != declared["sha256"]:
            raise SystemExit(f"{arm}: hash mismatch\n  expected {declared['sha256']}\n"
                             f"  observed {digest}")
        paths[arm] = path
        print(f"{arm:<12} hash verified {digest[:16]}…", flush=True)
    if args.dry_run:
        print("Dry run: hashes verified, nothing computed.", file=sys.stderr)
        return 0

    import RNA

    model = RNA.md()
    model.temperature = 37.0
    model.dangles = 2
    cache = {}

    def fold(rna):
        value = cache.get(rna)
        if value is None:
            value = RNA.fold_compound(rna, model).mfe()[1]
            cache[rna] = value
        return value

    conventions = {arm: detect_convention(path) for arm, path in paths.items()}
    for arm, convention in conventions.items():
        print(f"{arm:<12} modal length {convention['modal_length']}  suffix rate "
              f"{convention['suffix_rate']:.3f}  trim {convention['trim_suffix']}  "
              f"usable {convention['usable']}", flush=True)
    unusable = [arm for arm, c in conventions.items() if not c["usable"]]
    if unusable:
        print(f"EXCLUDED, not the 50 nt library: {unusable}", flush=True)

    arms = {}
    for arm, path in paths.items():
        if not conventions[arm]["usable"]:
            continue
        rows, excluded = load_arm(path, trim_suffix=conventions[arm]["trim_suffix"])
        depths = [d for _, _, d in rows]
        threshold = statistics.median(depths) if depths else 0.0
        kept = [(u, load) for u, load, d in rows if d >= threshold]
        rng = random.Random(seed)
        sample = rng.sample(kept, min(size, len(kept)))
        loads = [load for _, load in sample]
        mean, sd = statistics.fmean(loads), statistics.stdev(loads)
        table = []
        for utr, load in sample:
            row = features(utr, fold)
            row["standardised_load"] = (load - mean) / sd
            table.append(row)
        arms[arm] = {
            "rows_read": len(rows) + sum(excluded.values()),
            "rows_usable": len(rows),
            "excluded": excluded,
            "depth_threshold": threshold,
            "rows_after_depth_filter": len(kept),
            "subsampled": len(sample),
            "raw_load_mean": mean,
            "raw_load_sd": sd,
            "gc_mean": statistics.fmean(r["gc_fraction"] for r in table),
            "gc_sd": statistics.stdev(r["gc_fraction"] for r in table),
            "out_of_frame_uaug_rate": statistics.fmean(
                r["out_of_frame_uaug"] for r in table),
            "mfe_mean": statistics.fmean(r["vienna_mfe"] for r in table),
            "table": table,
        }
        print(f"{arm:<12} usable {len(rows):>7}  after depth {len(kept):>7}  "
              f"sampled {len(sample):>6}  excluded {excluded}", flush=True)

    slopes = {}
    for arm, data in arms.items():
        table = data["table"]
        loads = [r["standardised_load"] for r in table]
        slopes[arm] = {
            "out_of_frame_uaug": group_difference(
                [r["out_of_frame_uaug"] for r in table], loads),
            "gc_fraction": ols([r["gc_fraction"] for r in table], loads),
            "vienna_mfe": ols([r["vienna_mfe"] for r in table], loads),
        }

    rule = protocol["declared_criteria"]["decision_rule"]
    unmod_arms = [a for a in slopes if a.startswith("unmod")]
    modified_arms = [a for a in slopes if a.startswith("m1pseudo")]
    # The declared denominator is the larger WITHIN-condition replicate
    # difference. m1pseudo_2 is a different library and is excluded, so the
    # m1psi condition has no replicate and the denominator comes from the
    # unmodified pair alone. That is weaker and is recorded as borrowed.
    denominator_borrowed = len(modified_arms) < 2
    comparison = {}
    for feature in ("out_of_frame_uaug", "gc_fraction", "vienna_mfe"):
        unmod = [slopes[a][feature]["slope"] for a in sorted(unmod_arms)]
        modified = [slopes[a][feature]["slope"] for a in sorted(modified_arms)]
        spreads = [max(v) - min(v) for v in (unmod, modified) if len(v) > 1]
        within = max(spreads) if spreads else None
        between = abs(statistics.fmean(unmod) - statistics.fmean(modified))
        ratio = (between / within) if within else None
        if ratio is None:
            verdict = "undetermined"
        elif ratio <= 1.0:
            verdict = "consistent_with_constant"
        elif ratio <= 2.0:
            verdict = "ambiguous"
        else:
            verdict = "sequence_dependent"
        comparison[feature] = {
            "denominator_borrowed_from_unmodified_replicates": denominator_borrowed,
            "unmodified_slopes": unmod,
            "m1pseudo_slopes": modified,
            "unmodified_mean": statistics.fmean(unmod),
            "m1pseudo_mean": statistics.fmean(modified),
            "between_modification_difference": between,
            "within_modification_replicate_difference": within,
            "ratio": ratio,
            "verdict": verdict,
            "sign_changed": (statistics.fmean(unmod) > 0) != (statistics.fmean(modified) > 0),
            "decision_rule": rule,
        }

    gc_shift = abs(arms["unmod_1"]["gc_mean"] - arms["m1pseudo_1"]["gc_mean"])
    verdicts = {f: c["verdict"] for f, c in comparison.items()}
    payload = {
        "purpose": protocol["purpose"],
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": str(PROTOCOL.relative_to(ROOT)),
        "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
        "all_file_hashes_verified": True,
        "modification": "N1-methylpseudouridine, the nucleoside this project's molecules carry",
        "arms": {arm: {k: v for k, v in data.items() if k != "table"}
                 for arm, data in arms.items()},
        "slopes_per_arm": slopes,
        "comparison": comparison,
        "verdicts": verdicts,
        "preprocessing_correction": {
            "what_was_declared": ("the 9-nt ATGGGCGAA suffix is trimmed from the "
                                  "m1-pseudouridine records"),
            "what_is_actually_true": ("the suffix is a PER-FILE export convention: unmod_2 "
                                      "carries it too, and m1pseudo_2 is a different library "
                                      "of 54 nt with no constant suffix"),
            "what_was_changed": "the suffix is detected per file from its observed frequency",
            "justification": "mechanical, decided from observed sequence conventions alone",
            "consequence": ("m1pseudo_2 is excluded as not being the 50 nt library, so the "
                            "m1-pseudouridine condition has NO replicate arm and the "
                            "within-condition denominator is borrowed from the unmodified "
                            "pair. This weakens the test and is recorded on every feature."),
            "effect_on_features_or_decision_rule": "none; both are as declared",
        },
        "arms_excluded": {arm: conventions[arm] for arm in conventions
                          if not conventions[arm]["usable"]},
        "conventions_detected": conventions,
        "library_distribution_check": {
            "gc_mean_difference_between_conditions": gc_shift,
            "same_distribution": gc_shift < 0.01,
            "note": ("The arms share no sequences, so a between-library slope comparison "
                     "assumes both libraries are drawn from the same sequence distribution. "
                     "A GC mean difference below 0.01 is treated as consistent with that."),
        },
        "supports_the_project_ranking_assumption": all(
            v == "consistent_with_constant" for v in verdicts.values()),
        "what_this_cannot_establish": protocol["what_this_cannot_establish"],
        "no_claim": [
            "A slope is an association within a random library, not causation.",
            "Absolute ribosome load is not comparable between arms, because the unmodified "
            "library was fractionated into 14 polysome fractions and the m1psi library into "
            "13. Only within-arm relationships are compared.",
            "The three features were declared in advance for being mechanistically motivated "
            "and cheap. They are not a complete account of what determines ribosome load.",
            "A 50 nt random UTR on eGFP in HEK293T is not this project's 1811 nt construct "
            "scored for A549 and T cells.",
            "This says nothing about the stability side.",
        ],
    }

    if denominator_borrowed:
        print("\nNOTE: the m1psi condition has no replicate arm; the within-condition "
              "denominator is borrowed from the unmodified pair.", flush=True)
    print("\n%-20s %-22s %-22s %8s %8s  %s" % (
        "feature", "unmodified slopes", "m1psi slopes", "between", "within", "verdict"))
    for feature, block in comparison.items():
        print("%-20s %-22s %-22s %8.4f %8.4f  %s%s" % (
            feature,
            " / ".join("%.4f" % s for s in block["unmodified_slopes"]),
            " / ".join("%.4f" % s for s in block["m1pseudo_slopes"]),
            block["between_modification_difference"],
            block["within_modification_replicate_difference"],
            block["verdict"].upper(),
            "  SIGN CHANGED" if block["sign_changed"] else ""))
    print("\nratios: " + "  ".join(
        f"{f} {c['ratio']:.2f}" for f, c in comparison.items()))
    print(f"library GC mean difference {gc_shift:.5f}  same distribution "
          f"{payload['library_distribution_check']['same_distribution']}")
    print(f"supports the project's ranking assumption: "
          f"{payload['supports_the_project_ranking_assumption']}")

    out = ROOT / args.out / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True, exist_ok=False)
    (out / "summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(f"\nWrote {out}/summary.json", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
