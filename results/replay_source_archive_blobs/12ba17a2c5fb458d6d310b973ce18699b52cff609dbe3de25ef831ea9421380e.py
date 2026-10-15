#!/usr/bin/env python3
"""Bound and replay synthetic1000/5000/10000nt sampled-training resource steps."""
import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import timestamp,publish
from rnastable.exposures import record_exposure,read_exposure,exposure_records
from rnastable.folding import run_bounded
from rnastable.native_journal import atomic_json
from rnastable.population_resource import toy_record,training_step
from rnastable.reference import digest
from rnastable.reference_audit import require


def worker(run):
    run=Path(run);manifest=json.loads((run/'manifest.json').read_text());record=json.loads((run/'record.json').read_text());require(digest((run/'record.json').read_bytes())==manifest['record_sha256'],'Input changed')
    for name,sha in manifest['code_sha256'].items():require(digest(Path(name).read_bytes())==sha,'Source changed before resource step')
    start=time.monotonic();sample,metadata,result=training_step(record,manifest['config'],manifest['sampling']);np.savez_compressed(run/'sample.npz',indices=sample[0].numpy(),labels=sample[1].numpy());atomic_json(run/'result.json',{'id':record['id'],'length':len(record['sequence']),'metadata':metadata,**result,'step_wall_seconds':time.monotonic()-start,'sample_sha256':digest((run/'sample.npz').read_bytes())})


def audit(path):
    summary=json.loads(Path(path).read_text());run=Path(summary['run_dir']);require(summary==json.loads((run/'summary.json').read_text()) and summary['accuracy_evaluated'] is False and summary['test_evaluated'] is False,'Resource summary differs');require(digest((run/'manifest.json').read_bytes())==summary['manifest_sha256'],'Parent manifest changed');parent=json.loads((run/'manifest.json').read_text());require(parent['lengths']==[1000,5000,10000] and len(summary['rows'])==3,'Resource plan differs');event=summary['exposure_event'];event_path=Path(event['path']);require(digest(event_path.read_bytes())==event['sha256'] and event_path.resolve().parent==(run/'exposures').resolve(),'Exposure changed');data=read_exposure(event_path);require(data['stage']=='training_started' and data['records']==exposure_records([toy_record(n) for n in parent['lengths']],str(run)+' training_started'),'Synthetic exposure differs')
    for length,row in zip(parent['lengths'],summary['rows']):
        child=run/str(length);manifest=json.loads((child/'manifest.json').read_text());require(digest((child/'manifest.json').read_bytes())==row['manifest_sha256'] and manifest['config']==parent['config'] and manifest['sampling']==parent['sampling'],'Child manifest differs');record=json.loads((child/'record.json').read_text());require(record==toy_record(length) and digest((child/'record.json').read_bytes())==manifest['record_sha256'],'Synthetic record changed');process=json.loads((child/'process.json').read_text());require(digest((child/'process.json').read_bytes())==row['process_sha256'] and process['status']==row['status'],'Bounded process changed')
        if row['status']!='ok':continue
        require(digest((child/'result.json').read_bytes())==row['result_sha256'],'Resource result changed');result=json.loads((child/'result.json').read_text());sample,metadata,replay=training_step(record,manifest['config'],manifest['sampling']);require(result['metadata']==metadata,'Population/sample replay differs');require(digest((child/'sample.npz').read_bytes())==result['sample_sha256'],'Sample file changed')
        with np.load(child/'sample.npz',allow_pickle=False) as saved:require(set(saved.files)=={'indices','labels'} and np.array_equal(saved['indices'],sample[0].numpy()) and np.array_equal(saved['labels'],sample[1].numpy()),'Sample tensors differ')
        for key,value in replay.items():require(result[key]==value,'Training step replay differs: '+key)
        for key in ('initial_sampled_population_loss','after_step_sampled_population_loss','gradient_l2_norm','step_wall_seconds'):require(np.isfinite(result[key]) and result[key]>=0,'Invalid measured resource value')
        require(row==row_for(child,process,result),'Resource row differs')
    return summary


def row_for(child,process,result=None):
    row={'length':int(child.name),'status':process['status'],'manifest_sha256':digest((child/'manifest.json').read_bytes()),'process_sha256':digest((child/'process.json').read_bytes()),'wall_seconds':process['wall_seconds'],'peak_rss_mib':process.get('peak_rss_mib')}
    if result is not None:row.update({'result_sha256':digest((child/'result.json').read_bytes()),'population_positive':result['metadata']['population_positive'],'population_negative':result['metadata']['population_negative'],'sampled_negative':result['metadata']['sampled_negative'],'retained_sample_tensor_bytes':result['metadata']['retained_tensor_bytes'],'full_label_tensor_bytes_if_materialized':result['full_label_tensor_bytes_if_materialized'],'initial_loss':result['initial_sampled_population_loss'],'after_step_loss':result['after_step_sampled_population_loss'],'gradient_l2_norm':result['gradient_l2_norm']})
    return row


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--worker',type=Path);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    if args.worker:return worker(args.worker)
    if args.verify:
        summary=audit(ROOT/'results/population_resource_summary.json');print('Population resource audit passed: three exact sampled-gradient/model-state replays; no accuracy evaluation.');return summary
    run=ROOT/'results/population_resource_runs'/timestamp();run.mkdir(parents=True,exist_ok=False);config=json.loads((ROOT/'configs/helix_comparative_development.json').read_text());settings={'seed':20261006,'negatives_per_positive':32,'minimum_negatives':128,'max_length':10000};paths=[Path(__file__),*[ROOT/'src/rnastable'/n for n in ('population_resource.py','population_sampling.py','helix_pairs.py','global_sparse_pairs.py','context_pairs.py','process_guard.py','folding.py')]];code={str(p):digest(p.read_bytes()) for p in paths};parent={'run_dir':str(run),'lengths':[1000,5000,10000],'config':config,'sampling':settings,'code_sha256':code,'timeout_seconds':180,'memory_limit_gib':8,'policy':'Constructed nested reverse-complement labels; one sampled gradient/Adam step per length in separate bounded processes. No all-pair label enumeration, model checkpoint selection, biological accuracy or stability.'};atomic_json(run/'manifest.json',parent);event=record_exposure(run,'training_started',[toy_record(n) for n in parent['lengths']]);rows=[]
    for length in parent['lengths']:
        child=run/str(length);child.mkdir();record=toy_record(length);atomic_json(child/'record.json',record);atomic_json(child/'manifest.json',{'config':config,'sampling':settings,'code_sha256':code,'record_sha256':digest((child/'record.json').read_bytes())});process=run_bounded([sys.executable,str(Path(__file__).resolve()),'--worker',str(child)],'',timeout=180,memory_limit_gib=8,cwd=ROOT);(child/'process.log').write_text(process.pop('stdout','')+'\n'+process.get('error',''));atomic_json(child/'process.json',process);result=json.loads((child/'result.json').read_text()) if process['status']=='ok' else None;rows.append(row_for(child,process,result));print(json.dumps(rows[-1]),flush=True)
    summary={'complete':True,'run_dir':str(run),'manifest_sha256':digest((run/'manifest.json').read_bytes()),'exposure_event':event,'planned_steps':3,'successful_steps':sum(row['status']=='ok' for row in rows),'accuracy_evaluated':False,'test_evaluated':False,'rows':rows,'limitations':['Synthetic nested annotations only; one update demonstrates feasibility, not long biological accuracy.','Retained label tensor bytes exclude model/optimizer/Python allocations; theoretical full tensor bytes describe the avoided index/label layout, not measured savings.','Whole-process GNUtime peak RSS includes Python/Torch startup and excludes guard supervisor; per-process memory cap is not a tree-wide RSS cap.','Other development tasks may overlap; timings are observations, not isolated speed benchmarks.']};atomic_json(run/'summary.json',summary);report=['# Synthetic sampled-training resource steps','',parent['policy'],'',*summary['limitations'],'','| Length | Status | Wall seconds | Process peak RSS MiB | Sample label bytes | Full label layout bytes (theoretical) |','|---:|---|---:|---:|---:|---:|']
    for row in rows:report.append(f"| {row['length']} | {row['status']} | {row['wall_seconds']} | {row['peak_rss_mib']} | {row.get('retained_sample_tensor_bytes')} | {row.get('full_label_tensor_bytes_if_materialized')} |")
    fields=sorted({key for row in rows for key in row});publish(ROOT,'population_resource',summary,rows,fields,'\n'.join(report)+'\n');return summary

if __name__=='__main__':main()
