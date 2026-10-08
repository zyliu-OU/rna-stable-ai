#!/usr/bin/env python3
"""Check selected FASTA hashes, constraints and reference decisions from a review."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rnastable.artifacts import sha256
from rnastable.optimization import check_constraints, hamming
from rnastable.selection import select_finalist
from rnastable.sequences import read_fasta

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--summary',type=Path,default=ROOT/'results/selection_review_summary.json')
args=parser.parse_args()
summary=json.loads(args.summary.read_text())
assert summary['mode']=='saved_evidence_review_no_new_folds'
source=Path(summary['source_summary'])
assert hashlib.sha256(source.read_bytes()).hexdigest()==summary['source_summary_sha256']
source_rows=json.loads(source.read_text())['rows']
assert [r['job_id'] for r in summary['rows']]==[r['job_id'] for r in source_rows]
sources=[];reasons=[]
for row in summary['rows']:
    path=Path(row['source_evidence'])
    assert hashlib.sha256(path.read_bytes()).hexdigest()==row['source_evidence_sha256']
    evidence=json.loads(path.read_text())
    original=read_fasta(path.parent/'input.fasta')[0][1]
    finalist=read_fasta(evidence['row']['finalist_fasta'])[0][1]
    decision=select_finalist(original,finalist,evidence['search']['status'],
                             evidence['reference'],evidence['validation'])
    selected=read_fasta(row['selected_fasta'])[0][1]
    assert selected==(finalist if decision['source']=='finalist' else original)
    assert sha256(selected)==row['selected_sha256']
    assert hamming(selected,original)==row['selected_mutations_from_input']
    check_constraints(selected,original,evidence['config'])
    for key,decision_key in [('selection_source','source'),('selection_reason','reason'),
                             ('candidate_vienna_delta_kcal_mol','candidate_vienna_delta_kcal_mol'),
                             ('selected_vienna_delta_kcal_mol','selected_vienna_delta_kcal_mol')]:
        assert row[key]==decision[decision_key]
    sources.append(row['selection_source']);reasons.append(row['selection_reason'])
from collections import Counter
assert dict(Counter(sources))==summary['selection_counts']
assert dict(Counter(reasons))==summary['reason_counts']
run=Path(summary['run_dir'])
assert json.loads((run/'summary.json').read_text())==summary
csv_rows=list(csv.DictReader((args.summary.parent/'selection_review.csv').open()))
assert len(csv_rows)==len(summary['rows'])
for csv_row,row in zip(csv_rows,summary['rows']):
    assert csv_row=={k:('' if v is None else str(v)) for k,v in row.items()}
print(f'Selection review audit passed: {len(sources)} selected FASTAs, hashes, decisions, constraints and CSV verified.')
