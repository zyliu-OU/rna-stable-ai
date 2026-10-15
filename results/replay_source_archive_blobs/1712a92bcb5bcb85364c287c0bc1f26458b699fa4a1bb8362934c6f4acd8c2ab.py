#!/usr/bin/env python3
"""Replay tiled synthetic scores/candidates and short validation decoder diagnostics."""
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.global_sparse_pairs import make_global_model,sparse_candidates,decode_sparse
from rnastable.reference import digest
from rnastable.reference_audit import require
from run_global_sparse_scalability import decoder_diagnostics


def audit_global_scalability(path):
    import torch
    summary=json.loads(Path(path).read_text());run=Path(summary['run_dir'])
    require(summary['complete'] is True and summary['test_evaluated'] is False,'not development/synthetic-only')
    require(json.loads((run/'summary.json').read_text())==summary,'retained summary differs')
    for name,key in [('manifest.json','manifest_sha256'),('predictions.json','predictions_sha256'),('decoder_diagnostics.json','diagnostics_sha256')]:require(digest((run/name).read_bytes())==summary[key],'artifact changed: '+name)
    manifest=json.loads((run/'manifest.json').read_text());config=manifest['config']
    require(manifest['run_dir']==str(run),'run identity differs')
    for name,key in [('inputs.json','inputs_sha256'),('development_summary.json','development_sha256'),('validation.json','validation_sha256')]:require(digest((run/name).read_bytes())==manifest[key],'frozen input changed')
    development=json.loads((run/'development_summary.json').read_text());checkpoint=Path(manifest['checkpoint'])
    require(development['test_evaluated'] is False and config==development['config'] and checkpoint==Path(development['run_dir'])/'best_context_model.pt','source model binding differs')
    require(digest(checkpoint.read_bytes())==manifest['checkpoint_sha256']==development['checkpoint_sha256'][checkpoint.name],'checkpoint changed')
    rng=np.random.default_rng(manifest['seed']);expected=[{'id':'synthetic_'+str(n),'sequence':''.join(rng.choice(list('ACGU'),n))} for n in (1000,5000,10000)]
    require(expected==json.loads((run/'inputs.json').read_text()),'synthetic plan differs')
    torch.set_num_threads(config['cpu_threads']);model=make_global_model(config);model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True))
    validation=json.loads((run/'validation.json').read_text())['records'];require((run/'validation.json').read_bytes()==(Path(development['run_dir'])/'validation.json').read_bytes(),'validation source differs')
    diagnostics=decoder_diagnostics(model,validation,config);require(diagnostics==json.loads((run/'decoder_diagnostics.json').read_text()),'validation decoder replay differs')
    require({key:sum(r[key] for r in diagnostics)/len(diagnostics) for key in ('greedy_pair_f1','sparse_exact_pair_f1','full_exact_pair_f1')}==summary['validation_decoder_f1'],'decoder diagnostic aggregates differ')
    rows=json.loads((run/'predictions.json').read_text());require(len(rows)==len(expected),'prediction inventory differs')
    for record,row in zip(expected,rows):
        require(row['id']==record['id'] and row['length']==len(record['sequence']),'sequence identity differs')
        p=Path(row['candidate_path']);require(p.resolve().parent==run.resolve() and digest(p.read_bytes())==row['candidate_sha256'],'candidate file changed')
        c=sparse_candidates(model,record['sequence'],config['top_k'],config['block_size'])
        with np.load(p,allow_pickle=False) as saved:require(np.array_equal(saved['pairs'],c['pairs']) and np.array_equal(saved['scores'],c['scores']),'candidate scores/indices differ')
        require(c['candidate_count']<=row['length']*config['top_k'] and c['peak_score_tile_elements']<=row['length']*config['block_size'],'candidate/tile bounds exceeded')
        decoded=decode_sparse(record['sequence'],c['pairs'],c['scores']);require(all(row[k]==v for k,v in decoded.items()),'sparse decoder replay differs')
        require(all(row[k]==v for k,v in c.items() if k not in ('pairs','scores','interpretation')),'candidate diagnostics differ')
        require(all(type(row[k]) in (int,float) and np.isfinite(row[k]) and row[k]>=0 for k in ('scoring_wall_seconds','decoding_wall_seconds')),'invalid timing')
    require([{k:v for k,v in r.items() if k!='structure'} for r in rows]==summary['rows'],'scalability summary differs')
    print('Global sparse scalability audit passed: exact tiled scores/candidates, greedy structures and short validation decoder diagnostics; no test inference.')
    return summary

if __name__=='__main__':audit_global_scalability(ROOT/'results/global_sparse_scalability_summary.json')
