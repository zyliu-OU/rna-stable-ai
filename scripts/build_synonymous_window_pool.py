#!/usr/bin/env python3
"""Enumerate the windowed synonymous design space into finite pools.

The user chose on 2026-10-20 that the optimisation domain is synonymous edits
confined to a window at the 5' end of the Fluc ORF. This builds that pool under
`configs/synonymous_window_design_space_v1_2026-10-20.json` and records it.

Both GC modes are built, because free mode leaves window GC strongly correlated
with edit distance and neutral mode removes that by construction at the cost of
a much smaller space. Recording both lets the choice be made on the measurement.

It scores nothing. `new_sequence_scoring_enabled` and
`expression_candidate_design_enabled` are both false in gate v5, so no structure,
stability or translation value is computed, no optimizer feature matrix is
emitted, and no member is proposed as an assay candidate. The driver refuses to
run if either switch has been opened, because a real campaign needs its own
entry point rather than this one.
"""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import hashlib
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.synonymous_window import build_pool, split_codons, translate

SPEC = ROOT / "configs/synonymous_window_design_space_v1_2026-10-20.json"
GATE = ROOT / "configs/stage2_to_stage3_gate_v5_2026-10-20.json"
FORMULATION = ROOT / "configs/pareto_objective_formulation_v1_2026-10-20.json"
MODES = ("free", "neutral")


def correlation(xs, ys):
    """Pearson r, or None when a variable is constant and r is undefined."""
    if len(set(xs)) < 2 or len(set(ys)) < 2:
        return None
    return statistics.correlation(xs, ys)


def verify(pool, reference_codons, window_codons, max_homopolymer):
    """Re-check every member here rather than trusting the generator."""
    protein = translate(reference_codons)
    allowed = set(pool["window_codon_indices"])
    failures = []
    for member in pool["members"]:
        codons = member["codons"]
        if translate(codons) != protein:
            failures.append((member["member"], "protein_changed"))
        if len(codons) != len(reference_codons):
            failures.append((member["member"], "length_changed"))
        changed = {i for i, (a, b) in enumerate(zip(reference_codons, codons)) if a != b}
        if changed - allowed:
            failures.append((member["member"], "change_outside_window"))
        if member["longest_homopolymer"] > max_homopolymer:
            failures.append((member["member"], "homopolymer_run_too_long"))
        sequence = "".join(codons)
        if member["orf_sha256"] != hashlib.sha256(sequence.encode()).hexdigest():
            failures.append((member["member"], "hash_mismatch"))
    hashes = {member["orf_sha256"] for member in pool["members"]}
    if len(hashes) != len(pool["members"]):
        failures.append((None, "duplicate_members"))
    if not pool["members"][0]["is_reference"] or pool["members"][0]["substitution_count"]:
        failures.append((0, "member_zero_is_not_the_reference"))
    return failures


def summarise(pool):
    members = pool["members"]
    subs = [m["substitution_count"] for m in members]
    window_gc = [m["window_gc_fraction"] for m in members]
    return {
        "size": pool["size"],
        "gc_mode": pool["gc_mode"],
        "substitutable_positions": pool["substitutable_positions"],
        "substitution_count_range": [min(subs), max(subs)],
        "distinct_substitution_counts": len(set(subs)),
        "window_gc_range": [min(window_gc), max(window_gc)],
        "window_gc_is_constant": len(set(window_gc)) == 1,
        "pearson_substitutions_vs_window_gc": correlation(subs, window_gc),
        "pearson_substitutions_vs_orf_gc3": correlation(
            subs, [m["orf_gc3_fraction"] for m in members]),
        "attempts": pool["attempts"],
        "rejected": pool["rejected"],
        "unique_members": len({m["orf_sha256"] for m in members}),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--out", default="results/synonymous_window_pool_runs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    spec = json.loads(SPEC.read_text())
    gate = json.loads(GATE.read_text())
    if gate["new_sequence_scoring_enabled"] or gate["expression_candidate_design_enabled"]:
        raise SystemExit("Gate opened a campaign switch; this enumeration driver is not "
                         "the right entry point for scoring or candidate selection")

    cds = "".join((ROOT / spec["reference"]["orf"]).read_text().split())
    reference = split_codons(cds)
    if len(reference) != spec["reference"]["codon_count"]:
        raise SystemExit(f"Reference codon count differs: {len(reference)}")
    window_codons = spec["window"]["codons"]
    max_homopolymer = spec["constraints"]["max_homopolymer_run"]

    pools, summaries, all_failures = {}, {}, {}
    for mode in MODES:
        pool = build_pool(cds, window_codons=window_codons, size=args.size,
                          seed=spec["sampling"]["seed"], max_homopolymer=max_homopolymer,
                          gc_mode=mode)
        failures = verify(pool, reference, window_codons, max_homopolymer)
        pools[mode], summaries[mode], all_failures[mode] = pool, summarise(pool), failures
        stats = summaries[mode]
        r = stats["pearson_substitutions_vs_window_gc"]
        print(f"{mode:<8} n={stats['size']:<4} subs {stats['substitution_count_range'][0]}"
              f"..{stats['substitution_count_range'][1]:<3} "
              f"windowGC {stats['window_gc_range'][0]:.4f}..{stats['window_gc_range'][1]:.4f}  "
              f"r={'constant' if r is None else format(r, '+.4f')}  "
              f"substitutable {stats['substitutable_positions']:<3} "
              f"rejected {stats['rejected']}  failures {len(failures)}", flush=True)

    payload = {
        "purpose": ("The windowed synonymous design space, enumerated into finite pools. "
                    "A specification of the optimisation domain, not a candidate set."),
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "specification": str(SPEC.relative_to(ROOT)),
        "formulation": str(FORMULATION.relative_to(ROOT)),
        "gate": str(GATE.relative_to(ROOT)),
        "reference_orf_sha256": pools["free"]["reference_orf_sha256"],
        "protein_sha256": pools["free"]["protein_sha256"],
        "orf_length_nt": pools["free"]["orf_length_nt"],
        "codon_count": pools["free"]["codon_count"],
        "window_codons": window_codons,
        "window_codon_indices": pools["free"]["window_codon_indices"],
        "max_homopolymer": max_homopolymer,
        "seed": spec["sampling"]["seed"],
        "per_mode": summaries,
        "verification_failures": {mode: failures for mode, failures in all_failures.items()},
        "all_members_verified": all(not failures for failures in all_failures.values()),
        "protein_preserved_on_every_member": True,
        "scored": False,
        "optimizer_features_emitted": False,
        "candidates_proposed_for_assay": False,
        "gc_confound": {
            "free_mode_pearson_substitutions_vs_window_gc":
                summaries["free"]["pearson_substitutions_vs_window_gc"],
            "neutral_mode_window_gc_is_constant": summaries["neutral"]["window_gc_is_constant"],
            "why": ("The reference 5' window is GC-maximal for this protein segment, so every "
                    "synonymous edit moves GC down or sideways. The correlation is a property "
                    "of editing away from a GC-optimised reference, not a sampler artifact, "
                    "and sampling cannot remove it in free mode."),
            "consequence": ("In free mode edit distance and GC content cannot be separated; "
                            "any effect attributed to one could be the other. Neutral mode "
                            "removes the confound by construction and costs space."),
            "which_is_primary": "not decided; both are recorded so the choice rests on these numbers",
        },
        "no_claim": [
            "Specifying a design space establishes no stability, translation or expression benefit.",
            "No member was scored, ranked or proposed for an assay.",
            "The 30-codon window and the 5' region are declared choices, not findings of this project.",
            "A free-mode pool cannot separate edit distance from GC content.",
            "Protein preservation is verified; nothing else about a member is verified.",
        ],
    }

    print(f"\nall members verified: {payload['all_members_verified']}")
    if args.dry_run:
        print("\nDry run: nothing written.", file=sys.stderr)
        return 0
    if not payload["all_members_verified"]:
        raise SystemExit("Verification failed; refusing to write a pool")
    out = ROOT / args.out / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True, exist_ok=False)
    (out / "summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    for mode in MODES:
        members = [{k: v for k, v in member.items() if k != "codons"}
                   | {"orf": "".join(member["codons"])} for member in pools[mode]["members"]]
        (out / f"pool_{mode}.json").write_text(json.dumps(
            {"gc_mode": mode, "window_codon_indices": pools[mode]["window_codon_indices"],
             "members": members}, indent=2, sort_keys=True))
    print(f"\nWrote {out}/summary.json and pool_free.json, pool_neutral.json", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
