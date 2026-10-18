#!/usr/bin/env python3
"""Supplement frozen CRW results with hit coverage and panel exposure checks."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.artifacts import timestamp
from rnastable.native_journal import atomic_json
from rnastable.reference import digest
from audit_crw_rfam_batch_results import verify as verify_batch
from audit_bprna_candidate_clans import parse_seed, SOURCE

BATCH = ROOT / "results/crw_rfam_batch_result_audit_runs/20261018T221637.760541Z/summary.json"
PANEL = ROOT / "results/bprna_five_clan_feasibility_protocol_runs/20261017T191211.629652Z/selection.json"
CANDIDATES = ROOT / "results/bprna_candidate_clans_runs/20261017T190647.643559Z/summary.json"


def summarize(records, panel, candidates):
    families, clans, rows = set(), set(), []
    for record in records:
        if record["status"] != "completed" or not record["sequence_verified"]:
            raise ValueError("Every CRW response must be completed and sequence-bound")
        hits = []
        for hit in record["hits"]:
            start, end = hit["start"], hit["end"]
            if not 1 <= min(start, end) <= max(start, end) <= record["length_nt"]:
                raise ValueError("Hit coordinates outside query sequence")
            strong = hit["evalue"] <= 1e-5
            hits.append({**hit, "query_span_nt": abs(end - start) + 1,
                         "query_span_fraction": (abs(end - start) + 1) / record["length_nt"],
                         "included_as_possible_exposure": strong})
            if strong:
                families.add(hit["family_id"])
                if hit["clan_id"]:
                    clans.add(hit["clan_id"])
        rows.append({"id": record["id"], "length_nt": record["length_nt"], "hits": hits})

    def overlap(item):
        return item["family_id"] in families or (item["clan_id"] is not None
                                                   and item["clan_id"] in clans)

    return {"policy": {"evalue_max": 1e-5, "all_significant_hits_are_possible_exposures": True,
                       "query_span_is_not_full_length_lineage_assignment": True,
                       "unassigned_clan_means_independent": False,
                       "independent_test_claim": False, "model_inference_performed": False},
            "records": rows, "possible_exposed_families": sorted(families),
            "possible_exposed_clans": sorted(clans),
            "panel_reference_count": len(panel),
            "panel_overlap_count": sum(overlap(r) for r in panel),
            "candidate_family_overlaps": [r["family_id"] for r in candidates if overlap(r)],
            "full_length_lineage_gate_satisfied": False,
            "reason": "Short local hits do not resolve whole-record lineage; absence of panel overlap is not proof of independence."}


def compute():
    verify_batch(BATCH)
    batch = json.loads(BATCH.read_text())
    seed = parse_seed()
    for record in batch["records"]:
        for hit in record["hits"]:
            if seed[hit["family_id"]]["clan_id"] != hit["clan_id"]:
                raise ValueError("Saved hit clan differs from pinned release")
    panel = json.loads(PANEL.read_text())["selected"]
    candidates = json.loads(CANDIDATES.read_text())["families"]
    return summarize(batch["records"], panel, candidates)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--verify-run", type=Path)
    args = parser.parse_args()
    paths = (BATCH, PANEL, CANDIDATES, SOURCE, Path(__file__).resolve())
    if args.run:
        folder = ROOT / "results/crw_panel_exposure_runs" / timestamp()
        folder.mkdir(parents=True, exist_ok=False)
        manifest = {"inputs_sha256": {str(p): digest(p.read_bytes()) for p in paths}}
        atomic_json(folder / "manifest.json", manifest)
        result = {"complete": True, "run_dir": str(folder), **compute()}
        atomic_json(folder / "summary.json", result)
        print(folder / "summary.json")
        print("Panel overlaps:", result["panel_overlap_count"])
        print("Candidate family overlaps:", result["candidate_family_overlaps"])
    else:
        folder = args.verify_run.resolve().parent
        manifest = json.loads((folder / "manifest.json").read_text())
        if manifest != {"inputs_sha256": {str(p): digest(p.read_bytes()) for p in paths}}:
            raise ValueError("Supplementary audit inputs differ")
        expected = {"complete": True, "run_dir": str(folder), **compute()}
        if json.loads(args.verify_run.read_text()) != expected:
            raise ValueError("Supplementary audit replay differs")
        print("CRW panel exposure replay passed")


if __name__ == "__main__":
    main()
