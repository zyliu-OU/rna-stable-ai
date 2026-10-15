#!/usr/bin/env python3
"""Replay local exchanges and their monotone objective/validation metrics."""
import argparse
import json
from pathlib import Path
import sys
import math
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.global_sparse_pairs import make_global_model,sparse_candidates
from rnastable.reference import digest
from rnastable.reference_audit import require
from rnastable.scoring import structure_agreement
from rnastable.sparse_refinement import refine_sparse


def audit_refinement(path):
    import torch
    summary=json.loads(Path(path).read_text());run=Path(summary['run_dir'])
    require(summary['complete'] is True and summary['test_evaluated'] is False,'not development-only refinement')
    require(summary==json.loads((run/'summary.json').read_text()),'retained refinement summary differs')
    for name,key in [('manifest.json','manifest_sha256'),('validation_predictions.json','validation_sha256'),('synthetic_predictions.json','synthetic_sha256')]:require(digest((run/name).read_bytes())==summary[key],'refinement artifact changed')
    manifest=json.loads((run/'manifest.json').read_text());settings=manifest['settings'];source_run=Path(manifest['source_run_dir'])
    require(manifest['run_dir']==str(run) and settings in ({'passes':2,'max_remove':2,'group_cap':8},{'passes':2,'max_remove':2,'group_cap':8,'include_subsets':True}),'fixed refinement settings differ')
    require(digest((run/'source_summary.json').read_bytes())==manifest['source_summary_sha256'],'frozen source summary changed')
    source=json.loads((run/'source_summary.json').read_text());require(source['run_dir']==str(source_run) and source==json.loads((source_run/'summary.json').read_text()),'retained source differs')
    require(digest((source_run/'manifest.json').read_bytes())==manifest['source_manifest_sha256']==source['manifest_sha256'],'source manifest changed')
    source_manifest=json.loads((source_run/'manifest.json').read_text());config=source_manifest['config'];checkpoint=Path(source_manifest['checkpoint'])
    require(digest(checkpoint.read_bytes())==manifest['checkpoint_sha256']==source_manifest['checkpoint_sha256'],'source checkpoint changed')
    for name,key in [('inputs.json','inputs_sha256'),('validation.json','validation_sha256')]:require(digest((source_run/name).read_bytes())==source_manifest[key],'source input changed')
    require(digest((source_run/'decoder_diagnostics.json').read_bytes())==source['diagnostics_sha256'] and digest((source_run/'predictions.json').read_bytes())==source['predictions_sha256'],'source prediction/diagnostics changed')
    torch.set_num_threads(config['cpu_threads']);model=make_global_model(config);model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True))
    records=json.loads((source_run/'validation.json').read_text())['records'];prior=json.loads((source_run/'decoder_diagnostics.json').read_text());rows=json.loads((run/'validation_predictions.json').read_text())
    require(len(records)==len(prior)==len(rows)==summary['validation_records'],'validation inventory differs')
    for record,previous,row in zip(records,prior,rows):
        require(row['id']==record['id']==previous['id'],'validation identity differs')
        c=sparse_candidates(model,record['sequence'],config['top_k'],config['block_size']);expected=refine_sparse(record['sequence'],c['pairs'],c['scores'],**settings)
        require(all(row[k]==v for k,v in expected.items()),'refinement replay differs')
        require(row['refined_pair_f1']==structure_agreement(row['structure'],record['structure'])['pair_f1'] and row['greedy_pair_f1']==previous['greedy_pair_f1'] and row['sparse_exact_pair_f1']==previous['sparse_exact_pair_f1'],'validation diagnostic score differs')
        require(row['objective_history']==sorted(row['objective_history']) and row['objective']>=row['greedy_objective']-1e-8,'objective decrease')
        require(type(row['refinement_wall_seconds']) in (int,float) and math.isfinite(row['refinement_wall_seconds']) and row['refinement_wall_seconds']>=0,'invalid timing')
    require({key:sum(r[key] for r in rows)/len(rows) for key in ('greedy_pair_f1','refined_pair_f1','sparse_exact_pair_f1')}==summary['validation_decoder_f1'],'validation aggregate differs')
    records=json.loads((source_run/'inputs.json').read_text());prior=json.loads((source_run/'predictions.json').read_text());rows=json.loads((run/'synthetic_predictions.json').read_text())
    require(len(records)==len(prior)==len(rows)==3,'synthetic inventory differs')
    for record,previous,row in zip(records,prior,rows):
        require(row['id']==record['id']==previous['id'] and row['length']==len(record['sequence']),'synthetic identity differs')
        p=Path(row['source_candidate_path']);require(str(p)==previous['candidate_path'] and digest(p.read_bytes())==previous['candidate_sha256']==row['source_candidate_sha256'],'synthetic candidates changed')
        with np.load(p,allow_pickle=False) as saved:expected=refine_sparse(record['sequence'],saved['pairs'],saved['scores'],**settings)
        require(all(row[k]==v for k,v in expected.items()),'synthetic refinement replay differs')
        require(row['objective_history']==sorted(row['objective_history']) and row['objective']>=row['greedy_objective']-1e-8,'synthetic objective decrease')
        require(type(row['refinement_wall_seconds']) in (int,float) and math.isfinite(row['refinement_wall_seconds']) and row['refinement_wall_seconds']>=0,'invalid synthetic timing')
    require([{k:v for k,v in row.items() if k!='structure'} for row in rows]==summary['synthetic'],'synthetic aggregates differ')
    print('Sparse refinement audit passed: exact local-exchange replay, monotone objectives and reused-validation/synthetic exports; no test inference.')
    return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--summary',type=Path,default=ROOT/'results/sparse_refinement_summary.json');args=parser.parse_args();audit_refinement(args.summary)
