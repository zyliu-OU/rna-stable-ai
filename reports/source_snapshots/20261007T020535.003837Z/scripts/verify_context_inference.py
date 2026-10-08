#!/usr/bin/env python3
"""Verify saved context inference without training or reference evaluation."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.context_inference import audit_inference
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--summary',type=Path,default=ROOT/'results/context_inference_summary.json');args=parser.parse_args()
try:audit_inference(args.summary)
except (ValueError,OSError,KeyError,TypeError,RuntimeError) as exc:parser.exit(2,f'Context inference audit rejected: {exc}\n')
