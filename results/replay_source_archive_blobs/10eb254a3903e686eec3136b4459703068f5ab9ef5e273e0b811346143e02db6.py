#!/usr/bin/env python3
"""Measure tiled global scoring on synthetic long inputs and decoder gaps on reused validation."""
import json
from pathlib import Path
import resource
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import timestamp
from rnastable.global_sparse_pairs import make_global_model,sparse_candidates,decode_sparse,global_supervision
from rnastable.pair_model import decode_pairs
from rnastable.reference import digest
from rnastable.scoring import structure_agreement
from rnastable.structure_model import tokens


def decoder_diagnostics(model,records,config):
    import torch
    rows=[]
    for r in records:
        c=sparse_candidates(model,r['sequence'],config['top_k'],config['block_size']);greedy=decode_sparse(r['sequence'],c['pairs'],c['scores'])
        n=len(r['sequence']);sparse=np.zeros((n,n))
        for (i,j),score in zip(c['pairs'],c['scores']):sparse[i,j]=sparse[j,i]=score
        sparse_exact=decode_pairs(r['sequence'],sparse)
        edges,_,_=global_supervision(r)
        with torch.inference_mode():values=model(tokens(r['sequence']),edges).numpy()
        dense=np.zeros((n,n))
        for (i,j),score in zip(edges.tolist(),values):dense[i,j]=dense[j,i]=float(score)
        full_exact=decode_pairs(r['sequence'],dense)
        rows.append({'id':r['id'],'length':n,'greedy_structure':greedy['structure'],'sparse_exact_structure':sparse_exact,'full_exact_structure':full_exact,
                     'greedy_pair_f1':structure_agreement(greedy['structure'],r['structure'])['pair_f1'],'sparse_exact_pair_f1':structure_agreement(sparse_exact,r['structure'])['pair_f1'],'full_exact_pair_f1':structure_agreement(full_exact,r['structure'])['pair_f1'],
                     'greedy_objective':greedy['objective'],'sparse_exact_objective':sum(sparse[i,j] for i,j in __import__('rnastable.scoring',fromlist=['base_pairs']).base_pairs(sparse_exact))})
    return rows


def main():
    import torch
    source=ROOT/'results/global_sparse_development_summary.json';development=json.loads(source.read_text());config=development['config'];checkpoint=Path(development['run_dir'])/'best_context_model.pt'
    if digest(checkpoint.read_bytes())!=development['checkpoint_sha256'][checkpoint.name]:raise ValueError('Global checkpoint changed')
    torch.set_num_threads(2);model=make_global_model(config);model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True))
    validation_path=Path(development['run_dir'])/'validation.json';validation=json.loads(validation_path.read_text())['records']
    rng=np.random.default_rng(20261006);records=[{'id':'synthetic_'+str(n),'sequence':''.join(rng.choice(list('ACGU'),n))} for n in (1000,5000,10000)]
    run=ROOT/'results/global_sparse_scalability_runs'/timestamp();run.mkdir(parents=True)
    (run/'inputs.json').write_text(json.dumps(records,indent=2)+'\n');(run/'development_summary.json').write_bytes(source.read_bytes());(run/'validation.json').write_bytes(validation_path.read_bytes())
    paths=[Path(__file__),ROOT/'src/rnastable/global_sparse_pairs.py',ROOT/'src/rnastable/pair_model.py']
    manifest={'run_dir':str(run),'config':config,'seed':20261006,'checkpoint':str(checkpoint),'checkpoint_sha256':digest(checkpoint.read_bytes()),'development_sha256':digest(source.read_bytes()),'inputs_sha256':digest((run/'inputs.json').read_bytes()),'validation_sha256':digest((run/'validation.json').read_bytes()),'code_sha256':{str(p):digest(p.read_bytes()) for p in paths},'policy':'Synthetic long inputs plus reused short validation decoder diagnostics only; no test evaluation.'}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');rows=[]
    diagnostics=decoder_diagnostics(model,validation,config);(run/'decoder_diagnostics.json').write_text(json.dumps(diagnostics,indent=2)+'\n')
    for record in records:
        print(f'Global tiled scoring: {record["id"]}',flush=True)
        begin=time.monotonic();c=sparse_candidates(model,record['sequence'],config['top_k'],config['block_size']);scoring=time.monotonic()-begin
        begin=time.monotonic();decoded=decode_sparse(record['sequence'],c['pairs'],c['scores']);decoding=time.monotonic()-begin
        candidate_path=run/(record['id']+'_candidates.npz');np.savez(candidate_path,pairs=c['pairs'],scores=c['scores'])
        row={'id':record['id'],'length':len(record['sequence']),**decoded,**{k:v for k,v in c.items() if k not in ('pairs','scores','interpretation')},'scoring_wall_seconds':scoring,'decoding_wall_seconds':decoding,'candidate_path':str(candidate_path),'candidate_sha256':digest(candidate_path.read_bytes())};rows.append(row)
        print(json.dumps({k:v for k,v in row.items() if k!='structure'}),flush=True)
    (run/'predictions.json').write_text(json.dumps(rows,indent=2)+'\n')
    summary={'complete':True,'run_dir':str(run),'test_evaluated':False,'purpose':'global_sparse_scalability_and_reused_validation_diagnostics','manifest_sha256':digest((run/'manifest.json').read_bytes()),'predictions_sha256':digest((run/'predictions.json').read_bytes()),'diagnostics_sha256':digest((run/'decoder_diagnostics.json').read_bytes()),'rows':[{k:v for k,v in row.items() if k!='structure'} for row in rows],'validation_decoder_f1':{key:sum(r[key] for r in diagnostics)/len(diagnostics) for key in ('greedy_pair_f1','sparse_exact_pair_f1','full_exact_pair_f1')},'process_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'limitations':['Quadratic all-distance scoring work; tile/top-k candidate storage is bounded.','Greedy decoding is approximate; exact decoder diagnostics are limited to reused short validation.','Candidate-array bytes exclude transient Torch tensors and process overhead.','One timing per synthetic length; no speedup, long-RNA accuracy or biological stability claim.']}
    (run/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(ROOT/'results/global_sparse_scalability_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
