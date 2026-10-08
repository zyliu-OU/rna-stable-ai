#!/usr/bin/env python3
"""Compare exact sparse, greedy and frozen refinement on identical development candidates."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import timestamp,publish
from rnastable.context_inference import load_checkpoint,method_name
from rnastable.exact_sparse_pairs import decode_exact_sparse
from rnastable.exposures import record_exposure
from rnastable.global_sparse_pairs import sparse_candidates,decode_sparse
from rnastable.sparse_refinement import refine_sparse
from rnastable.reference import digest
from rnastable.reference_audit import require
from rnastable.scoring import structure_agreement
from compare_expanded_development import source_group


def measure(path):
    source_bytes,config,checkpoint,model=load_checkpoint(path);source=json.loads(source_bytes);source_run=Path(source['run_dir']);manifest=json.loads((source_run/'manifest.json').read_text());data=(source_run/'validation.json').read_bytes()
    require(digest(data)==manifest['snapshot_sha256']['validation.json'],'Validation source changed');records=json.loads(data)['records']
    require(digest((source_run/'predictions.json').read_bytes())==source['predictions_sha256'],'Source predictions changed')
    retained={r['id']:r for r in json.loads((source_run/'predictions.json').read_text())['records'] if r['method']==method_name(config)};require(set(retained)=={r['id'] for r in records},'Source prediction inventory differs')
    rows=[];arrays={}
    for index,record in enumerate(records):
        candidates=sparse_candidates(model,record['sequence'],config['top_k'],config['block_size']);pairs,scores=candidates['pairs'],candidates['scores'];arrays[f'pairs_{index}']=pairs;arrays[f'scores_{index}']=scores
        decoded={'greedy':decode_sparse(record['sequence'],pairs,scores),'refined':refine_sparse(record['sequence'],pairs,scores,**config['refinement']),'exact_sparse':decode_exact_sparse(record['sequence'],pairs,scores)}
        require(retained[record['id']]['sequence']==record['sequence'] and decoded['refined']['structure']==retained[record['id']]['structure'],'Frozen refinement prediction differs')
        require(decoded['exact_sparse']['objective']+1e-8>=max(decoded['greedy']['objective'],decoded['refined']['objective']),'Exact decoder objective below heuristic')
        for decoder,result in decoded.items():rows.append({'id':record['id'],'model':method_name(config),'decoder':decoder,'group':source_group(record),'length':len(record['sequence']),'candidate_count':len(pairs),'structure':result['structure'],'objective':result['objective'],'pair_f1':structure_agreement(result['structure'],record['structure'])['pair_f1'],**({'dp_array_bytes':result['dp_array_bytes']} if decoder=='exact_sparse' else {})})
    return source_bytes,data,records,arrays,rows


def aggregate(rows):
    groups=[]
    for model in dict.fromkeys(r['model'] for r in rows):
        selected=[r for r in rows if r['model']==model]
        for group in ['all',*dict.fromkeys(r['group'] for r in selected)]:
            for decoder in ('greedy','refined','exact_sparse'):
                rs=[r for r in selected if r['decoder']==decoder and (group=='all' or r['group']==group)]
                groups.append({'model':model,'group':group,'decoder':decoder,'records':len(rs),'mean_pair_f1':sum(r['pair_f1'] for r in rs)/len(rs),'mean_objective':sum(r['objective'] for r in rs)/len(rs)})
    return groups


def main():
    import numpy as np
    run=ROOT/'results/exact_sparse_development_runs'/timestamp();run.mkdir(parents=True,exist_ok=False);frozen=None;sources={};rows=[]
    for name in ('long_comparative_development','sampled_comparative_development'):
        path=ROOT/'results'/(name+'_summary.json');source_bytes=path.read_bytes();source=json.loads(source_bytes);data=(Path(source['run_dir'])/'validation.json').read_bytes()
        if frozen is None:
            frozen=data;records=json.loads(data)['records'];require(all(len(r['sequence'])<=1024 for r in records),'Exact decoder development bound exceeded')
            (run/'validation.json').write_bytes(data);event=record_exposure(run,'validation_started',records)
        require(data==frozen,'Decoder comparison cohort differs');(run/(name+'.json')).write_bytes(source_bytes);sources[name]=digest(source_bytes)
        _,_,_,arrays,measured=measure(run/(name+'.json'));np.savez_compressed(run/(name+'_candidates.npz'),**arrays);rows+=measured
    manifest={'run_dir':str(run),'sources':sources,'validation_sha256':digest(frozen),'candidate_sha256':{name:digest((run/(name+'_candidates.npz')).read_bytes()) for name in sources},'code_sha256':{str(p):digest(p.read_bytes()) for p in (Path(__file__),ROOT/'src/rnastable/exact_sparse_pairs.py',ROOT/'src/rnastable/global_sparse_pairs.py',ROOT/'src/rnastable/sparse_refinement.py')},'policy':'Identical exposed development records and candidates. Exact maximum summed logits under noncrossing constraints, not maximum label agreement or unrestricted pair search. Bounded to1024 nt/64 candidates per endpoint. No fitting or fresh test.'}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(run/'rows.json').write_text(json.dumps(rows,indent=2)+'\n');groups=aggregate(rows)
    summary={'complete':True,'test_evaluated':False,'run_dir':str(run),'manifest_sha256':digest((run/'manifest.json').read_bytes()),'rows_sha256':digest((run/'rows.json').read_bytes()),'exposure_event':event,'groups':groups,'interpretation':manifest['policy']}
    (run/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');report=['# Exact sparse development comparison','',summary['interpretation'],'','| Model | Group | Decoder | Records | Mean pair F1 | Mean logit objective |','|---|---|---|---:|---:|---:|']
    for r in groups:report.append(f'| {r["model"]} | {r["group"]} | {r["decoder"]} | {r["records"]} | {r["mean_pair_f1"]} | {r["mean_objective"]} |')
    publish(ROOT,'exact_sparse_development',summary,groups,list(groups[0]),'\n'.join(report)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
