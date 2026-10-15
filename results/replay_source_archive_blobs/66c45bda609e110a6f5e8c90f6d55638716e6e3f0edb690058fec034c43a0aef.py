#!/usr/bin/env python3
"""Audit each saved CPU sweep trajectory, finalist, reference and aggregate."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import sha256
from rnastable.folding import parse_output
from rnastable.optimization import check_constraints,hamming
from rnastable.scoring import structure_agreement
from rnastable.sequences import generate_sequence,read_fasta
from rnastable.selection import select_finalist

parser=argparse.ArgumentParser()
parser.add_argument('--summary',type=Path,default=ROOT/'results/evaluation_sweep_summary.json')
args=parser.parse_args()
summary=json.loads(args.summary.read_text())
run_dir=Path(summary['run_dir'])
manifest=json.loads((run_dir/'manifest.json').read_text())
assert summary['config_sha256']==manifest['config_sha256']
assert summary['complete'] and len(summary['rows'])==len(manifest['jobs'])
assert len({r['job_id'] for r in summary['rows']})==summary['planned_runs']
assert summary['status_counts']==dict(Counter(r['status'] for r in summary['rows']))
validated,failures,audited_proposals=0,0,0

def audit_fold(record,sequence,tool):
    if record is None or record['status']!='ok':
        return
    output=Path(record['raw_output']).read_text()
    assert sequence in output.splitlines()
    parsed=parse_output(tool,output,len(sequence))
    assert parsed['structure']==record['structure']
    assert parsed['mfe_kcal_mol']==record['mfe_kcal_mol']

for job,row in zip(manifest['jobs'],summary['rows']):
    assert job['job_id']==row['job_id']
    original=generate_sequence(job['length'],job['kind'],job['sequence_seed'])
    assert sha256(original)==row['input_sha256']
    if not row.get('summary_path'):
        assert row['status']=='error' and row.get('error')
        failures+=1
        continue
    evidence=json.loads(Path(row['summary_path']).read_text())
    assert evidence['row']==row and evidence['job']==job
    config=evidence['config']
    assert config=={**summary['config']['optimization'],'seed':job['search_seed'],'beam_size':job['beam_size']}
    finalist=read_fasta(row['finalist_fasta'])[0][1]
    check_constraints(finalist,original,config)
    assert sha256(finalist)==row['finalist_sha256']
    assert hamming(finalist,original)==row['mutations_from_input']
    search=evidence['search']
    audit_fold(search['baseline'],original,'LinearFold')
    current=original
    best=search['baseline'].get('mfe_kcal_mol')
    accepted=0
    attempt=Path(row['summary_path']).parent
    for history in search['history']:
        if history['status']!='ok':
            assert not history['accepted']
            continue
        output=(attempt/f'step_{history["step"]:04d}.txt').read_text()
        proposal=output.splitlines()[0]
        assert sha256(proposal)==history['proposal_sha256']
        check_constraints(proposal,original,config)
        assert json.loads(history['changed_positions'])==[i+1 for i,(a,b) in enumerate(zip(current,proposal)) if a!=b]
        energy=parse_output('LinearFold',output,len(proposal))['mfe_kcal_mol']
        assert energy==history['proposed_energy_kcal_mol']
        improving=energy<=best-config['min_improvement_kcal_mol']+1e-9
        assert history['accepted']==improving
        if improving:
            current,best=proposal,energy
            accepted+=1
        assert best==history['best_energy_kcal_mol']
        audited_proposals+=1
    assert current==finalist and accepted==row['accepted_steps']
    reference,validation=evidence['reference'],evidence['validation']
    if 'selection' in evidence:
        decision=select_finalist(original,finalist,search['status'],reference,validation)
        assert decision==evidence['selection']
        selected=read_fasta(row['selected_fasta'])[0][1]
        assert selected==(finalist if decision['source']=='finalist' else original)
        check_constraints(selected,original,config)
        assert sha256(selected)==row['selected_sha256']
        assert hamming(selected,original)==row['selected_mutations_from_input']
        assert row['selection_source']==decision['source'] and row['selection_reason']==decision['reason']
        assert row['selected_vienna_delta_kcal_mol']==decision['selected_vienna_delta_kcal_mol']
        if decision['source']=='finalist':
            assert reference['status']==validation['status']=='ok'
            assert validation['mfe_kcal_mol'] < reference['mfe_kcal_mol']-1e-9
    audit_fold(reference,original,'ViennaRNA')
    audit_fold(validation,finalist,'ViennaRNA')
    if row['status']=='validated':
        assert reference['status']=='ok' and validation['status']=='ok'
        delta=validation['mfe_kcal_mol']-reference['mfe_kcal_mol']
        assert math.isclose(delta,row['vienna_delta_kcal_mol'],abs_tol=1e-8)
        assert math.isclose(delta/len(original),row['vienna_delta_kcal_mol_per_nt'],abs_tol=1e-10)
        assert row['vienna_improvement_confirmed']==(delta < -1e-9)
        assert row['input_pair_f1']==structure_agreement(search['baseline']['structure'],reference['structure'])['pair_f1']
        assert row['finalist_pair_f1']==structure_agreement(search['best']['structure'],validation['structure'])['pair_f1']
        validated+=1
    else:
        assert row.get('vienna_delta_kcal_mol') is None
        failures+=1
for aggregate in summary['aggregates']:
    group=[r for r in summary['rows'] if all(r[k]==aggregate[k] for k in ('kind','length','beam_size'))]
    measured=[r for r in group if r['status']=='validated']
    assert len(measured)==aggregate['validated_runs']
    assert len(group)-len(measured)==aggregate['failed_runs']
    assert sum(r['vienna_delta_kcal_mol'] < -1e-9 for r in measured)==aggregate['confirmed_improvements']
    if measured:
        mean=sum(r['vienna_delta_kcal_mol_per_nt'] for r in measured)/len(measured)
        assert math.isclose(mean,aggregate['mean_vienna_delta_kcal_mol_per_nt'],abs_tol=1e-10)
    else:
        assert aggregate['mean_vienna_delta_kcal_mol_per_nt'] is None
print(f'Sweep audit passed: {validated} validated runs, {failures} recorded failures, {audited_proposals} proposal folds; constraints, raw outputs, decisions and aggregate denominators verified.')
