#!/usr/bin/env python3
"""Verify frozen family assignments, split isolation and exposure checks."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rnastable.family_plan import audit_family_plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    try: result = audit_family_plan(args.run)
    except (ValueError, OSError, KeyError, TypeError) as exc: parser.exit(2, f'Family audit rejected: {exc}\n')
    print(f'Family plan audit passed: {result["counts"]}; {result["exposure_records_checked"]} exposure records checked.')


if __name__ == '__main__': main()
