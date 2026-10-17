#!/usr/bin/env python3
"""Bind selected bpRNA training RNAs to the official SQL origin rows by sequence."""

import argparse
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

SELECTED = ROOT / "results/bprna_long_training_smoke_runs/20261017T033749.792816Z/selection.json"
SOURCE = ROOT / "results/bprna_origin_metadata_source/Load_bpRNA_1m_Mysql_Part1.zip"
SQL_MEMBER = "Load_bpRNA_1m_Mysql_Part1/5_RNATable_Load.sql"
PROTOCOL = ROOT / "results/bprna_long_origin_binding_v2_protocol.json"
ROW = re.compile(rb"VALUES \((\d+),'(bpRNA_(?:CRW|RFAM)_\d+)','((?:''|[^'])*)','([A-Za-z]+)',")
RFAM_ORIGIN = re.compile(r"^(RF\d{5})_(.+)$")


def policy():
    return {"stage": "selected_long_training_origin_binding",
            "binding": "same_source_group_and_uppercase_exact_sequence",
            "numeric_bpRNA_id_is_family_id": False,
            "ambiguous_matches_retained": True,
            "development_only": True, "independent_test_claim": False}


def selected_records():
    rows = json.loads(SELECTED.read_text())["selected"]
    if (len(rows) != 17 or len({r["id"] for r in rows}) != 17
            or sum(r["source_group"] == "CRW" for r in rows) != 7
            or sum(r["source_group"] == "RFAM" for r in rows) != 10):
        raise ValueError("Selected bpRNA inventory changed")
    return rows


def audit(path):
    manifest = json.loads(Path(path).read_text())
    folder = Path(manifest["run_dir"])
    if manifest != json.loads((folder / "manifest.json").read_text()) or manifest["policy"] != policy():
        raise ValueError("Origin-binding manifest or policy changed")
    if (manifest["selected_sha256"] != digest(SELECTED.read_bytes())
            or manifest["source_sha256"] != digest(SOURCE.read_bytes())
            or manifest["driver_sha256"] != digest(Path(__file__).read_bytes())):
        raise ValueError("Origin-binding input or driver changed")
    return manifest, selected_records()


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    selected_records()
    with zipfile.ZipFile(SOURCE) as archive:
        if SQL_MEMBER not in archive.namelist():
            raise ValueError("Official RNA table missing")
    folder = ROOT / "results/bprna_long_origin_binding_v2_protocol_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {"run_dir": str(folder), "policy": policy(),
                "selected_sha256": digest(SELECTED.read_bytes()),
                "source_sha256": digest(SOURCE.read_bytes()),
                "driver_sha256": digest(Path(__file__).read_bytes())}
    atomic_json(folder / "manifest.json", manifest)
    audit(folder / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen bpRNA origin binding:", folder / "manifest.json")


def metadata(name, sql_id, description):
    match = re.search(r"Original Name: (.*?)(?:, Original Accession ID:| Desc:|$)", description)
    original = match.group(1) if match else None
    accession = re.search(r"Original Accession ID: ([^,]+)", description)
    family = RFAM_ORIGIN.fullmatch(original or "") if name.startswith("bpRNA_RFAM_") else None
    return {"sql_rna_id": sql_id, "sql_name": name, "original_name": original,
            "original_accession_id": accession.group(1) if accession else None,
            "rfam_family_id": family.group(1) if family else None,
            "rfam_member_id": family.group(2) if family else None}


def compute(selected):
    by_name = {r["id"]: r for r in selected}
    by_hash = {}
    for record in selected:
        by_hash.setdefault(record["sequence_sha256"], []).append(record)
    matches = {r["id"]: [] for r in selected}
    same_name = {r["id"]: [] for r in selected}
    parsed = 0
    with zipfile.ZipFile(SOURCE) as archive, archive.open(SQL_MEMBER) as stream:
        for line in stream:
            found = ROW.search(line)
            if not found:
                continue
            parsed += 1
            sql_id = int(found.group(1))
            name = found.group(2).decode()
            description = found.group(3).replace(b"''", b"'").decode()
            sequence = found.group(4).upper()
            sha = hashlib.sha256(sequence).hexdigest()
            if name in same_name:
                same_name[name].append({"sql_rna_id": sql_id,
                                        "sequence_sha256": sha,
                                        "length_nt": len(sequence),
                                        "sequence_matches_selected": sha == by_name[name]["sequence_sha256"]})
            for record in by_hash.get(sha, []):
                if not name.startswith("bpRNA_" + record["source_group"] + "_"):
                    continue
                if sequence.decode() != record["sequence"]:
                    raise ValueError("Sequence hash collision in origin binding")
                matches[record["id"]].append(metadata(name, sql_id, description))
    rows = []
    for record in selected:
        name = record["id"]
        options = sorted(matches[name], key=lambda row: (row["sql_name"], row["rfam_family_id"] or ""))
        if not options:
            raise ValueError(f"No sequence-bound SQL origin for {name}")
        if record["source_group"] == "CRW" and not any(row["sql_name"] == name for row in options):
            raise ValueError(f"CRW origin identity differs: {name}")
        if record["source_group"] == "RFAM" and any(not row["rfam_family_id"] for row in options):
            raise ValueError(f"RFAM family missing in SQL origin: {name}")
        rows.append({"id": name, "source_group": record["source_group"],
                     "sequence_sha256": record["sequence_sha256"],
                     "length_nt": len(record["sequence"]),
                     "same_numeric_id_sql_rows": same_name[name],
                     "sequence_bound_origins": options,
                     "same_name_and_sequence_origin": next((row for row in options
                                                            if row["sql_name"] == name), None),
                     "rfam_family_ids": sorted({row["rfam_family_id"] for row in options
                                               if row["rfam_family_id"]}),
                     "family_assignment_ambiguous": len({row["rfam_family_id"] for row in options
                                                         if row["rfam_family_id"]}) > 1})
    return {"records": rows, "selected_count": len(rows), "parsed_sql_rows": parsed,
            "crw_origin_bound_count": sum(r["source_group"] == "CRW" for r in rows),
            "rfam_unique_family_count": sum(r["source_group"] == "RFAM" and
                                            len(r["rfam_family_ids"]) == 1 for r in rows),
            "rfam_ambiguous_family_count": sum(r["family_assignment_ambiguous"] for r in rows),
            "same_numeric_id_mismatch_count": sum(any(not x["sequence_matches_selected"]
                                                       for x in r["same_numeric_id_sql_rows"])
                                                  for r in rows),
            "development_only": True, "independent_test_claim": False}


def execute():
    manifest, selected = audit(PROTOCOL)
    folder = ROOT / "results/bprna_long_origin_binding_v2_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    atomic_json(folder / "protocol.json", manifest)
    result = {"complete": True, "run_dir": str(folder), **compute(selected)}
    atomic_json(folder / "summary.json", result)
    print("bpRNA long origin binding:", folder / "summary.json")
    print("RFAM unique/ambiguous:", result["rfam_unique_family_count"],
          result["rfam_ambiguous_family_count"])
    print("Same-numeric-ID SQL mismatches:", result["same_numeric_id_mismatch_count"])


def verify_run(path):
    folder = Path(path).resolve().parent
    _, selected = audit(folder / "protocol.json")
    expected = {"complete": True, "run_dir": str(folder), **compute(selected)}
    if json.loads(Path(path).read_text()) != expected:
        raise ValueError("Origin-binding run replay differs")
    print("bpRNA long origin-binding run replay passed")


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
        print("bpRNA origin-binding protocol replay passed")


if __name__ == "__main__":
    main()
