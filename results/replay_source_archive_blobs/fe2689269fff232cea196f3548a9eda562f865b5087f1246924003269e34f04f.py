#!/usr/bin/env python3
"""Evaluate bounded sparse exchanges using reused validation and saved synthetic candidates."""
import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import timestamp
from rnastable.global_sparse_pairs import make_global_model,sparse_candidates
from rnastable.reference import digest
from rnastable.scoring import structure_agreement
from rnastable.sparse_refinement import refine_sparse


def main():
    import torch
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--include-subsets',action='store_true');args=parser.parse_args()
    source_path=ROOT/'results/global_sparse_scalability_summary.json';source=json.loads(source_path.read_text());source_run=Path(source['run_dir'])
    manifest=json.loads((source_run/'manifest.json').read_text());config=manifest['config'];checkpoint=Path(manifest['checkpoint'])
    if digest(checkpoint.read_bytes())!=manifest['checkpoint_sha256']:raise ValueError('Global checkpoint changed')
    torch.set_num_threads(2);model=make_global_model(config);model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True))
    validation=json.loads((source_run/'validation.json').read_text())['records'];diagnostics=json.loads((source_run/'decoder_diagnostics.json').read_text())
    synthetic=json.loads((source_run/'inputs.json').read_text());prior_predictions=json.loads((source_run/'predictions.json').read_text())
    run=ROOT/'results/sparse_refinement_runs'/timestamp();run.mkdir(parents=True)
    (run/'source_summary.json').write_bytes(source_path.read_bytes());settings={'passes':2,'max_remove':2,'group_cap':8}
    if args.include_subsets:settings['include_subsets']=True
    frozen={'run_dir':str(run),'settings':settings,'source_run_dir':str(source_run),'source_summary_sha256':digest(source_path.read_bytes()),'source_manifest_sha256':digest((source_run/'manifest.json').read_bytes()),'checkpoint_sha256':digest(checkpoint.read_bytes()),'code_sha256':{str(p):digest(p.read_bytes()) for p in (Path(__file__),ROOT/'src/rnastable/sparse_refinement.py')},'policy':'No model fitting, new test predictions or hyperparameter selection. Fixed local-exchange diagnostic on reused validation and synthetic candidates.'}
    (run/'manifest.json').write_text(json.dumps(frozen,indent=2)+'\n');validation_rows=[];synthetic_rows=[]
    for record,prior in zip(validation,diagnostics):
        candidates=sparse_candidates(model,record['sequence'],config['top_k'],config['block_size'])
        begin=time.monotonic();refined=refine_sparse(record['sequence'],candidates['pairs'],candidates['scores'],**settings);wall=time.monotonic()-begin
        validation_rows.append({'id':record['id'],**refined,'refinement_wall_seconds':wall,'refined_pair_f1':structure_agreement(refined['structure'],record['structure'])['pair_f1'],'greedy_pair_f1':prior['greedy_pair_f1'],'sparse_exact_pair_f1':prior['sparse_exact_pair_f1']})
    for record,prior in zip(synthetic,prior_predictions):
        print(f'Sparse exchanges: {record["id"]}',flush=True)
        p=Path(prior['candidate_path'])
        if digest(p.read_bytes())!=prior['candidate_sha256']:raise ValueError('Saved synthetic candidates changed')
        with np.load(p,allow_pickle=False) as candidate:
            begin=time.monotonic();refined=refine_sparse(record['sequence'],candidate['pairs'],candidate['scores'],**settings);wall=time.monotonic()-begin
        synthetic_rows.append({'id':record['id'],'length':len(record['sequence']),**refined,'refinement_wall_seconds':wall,'source_candidate_path':str(p),'source_candidate_sha256':prior['candidate_sha256']})
        print(json.dumps({k:v for k,v in synthetic_rows[-1].items() if k!='structure'}),flush=True)
    (run/'validation_predictions.json').write_text(json.dumps(validation_rows,indent=2)+'\n');(run/'synthetic_predictions.json').write_text(json.dumps(synthetic_rows,indent=2)+'\n')
    summary={'complete':True,'run_dir':str(run),'test_evaluated':False,'manifest_sha256':digest((run/'manifest.json').read_bytes()),'validation_sha256':digest((run/'validation_predictions.json').read_bytes()),'synthetic_sha256':digest((run/'synthetic_predictions.json').read_bytes()),'validation_records':len(validation_rows),'validation_decoder_f1':{key:sum(r[key] for r in validation_rows)/len(validation_rows) for key in ('greedy_pair_f1','refined_pair_f1','sparse_exact_pair_f1')},'synthetic':[{k:v for k,v in row.items() if k!='structure'} for row in synthetic_rows],'limitations':['Objective improvement is guaranteed for accepted moves; F1 improvement is not guaranteed.','Fixed passes/group caps can miss improving exchanges and do not establish global optimality.','Synthetic candidate reuse measures decoder computation, not neural accuracy; all labelled metrics are reused development.']}
    (run/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(ROOT/'results/sparse_refinement_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
