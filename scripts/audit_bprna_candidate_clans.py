#!/usr/bin/env python3
"""Replayable Rfam 15.1 clan audit for provisional bpRNA candidates."""

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.reference import digest  # noqa: E402

SOURCE = ROOT / "results/rfam_release_15_1_clan_source/Rfam.seed.gz"
CANDIDATES = ROOT / "results/bprna_family_separated_candidates_v3_runs/20261017T190513.066933Z/summary.json"
PROTOCOL = ROOT / "results/bprna_candidate_clans_protocol.json"


def policy():
    return {"rfam_release": "15.1", "source_format": "Rfam.seed.gz_stockholm_GF_AC_ID_CL",
            "candidate_group": "provisional_400_4999nt_bprna_rfam",
            "no_clan_means_independent": False,
            "unknown_crw_lineage_resolved": False,
            "independent_test_claim": False, "model_inference_performed": False}


def parse_seed():
    families = {}
    accession = name = clan = None
    with gzip.open(SOURCE, "rb") as stream:
        for line in stream:
            if line.startswith(b"#=GF AC "):
                if accession is not None:
                    raise ValueError("Unclosed seed family")
                accession = line.split()[2].decode("ascii")
            elif line.startswith(b"#=GF ID "):
                name = line.split()[2].decode("ascii")
            elif line.startswith(b"#=GF CL "):
                clan = line.split()[2].decode("ascii")
            elif line.startswith(b"//"):
                if accession is None or name is None or accession in families:
                    raise ValueError("Invalid seed family boundary")
                if (not re.fullmatch(r"RF\d{5}", accession)
                        or clan is not None and not re.fullmatch(r"CL\d{5}", clan)):
                    raise ValueError("Invalid Rfam accession or clan")
                families[accession] = {"name": name, "clan_id": clan}
                accession = name = clan = None
    if accession is not None or len(families) < 4000:
        raise ValueError("Rfam seed archive incomplete")
    return families


def audit(path):
    manifest = json.loads(Path(path).read_text())
    folder = Path(manifest["run_dir"])
    if (manifest != json.loads((folder / "manifest.json").read_text())
            or manifest["policy"] != policy()
            or manifest["driver_sha256"] != digest(Path(__file__).read_bytes())
            or manifest["source_sha256"] != digest(SOURCE.read_bytes())
            or manifest["candidate_sha256"] != digest(CANDIDATES.read_bytes())):
        raise ValueError("Clan audit protocol differs")
    return manifest


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    parse_seed()
    folder = ROOT / "results/bprna_candidate_clans_protocol_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {"run_dir": str(folder), "policy": policy(),
                "source_url": "https://ftp.ebi.ac.uk/pub/databases/Rfam/15.1/Rfam.seed.gz",
                "source_sha256": digest(SOURCE.read_bytes()),
                "candidate_sha256": digest(CANDIDATES.read_bytes()),
                "driver_sha256": digest(Path(__file__).read_bytes())}
    atomic_json(folder / "manifest.json", manifest)
    audit(folder / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen clan audit:", folder / "manifest.json")


def compute():
    seed = parse_seed()
    candidates = json.loads(CANDIDATES.read_text())
    if candidates["provisional_family_count"] != 39:
        raise ValueError("Candidate inventory changed")
    known = set(candidates["known_family_ids"])
    if known - set(seed):
        raise ValueError("Known exposed family absent from Rfam release")
    exposed_by_clan = {}
    for family in known:
        clan = seed[family]["clan_id"]
        if clan:
            exposed_by_clan.setdefault(clan, []).append(family)
    rows = []
    for family in candidates["families"]:
        family_id = family["family_id"]
        if family_id in known or family_id not in seed:
            raise ValueError("Candidate family missing or already exposed")
        clan = seed[family_id]["clan_id"]
        overlap = sorted(exposed_by_clan.get(clan, [])) if clan else []
        status = ("known_exposed_clan" if overlap else
                  "no_clan_assigned" if clan is None else "distinct_known_clan")
        rows.append({"family_id": family_id, "rfam_name": seed[family_id]["name"],
                     "clan_id": clan, "known_exposed_clan_families": overlap,
                     "candidate_count": family["candidate_count"],
                     "min_length_nt": family["min_length_nt"],
                     "max_length_nt": family["max_length_nt"], "status": status})
    counts = Counter(r["status"] for r in rows)
    sequence_counts = Counter()
    for row in rows:
        sequence_counts[row["status"]] += row["candidate_count"]
    return {"policy": policy(), "source_family_count": len(seed),
            "known_exposed_family_count": len(known),
            "known_exposed_clans": sorted(exposed_by_clan),
            "family_status_counts": dict(sorted(counts.items())),
            "candidate_status_counts": dict(sorted(sequence_counts.items())),
            "families": rows, "readiness": "clan_screen_only_crw_unresolved"}


def run():
    manifest = audit(PROTOCOL)
    folder = ROOT / "results/bprna_candidate_clans_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    atomic_json(folder / "protocol.json", manifest)
    result = {"complete": True, "run_dir": str(folder), **compute()}
    atomic_json(folder / "summary.json", result)
    print("Clan audit:", folder / "summary.json")
    print("Family statuses:", result["family_status_counts"])


def verify(path):
    folder = Path(path).resolve().parent
    audit(folder / "protocol.json")
    expected = {"complete": True, "run_dir": str(folder), **compute()}
    if json.loads(Path(path).read_text()) != expected:
        raise ValueError("Clan audit replay differs")
    print("Clan audit replay passed")


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
