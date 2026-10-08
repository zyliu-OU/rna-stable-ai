#!/usr/bin/env python3
"""Audit saved search decisions and constraints from raw candidate outputs."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rnastable.artifacts import sha256
from rnastable.folding import parse_output
from rnastable.optimization import check_constraints, hamming
from rnastable.sequences import read_fasta
from rnastable.selection import select_finalist

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--summary', type=Path, default=ROOT/'results/optimization_history_summary.json')
args = parser.parse_args()
summary = json.loads(args.summary.read_text())
config = summary['config']
run_dir = Path(summary['run_dir'])
original = read_fasta(run_dir/'input.fasta')[0][1]
finalist = read_fasta(summary['finalist_fasta'])[0][1]
assert sha256(original) == summary['input_sha256']
assert sha256(finalist) == summary['finalist_sha256']
check_constraints(finalist, original, config)
assert hamming(finalist, original) == summary['mutations_from_input']
current = original
best = summary['search']['baseline'].get('mfe_kcal_mol')
accepted = 0
for row in summary['search']['history']:
    if row['status'] != 'ok':
        assert not row['accepted']
        continue
    output = (run_dir/f'step_{row["step"]:04d}.txt').read_text()
    sequence = output.splitlines()[0]
    check_constraints(sequence, original, config)
    assert sha256(sequence) == row['proposal_sha256']
    assert json.loads(row['changed_positions']) == [i+1 for i,(a,b) in enumerate(zip(current,sequence)) if a!=b]
    score = parse_output('LinearFold', output, len(sequence))['mfe_kcal_mol']
    assert score == row['proposed_energy_kcal_mol']
    improving = score <= best-config['min_improvement_kcal_mol']+1e-9
    assert row['accepted'] == improving
    if improving:
        current, best = sequence, score
        accepted += 1
    assert row['best_energy_kcal_mol'] == best
assert current == finalist
assert accepted == summary['search']['accepted_steps']
validation = summary['validation']
if validation and all(v['status']=='ok' for v in validation.values()):
    delta = validation['finalist']['mfe_kcal_mol']-validation['input']['mfe_kcal_mol']
    assert delta == summary['vienna_energy_delta_kcal_mol']
    assert summary['vienna_improvement_confirmed'] == (delta < -1e-9)
if 'selection' in summary:
    decision=select_finalist(original,finalist,summary['search']['status'],
                             validation.get('input'),validation.get('finalist'))
    assert summary['selection']==decision
    selected=read_fasta(summary['selected_fasta'])[0][1]
    assert selected==(finalist if decision['source']=='finalist' else original)
    assert sha256(selected)==summary['selected_sha256']
    assert hamming(selected,original)==summary['selected_mutations_from_input']
    check_constraints(selected,original,config)
    if decision['source']=='finalist':
        assert validation['input']['status']==validation['finalist']['status']=='ok'
        assert validation['finalist']['mfe_kcal_mol'] < validation['input']['mfe_kcal_mol']-1e-9
    print(f'Selection audit passed: {decision["source"]}; {decision["reason"]}.')
print(f'Optimization audit passed: {len(summary["search"]["history"])} proposals, {accepted} accepted, {summary["mutations_from_input"]} final mutations, all constraints preserved.')
