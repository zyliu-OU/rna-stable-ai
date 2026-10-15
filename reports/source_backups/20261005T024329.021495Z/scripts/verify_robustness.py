#!/usr/bin/env python3
"""Verify raw trajectories and search/input denominators in a robustness report."""
import csv
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'results/evaluation_robustness_summary.json'
subprocess.run([sys.executable,str(ROOT/'scripts/verify_sweep.py'),'--summary',str(path)],check=True)
summary=json.loads(path.read_text());rows=summary['rows']
assert len(rows)==36 and len(summary['per_input_variability'])==12
for item in summary['per_input_variability']:
    group=[r for r in rows if all(r[k]==item[k] for k in ['kind','length','beam_size','sequence_seed'])]
    assert len(group)==item['search_runs']==3
    assert len({r['search_seed'] for r in group})==3
    assert all(r['input_sha256']==item['input_sha256'] for r in group)
    measured=[r['selected_vienna_delta_kcal_mol'] for r in group if r.get('selected_vienna_delta_kcal_mol') is not None]
    assert len(measured)==item['known_selected_energies']
    assert item['selected_finalists']==sum(r.get('selection_source')=='finalist' for r in group)
    assert item['returned_inputs']==sum(r.get('selection_source')=='input' for r in group)
    assert item['selection_missing_runs']==sum(r.get('selection_source') not in ('input','finalist') for r in group)
    assert item['selected_finalists']+item['returned_inputs']+item['selection_missing_runs']==len(group)
    if measured:
        assert math.isclose(statistics.mean(measured),item['mean_selected_delta_kcal_mol'],abs_tol=1e-10)
        assert min(measured)==item['min_selected_delta_kcal_mol'] and max(measured)==item['max_selected_delta_kcal_mol']
        assert all(v<=1e-9 for v in measured)
    else:assert item['mean_selected_delta_kcal_mol'] is None
for item in summary['input_weighted_groups']:
    inputs=[r for r in summary['per_input_variability'] if all(r[k]==item[k] for k in ['kind','length','beam_size'])]
    assert len(inputs)==item['input_count']==3
    means=[r['mean_selected_delta_kcal_mol'] for r in inputs if r['mean_selected_delta_kcal_mol'] is not None]
    assert len(means)==item['inputs_with_measured_selection']
    if means:assert math.isclose(statistics.mean(means),item['mean_input_mean_selected_delta_kcal_mol'],abs_tol=1e-10)
    else:assert item['mean_input_mean_selected_delta_kcal_mol'] is None
for suffix,key in [('inputs','per_input_variability'),('groups','input_weighted_groups'),('pairs','paired_comparisons')]:
    csv_rows=list(csv.DictReader((ROOT/f'results/evaluation_robustness_{suffix}.csv').open()))
    assert len(csv_rows)==len(summary[key])
    for csv_row,item in zip(csv_rows,summary[key]):
        assert csv_row=={k:('' if v is None else str(v)) for k,v in item.items()}
sys.path.insert(0,str(ROOT/'src'))
from rnastable.robustness import search_variability
from rnastable.replication import paired_comparisons
assert search_variability(rows)==(summary['per_input_variability'],summary['input_weighted_groups'])
assert paired_comparisons(rows)==summary['paired_comparisons']
print('Robustness audit passed: 36 searches, 6 inputs, 18 paired beams; within-input and across-input denominators verified.')
