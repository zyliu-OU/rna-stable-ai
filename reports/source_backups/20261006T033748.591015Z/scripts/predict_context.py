#!/usr/bin/env python3
"""Predict nested RNA structures from a saved context checkpoint and input FASTA."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.context_inference import infer_fasta
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-summary',type=Path,default=ROOT/'results/context_development_summary.json')
parser.add_argument('--decoder',choices=['source','exact_sparse'],default='source',help='Use the frozen source decoder, or exact sparse decoding up to1024 nt for global checkpoints')
parser.add_argument('--fasta',type=Path,required=True)
args=parser.parse_args()
try:summary=infer_fasta(ROOT,args.source_summary,args.fasta,args.decoder)
except (ValueError,OSError,KeyError,TypeError,RuntimeError) as exc:parser.exit(2,f'Context inference rejected: {exc}\n')
(ROOT/'results/context_inference_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
