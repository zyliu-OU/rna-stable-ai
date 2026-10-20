#!/usr/bin/env python3
"""Constraint-decoder, resource and replay checks for the native path.

Gate requirement 5 is "Pass_constraint_decoder_resource_and_replay_checks". It
was written when the learned pair model was the structure component, and its
replay leg meant reloading learned checkpoints. Those checkpoints were deleted
on 2026-10-20 when the model was retired, so that leg is permanently unrunnable
as written. The project's structure now comes from LinearFold and ViennaRNA, so
this re-scopes all three legs onto the components actually relied upon:

- replay: re-fold the frozen long native-control cohort and require the frozen
  structures and energies to reproduce exactly, from the recorded config.
- constraint decoder: fold under hard constraints derived from the reference
  pairs and require every enforced pair to appear in the returned structure,
  for BOTH native controls, plus a negative control per tool proving a
  constraint that cannot be met is refused rather than silently dropped.
- resource: report measured wall time and peak RSS per method and length band
  against the limits in the frozen config.

Two things this does not do. It does not restore the learned-model replay leg,
which no longer has an artifact to replay. And passing these checks is evidence
for a gate review, not a finding that the requirement is satisfied.

Constraint-string conventions differ between the two tools and are not
interchangeable: ViennaRNA treats '.' as unconstrained, LinearFold treats '.'
as forced-unpaired and '?' as unconstrained. Using one tool's convention with
the other silently changes the question being asked, so each is built with its
own filler character.
"""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from rnastable.folding import fold_sequence, parse_output, run_bounded, tool_commands
from rnastable.pair_model import CANONICAL
from rnastable.scoring import base_pairs
from evaluate_long_native_controls import CONFIG, COHORT, METHODS

FROZEN = ROOT / "results/long_native_controls_runs/20261017T034318.804594Z/rows.json"
BANDS = (("1_999", 1, 1000), ("1000_1999", 1000, 2000), ("2000_2999", 2000, 3000))
# Unconstrained filler per tool. These are not interchangeable; see the module
# docstring.
UNCONSTRAINED = {"ViennaRNA": ".", "LinearFold": "?"}
MAX_ENFORCED_PAIRS = 20


def cohort_records():
    records = json.loads((COHORT / "selection.json").read_text())["selected"]
    if len(records) != 11:
        raise SystemExit(f"Expected the frozen 11-record cohort, found {len(records)}")
    return records


def constraint_string(record, method, limit=MAX_ENFORCED_PAIRS):
    """Hard constraints from the reference pairs, deterministically chosen.

    Only canonical pairs wide enough to be foldable are enforced, because a
    pair the thermodynamic model cannot form at all tests the tool's refusal
    path rather than its decoder. Pairs are taken in position order and capped,
    so the string is reproducible and the fold stays bounded.
    """
    sequence = record["sequence"]
    legal = [(i, j) for i, j in sorted(map(tuple, record["pairs"]))
             if j - i >= 4 and sequence[i] + sequence[j] in CANONICAL]
    chosen, used = [], set()
    for i, j in legal:
        if len(chosen) >= limit:
            break
        # Nested, non-crossing and non-overlapping, so the string is a valid
        # dot-bracket that both decoders can parse.
        if i in used or j in used:
            continue
        if any(i < a < j < b or a < i < b < j for a, b in chosen):
            continue
        chosen.append((i, j))
        used.update((i, j))
    characters = [UNCONSTRAINED[method]] * len(sequence)
    for i, j in chosen:
        characters[i], characters[j] = "(", ")"
    return "".join(characters), chosen


def fold_constrained(method, sequence, constraint):
    """One constrained fold, under the same bounds as an unconstrained one."""
    commands = tool_commands(ROOT, CONFIG)
    if method == "ViennaRNA":
        command, cwd = [sys.executable, "-m", "rnastable.vienna_constraint_worker",
                        str(CONFIG["temperature_c"])], ROOT / "src"
    else:
        base, cwd = commands[method]
        command = [*base, "--constraints"]
    result = run_bounded(command, f"{sequence}\n{constraint}",
                         CONFIG["timeout_seconds"], CONFIG["memory_limit_gib"], cwd)
    output = result.pop("stdout", "")
    if result["status"] == "ok":
        try:
            result.update(parse_output(method, output, len(sequence)))
        except ValueError as exc:
            result.update(status="parse_error", error=str(exc))
    return result


def replay_check(records):
    """Re-fold the frozen cohort and require exact reproduction."""
    frozen = {(row["id"], row["method"]): row
              for row in json.loads(FROZEN.read_text())}
    rows, resources = [], []
    for index, record in enumerate(sorted(records, key=lambda r: r["id"]), 1):
        for method in METHODS:
            reference = frozen.get((record["id"], method))
            if reference is None:
                rows.append({"id": record["id"], "method": method,
                             "outcome": "absent_from_frozen_rows"})
                continue
            result = fold_sequence(ROOT, record["sequence"], CONFIG, method)
            expected = reference["fold"]
            same_structure = result.get("structure") == expected.get("structure")
            same_energy = result.get("mfe_kcal_mol") == expected.get("mfe_kcal_mol")
            rows.append({
                "id": record["id"], "method": method,
                "length_nt": len(record["sequence"]),
                "status": result["status"],
                "structure_reproduced": same_structure,
                "energy_reproduced": same_energy,
                "outcome": "ok" if (same_structure and same_energy) else "mismatch",
                "frozen_mfe_kcal_mol": expected.get("mfe_kcal_mol"),
                "replayed_mfe_kcal_mol": result.get("mfe_kcal_mol"),
            })
            if result["status"] == "ok":
                resources.append({"method": method, "length_nt": len(record["sequence"]),
                                  "wall_seconds": result["wall_seconds"],
                                  "peak_rss_mib": result.get("peak_rss_mib")})
        print(f"  replay [{index}/{len(records)}] {record['id'][:46]}", flush=True)
    return rows, resources


def constraint_check(records):
    """Enforced pairs must appear in the fold, and refusals must be refusals."""
    rows = []
    for index, record in enumerate(sorted(records, key=lambda r: r["id"]), 1):
        for method in METHODS:
            constraint, chosen = constraint_string(record, method)
            if not chosen:
                rows.append({"id": record["id"], "method": method,
                             "outcome": "no_enforceable_reference_pairs"})
                continue
            result = fold_constrained(method, record["sequence"], constraint)
            structure = result.get("structure")
            honoured = (sorted(base_pairs(structure)) if structure else [])
            missing = sorted(set(chosen) - set(honoured))
            rows.append({
                "id": record["id"], "method": method,
                "length_nt": len(record["sequence"]),
                "status": result["status"],
                "enforced_pairs": len(chosen),
                "enforced_pairs_absent_from_fold": len(missing),
                "outcome": "ok" if result["status"] == "ok" and not missing
                           else "constraint_not_honoured",
                "first_absent_pair": missing[0] if missing else None,
                "wall_seconds": result.get("wall_seconds"),
                "peak_rss_mib": result.get("peak_rss_mib"),
            })
        print(f"  constraints [{index}/{len(records)}] {record['id'][:42]}", flush=True)
    return rows


def refusal_check():
    """A pair that cannot be formed must be refused, not quietly dropped.

    ViennaRNA accepts an enforced pair that violates the minimum hairpin size,
    drops it, and returns a finite energy for a structure that does not contain
    it. The constraint worker therefore verifies satisfaction itself and exits
    non-zero. This check pins that behaviour for both tools, because a decoder
    that silently ignores a constraint would pass the check above by folding
    whatever it liked.
    """
    sequence = "GGGAAACCCUUUGGGAAACCC"
    rows = []
    for method in METHODS:
        filler = UNCONSTRAINED[method]
        # Positions 0 and 2 enclose a single base: below the minimum hairpin.
        constraint = "(" + filler + ")" + filler * (len(sequence) - 3)
        result = fold_constrained(method, sequence, constraint)
        structure = result.get("structure")
        honoured = (0, 2) in base_pairs(structure) if structure else False
        rows.append({
            "method": method,
            "constraint": constraint,
            "status": result["status"],
            "refused": result["status"] != "ok",
            "impossible_pair_reported_as_honoured": result["status"] == "ok"
                                                    and not honoured,
            "outcome": "refused" if result["status"] != "ok"
                       else ("honoured_unexpectedly" if honoured
                             else "silently_dropped"),
            "error": (result.get("error") or "").strip()[:300],
        })
    return rows


def resource_summary(resources, constraint_rows):
    def band_of(length):
        for name, low, high in BANDS:
            if low <= length < high:
                return name
        return "out_of_band"

    summary = {}
    for method in METHODS:
        by_band = defaultdict(lambda: {"wall": [], "rss": []})
        for row in resources:
            if row["method"] != method:
                continue
            bucket = by_band[band_of(row["length_nt"])]
            bucket["wall"].append(row["wall_seconds"])
            if row["peak_rss_mib"] is not None:
                bucket["rss"].append(row["peak_rss_mib"])
        constrained = [r["wall_seconds"] for r in constraint_rows
                       if r["method"] == method and r.get("wall_seconds") is not None]
        summary[method] = {
            "unconstrained_by_band": {
                name: {
                    "n": len(values["wall"]),
                    "max_wall_seconds": max(values["wall"]),
                    "mean_wall_seconds": statistics.fmean(values["wall"]),
                    "max_peak_rss_mib": max(values["rss"]) if values["rss"] else None,
                }
                for name, values in sorted(by_band.items())
            },
            "constrained_max_wall_seconds": max(constrained) if constrained else None,
            "limits_from_frozen_config": {
                "timeout_seconds": CONFIG["timeout_seconds"],
                "memory_limit_gib": CONFIG["memory_limit_gib"],
            },
        }
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--limit", type=int, default=0, help="cap records, for a smoke run")
    parser.add_argument("--out", default="results/native_path_requirement5_runs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    records = cohort_records()
    if args.limit:
        records = sorted(records, key=lambda r: r["id"])[:args.limit]

    print(f"records: {len(records)}  methods: {', '.join(METHODS)}")
    replay_rows, resources = replay_check(records)
    constraint_rows = constraint_check(records)
    refusal_rows = refusal_check()

    replay_ok = [r for r in replay_rows if r.get("outcome") == "ok"]
    constraint_ok = [r for r in constraint_rows if r.get("outcome") == "ok"]
    payload = {
        "purpose": ("Constraint-decoder, resource and replay checks re-scoped onto the "
                    "native controls the project relies on, for gate requirement 5."),
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "methods": list(METHODS),
        "config": CONFIG,
        "cohort": {
            "source": str(COHORT.relative_to(ROOT)),
            "records": len(records),
            "frozen_rows": str(FROZEN.relative_to(ROOT)),
        },
        "model_fitted": False,
        "learned_model_involved": False,
        "replay": {
            "checked": len(replay_rows),
            "reproduced_exactly": len(replay_ok),
            "passed": len(replay_ok) == len(replay_rows),
            "criterion": "dot-bracket structure AND MFE identical to the frozen row",
            "rows": replay_rows,
        },
        "constraint_decoder": {
            "checked": len(constraint_rows),
            "honoured": len(constraint_ok),
            "passed": len(constraint_ok) == len(constraint_rows),
            "criterion": ("every enforced reference pair present in the returned "
                          "structure, under the same time and memory bounds"),
            "maximum_enforced_pairs_per_record": MAX_ENFORCED_PAIRS,
            "conventions": UNCONSTRAINED,
            "rows": constraint_rows,
        },
        "refusal_control": {
            "passed": all(row["outcome"] == "refused" for row in refusal_rows),
            "criterion": ("a pair below the minimum hairpin size must be refused, not "
                          "dropped while a successful fold is reported"),
            "rows": refusal_rows,
        },
        "resources": resource_summary(resources, constraint_rows),
        "rescope_record": {
            "original_replay_target": ("learned-model checkpoints under "
                                       "results/sampled_long_development_runs/, deleted "
                                       "2026-10-20 when the model was retired"),
            "why_rescoped": ("The deleted checkpoints cannot be replayed, and nothing in "
                             "the production path loads them. The components the project "
                             "relies on are LinearFold and ViennaRNA, so the checks were "
                             "moved onto those rather than dropped."),
            "what_was_not_restored": ("The learned-model replay leg. It has no artifact to "
                                      "replay and is not reinstated by this run."),
            "authorised_by": "pending gate review; this script authorises nothing",
        },
        "no_claim": [
            "Reproducing a frozen fold is determinism, not accuracy.",
            "Honouring a constraint is decoder correctness, not structural correctness: a "
            "constrained fold is not evidence that the constrained pairs are real.",
            "Measured wall time and memory are from this machine and this cohort only.",
            "No model was fitted and no learned component was involved.",
            "Satisfying a requirement is a gate-review judgement, not an output of this "
            "script.",
        ],
    }

    print("\n=== replay ===")
    print(f"  {len(replay_ok)}/{len(replay_rows)} reproduced exactly")
    for row in replay_rows:
        if row.get("outcome") != "ok":
            print(f"    MISMATCH {row['method']} {row['id'][:40]} "
                  f"{row.get('frozen_mfe_kcal_mol')} -> {row.get('replayed_mfe_kcal_mol')}")
    print("=== constraint decoder ===")
    print(f"  {len(constraint_ok)}/{len(constraint_rows)} honoured every enforced pair")
    for row in constraint_rows:
        if row.get("outcome") != "ok":
            print(f"    NOT HONOURED {row['method']} {row['id'][:40]} "
                  f"absent={row.get('enforced_pairs_absent_from_fold')}")
    print("=== refusal control ===")
    for row in refusal_rows:
        print(f"  {row['method']:11s} {row['outcome']}")
    print("=== resources ===")
    for method, stats in payload["resources"].items():
        for band, values in stats["unconstrained_by_band"].items():
            print(f"  {method:11s} {band:10s} n={values['n']:2d} "
                  f"max {values['max_wall_seconds']:.2f}s  "
                  f"peak {values['max_peak_rss_mib']} MiB")

    if args.dry_run:
        print("\nDry run: nothing written.", file=sys.stderr)
        return 0
    out = ROOT / args.out / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True, exist_ok=False)
    (out / "summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(f"\nWrote {out}/summary.json", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
