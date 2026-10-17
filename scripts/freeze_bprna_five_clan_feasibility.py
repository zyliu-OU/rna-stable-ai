#!/usr/bin/env python3
"""Freeze a label-blind five-clan bpRNA feasibility panel under 5000 nt."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp  # noqa: E402
from rnastable.native_journal import atomic_json  # noqa: E402
from rnastable.reference import digest  # noqa: E402

CLANS = ROOT / "results/bprna_candidate_clans_runs/20261017T190647.643559Z/summary.json"
BINDING = ROOT / "results/bprna_candidate_sequence_binding_runs/20261017T190750.775148Z/summary.json"
PROTOCOL = ROOT / "results/bprna_five_clan_feasibility_protocol.json"


def policy():
    return {"stage": "conditional_five_clan_comparative_feasibility",
            "length_nt": [400, 4999], "families_per_clan": 1,
            "family_choice": "maximum_provisional_candidate_count_then_family_id",
            "sequences_per_family_max": 3,
            "sequence_choice": "evenly_spaced_by_length_then_sha256",
            "duplicate_source_structures": "retain_all_do_not_choose_by_label",
            "source_structure_labels_read": False,
            "crw_lineage_gate_satisfied": False,
            "independent_test_claim": False,
            "model_inference_authorized": False}


def plan():
    clan_data = json.loads(CLANS.read_text())
    binding = json.loads(BINDING.read_text())
    if (clan_data["family_status_counts"].get("distinct_known_clan") != 10
            or binding["sequence_bound_count"] != 433):
        raise ValueError("Clan or source binding inventory changed")
    by_clan = {}
    for family in clan_data["families"]:
        if family["status"] == "distinct_known_clan":
            by_clan.setdefault(family["clan_id"], []).append(family)
    if len(by_clan) != 5:
        raise ValueError("Five-clan candidate inventory changed")
    records = binding["records"]
    selected = []
    decisions = []
    for clan in sorted(by_clan):
        family = sorted(by_clan[clan], key=lambda r: (-r["candidate_count"], r["family_id"]))[0]
        choices = sorted((r for r in records if r["family_id"] == family["family_id"]),
                         key=lambda r: (r["length_nt"], r["sequence_sha256"]))
        count = min(policy()["sequences_per_family_max"], len(choices))
        positions = [0] if count == 1 else [round(i * (len(choices) - 1) / (count - 1))
                                               for i in range(count)]
        if len(set(positions)) != count:
            raise ValueError("Repeated metadata selection position")
        decisions.append({"clan_id": clan, "family_id": family["family_id"],
                          "candidate_count": len(choices), "selected_positions": positions})
        for index in positions:
            record = choices[index]
            if (record["clan_status"] != "distinct_known_clan"
                    or not 400 <= record["length_nt"] <= 4999
                    or not record["source_matches"]):
                raise ValueError("Selected record violates label-blind policy")
            selected.append({"clan_id": clan, "family_id": family["family_id"],
                             "sql_name": record["sql_name"],
                             "sequence_sha256": record["sequence_sha256"],
                             "length_nt": record["length_nt"],
                             "source_matches": record["source_matches"]})
    return {"selected": selected, "decisions": decisions,
            "selected_count": len(selected), "selected_clan_count": len(by_clan),
            "structure_labels_read": False, "independent_test_claim": False}


def audit(path):
    manifest = json.loads(Path(path).read_text())
    folder = Path(manifest["run_dir"])
    if (manifest != json.loads((folder / "manifest.json").read_text())
            or manifest["policy"] != policy()
            or manifest["driver_sha256"] != digest(Path(__file__).read_bytes())
            or manifest["clan_sha256"] != digest(CLANS.read_bytes())
            or manifest["binding_sha256"] != digest(BINDING.read_bytes())
            or manifest["selection_sha256"] != digest((folder / "selection.json").read_bytes())
            or json.loads((folder / "selection.json").read_text()) != plan()):
        raise ValueError("Five-clan feasibility protocol differs")
    return manifest


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError(PROTOCOL)
    selection = plan()
    folder = ROOT / "results/bprna_five_clan_feasibility_protocol_runs" / timestamp()
    folder.mkdir(parents=True, exist_ok=False)
    atomic_json(folder / "selection.json", selection)
    manifest = {"run_dir": str(folder), "policy": policy(),
                "clan_sha256": digest(CLANS.read_bytes()),
                "binding_sha256": digest(BINDING.read_bytes()),
                "driver_sha256": digest(Path(__file__).read_bytes()),
                "selection_sha256": digest((folder / "selection.json").read_bytes())}
    atomic_json(folder / "manifest.json", manifest)
    audit(folder / "manifest.json")
    atomic_json(PROTOCOL, manifest)
    print("Frozen five-clan feasibility plan:", folder / "manifest.json")
    print("Selected:", selection["selected_count"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--verify-protocol", type=Path)
    args = parser.parse_args()
    if args.freeze:
        freeze()
    else:
        audit(args.verify_protocol)
        print("Five-clan feasibility protocol replay passed")


if __name__ == "__main__":
    main()
