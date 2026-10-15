#!/usr/bin/env python3
"""Replicate the fixed-budget three-arm prior pilot on exposed resource inputs."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import timestamp,publish
from rnastable.native_journal import atomic_json,exclusive_driver
from rnastable.reference import digest
from rnastable.reference_audit import require
from verify_checkpoint_prior_pilot import audit_prior

PLAN=[{'input_index':index,'seed':seed} for index in (0,1,2) for seed in (20261006,20261007)]


def aggregate(run,components):
    rows=[]
    for summary in components:
        for row in summary['rows']:
            rows.append({'input_id':summary['input_id'],'seed':summary['seed'],**row})
    return {'complete':True,'run_dir':str(run),'plan':PLAN,'test_accuracy_evaluated':False,'model_fitted':False,
            'manifest_sha256':digest((run/'manifest.json').read_bytes()),
            'components':[{'summary':str(Path(s['run_dir'])/'summary.json'),'sha256':digest((Path(s['run_dir'])/'summary.json').read_bytes())} for s in components],
            'rows':rows,'equal_native_proposal_budget_measured':all(s['equal_native_proposal_budget_measured'] for s in components),
            'unique_native_requests':sum(s['cost_accounting']['native']['unique_requests'] for s in components),
            'unknown_native_requests':sum(s['cost_accounting']['native']['unknown_requests'] for s in components),
            'known_native_wall_seconds':sum(s['cost_accounting']['native']['known_native_wall_seconds'] for s in components),
            'completed_proxy_calls_across_attempts':sum(s['cost_accounting']['completed_proxy_calls_across_attempts'] for s in components),
            'known_proxy_wall_seconds_across_attempts':sum(s['cost_accounting']['known_proxy_wall_seconds_across_attempts'] for s in components),
            'limitations':['Three previously exposed synthetic inputs and two search seeds; repeated seeds share inputs and are not independent biological samples.',
                           'Descriptive native-energy/proposal-ranking comparison only; no accuracy evaluation, fitting, generalization or biological stability claim.',
                           'Equal planned native requests do not imply equal wall time or proxy costs. Failed and timeout folds retain their request denominator.',
                           'Audit proxy replay costs are excluded from experimental search cost; incomplete attempts may add unknown proxy work.']}


def audit(path):
    summary=json.loads(Path(path).read_text());run=Path(summary['run_dir'])
    require(summary==json.loads((run/'summary.json').read_text()),'Replication summary differs')
    manifest=json.loads((run/'manifest.json').read_text())
    require(manifest['plan']==PLAN and digest((run/'manifest.json').read_bytes())==summary['manifest_sha256'],'Replication plan changed')
    components=[]
    require(len(summary['components'])==len(PLAN),'Replication component count differs')
    for expected,item in zip(PLAN,summary['components']):
        p=Path(item['summary']);require(digest(p.read_bytes())==item['sha256'],'Replication component changed')
        component=audit_prior(p);binding=json.loads((Path(component['run_dir'])/'manifest.json').read_text())
        require(binding['input_index']==expected['input_index'] and component['seed']==expected['seed'],'Replication input/seed differs')
        require(binding['config']=={**json.loads((ROOT/'configs/checkpoint_prior_pilot.json').read_text()),'seed':expected['seed']},'Replication fixed budget/config differs')
        components.append(component)
    for key in ('checkpoint_sha256','snapshot_sha256','code_sha256','native_runtime'):
        values=[json.loads((Path(s['run_dir'])/'manifest.json').read_text())[key] for s in components]
        if key=='snapshot_sha256':values=[{k:v for k,v in value.items() if k!='input.fasta'} for value in values]
        require(all(value==values[0] for value in values),'Replication source/runtime differs')
    require(aggregate(run,components)==summary,'Replication aggregate/denominators differ')
    print(f"Replication audit passed: {len(components)} components, {len(summary['rows'])} trajectories, {summary['unique_native_requests']} native requests.")
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--verify',action='store_true');parser.add_argument('--resume',type=Path);args=parser.parse_args()
    if args.verify:return audit(ROOT/'results/checkpoint_prior_replication_summary.json')
    if args.resume:run=args.resume.resolve()
    else:
        run=ROOT/'results/checkpoint_prior_replication_runs'/timestamp();run.mkdir(parents=True)
        atomic_json(run/'manifest.json',{'plan':PLAN,'policy':'Exposed synthetic resource replication, no labels or fitting.'})
    with exclusive_driver(run/'.driver.lock'):
        require(json.loads((run/'manifest.json').read_text())['plan']==PLAN,'Replication resume plan differs')
        components=[]
        for index,item in enumerate(PLAN):
            name=f'checkpoint_prior_replica_{index}';pointer=run/f'component_{index}.json';log=run/f'component_{index}.log'
            if pointer.exists():
                state=json.loads(pointer.read_text());summary=audit_prior(state['summary']);require(digest(Path(state['summary']).read_bytes())==state['sha256'],'Completed replica changed');components.append(summary);continue
            # A child created before a driver interruption can be resumed by its logged run directory.
            existing=[]
            for manifest_path in (ROOT/'results/checkpoint_prior_pilot_runs').glob('*/manifest.json'):
                binding=json.loads(manifest_path.read_text())
                if binding.get('replication_component')==str(pointer):existing.append(manifest_path.parent)
            require(len(existing)<=1,'Ambiguous replica resume')
            command=[sys.executable,str(ROOT/'scripts/run_checkpoint_prior_pilot.py'),'--input-index',str(item['input_index']),'--seed',str(item['seed']),'--publish-name',name,'--replication-component',str(pointer)]
            if existing:command+=['--resume',str(existing[0])]
            print(f"Replica {index+1}/{len(PLAN)}: input {item['input_index']}, seed {item['seed']}",flush=True)
            with log.open('a') as stream:subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True)
            if existing:summary=audit_prior(existing[0]/'summary.json')
            else:summary=audit_prior(ROOT/'results'/f'{name}_summary.json')
            atomic_json(pointer,{'summary':str(Path(summary['run_dir'])/'summary.json'),'sha256':digest((Path(summary['run_dir'])/'summary.json').read_bytes())});components.append(summary)
        summary=aggregate(run,components);atomic_json(run/'summary.json',summary)
        report=['# Checkpoint prior synthetic replication','',f'Run: `{run}`','',*summary['limitations'],'',
                '| Input | Seed | Policy | Native proposals | Proxy calls | Selected Vienna delta | Selection reason |',
                '|---|---:|---|---:|---:|---:|---|']
        for row in summary['rows']:report.append(f"| {row['input_id']} | {row['seed']} | {row['policy']} | {row['attempted_proposal_folds']} | {row['proxy_evaluations']} | {row['selected_vienna_delta_kcal_mol']} | {row['selection_reason']} |")
        report+=['',f"Unique native requests: {summary['unique_native_requests']}; unknown requests: {summary['unknown_native_requests']}; completed experimental proxy calls: {summary['completed_proxy_calls_across_attempts']}.",f"Known native wall seconds: {summary['known_native_wall_seconds']:.3f}; known scorer wall seconds: {summary['known_proxy_wall_seconds_across_attempts']:.3f}."]
        publish(ROOT,'checkpoint_prior_replication',summary,summary['rows'],list(summary['rows'][0]),'\n'.join(report)+'\n');print(json.dumps(summary,indent=2));return summary

if __name__=='__main__':main()
