#!/usr/bin/env python3
"""Require explicit family evidence and an exposure ledger before freezing a study."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rnastable.artifacts import timestamp
from rnastable.family_plan import save_family_plan
from rnastable.exposures import collect_known_exposures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('references', 'assignments', 'plan', 'exposure'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args()
    try:
        # Known project exposures cannot be bypassed with an empty supplied ledger.
        known = collect_known_exposures(ROOT)
        run = ROOT/'results/family_plans'/timestamp()
        result = save_family_plan(run, args.references, args.assignments, args.plan, args.exposure, known)
    except (ValueError, OSError, TypeError) as exc:
        parser.exit(2, f'Family planning rejected: {exc}\n')
    print(f'Frozen family plan: {run}; counts {result["counts"]}')


if __name__ == '__main__': main()
