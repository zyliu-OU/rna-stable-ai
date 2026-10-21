#!/usr/bin/env python3
"""Screen candidate features for predicting IN-CELL mRNA stability.

The user has declared the in-cell axis as the target. The project's frozen STRAND
calibration was fitted entirely on in-solution labels, and the two axes rank at
Spearman +0.0545 on identical constructs, so the stability objective has never
been fitted to the axis that matters. Transcript GC alone already reaches +0.2253
on the held-out constructs, which is the bar.

The screen is UNIVARIATE by design. Gate v15 measured that this label-set size
supports about one feature: held-out correlation fell from +0.3651 at one feature
to +0.1317 at four while training correlation rose to +0.5972. Screening
combinations would repeat a mistake already paid for.

Measured Ribosome load is carried as a declared CEILING, not a usable feature. It
bounds what wiring RiboNN into the stability model could buy, which is the most
promising addition available from parts the combination already contains.

Nothing is fitted, adopted or wired here. The protocol was hashed before any
number was seen: configs/in_cell_feature_screen_v1_2026-10-20.json

Usage:
    python scripts/run_in_cell_feature_screen.py --archive /path/to/MOESM4.zip
"""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import glob
import hashlib
import json
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_two_axis_comparison import bin_key, concordance, number, read_table, spearman  # noqa: E402

PROTOCOL = ROOT / "configs/in_cell_feature_screen_v1_2026-10-20.json"
TWO_AXIS = ROOT / "configs/two_axis_comparison_v1_2026-10-20.json"
STOPS = {"TAA", "TAG", "TGA"}
DRACH = re.compile(r"(?=[AGT]{1}[AG]AC[ACT])")
ARE_SHORT = re.compile(r"(?=ATTTA)")
ARE_LONG = re.compile(r"(?=TTATTTATT)")


def composition(sequence, prefix):
    """Base, GC and dinucleotide fractions. Empty segments give no features."""
    out = {}
    if not sequence:
        return out
    length = len(sequence)
    for base in "ACGT":
        out[f"{prefix}_frac_{base.replace('T', 'U')}"] = sequence.count(base) / length
    out[f"{prefix}_gc"] = (sequence.count("G") + sequence.count("C")) / length
    pairs = [sequence[i:i + 2] for i in range(length - 1)]
    if pairs:
        out[f"{prefix}_cpg"] = pairs.count("CG") / len(pairs)
        out[f"{prefix}_upa"] = pairs.count("TA") / len(pairs)
    return out


def sequence_features(utr5, cds, utr3):
    features = {}
    features.update(composition(utr5, "utr5"))
    features.update(composition(cds, "cds"))
    features.update(composition(utr3, "utr3"))
    features["utr5_length"] = len(utr5)
    features["cds_length"] = len(cds)
    features["utr3_length"] = len(utr3)

    codons = [cds[i:i + 3] for i in range(0, len(cds) - 2, 3)]
    if codons:
        third = [c[2] for c in codons]
        features["cds_gc3"] = sum(1 for b in third if b in "GC") / len(third)

    features["utr3_are_attta"] = len(ARE_SHORT.findall(utr3))
    features["utr3_are_ttatttatt"] = len(ARE_LONG.findall(utr3))
    features["utr3_are_attta_per_kb"] = (
        len(ARE_SHORT.findall(utr3)) / len(utr3) * 1000 if utr3 else 0.0)
    whole = utr5 + cds + utr3
    features["drach_count"] = len(DRACH.findall(whole))
    features["drach_per_kb"] = len(DRACH.findall(whole)) / len(whole) * 1000

    # An upstream AUG is out of frame when it cannot reach the real start in frame.
    out_of_frame = sum(1 for i in range(len(utr5) - 2)
                       if utr5[i:i + 3] == "ATG" and (len(utr5) - i) % 3 != 0)
    features["utr5_uaug_out_of_frame"] = out_of_frame
    features["utr5_uaug_total"] = sum(1 for i in range(len(utr5) - 2)
                                      if utr5[i:i + 3] == "ATG")
    return features


def fold_region(payload):
    """Fold one region in the isolated ensemble worker. Regions are RNA, not DNA."""
    import subprocess

    key, sequence = payload
    if len(sequence) < 10:
        return key, None
    try:
        done = subprocess.run(
            [sys.executable, "-m", "rnastable.ensemble_worker"],
            input=json.dumps({"sequence": sequence.replace("T", "U"),
                              "temperature": 37.0}),
            text=True, capture_output=True, timeout=600, check=True,
            cwd=str(ROOT / "src"))
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return key, None
    result = json.loads(done.stdout)
    if result.get("status") != "ok":
        return key, None
    candidates = result["feature_candidates"]
    return key, {"aup": candidates["aup"],
                 "energy_per_nt": candidates["ensemble_energy_per_nt"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--archive", required=True)
    parser.add_argument("--jobs", type=int, default=24)
    parser.add_argument("--split", choices=("preserved", "stratified"), default="preserved",
                        help="preserved keeps the two-axis 122-record held-out set; "
                             "stratified redraws the split balanced across design families, "
                             "which the preserved split cannot do for UTR features")
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--out", default="results/in_cell_feature_screen_runs")
    args = parser.parse_args(argv)

    protocol = json.loads(PROTOCOL.read_text())
    declared = json.loads(TWO_AXIS.read_text())["test_set"]
    archive = Path(args.archive)
    archive_digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if archive_digest != declared["archive_sha256"]:
        raise SystemExit("archive sha256 does not match the protocol")
    records, table_digest = read_table(archive)
    if table_digest != declared["table_sha256"]:
        raise SystemExit("table sha256 does not match the protocol")

    two_axis = json.loads(Path(sorted(glob.glob(
        str(ROOT / "results/two_axis_comparison_runs/*/summary.json")))[-1]).read_text())
    test_ids = {r["sequence_id"] for r in two_axis["rows"]}

    train, test = [], []
    for record in records:
        if number(record, "In-cell half-life") is None:
            continue
        if not all(record.get(s) for s in
                   ("Sequence 5 UTR", "Sequence CDS", "Sequence 3 UTR")):
            continue
        entry = {
            "sequence_id": record["Sequence ID"],
            "group": record.get("Group", ""),
            "measured_in_cell_hours": number(record, "In-cell half-life"),
            "ribosome_load_measured": number(record, "Ribosome load"),
            "utr5": record["Sequence 5 UTR"].upper(),
            "cds": record["Sequence CDS"].upper(),
            "utr3": record["Sequence 3 UTR"].upper(),
        }
        (test if record["Sequence ID"] in test_ids else train).append(entry)
    print(f"preserved split: train {len(train)}  test {len(test)}", flush=True)
    if len(test) != 122:
        raise SystemExit(f"held-out set is {len(test)}, expected 122")

    split_note = (
        "The preserved split keeps the two-axis comparison's 122-record held-out set, so no "
        "in-cell label that this project has already used is reused. It cannot screen UTR "
        "features: its training half is 78 of 81 CDS (Nluc) variants, which hold the UTRs "
        "fixed, so utr5_gc takes 2 distinct values in training against 46 in the held-out "
        "set, and every UTR feature is near-constant.")
    if args.split == "stratified":
        import random
        rng = random.Random(args.seed)
        families = {}
        for entry in train + test:
            families.setdefault(entry["group"], []).append(entry)
        train, test = [], []
        for group in sorted(families):
            members = sorted(families[group], key=lambda e: e["sequence_id"])
            rng.shuffle(members)
            cut = len(members) // 2
            test.extend(members[:cut])
            train.extend(members[cut:])
        print(f"stratified split: train {len(train)}  test {len(test)}", flush=True)
        split_note += (
            f" This run therefore REDRAWS the split, balanced within each design family at "
            f"seed {args.seed}. The amendment is recorded rather than applied silently. It "
            "departs from the protocol's declared 'preserve the existing split' clause, for "
            "the reason above. Consequence to carry: an in-cell result on this split is NOT "
            "comparable to the in-solution results, which keep the 122-record set, and any "
            "future in-cell claim must state which split it used.")

    everything = train + test
    for entry in everything:
        entry["features"] = sequence_features(entry["utr5"], entry["cds"], entry["utr3"])

    jobs = []
    for index, entry in enumerate(everything):
        for region in ("utr5", "cds", "utr3"):
            jobs.append(((index, region), entry[region]))
    print(f"folding {len(jobs)} regions on {args.jobs} workers...", flush=True)
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        for (index, region), folded in pool.map(fold_region, jobs):
            if folded is None:
                continue
            everything[index]["features"][f"{region}_aup"] = folded["aup"]
            everything[index]["features"][f"{region}_energy_per_nt"] = folded["energy_per_nt"]

    names = sorted({k for e in everything for k in e["features"]})
    complete = [n for n in names
                if all(n in e["features"] for e in everything)]
    dropped = sorted(set(names) - set(complete))
    print(f"{len(complete)} features complete on all records"
          f"{f', dropped {dropped}' if dropped else ''}", flush=True)

    train_target = [e["measured_in_cell_hours"] for e in train]
    test_target = [e["measured_in_cell_hours"] for e in test]
    lengths = {n: [e["features"][n] for e in train]
               for n in ("utr5_length", "cds_length", "utr3_length")}

    screen = {}
    for name in complete:
        values = [e["features"][name] for e in train]
        if len(set(values)) < 3:
            screen[name] = {"screened": False, "reason": "near-constant on training records"}
            continue
        screen[name] = {
            "screened": True,
            "train_spearman": spearman(values, train_target),
            "train_spearman_vs_lengths": {
                k: spearman(values, v) for k, v in lengths.items()},
        }
    # The declared ceiling: a measurement, never an input.
    ribo_train = [e["ribosome_load_measured"] for e in train]
    ribo_test = [e["ribosome_load_measured"] for e in test]
    ceiling = None
    if all(v is not None for v in ribo_train + ribo_test):
        ceiling = {"train_spearman": spearman(ribo_train, train_target),
                   "test_spearman": spearman(ribo_test, test_target)}

    screened = [n for n in screen if screen[n]["screened"]]
    ranked = sorted(screened, key=lambda n: abs(screen[n]["train_spearman"]), reverse=True)
    bar = two_axis["gc_alone"]["spearman_vs_in_cell"]
    promoted = [n for n in ranked if abs(screen[n]["train_spearman"]) > abs(bar)]

    # Promoted candidates are scored ONCE on the held-out set.
    held_out = {}
    for name in promoted:
        values = [e["features"][name] for e in test]
        held_out[name] = {
            "test_spearman": spearman(values, test_target),
            "test_concordance": concordance(
                [-v for v in values] if screen[name]["train_spearman"] < 0 else values,
                test_target),
        }

    beat_bar = [n for n in promoted if abs(held_out[n]["test_spearman"]) > abs(bar)]
    summary = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": protocol["purpose"],
        "protocol": str(PROTOCOL.relative_to(ROOT)),
        "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
        "source": {"archive_sha256": archive_digest, "table_sha256": table_digest,
                   "not_redistributed": declared["not_redistributed"]},
        "axis": protocol["the_axis_is_now_declared"],
        "split": {"mode": args.split, "seed": args.seed, "note": split_note},
        "counts": {"train": len(train), "test": len(test),
                   "features_complete": len(complete),
                   "features_screened": len(screened),
                   "features_dropped": dropped},
        "fitting_performed": "none",
        "screen_is_univariate_because": (
            "gate v15 measured that this label-set size supports about one feature: "
            "held-out correlation fell from +0.3651 at one feature to +0.1317 at four "
            "while training correlation rose to +0.5972"),
        "bar": {"transcript_gc_alone_in_cell_held_out": bar,
                "frozen_in_solution_arm_in_cell_held_out":
                    two_axis["ours"]["spearman_vs_in_cell"],
                "statement": "A candidate is only interesting if it clears the free single "
                             "feature on the held-out constructs."},
        "multiplicity_warning": (
            f"{len(screened)} features were screened on {len(train)} training records. "
            f"{len(promoted)} cleared the bar on training and were scored once on the "
            "held-out set. With this many candidates and this few records, a training "
            "correlation above the bar is expected by chance for several features, which "
            "is why the held-out column is the only one that counts."),
        "train_screen": screen,
        "ranking_by_train_abs_spearman": [
            {"feature": n, "train_spearman": screen[n]["train_spearman"]} for n in ranked],
        "promoted_to_held_out": held_out,
        "features_beating_the_bar_on_held_out": beat_bar,
        "measured_ribosome_load_ceiling": {
            "values": ceiling,
            "is_not_a_usable_feature": (
                "Ribosome load is a MEASUREMENT and cannot be an input in production. It is "
                "carried to bound what wiring RiboNN's predicted translation efficiency into "
                "the stability model could buy. RiboNN's prediction is necessarily weaker "
                "than the measurement, so this is an upper bound, not an expectation."),
            "verdict": (None if ceiling is None else
                        ("the ceiling clears the transcript GC bar, so wiring RiboNN into the "
                         "stability model is worth testing"
                         if abs(ceiling["test_spearman"]) > abs(bar) else
                         "the ceiling does not clear the transcript GC bar, so wiring RiboNN "
                         "into the stability model is not worth building")),
        },
        "what_this_cannot_establish": protocol["what_this_cannot_establish"],
        "rows": [{k: v for k, v in e.items() if k not in ("utr5", "cds", "utr3")}
                 for e in everything],
    }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%f") + "Z"
    out = ROOT / args.out / stamp
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out / 'summary.json'}\n")
    print(f"bar to beat: transcript GC alone on held-out = {bar:+.4f}")
    if ceiling:
        print(f"CEILING, measured ribosome load: train {ceiling['train_spearman']:+.4f}  "
              f"held-out {ceiling['test_spearman']:+.4f}")
    print(f"\ntop 15 of {len(screened)} screened, by |train rho|:")
    print(f"  {'feature':<28}{'train':>9}{'held-out':>11}")
    for name in ranked[:15]:
        test_value = (f"{held_out[name]['test_spearman']:+.4f}" if name in held_out else "--")
        print(f"  {name:<28}{screen[name]['train_spearman']:>+9.4f}{test_value:>11}")
    print(f"\npromoted on training: {len(promoted)}")
    print(f"beat the bar on HELD-OUT: {beat_bar if beat_bar else 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
