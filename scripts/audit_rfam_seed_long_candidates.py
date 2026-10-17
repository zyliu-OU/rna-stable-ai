#!/usr/bin/env python3
"""Audit 1000–4999-nt Rfam 15.1 seed sequences against known exposures."""

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.reference import digest  # noqa: E402
from audit_bprna_candidate_clans import parse_seed  # noqa: E402

SEED = ROOT / "results/rfam_release_15_1_clan_source/Rfam.seed.gz"
KNOWN = ROOT / "results/bprna_family_separated_candidates_v3_runs/20261017T190513.066933Z/summary.json"
OLD = ROOT / "results/bprna_length_pilot_protocol_runs/20261016T174446.305367Z/train.json"
EXTRA = ROOT / "results/bprna_long_training_smoke_runs/20261017T033749.792816Z/selection.json"
DEV = ROOT / "results/long_validation_coverage_runs/20261017T033935.363253Z/candidates.json"
PROTOCOL = ROOT / "results/rfam_seed_long_candidate_audit_protocol.json"


def policy():
    return {"release": "15.1", "length_nt": [1000, 4999],
            "sequence_source": "Rfam_seed_Stockholm_nonannotation_rows",
            "family_clan_source": "Rfam_seed_GF_AC_CL",
            "exact_training_segment_nt": 30,
            "structure_consensus_labels_read": False,
            "independent_test_claim": False, "model_inference_performed": False}


def inputs():
    known = json.loads(KNOWN.read_text())
    seed_families = parse_seed()
    known_families = set(known["known_family_ids"])
    if len(known_families) != 23 or known_families - set(seed_families):
        raise ValueError("Known family inventory changed")
    exposed_clans = {seed_families[f]["clan_id"] for f in known_families
                     if seed_families[f]["clan_id"]}
    train = (json.loads(OLD.read_text())["records"]
             + json.loads(EXTRA.read_text())["selected"])
    dev = json.loads(DEV.read_text())
    if len(train) != 105 or len(dev) != 338:
        raise ValueError("Exposure inventory changed")
    words = {r["sequence"][i:i + 30] for r in train
             for i in range(len(r["sequence"]) - 29)}
    hashes = {hashlib.sha256(r["sequence"].encode()).hexdigest()
              for r in train + dev}
    return seed_families, known_families, exposed_clans, words, hashes


def audit(path):
    manifest = json.loads(Path(path).read_text())
    folder = Path(manifest["run_dir"])
    if (manifest != json.loads((folder / "manifest.json").read_text())
            or manifest["policy"] != policy()
            or manifest["driver_sha256"] != digest(Path(__file__).read_bytes())):
        raise ValueError("Seed long-candidate protocol differs")
    for name, sha in manifest["inputs_sha256"].items():
        if digest(Path(name).read_bytes()) != sha:
            raise ValueError(f"Seed audit source changed: {name}")
    inputs()
    return manifest


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    inputs()
    folder = ROOT / "results/rfam_seed_long_candidate_audit_protocol_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {"run_dir": str(folder), "policy": policy(),
                "inputs_sha256": {str(p): digest(p.read_bytes())
                                  for p in (SEED, KNOWN, OLD, EXTRA, DEV)},
                "driver_sha256": digest(Path(__file__).read_bytes())}
    atomic_json(folder / "manifest.json", manifest)
    audit(folder / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen seed long-candidate audit:", folder / "manifest.json")


def compute():
    families, known_families, exposed_clans, words, hashes = inputs()
    rows = []
    accession = None
    fragments = defaultdict(list)

    def finish():
        if accession is None:
            return
        family = families[accession]
        for identity, pieces in fragments.items():
            aligned = "".join(pieces).upper().replace("T", "U")
            sequence = "".join(c for c in aligned if c not in ".-~")
            if not 1000 <= len(sequence) <= 4999 or set(sequence) - set("ACGU"):
                continue
            sha = hashlib.sha256(sequence.encode()).hexdigest()
            shared = sum(sequence[i:i + 30] in words for i in range(len(sequence) - 29))
            if accession in known_families:
                status = "known_exposed_family"
            elif family["clan_id"] in exposed_clans:
                status = "known_exposed_clan"
            elif sha in hashes:
                status = "exact_exposed_sequence"
            elif shared:
                status = "shared_30nt_training_segment"
            else:
                status = "provisional_candidate"
            rows.append({"family_id": accession, "clan_id": family["clan_id"],
                         "seed_identity": identity, "length_nt": len(sequence),
                         "sequence_sha256": sha,
                         "shared_30nt_training_segments": shared,
                         "status": status})

    with gzip.open(SEED, "rb") as stream:
        for raw in stream:
            line = raw.decode("latin1").strip()
            if line.startswith("#=GF AC "):
                if accession is not None:
                    raise ValueError("Unclosed seed family")
                accession = line.split()[2]
            elif line == "//":
                finish()
                accession = None
                fragments = defaultdict(list)
            elif accession and line and not line.startswith("#"):
                parts = line.split()
                if len(parts) >= 2:
                    fragments[parts[0]].append(parts[1])
    if accession is not None:
        raise ValueError("Unclosed final seed family")
    counts = Counter(r["status"] for r in rows)
    return {"policy": policy(), "eligible_seed_sequence_count": len(rows),
            "eligible_family_count": len({r["family_id"] for r in rows}),
            "status_counts": dict(sorted(counts.items())), "records": rows,
            "independent_long_candidate_count": counts["provisional_candidate"]}


def run():
    manifest = audit(PROTOCOL)
    folder = ROOT / "results/rfam_seed_long_candidate_audit_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    atomic_json(folder / "protocol.json", manifest)
    result = {"complete": True, "run_dir": str(folder), **compute()}
    atomic_json(folder / "summary.json", result)
    print("Seed long-candidate audit:", folder / "summary.json")
    print(result["status_counts"])


def verify(path):
    folder = Path(path).resolve().parent
    audit(folder / "protocol.json")
    expected = {"complete": True, "run_dir": str(folder), **compute()}
    if json.loads(Path(path).read_text()) != expected:
        raise ValueError("Seed long-candidate replay differs")
    print("Seed long-candidate replay passed")


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
