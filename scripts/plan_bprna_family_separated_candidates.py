#!/usr/bin/env python3
"""Inventory provisional under-5000-nt bpRNA RFAM validation candidates."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.reference import digest  # noqa: E402
from bind_bprna_long_origin_metadata import SOURCE, SQL_MEMBER, ROW, metadata  # noqa: E402

OLD = ROOT / "results/bprna_length_pilot_protocol_runs/20261016T174446.305367Z/train.json"
EXTRA = ROOT / "results/bprna_long_training_smoke_runs/20261017T033749.792816Z/selection.json"
DEV_CANDIDATES = ROOT / "results/long_validation_coverage_runs/20261017T033935.363253Z/candidates.json"
ORIGINS = ROOT / "results/bprna_long_origin_binding_v2_runs/20261017T185531.913009Z/summary.json"
PROTOCOL = ROOT / "results/bprna_family_separated_candidates_v3_protocol.json"


def inputs():
    old = json.loads(OLD.read_text())["records"]
    extra = json.loads(EXTRA.read_text())["selected"]
    dev_candidates = json.loads(DEV_CANDIDATES.read_text())
    origins = json.loads(ORIGINS.read_text())["records"]
    if (len(old), len(extra), len(origins), len(dev_candidates)) != (88, 17, 17, 338):
        raise ValueError("Training/development inventory changed")
    known_families = {r["family_id"] for r in old + dev_candidates if r.get("family_id")}
    known_families.update(f for r in origins for f in r["rfam_family_ids"])
    train = old + extra
    words = {r["sequence"][i:i + 30] for r in train
             for i in range(len(r["sequence"]) - 29)}
    hashes = {hashlib.sha256(r["sequence"].encode()).hexdigest()
              for r in train + dev_candidates}
    return known_families, words, hashes


def policy():
    return {"length_nt": [400, 4999], "source_group": "RFAM",
            "known_family_exclusion": "88_control_17_extended_338_development_candidates",
            "exact_segment_screen_nt": 30, "one_row_per_unique_sequence_family": True,
            "structure_labels_used_for_selection": False, "clan_membership_verified": False,
            "seven_crw_family_lineages_resolved": False,
            "independent_test_claim": False, "model_inference_performed": False}


def audit(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    if (manifest != json.loads((run / "manifest.json").read_text())
            or manifest["policy"] != policy()
            or manifest["driver_sha256"] != digest(Path(__file__).read_bytes())):
        raise ValueError("Candidate protocol differs")
    for name, sha in manifest["inputs_sha256"].items():
        if digest(Path(name).read_bytes()) != sha:
            raise ValueError(f"Candidate source changed: {name}")
    inputs()
    return manifest


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    inputs()
    with zipfile.ZipFile(SOURCE) as archive:
        if SQL_MEMBER not in archive.namelist():
            raise ValueError("Official SQL table missing")
    run = ROOT / "results/bprna_family_separated_candidates_v3_protocol_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    manifest = {"run_dir": str(run), "policy": policy(),
                "inputs_sha256": {str(p): digest(p.read_bytes())
                                  for p in (OLD, EXTRA, DEV_CANDIDATES, ORIGINS, SOURCE)},
                "driver_sha256": digest(Path(__file__).read_bytes())}
    atomic_json(run / "manifest.json", manifest)
    audit(run / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Candidate protocol:", run / "manifest.json")


def compute():
    known, train_words, exposed_hashes = inputs()
    counts = Counter()
    family_rows = defaultdict(list)
    unique = set()
    parsed = 0
    with zipfile.ZipFile(SOURCE) as archive, archive.open(SQL_MEMBER) as stream:
        for line in stream:
            match = ROW.search(line)
            if not match or not match.group(2).startswith(b"bpRNA_RFAM_"):
                continue
            parsed += 1
            sequence = match.group(4).upper().decode()
            if not 400 <= len(sequence) <= 4999 or set(sequence) - set("ACGU"):
                continue
            name = match.group(2).decode()
            description = match.group(3).replace(b"''", b"'").decode()
            family = metadata(name, int(match.group(1)), description)["rfam_family_id"]
            if not family:
                counts["missing_archived_family"] += 1
                continue
            sha = hashlib.sha256(sequence.encode()).hexdigest()
            key = (family, sha)
            if key in unique:
                counts["duplicate_sequence_within_family"] += 1
                continue
            unique.add(key)
            counts["eligible_unique_sequence_family"] += 1
            if family in known:
                counts["known_training_or_development_family"] += 1
                continue
            if sha in exposed_hashes:
                counts["exact_exposed_sequence"] += 1
                continue
            shared = sum(sequence[i:i + 30] in train_words
                         for i in range(len(sequence) - 29))
            if shared:
                counts["shared_30nt_training_segment"] += 1
                continue
            counts["provisional_candidate"] += 1
            family_rows[family].append({"sql_name": name, "sequence_sha256": sha,
                                        "length_nt": len(sequence)})
    families = [{"family_id": family, "candidate_count": len(rows),
                 "min_length_nt": min(r["length_nt"] for r in rows),
                 "max_length_nt": max(r["length_nt"] for r in rows),
                 "records": sorted(rows, key=lambda r: (r["sql_name"], r["sequence_sha256"]))}
                for family, rows in sorted(family_rows.items())]
    return {"policy": policy(), "parsed_rfam_sql_rows": parsed,
            "known_family_ids": sorted(known), "counts": dict(sorted(counts.items())),
            "provisional_family_count": len(families), "families": families,
            "readiness": "metadata_candidates_only_crw_and_clan_unresolved"}


def run():
    manifest = audit(PROTOCOL)
    folder = ROOT / "results/bprna_family_separated_candidates_v3_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    atomic_json(folder / "protocol.json", manifest)
    result = {"complete": True, "run_dir": str(folder), **compute()}
    atomic_json(folder / "summary.json", result)
    print("Candidate inventory:", folder / "summary.json")
    print("Families:", result["provisional_family_count"],
          "candidates:", result["counts"].get("provisional_candidate", 0))


def verify(path):
    folder = Path(path).resolve().parent
    audit(folder / "protocol.json")
    expected = {"complete": True, "run_dir": str(folder), **compute()}
    if json.loads(Path(path).read_text()) != expected:
        raise ValueError("Candidate inventory replay differs")
    print("Candidate inventory replay passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--verify-run", type=Path)
    args = parser.parse_args()
    if args.freeze:
        freeze()
    elif args.run:
        run()
    else:
        verify(args.verify_run)


if __name__ == "__main__":
    main()
