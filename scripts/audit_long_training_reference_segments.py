#!/usr/bin/env python3
"""Frozen exact-segment overlap audit for long bpRNA training and development RNAs."""

import argparse
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.reference import digest  # noqa: E402

TRAIN = ROOT / "results/bprna_long_training_smoke_runs/20261017T033749.792816Z/selection.json"
DEVELOPMENT = ROOT / "results/long_validation_coverage_runs/20261017T033935.363253Z/selection.json"
PROTOCOL = ROOT / "results/long_training_reference_segment_audit_protocol.json"
LENGTHS = (20, 30, 40)
SHUFFLES_PER_RECORD = 32
SEED = 20261017


def policy():
    return {"segment_lengths_nt": list(LENGTHS),
            "negative_control": "mononucleotide_shuffle_each_training_sequence",
            "shuffles_per_record": SHUFFLES_PER_RECORD, "seed": SEED,
            "development_only": True, "family_assignment_claim": False,
            "independent_test_claim": False, "model_inference_performed": False}


def kmers(sequence, length):
    return {sequence[i:i + length] for i in range(len(sequence) - length + 1)}


def inputs():
    train = json.loads(TRAIN.read_text())["selected"]
    development = json.loads(DEVELOPMENT.read_text())["selected"]
    if (len(train) != 17 or len(development) != 11
            or len({r["id"] for r in train + development}) != 28
            or {r["family_id"] for r in development} !=
            {"RF00177", "RF02540", "RF02541", "RF02542"}
            or any("family_id" in r for r in train)):
        raise ValueError("Exact-segment audit input inventory changed")
    return train, development


def audit(path):
    manifest = json.loads(Path(path).read_text())
    folder = Path(manifest["run_dir"])
    if manifest != json.loads((folder / "manifest.json").read_text()) or manifest["policy"] != policy():
        raise ValueError("Exact-segment manifest or policy changed")
    for name, sha in manifest["source_sha256"].items():
        if digest(Path(name).read_bytes()) != sha:
            raise ValueError(f"Exact-segment source changed: {name}")
    if digest(Path(__file__).read_bytes()) != manifest["driver_sha256"]:
        raise ValueError("Exact-segment driver changed")
    return manifest, *inputs()


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    inputs()
    folder = ROOT / "results/long_training_reference_segment_audit_protocol_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {"run_dir": str(folder), "policy": policy(),
                "source_sha256": {str(path): digest(path.read_bytes())
                                  for path in (TRAIN, DEVELOPMENT)},
                "driver_sha256": digest(Path(__file__).read_bytes())}
    atomic_json(folder / "manifest.json", manifest)
    audit(folder / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen exact-segment audit:", folder / "manifest.json")


def compute(train, development):
    reference_kmers = {length: [(r, kmers(r["sequence"], length)) for r in development]
                       for length in LENGTHS}
    rows = []
    for index, record in enumerate(train):
        by_length = {}
        for length in LENGTHS:
            source = kmers(record["sequence"], length)
            matches = [{"reference_id": ref["id"], "family_id": ref["family_id"],
                        "shared_distinct_segments": len(source & words)}
                       for ref, words in reference_kmers[length]]
            best = sorted(matches, key=lambda row: (-row["shared_distinct_segments"], row["reference_id"]))[0]
            by_length[str(length)] = {
                "max_shared_distinct_segments": best["shared_distinct_segments"],
                "best_reference_id": best["reference_id"] if best["shared_distinct_segments"] else None,
                "best_reference_family_id": best["family_id"] if best["shared_distinct_segments"] else None,
                "families_with_any_shared_segment": sorted({m["family_id"] for m in matches
                                                            if m["shared_distinct_segments"]})}
        null_maxima = []
        for replicate in range(SHUFFLES_PER_RECORD):
            bases = list(record["sequence"])
            random.Random(SEED + index * 1000 + replicate).shuffle(bases)
            shuffled = kmers("".join(bases), 30)
            null_maxima.append(max(len(shuffled & words) for _, words in reference_kmers[30]))
        rows.append({"id": record["id"], "source_group": record["source_group"],
                     "length_nt": len(record["sequence"]), "by_length": by_length,
                     "shuffle30_maxima": null_maxima})
    counts = {str(length): sum(row["by_length"][str(length)]["max_shared_distinct_segments"] > 0
                               for row in rows) for length in LENGTHS}
    return {"records": rows, "records_with_any_shared_segment": counts,
            "highest_shuffle_30_segment_overlap": max(max(r["shuffle30_maxima"]) for r in rows),
            "train_count": len(train), "development_count": len(development),
            "family_assignment_claim": False, "independent_test_claim": False}


def execute():
    manifest, train, development = audit(PROTOCOL)
    folder = ROOT / "results/long_training_reference_segment_audit_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    atomic_json(folder / "protocol.json", manifest)
    result = {"complete": True, "run_dir": str(folder), **compute(train, development)}
    atomic_json(folder / "summary.json", result)
    print("Exact-segment audit:", folder / "summary.json")
    print("Training records sharing an exact segment:", result["records_with_any_shared_segment"])
    print("Highest 30-nt shuffle overlap:", result["highest_shuffle_30_segment_overlap"])


def verify_run(path):
    folder = Path(path).resolve().parent
    manifest, train, development = audit(folder / "protocol.json")
    result = json.loads(Path(path).read_text())
    if (result["run_dir"] != str(folder) or result["complete"] is not True
            or result != {"complete": True, "run_dir": str(folder),
                          **compute(train, development)}):
        raise ValueError("Exact-segment run replay differs")
    print("Exact-segment run replay passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--verify-protocol", type=Path)
    mode.add_argument("--verify-run", type=Path)
    args = parser.parse_args()
    if args.freeze:
        freeze()
    elif args.run:
        execute()
    elif args.verify_run:
        verify_run(args.verify_run)
    else:
        audit(args.verify_protocol)
        print("Exact-segment protocol replay passed")


if __name__ == "__main__":
    main()
