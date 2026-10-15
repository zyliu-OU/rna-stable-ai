"""Bounded independent-input batches for prospective CPU budget comparisons."""
from collections import Counter
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import sys

from .artifacts import publish, timestamp, write_artifact
from .batch_audit import event_peak
from .batching import run_batches
from .budget_progress import count_saved_searches
from .budget_study import arm_specs
from .sweep import fingerprint, load_sweep_config, provenance

ROOT = Path(__file__).resolve().parents[2]


def aggregate_pairs(rows):
    result=[]
    for length in sorted({r['length'] for r in rows}):
        group=[r for r in rows if r['length']==length]
        measured=[r['restart_minus_long_kcal_mol'] for r in group if r['comparison_status']=='measured']
        result.append({'length':length,'planned_inputs':len(group),'measured_pairs':len(measured),
                       'unknown_pairs':len(group)-len(measured),
                       'winners':dict(Counter(r['winner'] for r in group)),
                       'mean_restart_minus_long_kcal_mol':sum(measured)/len(measured) if measured else None})
    return result


def batch_provenance():
    paths=[Path(__file__),ROOT/'src/rnastable/budget_progress.py',
           ROOT/'src/rnastable/batching.py',ROOT/'src/rnastable/budget_study.py',
           ROOT/'src/rnastable/portfolio.py',ROOT/'scripts/log_command.py']
    return {**provenance(),'batch_code_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}


def run_budget_batches(root, config_path, workers=2, resume=None):
    if workers not in (1,2) or type(workers) is not int:
        raise ValueError('Budget batches support one or two workers')
    root,config_path=Path(root).resolve(),Path(config_path).resolve()
    spec=json.loads(config_path.read_text())
    base=(config_path.parent/spec['optimization_config']).resolve()
    arms=arm_specs(spec,base)
    report_name=spec.get('report_name','equal_budget_batched')
    if not isinstance(report_name,str) or not re.fullmatch(r'[a-z][a-z0-9_]*',report_name):
        raise ValueError('report_name must contain lowercase letters, digits and underscores')
    current=batch_provenance()
    if resume:
        run=Path(resume).resolve()
        if not run.is_relative_to(root/'results/equal_budget_batch_runs'):
            raise ValueError('Resume must be under this output root/results/equal_budget_batch_runs')
        manifest=json.loads((run/'manifest.json').read_text())
        if (manifest['config_sha256']!=fingerprint(spec)
                or manifest['execution']['max_cpu_jobs']!=workers):
            raise ValueError('Batch resume rejected: configuration, code, environment or worker limit changed')
        if manifest['provenance']!=current:
            raise ValueError(
                'Batch resume rejected: code or environment changed. Historical runs require '
                'their exact frozen driver, dependencies and environment; the archive-safe '
                'progress update does not permit a provenance override. Existing manifests '
                'and results are preserved. For a completed run, audit its published summary '
                f'without refolding: {sys.executable} {ROOT / "scripts/verify_equal_budget.py"} '
                f'--summary {root / "results" / (report_name + "_summary.json")}')
        for task in manifest['components']:
            if hashlib.sha256(Path(task['config']).read_bytes()).hexdigest()!=task['config_sha256']:
                raise ValueError('Batch resume rejected: frozen component config changed')
    else:
        run=root/'results/equal_budget_batch_runs'/timestamp()
        run.mkdir(parents=True,exist_ok=False)
        # Validate both fully expanded arms before writing a runnable parent manifest.
        for name,arm in arms.items():
            path=run/(name+'_validation_config.json')
            path.write_text(json.dumps(arm,indent=2)+'\n')
            load_sweep_config(path)
        tasks=[]
        for length,kind,seed in itertools.product(spec['lengths'],spec['kinds'],spec['sequence_seeds']):
            identity=f'{kind}_{length}_seed{seed}'
            directory=run/'components'/identity
            directory.mkdir(parents=True)
            component={**spec,'lengths':[length],'kinds':[kind],'sequence_seeds':[seed],
                       'optimization_config':str(base)}
            path=directory/'config.json'
            path.write_text(json.dumps(component,indent=2)+'\n')
            tasks.append({'id':identity,'kind':kind,'length':length,'sequence_seed':seed,
                          'root':str(directory),'config':str(path),
                          'config_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                          'log':str(directory/'driver_output.txt')})
        manifest={'utc':timestamp(),'run_dir':str(run),'config':spec,'config_path':str(config_path),
                  'config_sha256':fingerprint(spec),'provenance':current,'components':tasks,
                  'selection_policy':'lowest_confirmed_vienna_energy_then_job_id_v1',
                  'execution':{'mode':'independent_input_budget_batches','max_cpu_jobs':workers,
                               'timing_scope':'Concurrent CPU wall times include contention; not isolated benchmark timing.'}}
        (run/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Prespecified CPU budget batches: {run}',flush=True)
    tasks=manifest['components']
    event_log=run/'driver_events'/timestamp()/'events.jsonl'
    event_log.parent.mkdir(parents=True)
    def event(kind,**fields):
        with event_log.open('a') as stream:
            stream.write(json.dumps({'utc':timestamp(),'event':kind,**fields})+'\n')
            stream.flush();os.fsync(stream.fileno())
    def command(task):
        directory=Path(task['root'])
        cmd=[sys.executable,str(ROOT/'scripts/log_command.py'),'--log-dir',str(directory/'reports'),
             str(ROOT/'scripts/rnastable'),'compare-search-budgets','--config',task['config'],
             '--output-root',task['root']]
        prior=sorted((directory/'results/equal_budget_runs').glob('*/manifest.json'))
        if prior:cmd+=['--resume',str(prior[-1].parent)]
        return cmd
    def progress(kind,index,value,completed,total):
        name=tasks[index]['id'] if index>=0 else 'active batches'
        event(kind,component=name,**({'returncode':value} if kind=='finished' else {'pid':value}))
        saved=count_saved_searches(tasks)
        print(f'CPU budget batches: {kind} {name}; {completed}/{total} inputs; {saved}/{len(tasks)*(1+len(spec["restart_search_seeds"]))} saved searches',flush=True)
        write_artifact(run/'driver_status.json',json.dumps({'complete':False,'event_log':str(event_log),
                       'completed_batches':completed,'saved_searches':saved},indent=2)+'\n')
    try:
        codes=run_batches(tasks,command,workers,progress)
    except KeyboardInterrupt:
        event('interrupted')
        write_artifact(run/'driver_status.json',json.dumps({'complete':False,'interrupted':True,
                       'event_log':str(event_log)},indent=2)+'\n')
        raise
    if any(code!=0 for code in codes):
        event('failed',component_exit_codes=codes)
        write_artifact(run/'driver_status.json',json.dumps({'complete':False,'component_exit_codes':codes,
                       'event_log':str(event_log)},indent=2)+'\n')
        raise ValueError(f'Budget batch failures {codes}; other inputs continued; resume {run}')
    rows,sources=[],[]
    for task in tasks:
        path=Path(task['root'])/'results/equal_budget_summary.json'
        source=json.loads(path.read_text())
        if not source['complete'] or len(source['rows'])!=1:
            raise ValueError('Each component must provide exactly one completed paired input')
        row=source['rows'][0]
        if (row['kind'],row['length'],row['sequence_seed'])!=(task['kind'],task['length'],task['sequence_seed']):
            raise ValueError('Component input identity differs from the parent plan')
        rows.append(row)
        sources.append({'component':task['id'],'path':str(path),
                        'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    if len({(r['kind'],r['length'],r['sequence_seed']) for r in rows})!=len(tasks):
        raise ValueError('Duplicate paired input in batch merge')
    event('complete')
    events=[json.loads(line) for line in event_log.read_text().splitlines()]
    peak=event_peak(events,{t['id'] for t in tasks},workers)
    result={'utc':timestamp(),'mode':'batched_cpu_equal_proposal_budget','complete':True,
            'run_dir':str(run),'report_name':report_name,'config':spec,'config_sha256':fingerprint(spec),
            'manifest_sha256':hashlib.sha256((run/'manifest.json').read_bytes()).hexdigest(),
            'provenance':current,'sources':sources,'rows':rows,'aggregates':aggregate_pairs(rows),
            'execution':manifest['execution'],'peak_cpu_jobs':peak,
            'limitations':['Only two synthetic inputs per length in the default long pilot; descriptive outcomes only.',
                           'Equal proposal caps do not equalize folding requests or CPU work.',
                           manifest['execution']['timing_scope'],
                           'Each input runs the long arm before its restarts; no speedup or biological stability claim.',
                           'Unknown paired outcomes remain missing; no neural training.']}
    (run/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    lines=['# Long-RNA equal-proposal-budget CPU study','',f'Run: `{run}`','',
           '| Length | Input seed | Long change | Restart change | Restart minus long | Winner |',
           '|---:|---:|---:|---:|---:|---|']
    for row in rows:
        lines.append('| '+' | '.join('unknown' if row[k] is None else f'{row[k]:.4f}' if isinstance(row[k],float) else str(row[k])
                      for k in ['length','sequence_seed','long_selected_delta_kcal_mol',
                                'restarts_selected_delta_kcal_mol','restart_minus_long_kcal_mol','winner'])+' |')
    lines+=['','Changes are kcal/mol; negative restart-minus-long favors restarts.','',*result['limitations'],'']
    publish(root,report_name,result,rows,list(rows[0]),'\n'.join(lines))
    write_artifact(run/'driver_status.json',json.dumps({'complete':True,'component_exit_codes':codes,
                   'event_log':str(event_log),'completed_batches':len(tasks)},indent=2)+'\n')
    print(json.dumps({'run_dir':str(run),'paired_inputs':len(rows),'peak_cpu_jobs':peak,
                      'aggregates':result['aggregates']},indent=2))
    return result
