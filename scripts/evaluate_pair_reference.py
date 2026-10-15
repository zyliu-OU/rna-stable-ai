#!/usr/bin/env python3
"""Evaluate supplied exact zero-based pairs, including pseudoknots, without inference."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.pair_reference import audit, run_evaluation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--references", type=Path)
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--output-root", type=Path, default=ROOT)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        return audit(args.verify)
    if args.references is None or args.predictions is None:
        parser.error("--references and --predictions are required for scoring")
    summary = run_evaluation(args.output_root, args.references, args.predictions)
    audit(Path(summary["run_dir"]) / "summary.json")
    return summary


if __name__ == "__main__":
    main()
