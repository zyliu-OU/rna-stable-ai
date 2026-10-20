#!/usr/bin/env python3
"""Assemble the reference transcript once the CDS bases are supplied.

The 5' and 3' UTRs and the region boundary decision are already recorded. This
script supplies the one missing piece, verifies it against the recorded CDS
hash, and writes the assembled transcript as an artifact.

Nothing is folded or scored here, and no floor is consulted. Assembly produces a
validated input and establishes no stability, translation or expression claim.

Usage:
    scripts/assemble_reference_transcript.py --cds path/to/cds.txt
    scripts/assemble_reference_transcript.py --cds path/to/cds.fasta --dry-run
"""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.transcript_assembly import assemble

DEFAULT_CONFIG = ROOT / "configs" / "transcript_inputs_v1_2026-10-19.json"
DEFAULT_OUT = ROOT / "results" / "reference_transcript"


def read_sequence(path):
    """Read bare sequence or single-record FASTA; refuse anything ambiguous.

    A multi-record FASTA is refused rather than silently taking the first
    record, because picking one would quietly choose which construct is the
    reference.
    """
    text = Path(path).read_text().strip()
    if not text:
        raise ValueError(f"{path} is empty")
    if text.startswith(">"):
        records = [b for b in text.split(">") if b.strip()]
        if len(records) != 1:
            raise ValueError(
                f"{path} holds {len(records)} FASTA records; supply exactly one so the "
                "reference construct is unambiguous"
            )
        text = "".join(records[0].splitlines()[1:])
    return "".join(text.split())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cds", required=True,
                        help="file holding the reference CDS bases, bare or single-record FASTA")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG),
                        help="transcript inputs record (default: the committed v1 config)")
    parser.add_argument("--tx-id", default="FLUC-REF-V1")
    parser.add_argument("--provenance", required=True,
                        help="where these CDS bases came from, e.g. 'supplied by Ping 2026-10-20'")
    parser.add_argument("--assay-context", default="assay_definition_v3_2026-10-19")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--cds-component", default="cds",
                        help="which recorded CDS to verify against: cds (Fluc) or cds_fluc_pest")
    parser.add_argument("--poly-a", action="store_true",
                        help="append the recorded template-encoded poly(A) tail; off by default "
                             "because it may push the input out of the models' distribution")
    parser.add_argument("--dry-run", action="store_true",
                        help="verify and report without writing any artifact")
    args = parser.parse_args(argv)

    # A refusal here is an expected outcome, not a crash: it means the supplied
    # bases are not the recorded reference. Report it as a plain message so the
    # reason is readable rather than buried in a traceback.
    try:
        transcript, report = assemble(
            read_sequence(args.cds), args.config, args.tx_id, args.provenance,
            args.assay_context, include_poly_a=args.poly_a,
            cds_component=args.cds_component)
    except ValueError as exc:
        raise SystemExit(f"Refused: {exc}")

    payload = report.to_dict()
    print(json.dumps(payload, indent=2))

    if args.dry_run:
        print("\nDry run: verified only, nothing written.", file=sys.stderr)
        return 0

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    # Refuse to overwrite: an assembled reference transcript is the input every
    # later score is bound to, so replacing one in place would silently break
    # that binding.
    target = out / f"{args.tx_id}.json"
    if target.exists():
        raise SystemExit(
            f"{target} already exists. Remove it deliberately or choose another --tx-id; "
            "an assembled reference is not overwritten in place."
        )
    target.write_text(json.dumps(
        {"report": payload, "sequence_rna": transcript.sequence,
         "cds_start": transcript.cds_start, "cds_end": transcript.cds_end},
        indent=2, sort_keys=True))
    print(f"\nWrote {target}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
