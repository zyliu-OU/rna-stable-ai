#!/usr/bin/env python3
"""Measure candidate coverage of frozen reused validation; no fitting or test evaluation."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import timestamp,publish
from rnastable.candidate_diagnostics import candidate_coverage
from rnastable.context_inference import load_checkpoint,method_name
from rnastable.exposures import record_exposure
from rnastable.full_pair_supervision import full_supervision
from rnastable.global_sparse_pairs import sparse_candidates
from rnastable.reference import digest
from rnastable.reference_audit import require
from rnastable.structure_model import tokens
from compare_expanded_development import source_group


def measure(source_path):
    import torch
    source_bytes,config,checkpoint,model=load_checkpoint(source_path);source=json.loads(source_bytes);run=Path(source['run_dir']);manifest=json.loads((run/'manifest.json').read_text())
    data=(run/'validation.json').read_bytes();require(digest(data)==manifest['snapshot_sha256']['validation.json'],'Validation changed')
    records=json.loads(data)['records'];require(digest((run/'predictions.json').read_bytes())==source['predictions_sha256'],'Source predictions changed')
    predictions={r['id']:r for r in json.loads((run/'predictions.json').read_text())['records'] if r['method']==method_name(config)}
    require(set(predictions)=={r['id'] for r in records},'Source prediction inventory differs');rows=[]
    for record in records:
        candidates=sparse_candidates(model,record['sequence'],config['top_k'],config['block_size'])
        edges,y,_=full_supervision(record,config['training_max_length']);truth_edges=edges[y.bool()]
        with torch.inference_mode():scores=model(tokens(record['sequence']),truth_edges)
        positive=[tuple(map(int,p)) for p in truth_edges[scores>0].tolist()]
        require(predictions[record['id']]['sequence']==record['sequence'],'Prediction sequence differs')
        rows.append({'id':record['id'],'method':method_name(config),'group':source_group(record),'length':len(record['sequence']),'candidate_count':len(candidates['pairs']),**candidate_coverage(record,candidates['pairs'],positive,predictions[record['id']]['structure'])})
    return source_bytes,data,records,rows


def aggregate(rows):
    result=[]
    for method in dict.fromkeys(r['method'] for r in rows):
        selected=[r for r in rows if r['method']==method]
        for group in ['all',*dict.fromkeys(r['group'] for r in selected)]:
            rs=selected if group=='all' else [r for r in selected if r['group']==group]
            result.append({'method':method,'group':group,'records':len(rs),**{key:sum(r[key] for r in rs) for key in ('reference_pairs','unsupported_reference_pairs','nonpositive_reference_pairs','top_k_removed_reference_pairs','decoder_omitted_reference_pairs')},**{key:sum(r[key] for r in rs)/len(rs) for key in ('retained_reference_recall','oracle_candidate_f1_upper_bound','decoded_pair_f1')}})
    return result


def main():
    sources={};rows=[];frozen=None;run=ROOT/'results/candidate_diagnostic_runs'/timestamp();run.mkdir(parents=True,exist_ok=False)
    for name in ('long_comparative_development','sampled_comparative_development'):
        path=ROOT/'results'/(name+'_summary.json');source_bytes=path.read_bytes();source=json.loads(source_bytes);source_run=Path(source['run_dir']);data=(source_run/'validation.json').read_bytes()
        if frozen is None:frozen=data;(run/'validation.json').write_bytes(data);event=record_exposure(run,'validation_started',json.loads(data)['records'])
        require(data==frozen,'Diagnostic validation differs')
        (run/(name+'.json')).write_bytes(source_bytes);sources[name]=digest(source_bytes)
        _,_,_,measured=measure(run/(name+'.json'));rows+=measured
    manifest={'run_dir':str(run),'source_sha256':sources,'validation_sha256':digest(frozen),'code_sha256':{str(p):digest(p.read_bytes()) for p in (Path(__file__),ROOT/'src/rnastable/candidate_diagnostics.py',ROOT/'src/rnastable/global_sparse_pairs.py',ROOT/'src/rnastable/full_pair_supervision.py')},'policy':'Reference-informed diagnostic on already exposed development records. Oracle candidate upper bounds are not predictions. No fitting, fresh test or threshold selection.'}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(run/'rows.json').write_text(json.dumps(rows,indent=2)+'\n');groups=aggregate(rows)
    summary={'complete':True,'test_evaluated':False,'run_dir':str(run),'manifest_sha256':digest((run/'manifest.json').read_bytes()),'rows_sha256':digest((run/'rows.json').read_bytes()),'exposure_event':event,'groups':groups,'interpretation':manifest['policy']}
    (run/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');report=['# Expanded candidate diagnostics','',summary['interpretation'],'','| Method | Group | Records | Nonpositive reference pairs | Top-k removed | Decoder omitted | Oracle candidate F1 bound | Decoded F1 |','|---|---|---:|---:|---:|---:|---:|---:|']
    for r in groups:report.append(f'| {r["method"]} | {r["group"]} | {r["records"]} | {r["nonpositive_reference_pairs"]} | {r["top_k_removed_reference_pairs"]} | {r["decoder_omitted_reference_pairs"]} | {r["oracle_candidate_f1_upper_bound"]} | {r["decoded_pair_f1"]} |')
    publish(ROOT,'expanded_candidate_diagnostics',summary,groups,list(groups[0]),'\n'.join(report)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
