#!/usr/bin/env python3
"""Audit saved Rfam batch responses against seven exact CRW training sequences."""

import argparse
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

SELECTED = ROOT / "results/bprna_long_training_smoke_runs/20261017T033749.792816Z/selection.json"
FIRST = ROOT / "results/crw_rfam_13049_completed_response.json"
FOLDER = ROOT / "results/crw_rfam_batch_protocol_runs/20261017T190950.011534Z"
JOBS = FOLDER / "jobs.json"
PROTOCOL = ROOT / "results/crw_rfam_batch_result_audit_protocol.json"


def source_records():
    records = {r["id"]: r for r in json.loads(SELECTED.read_text())["selected"]
               if r["source_group"] == "CRW"}
    if len(records) != 7:
        raise ValueError("CRW training inventory changed")
    return records


def policy():
    return {"sequence_match": "uppercase_exact_full_sequence",
            "completion": "nonempty_searchSequence_and_closed_and_matching_jobId",
            "all_hits_retained": True, "evalue_filter_for_clan_summary": 1e-5,
            "empty_response_means_zero_hits": False,
            "single_family_claim_from_multiple_hits": False,
            "model_inference_performed": False}


def audit(path):
    manifest = json.loads(Path(path).read_text())
    folder = Path(manifest["run_dir"])
    if (manifest != json.loads((folder / "manifest.json").read_text())
            or manifest["policy"] != policy()
            or manifest["driver_sha256"] != digest(Path(__file__).read_bytes())):
        raise ValueError("CRW batch audit protocol differs")
    for name, sha in manifest["inputs_sha256"].items():
        if digest(Path(name).read_bytes()) != sha:
            raise ValueError(f"CRW batch audit input changed: {name}")
    source_records()
    return manifest


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    records = source_records()
    jobs = json.loads(JOBS.read_text())["jobs"]
    if set(jobs) != set(records) - {"bpRNA_CRW_13049"}:
        raise ValueError("CRW job inventory differs")
    folder = ROOT / "results/crw_rfam_batch_result_audit_protocol_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {"run_dir": str(folder), "policy": policy(),
                "inputs_sha256": {str(p): digest(p.read_bytes())
                                  for p in (SELECTED, FIRST, JOBS)},
                "driver_sha256": digest(Path(__file__).read_bytes())}
    atomic_json(folder / "manifest.json", manifest)
    audit(folder / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen CRW result audit:", folder / "manifest.json")


def classify(record_id, job_id, response, seed):
    record = source_records()[record_id]
    if response.get("jobId") != job_id:
        raise ValueError("Rfam job identity differs")
    sequence = response.get("searchSequence", "")
    if not sequence or not response.get("closed"):
        return {"id": record_id, "job_id": job_id, "status": "pending_or_unavailable",
                "sequence_verified": False, "family_assignment_claim": False,
                "observed_empty_result": not bool(sequence)}
    if (sequence != record["sequence"]
            or hashlib.sha256(sequence.encode()).hexdigest() != record["sequence_sha256"]):
        raise ValueError("Rfam response sequence differs from submitted CRW record")
    hits = []
    for name, group in response.get("hits", {}).items():
        for hit in group:
            family = hit["acc"]
            if family not in seed or seed[family]["name"] != hit["id"]:
                raise ValueError("Rfam hit absent from release 15.1 seed archive")
            hits.append({"family_id": family, "family_name": name,
                         "clan_id": seed[family]["clan_id"],
                         "start": hit["start"], "end": hit["end"],
                         "score": hit["score"], "evalue": hit["E"]})
    if len(hits) != response.get("numHits"):
        raise ValueError("Rfam hit count differs")
    hits.sort(key=lambda h: (h["evalue"], -h["score"], h["family_id"]))
    strong = [h for h in hits if h["evalue"] <= policy()["evalue_filter_for_clan_summary"]]
    clans = sorted({h["clan_id"] for h in strong if h["clan_id"]})
    return {"id": record_id, "job_id": job_id, "status": "completed",
            "sequence_verified": True, "length_nt": len(sequence),
            "returned_hit_count": len(hits), "hits": hits,
            "strong_hit_clans": clans,
            "single_strong_clan": clans[0] if len(clans) == 1 else None,
            "unique_strong_family_hit": len({h["family_id"] for h in strong}) == 1,
            "family_assignment_claim": False}


def compute(response_dir):
    seed = parse_seed()
    jobs = json.loads(JOBS.read_text())["jobs"]
    jobs["bpRNA_CRW_13049"] = "infernal_cmscan-R20261017-195709-0511-4231837-p1m"
    rows = []
    paths = {}
    for record_id, job_id in sorted(jobs.items()):
        path = FIRST if record_id == "bpRNA_CRW_13049" else response_dir / (record_id + ".json")
        if not path.exists():
            rows.append({"id": record_id, "job_id": job_id,
                         "status": "no_saved_response", "sequence_verified": False,
                         "family_assignment_claim": False})
            continue
        paths[str(path)] = digest(path.read_bytes())
        rows.append(classify(record_id, job_id, json.loads(path.read_text()), seed))
    return {"policy": policy(), "response_sha256": paths, "records": rows,
            "completed_count": sum(r["status"] == "completed" for r in rows),
            "single_strong_clan_count": sum(bool(r.get("single_strong_clan")) for r in rows),
            "all_completed": all(r["status"] == "completed" for r in rows)}


def run(response_dir):
    manifest = audit(PROTOCOL)
    response_dir = Path(response_dir).resolve()
    folder = ROOT / "results/crw_rfam_batch_result_audit_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    atomic_json(folder / "protocol.json", manifest)
    result = {"complete": True, "run_dir": str(folder),
              "response_dir": str(response_dir), **compute(response_dir)}
    atomic_json(folder / "summary.json", result)
    print("CRW result audit:", folder / "summary.json")
    print("Completed:", result["completed_count"], "of 7")


def verify(path):
    folder = Path(path).resolve().parent
    audit(folder / "protocol.json")
    saved = json.loads(Path(path).read_text())
    expected = {"complete": True, "run_dir": str(folder),
                "response_dir": saved["response_dir"],
                **compute(Path(saved["response_dir"]))}
    if saved != expected:
        raise ValueError("CRW result audit replay differs")
    print("CRW result audit replay passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--run", type=Path)
    mode.add_argument("--verify-run", type=Path)
    args = parser.parse_args()
    if args.freeze:
        freeze()
    elif args.run:
        run(args.run)
    else:
        verify(args.verify_run)


if __name__ == "__main__":
    main()
