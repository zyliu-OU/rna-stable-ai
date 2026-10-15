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
parser.add_argument('--decoder',choices=['source','exact_sparse','greedy','refined'],default='source',help='Use the frozen decoder; global checkpoints also allow exact sparse up to1024 nt or explicit approximate greedy/refined up to10000 nt')
parser.add_argument('--fasta',type=Path,required=True)
parser.add_argument('--pair-penalty',type=float,default=0,help='Explicit nonnegative pair-logit penalty for sparse decoding (0..8)');args=parser.parse_args()
try:summary=infer_fasta(ROOT,args.source_summary,args.fasta,args.decoder,args.pair_penalty)
except (ValueError,OSError,KeyError,TypeError,RuntimeError) as exc:parser.exit(2,f'Context inference rejected: {exc}\n')
(ROOT/'results/context_inference_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
