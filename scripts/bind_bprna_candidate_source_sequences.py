#!/usr/bin/env python3
"""Bind provisional bpRNA SQL candidates to DBN files by exact sequence hash."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.reference import digest  # noqa: E402

CANDIDATES = ROOT / "results/bprna_family_separated_candidates_v3_runs/20261017T190513.066933Z/summary.json"
CLANS = ROOT / "results/bprna_candidate_clans_runs/20261017T190647.643559Z/summary.json"
INVENTORY = ROOT / "results/bprna_training_length_inventory_2026-10-16_v2.json"
PROTOCOL = ROOT / "results/bprna_candidate_sequence_binding_protocol.json"


def source():
    inventory = json.loads(INVENTORY.read_text())
    return Path(inventory["source_run_dir"]) / "source.zip"


def policy():
    return {"binding": "uppercase_T_to_U_exact_sequence_SHA256",
            "numeric_id_join_allowed": False, "duplicate_source_matches_retained": True,
            "candidate_structure_labels_parsed": False,
            "independent_test_claim": False, "model_inference_performed": False}


def inputs():
    candidates = json.loads(CANDIDATES.read_text())
    clans = json.loads(CLANS.read_text())
    if candidates["provisional_family_count"] != 39 or len(clans["families"]) != 39:
        raise ValueError("Candidate or clan inventory changed")
    by_family = {r["family_id"]: r for r in clans["families"]}
    rows = []
    for family in candidates["families"]:
        meta = by_family[family["family_id"]]
        if meta["candidate_count"] != family["candidate_count"]:
            raise ValueError("Candidate/clan family count differs")
        for record in family["records"]:
            rows.append({"sql_name": record["sql_name"],
                         "family_id": family["family_id"],
                         "sequence_sha256": record["sequence_sha256"],
                         "length_nt": record["length_nt"],
                         "clan_status": meta["status"]})
    if len(rows) != 433:
        raise ValueError("Candidate count changed")
    return rows


def audit(path):
    manifest = json.loads(Path(path).read_text())
    folder = Path(manifest["run_dir"])
    if (manifest != json.loads((folder / "manifest.json").read_text())
            or manifest["policy"] != policy()
            or manifest["driver_sha256"] != digest(Path(__file__).read_bytes())):
        raise ValueError("Sequence binding protocol differs")
    for name, sha in manifest["inputs_sha256"].items():
        if digest(Path(name).read_bytes()) != sha:
            raise ValueError(f"Source changed: {name}")
    if manifest["source_sha256"] != digest(source().read_bytes()):
        raise ValueError("DBN source archive changed")
    inputs()
    return manifest


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    inputs()
    path = source()
    with zipfile.ZipFile(path) as archive:
        if not any(n.startswith("dbnFiles/bpRNA_RFAM_") for n in archive.namelist()):
            raise ValueError("DBN archive missing RFAM files")
    folder = ROOT / "results/bprna_candidate_sequence_binding_protocol_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {"run_dir": str(folder), "policy": policy(),
                "inputs_sha256": {str(p): digest(p.read_bytes())
                                  for p in (CANDIDATES, CLANS, INVENTORY)},
                "source_sha256": digest(path.read_bytes()),
                "driver_sha256": digest(Path(__file__).read_bytes())}
    atomic_json(folder / "manifest.json", manifest)
    audit(folder / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen sequence binding:", folder / "manifest.json")


def compute():
    rows = inputs()
    targets = {r["sequence_sha256"] for r in rows}
    matches = defaultdict(list)
    scanned = 0
    with zipfile.ZipFile(source()) as archive:
        for path in archive.namelist():
            if not (path.startswith("dbnFiles/bpRNA_RFAM_") and path.endswith(".dbn")):
                continue
            scanned += 1
            lines = archive.read(path).splitlines()
            if len(lines) < 4 or not re.fullmatch(rb"[ACGUTacgut]+", lines[3]):
                continue
            sequence = lines[3].upper().replace(b"T", b"U")
            sha = hashlib.sha256(sequence).hexdigest()
            if sha in targets:
                matches[sha].append({"zip_path": path, "length_nt": len(sequence)})
    bound = []
    for row in rows:
        hits = sorted(matches[row["sequence_sha256"]], key=lambda r: r["zip_path"])
        if any(hit["length_nt"] != row["length_nt"] for hit in hits):
            raise ValueError("Sequence-bound source length differs")
        bound.append({**row, "source_matches": hits,
                      "source_match_count": len(hits)})
    counts = Counter(r["clan_status"] for r in bound if r["source_match_count"])
    return {"policy": policy(), "rfam_dbn_files_scanned": scanned,
            "candidate_count": len(bound),
            "sequence_bound_count": sum(bool(r["source_match_count"]) for r in bound),
            "multiple_source_match_count": sum(r["source_match_count"] > 1 for r in bound),
            "bound_by_clan_status": dict(sorted(counts.items())), "records": bound,
            "readiness": "sequence_bound_only_structure_and_crw_unresolved"}


def run():
    manifest = audit(PROTOCOL)
    folder = ROOT / "results/bprna_candidate_sequence_binding_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    atomic_json(folder / "protocol.json", manifest)
    result = {"complete": True, "run_dir": str(folder), **compute()}
    atomic_json(folder / "summary.json", result)
    print("Sequence binding:", folder / "summary.json")
    print("Bound:", result["sequence_bound_count"], "of", result["candidate_count"])


def verify(path):
    folder = Path(path).resolve().parent
    audit(folder / "protocol.json")
    expected = {"complete": True, "run_dir": str(folder), **compute()}
    if json.loads(Path(path).read_text()) != expected:
        raise ValueError("Sequence binding replay differs")
    print("Sequence binding replay passed")


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
