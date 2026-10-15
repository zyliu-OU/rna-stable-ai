#!/usr/bin/env python3
"""Run independent input batches with at most two CPU folds at once; merge evidence."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import timestamp,write_artifact
from rnastable.batching import run_batches
from rnastable.sweep import load_sweep_config,plan_jobs,provenance,fingerprint,export_sweep


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=ROOT/'configs/evaluation_robustness_long.json')
    parser.add_argument('--workers',type=int,choices=[1,2],default=2)
    parser.add_argument('--resume',type=Path)
    args=parser.parse_args();config_path=args.config.resolve();spec=load_sweep_config(config_path)
    jobs=plan_jobs(spec);code_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                                   [Path(__file__),ROOT/'src/rnastable/batching.py',ROOT/'scripts/log_command.py']}
    current=provenance()
    if args.resume:
        run=args.resume.resolve()
        if not run.is_relative_to(ROOT/'results/sweep_runs'):
            parser.error('Resume must be a project sweep run directory')
        manifest=json.loads((run/'manifest.json').read_text())
        if (manifest['config_sha256']!=fingerprint(spec) or manifest['provenance']!=current or
            manifest.get('batch_driver_sha256')!=code_hashes or manifest['execution']['max_cpu_jobs']!=args.workers):
            parser.error('Resume rejected: configuration, workers, code or environment changed')
    else:
        stamp=timestamp();run=ROOT/'results/sweep_runs'/stamp;run.mkdir(parents=True)
        manifest={'utc':stamp,'config':spec,'config_sha256':fingerprint(spec),'provenance':current,
                  'jobs':jobs,'config_path':str(config_path),'batch_driver_sha256':code_hashes,
                  'execution':{'mode':'independent_input_batches','max_cpu_jobs':args.workers,
                      'timing_scope':'Concurrent CPU wall times include contention; not isolated benchmark timing.'}}
        manifest['components']=[]
        original=json.loads(config_path.read_text())
        for length in spec['lengths']:
            for kind in spec['kinds']:
                for seed in spec['sequence_seeds']:
                    identifier=f'{kind}_{length}_seed{seed}';directory=run/'components'/identifier
                    directory.mkdir(parents=True)
                    part={**original,'lengths':[length],'kinds':[kind],'sequence_seeds':[seed],
                          'optimization_config':str((config_path.parent/original['optimization_config']).resolve())}
                    part_path=directory/'config.json';part_path.write_text(json.dumps(part,indent=2)+'\n')
                    manifest['components'].append({'id':identifier,'root':str(directory),'config':str(part_path),
                                                   'log':str(directory/'driver_output.txt')})
        (run/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('CPU batch study:',run,flush=True)
    tasks=manifest['components']
    event_log=run/'driver_events'/timestamp()/'events.jsonl'
    event_log.parent.mkdir(parents=True)
    def record_event(event,**fields):
        with event_log.open('a') as stream:
            stream.write(json.dumps({'utc':timestamp(),'event':event,**fields})+'\n')
            stream.flush();os.fsync(stream.fileno())
    def command(task):
        root=Path(task['root'])
        cmd=[sys.executable,str(ROOT/'scripts/log_command.py'),'--log-dir',str(root/'reports'),
             str(ROOT/'scripts/rnastable'),'evaluate','--config',task['config'],'--output-root',str(root)]
        existing=sorted((root/'results/sweep_runs').glob('*/manifest.json'))
        if existing:cmd+=['--resume',str(existing[-1].parent)]
        return cmd
    def progress(event,index,value,completed,total):
        name=tasks[index]['id'] if index>=0 else 'active batches'
        record_event(event,component=name,**({'returncode':value} if event=='finished' else {'pid':value}))
        count=0
        for task in tasks:
            for p in (Path(task['root'])/'results/sweep_runs').glob('*/checkpoint.json'):
                try:count+=json.loads(p.read_text())['completed_jobs']
                except (OSError,ValueError):pass  # a child may currently be writing its checkpoint
        print(f'CPU batches: {event} {name}; value={value}; {completed}/{total} batches; {count}/{len(jobs)} saved searches',flush=True)
        write_artifact(run/'driver_status.json',json.dumps({'event':event,'completed_batches':completed,
                       'total_batches':total,'saved_searches':count,'complete':False,'event_log':str(event_log)},indent=2)+'\n')
    codes=run_batches(tasks,command,args.workers,progress)
    if any(code!=0 for code in codes):
        record_event('failed',component_exit_codes=codes)
        write_artifact(run/'driver_status.json',json.dumps({'complete':False,'component_exit_codes':codes,'event_log':str(event_log)},indent=2)+'\n')
        print('Batch failures recorded; other batches continued. Resume this directory with the same command.',flush=True)
        return 1
    by_id={}
    for task in tasks:
        component=json.loads((Path(task['root'])/'results/evaluation_sweep_summary.json').read_text())
        if not component['complete']:raise ValueError('Component sweep is incomplete')
        for row in component['rows']:
            if row['job_id'] in by_id:raise ValueError('Duplicate component job')
            by_id[row['job_id']]=row
    if set(by_id)!={j['job_id'] for j in jobs}:raise ValueError('Component jobs differ from the planned study')
    rows=[by_id[j['job_id']] for j in jobs]
    summary=export_sweep(ROOT,spec,run,rows,jobs,manifest,True)
    summary['execution']=manifest['execution']
    summary['limitations'].append(manifest['execution']['timing_scope'])
    for path in [run/'summary.json',ROOT/'results/evaluation_sweep_summary.json']:
        write_artifact(path,json.dumps(summary,indent=2,allow_nan=False)+'\n')
    report=ROOT/'reports/evaluation_sweep_report.md'
    text=report.read_text()
    old=f'./scripts/rnastable evaluate --config {manifest["config_path"]} --resume {run}'
    new=f'.venv/bin/python scripts/run_robustness_batches.py --config {shlex.quote(str(config_path))} --workers {args.workers} --resume {shlex.quote(str(run))}'
    write_artifact(report,text.replace(old,new)+'\n'+manifest['execution']['timing_scope']+'\n')
    record_event('complete')
    write_artifact(run/'driver_status.json',json.dumps({'complete':True,'component_exit_codes':codes,'event_log':str(event_log),
                   'completed_batches':len(tasks),'saved_searches':len(rows)},indent=2)+'\n')
    print(json.dumps({k:summary[k] for k in ['run_dir','planned_runs','completed_runs','status_counts']},indent=2))
    return 0


if __name__=='__main__':sys.exit(main())
