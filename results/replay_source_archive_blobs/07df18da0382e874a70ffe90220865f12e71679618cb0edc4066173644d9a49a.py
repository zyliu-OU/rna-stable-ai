#!/usr/bin/env python3
"""Verify a supplied-reference evaluation from its frozen input evidence."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rnastable.reference_audit import audit_reference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, default=ROOT/'results/reference_evaluation_summary.json')
    args = parser.parse_args()
    try:
        audit_reference(args.summary)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f'Reference audit failed: {exc}\n')


if __name__ == '__main__':
    main()
