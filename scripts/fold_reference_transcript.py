#!/usr/bin/env python3
"""Fold the assembled reference transcript and summarise it per region.

This runs RNAfold through the existing isolated worker on the transcript built
by scripts/assemble_reference_transcript.py, and reports MFE, ensemble free
energy, the STRAND average-log-odds feature, and per-region pairing.

A caveat is attached to every artifact this writes, and it is not decorative.
The assayed molecule is IVT mRNA in which every uridine is
N1-methylpseudouridine. ViennaRNA has no parameters for that nucleoside and
folds the sequence as if it were canonical U, so the numbers here are not the
thermodynamics of the molecule in the experiment. Because the modification is
constant across the panel, relative comparisons between constructs remain
usable; absolute values do not.

Usage:
    scripts/fold_reference_transcript.py --cds data/constructs/fluc_orf.txt
    scripts/fold_reference_transcript.py --cds ... --poly-a
"""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.component_integration import fold_fixed_input, strand_alo
from rnastable.transcript_assembly import assemble

DEFAULT_CONFIG = ROOT / "configs" / "transcript_inputs_v1_2026-10-19.json"
DEFAULT_OUT = ROOT / "results" / "reference_fold"

MODIFICATION_CAVEAT = (
    "Every uridine in the assayed molecule is N1-methylpseudouridine. ViennaRNA "
    "has no parameters for it and folded the sequence as canonical U, so these "
    "values are NOT the thermodynamics of the molecule in the experiment. The "
    "modification is constant across the panel, so relative comparisons between "
    "constructs remain usable; absolute values must not be reported as the "
    "assayed molecule's."
)


def region_summary(unpaired, start, end):
    """Mean unpaired probability over a half-open window."""
    window = unpaired[start:end]
    if not window:
        return None
    return {
        "start": start,
        "end": end,
        "length_nt": len(window),
        "mean_unpaired_probability": sum(window) / len(window),
        "min_unpaired_probability": min(window),
        "max_unpaired_probability": max(window),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cds", default=str(ROOT / "data" / "constructs" / "fluc_orf.txt"))
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--tx-id", default="FLUC-REF-V1")
    parser.add_argument("--provenance", default="committed construct inputs")
    parser.add_argument("--assay-context", default="assay_definition_v3_2026-10-19")
    parser.add_argument("--poly-a", action="store_true",
                        help="include the recorded template-encoded poly(A) tail")
    parser.add_argument("--temperature", type=float, default=37.0)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        transcript, report = assemble(
            Path(args.cds).read_text(), args.config, args.tx_id, args.provenance,
            args.assay_context, include_poly_a=args.poly_a)
    except ValueError as exc:
        raise SystemExit(f"Refused: {exc}")

    fold = fold_fixed_input(transcript, timeout=args.timeout, temperature=args.temperature)
    if fold.get("status") != "ok":
        raise SystemExit(f"Folding did not complete: {fold.get('reason', fold.get('status'))}")

    unpaired = fold["unpaired_probability_per_position"]
    paired = fold["paired_probability_per_position"]
    length = len(transcript.sequence)
    cds_start, cds_end = transcript.cds_start, transcript.cds_end

    regions = {
        "utr5": region_summary(unpaired, 0, cds_start),
        "cds": region_summary(unpaired, cds_start, cds_end),
        "utr3": region_summary(unpaired, cds_end, cds_end + report.utr3_length_nt),
    }
    if report.poly_a_included:
        regions["poly_a"] = region_summary(unpaired, cds_end + report.utr3_length_nt, length)
    # Initiation-region accessibility is the one local window with a specific
    # mechanistic reading, so it is reported separately rather than buried in
    # the 5' UTR mean. The window spans the last 15 nt of the 5' UTR and the
    # first 15 nt of the CDS, straddling the start codon.
    regions["start_codon_window"] = region_summary(
        unpaired, max(0, cds_start - 15), min(length, cds_start + 15))

    payload = {
        "tx_id": args.tx_id,
        "assembly": report.to_dict(),
        "fold": {
            "tool": fold.get("tool"),
            "version": fold.get("version"),
            "settings": fold.get("settings"),
            "mfe_kcal_mol": fold["mfe_kcal_mol"],
            "ensemble_free_energy_kcal_mol": fold["ensemble_free_energy_kcal_mol"],
            "mfe_per_nt_kcal_mol": fold["mfe_kcal_mol"] / length,
            "ensemble_free_energy_per_nt_kcal_mol": fold["ensemble_free_energy_kcal_mol"] / length,
            "strand_alo": strand_alo(paired),
            "mean_unpaired_probability": sum(unpaired) / length,
            "runtime_seconds": fold.get("runtime_seconds"),
            "input_sha256": fold.get("input_sha256"),
            "identity_sha256": fold.get("identity_sha256"),
        },
        "regions": regions,
        "modification_caveat": MODIFICATION_CAVEAT,
        "no_claim": (
            "A folding computation on a supplied sequence. Establishes no stability, "
            "translation or expression benefit, satisfies no gate requirement, and "
            "selects no floor."
        ),
    }
    print(json.dumps({k: v for k, v in payload.items() if k != "regions"}, indent=2))
    print(json.dumps({"regions": payload["regions"]}, indent=2))

    if args.dry_run:
        print("\nDry run: nothing written.", file=sys.stderr)
        return 0

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    suffix = "_polyA" if report.poly_a_included else "_core"
    target = out / f"{args.tx_id}{suffix}.json"
    if target.exists():
        raise SystemExit(f"{target} already exists; remove it deliberately or change --tx-id.")
    # The full per-position vectors are kept, since a summary cannot be
    # re-derived into them and the fold is expensive to repeat.
    payload["fold"]["paired_probability_per_position"] = paired
    payload["fold"]["unpaired_probability_per_position"] = unpaired
    payload["fold"]["mfe_structure"] = fold.get("mfe_structure")
    target.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(f"\nWrote {target}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
