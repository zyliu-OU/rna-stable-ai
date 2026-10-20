#!/usr/bin/env python3
"""Measure how far a 5' UTR's folding features depend on the ORF downstream.

Motivation. Folding Fluc and Fluc-PEST showed the identical 44 nt 5' UTR move
from 0.8389 to 0.5700 mean unpaired probability purely because the ORF changed.
That is one UTR in two contexts. It shows coupling exists but not whether it is
large enough to reorder a set of UTRs, which is the question that decides
whether a UTR may be evaluated outside the transcript it will be used in.

Scope. This scores synthetic sequences, so it is deliberately constrained to be
a mechanics characterisation and nothing else:

- The variants are dinucleotide-preserving shuffles of the reference 5' UTR.
  Shuffling destroys the GCCACC Kozak, so no variant here is a sequence anyone
  could propose. They are instruments for measuring the model, not candidates.
- The only reported quantity is agreement BETWEEN ORF contexts. No variant is
  ranked as better or worse, and no variant is recommended.
- Nothing here selects a sequence, freezes a floor, or satisfies a gate.

Dinucleotide shuffling is used rather than mononucleotide shuffling because
nearest-neighbour folding energies are dinucleotide-dependent; preserving
dinucleotide composition keeps the comparison about arrangement rather than
about composition the model is directly sensitive to.
"""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import json
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.component_integration import Transcript, fold_fixed_input, strand_alo
from rnastable.transcript_assembly import load_inputs, to_rna

DEFAULT_CONFIG = ROOT / "configs" / "transcript_inputs_v1_2026-10-19.json"
DEFAULT_OUT = ROOT / "results" / "utr_orf_coupling"


def dinucleotide_shuffle(sequence, rng):
    """Altschul-Erikson style Eulerian shuffle preserving dinucleotide counts.

    Retries on a disconnected last-edge graph rather than falling back to a
    mononucleotide shuffle, because a silent fallback would change what the
    experiment measures.
    """
    for _ in range(500):
        edges = {}
        for a, b in zip(sequence, sequence[1:]):
            edges.setdefault(a, []).append(b)
        last = sequence[-1]
        # Build a random arborescence toward `last`: the last edge out of each
        # other vertex must lead to a vertex already connected to `last`.
        tails = {}
        ok = True
        for vertex, outs in edges.items():
            if vertex == last:
                continue
            tails[vertex] = rng.choice(outs)
        seen = {last}
        for _ in range(len(tails) + 1):
            for vertex, target in tails.items():
                if target in seen:
                    seen.add(vertex)
        if any(v not in seen for v in tails):
            continue
        order = {}
        for vertex, outs in edges.items():
            remaining = list(outs)
            if vertex in tails:
                remaining.remove(tails[vertex])
            rng.shuffle(remaining)
            if vertex in tails:
                remaining.append(tails[vertex])
            order[vertex] = remaining
        out = [sequence[0]]
        cursor = sequence[0]
        for _ in range(len(sequence) - 1):
            if not order.get(cursor):
                ok = False
                break
            cursor = order[cursor].pop(0)
            out.append(cursor)
        if ok and len(out) == len(sequence):
            return "".join(out)
    raise RuntimeError("Dinucleotide shuffle failed to converge")


def spearman(xs, ys):
    """Rank correlation; ties averaged."""
    def rank(values):
        order = sorted(range(len(values)), key=lambda i: values[i])
        ranks = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            shared = (i + j) / 2 + 1
            for k in range(i, j + 1):
                ranks[order[k]] = shared
            i = j + 1
        return ranks
    a, b = rank(xs), rank(ys)
    ma, mb = statistics.fmean(a), statistics.fmean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5
    return num / den if den else float("nan")


def build(utr5, cds, utr3, tx_id):
    return Transcript(
        tx_id=tx_id, sequence=utr5 + cds + utr3, cds_start=len(utr5),
        cds_end=len(utr5) + len(cds),
        provenance="synthetic dinucleotide shuffle of the reference 5' UTR; not a candidate",
        assay_context="software mechanics only; no assay measurement or optimization")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--variants", type=int, default=24)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)

    data = load_inputs(args.config)
    components = data["components"]
    utr5_ref = to_rna(components["utr5"]["sequence_dna_uppercase"])
    utr3 = to_rna(components["utr3"]["sequence_dna_uppercase"])
    contexts = {
        "fluc": to_rna((ROOT / "data/constructs/fluc_orf.txt").read_text().strip()),
        "fluc_pest": to_rna((ROOT / "data/constructs/fluc_pest_orf.txt").read_text().strip()),
    }

    rng = random.Random(args.seed)
    variants = {"reference": utr5_ref}
    seen = {utr5_ref}
    while len(variants) < args.variants + 1:
        candidate = dinucleotide_shuffle(utr5_ref, rng)
        if candidate not in seen:
            seen.add(candidate)
            variants[f"shuffle_{len(variants):03d}"] = candidate

    rows = []
    for name, utr5 in variants.items():
        row = {"variant": name, "utr5": utr5, "is_reference": name == "reference"}
        for context, cds in contexts.items():
            record = build(utr5, cds, utr3, f"{name}__{context}")
            result = fold_fixed_input(record, timeout=args.timeout)
            if result.get("status") != "ok":
                raise SystemExit(f"Fold failed for {name}/{context}: {result.get('reason')}")
            unpaired = result["unpaired_probability_per_position"]
            row[context] = {
                "mfe_kcal_mol": result["mfe_kcal_mol"],
                "strand_alo": strand_alo(result["paired_probability_per_position"]),
                "utr5_mean_unpaired": statistics.fmean(unpaired[:len(utr5)]),
                "transcript_length_nt": len(record.sequence),
            }
        rows.append(row)
        print(f"  {name:14s} fluc utr5 {row['fluc']['utr5_mean_unpaired']:.4f}  "
              f"pest utr5 {row['fluc_pest']['utr5_mean_unpaired']:.4f}", flush=True)

    metrics = {}
    for metric in ("utr5_mean_unpaired", "strand_alo", "mfe_kcal_mol"):
        a = [r["fluc"][metric] for r in rows]
        b = [r["fluc_pest"][metric] for r in rows]
        metrics[metric] = {
            "spearman_between_contexts": spearman(a, b),
            "fluc_spread": max(a) - min(a),
            "fluc_pest_spread": max(b) - min(b),
            "mean_absolute_difference": statistics.fmean(abs(x - y) for x, y in zip(a, b)),
        }

    payload = {
        "purpose": "Quantify whether 5' UTR folding features reorder across ORF contexts.",
        "scope": ("Mechanics characterisation on synthetic shuffles. No candidate is "
                  "designed, ranked as better, or recommended. No floor is frozen and no "
                  "gate requirement is satisfied."),
        "variants": len(rows),
        "seed": args.seed,
        "shuffle": "dinucleotide-preserving Eulerian shuffle of the reference 5' UTR",
        "contexts": {k: {"cds_length_nt": len(v)} for k, v in contexts.items()},
        "metrics": metrics,
        "rows": rows,
        "no_claim": [
            "No variant here is a candidate; the shuffle destroys the Kozak context.",
            "Every uridine in the real molecules is N1-methylpseudouridine, which "
            "ViennaRNA does not represent.",
            "A folding computation establishes no stability, translation or expression "
            "benefit.",
        ],
    }
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"coupling_seed{args.seed}_n{args.variants}.json"
    if target.exists():
        raise SystemExit(f"{target} already exists; remove it deliberately.")
    target.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print("\n" + json.dumps(metrics, indent=2))
    print(f"\nWrote {target}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
