#!/usr/bin/env python3
"""Replay sequence alignments to accession context for two CRW group II records."""

import argparse
import json
from pathlib import Path
import sys

import Bio
from Bio import Align, SeqIO

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.artifacts import timestamp
from rnastable.native_journal import atomic_json
from rnastable.reference import digest
from bind_bprna_long_origin_metadata import verify_run as verify_origin

ORIGIN = ROOT / "results/bprna_long_origin_binding_v2_runs/20261017T185531.913009Z/summary.json"
SELECTED = ROOT / "results/bprna_long_training_smoke_runs/20261017T033749.792816Z/selection.json"
SOURCE = ROOT / "results/crw_original_provenance_source_runs/20261018T221853.357057Z"
TARGETS = {"bpRNA_CRW_54679": "Z48620.1", "bpRNA_CRW_54684": "V00694.1"}


def alignment_evidence(reference, query):
    aligner = Align.PairwiseAligner(mode="local", match_score=2, mismatch_score=-3,
                                   open_gap_score=-5, extend_gap_score=-0.5)
    alignment = aligner.align(reference, query)[0]
    coords = alignment.coordinates.tolist()
    identities = mismatches = insertions = deletions = 0
    for index in range(len(coords[0]) - 1):
        a, b = coords[0][index:index + 2]
        c, d = coords[1][index:index + 2]
        if b > a and d > c:
            if b - a != d - c:
                raise ValueError("Invalid alignment block")
            same = sum(x == y for x, y in zip(reference[a:b], query[c:d]))
            identities += same
            mismatches += b - a - same
        elif d > c:
            insertions += d - c
        else:
            deletions += b - a
    return {"score": alignment.score, "coordinates_zero_based_half_open": coords,
            "identities": identities, "mismatches": mismatches,
            "query_inserted_bases": insertions, "query_deleted_bases": deletions,
            "query_aligned_nt": coords[1][-1] - coords[1][0],
            "query_unaligned_prefix_nt": coords[1][0],
            "query_unaligned_suffix_nt": len(query) - coords[1][-1],
            "exact_full_query_substring": query in reference}


def compute():
    verify_origin(ORIGIN)
    origins = {r["id"]: r for r in json.loads(ORIGIN.read_text())["records"]}
    selected = {r["id"]: r for r in json.loads(SELECTED.read_text())["selected"]}
    retrieval = json.loads((SOURCE / "retrieval.json").read_text())
    sources = {r["filename"]: r for r in retrieval["sources"] if "sha256" in r}
    rows = []
    for record_id, accession in TARGETS.items():
        name = accession.split(".")[0] + ".gb"
        path = SOURCE / name
        if digest(path.read_bytes()) != sources[name]["sha256"]:
            raise ValueError("Retrieved accession hash differs")
        reference = SeqIO.read(path, "genbank")
        origin = origins[record_id]["same_name_and_sequence_origin"]
        query = selected[record_id]
        if (reference.id != accession or origin["original_accession_id"] != accession.split(".")[0]
                or origins[record_id]["sequence_sha256"] != query["sequence_sha256"]
                or digest(query["sequence"].encode()) != query["sequence_sha256"]):
            raise ValueError("Accession or selected sequence binding differs")
        evidence = alignment_evidence(str(reference.seq).upper().replace("T", "U"), query["sequence"])
        reference_coords = evidence["coordinates_zero_based_half_open"][0]
        start, end = reference_coords[0], reference_coords[-1]
        introns = []
        for feature in reference.features:
            if feature.type != "intron":
                continue
            left, right = int(feature.location.start), int(feature.location.end)
            overlap = max(0, min(end, right) - max(start, left))
            if overlap:
                introns.append({"reference_start_zero_based": left, "reference_end_exclusive": right,
                                "qualifiers": feature.qualifiers, "overlap_span_nt": overlap,
                                "entire_annotated_intron_within_alignment_span": overlap == right - left})
        if not origin["original_name"].startswith("a.I2.") or not introns:
            raise ValueError("Expected archived intron provenance absent")
        rows.append({"id": record_id, "length_nt": len(query["sequence"]),
                     "sequence_sha256": query["sequence_sha256"], "archived_origin": origin,
                     "accession_version": reference.id, "accession_description": reference.description,
                     "source_url": sources[name]["url"], "alignment": evidence,
                     "overlapping_intron_features": introns,
                     "broad_provenance_supported": "group_II_intron",
                     "formal_full_length_rfam_assignment": False,
                     "independent_validation_eligible": False})
    return {"records": rows, "policy": {
        "alignment": "first_optimal_local_forward_alignment",
        "match": 2, "mismatch": -3, "gap_open": -5, "gap_extend": -0.5,
        "coordinates": "zero_based_half_open",
        "alignment_is_exact_sequence_identity": False,
        "broad_group_II_provenance_basis": "sequence_bound_CRW_I2_name_plus_accession_intron_context",
        "family_assignment_from_name_alone": False,
        "future_independent_panels": "quarantine_these_records_and_group_II_homologs_pending_formal_lineage",
        "existing_frozen_studies_reclassified": False, "model_inference_performed": False}}


def fingerprints():
    paths = [ORIGIN, SELECTED, SOURCE / "retrieval.json", SOURCE / "Z48620.gb",
             SOURCE / "V00694.gb", Path(__file__).resolve()]
    return {"inputs_sha256": {str(p): digest(p.read_bytes()) for p in paths},
            "biopython_version": Bio.__version__}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--verify-run", type=Path)
    args = parser.parse_args()
    if args.run:
        folder = ROOT / "results/crw_original_provenance_audit_runs" / timestamp()
        folder.mkdir(parents=True, exist_ok=False)
        atomic_json(folder / "manifest.json", fingerprints())
        atomic_json(folder / "summary.json", {"complete": True, "run_dir": str(folder), **compute()})
        print(folder / "summary.json")
    else:
        folder = args.verify_run.resolve().parent
        if json.loads((folder / "manifest.json").read_text()) != fingerprints():
            raise ValueError("Original provenance audit input or software version differs")
        expected = {"complete": True, "run_dir": str(folder), **compute()}
        if json.loads(args.verify_run.read_text()) != expected:
            raise ValueError("Original provenance audit replay differs")
        print("CRW original provenance replay passed")


if __name__ == "__main__":
    main()
