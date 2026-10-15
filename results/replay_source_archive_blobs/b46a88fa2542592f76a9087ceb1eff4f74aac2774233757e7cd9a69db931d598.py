#!/usr/bin/env python3
"""Matched-seed full-BCE pair-head development study; no fresh test inputs."""
import argparse
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import timestamp,publish
from rnastable.folding import run_bounded
from rnastable.native_journal import atomic_json,canonical,exclusive_driver
from rnastable.pair_head_study import HEADS,head_config,train_component,audit_component,paired_initialization
from rnastable.reference import digest
from rnastable.reference_audit import require
from train_sampled_comparative_development import frozen_inputs

NAME='pair_head_development_study'


def validate_config(config):
    require(config['seeds']==[20261006,20261007,20261008] and config['heads']==list(HEADS),'Invalid fixed head/seed study plan')
    require(type(config['component_timeout_seconds']) is int and 1<=config['component_timeout_seconds']<=600 and type(config['memory_limit_gib']) in (int,float) and 0<config['memory_limit_gib']<=16,'Invalid component resource budget')
    require(datetime.fromisoformat(config['deadline_utc']).tzinfo is not None,'Study deadline needs timezone')
    return config


def aggregate(run,manifest,states,components):
    by_key={str(Path(summary['run_dir'])):summary for summary in components};rows=[]
    for item,state in zip(manifest['plan'],states):
        component=by_key.get(state['run_dir']);row={'seed':item['seed'],'head':item['head'],'status':state.get('result',{}).get('status',state['state']),'selected_epoch':None,'validation_pair_f1':None,'parameters':None,'known_training_wall_seconds':state.get('result',{}).get('wall_seconds')}
        if component:row.update(status='ok',selected_epoch=component['selected_epoch'],validation_pair_f1=component['selected_validation_pair_f1'],parameters=component['parameters'])
        rows.append(row)
    deltas=[]
    for seed in manifest['config']['seeds']:
        by_head={row['head']:row for row in rows if row['seed']==seed}
        for head in ('stack','helix'):
            delta=by_head[head]['validation_pair_f1']-by_head['baseline']['validation_pair_f1'] if by_head[head]['status']==by_head['baseline']['status']=='ok' else None
            deltas.append({'seed':seed,'head':head,'paired_development_f1_delta_vs_baseline':delta})
    return {'complete':True,'run_dir':str(run),'manifest_sha256':digest((run/'manifest.json').read_bytes()),'test_evaluated':False,'development_only':True,
            'planned_fits':len(manifest['plan']),'completed_fits':len(components),'unknown_cost_components':sum(state['state'] in ('interrupted','recovered_complete_unknown_cost') for state in states),
            'components':[{'summary':str(Path(summary['run_dir'])/'summary.json'),'sha256':digest((Path(summary['run_dir'])/'summary.json').read_bytes())} for summary in components],
            'attempt_sha256':{str((Path(state['run_dir'])/'attempt.json').relative_to(run)):digest((Path(state['run_dir'])/'attempt.json').read_bytes()) for state in states},
            'rows':rows,'paired_deltas':deltas,'matched_initializations_verified':paired_initialization(components),
            'limitations':['Three matched initialization seeds share the same 89 training and 47 reused validation records; not independent biological replication.',
                           'Validation selects checkpoints and supports development comparison only. Consumed test sets are not read or evaluated.',
                           'All heads retain identical base initialization, full pair BCE, optimizer, ten epochs and exact top-16 sparse decoder. Feature parameter counts differ.',
                           'Interrupted fits are not retried; any recovered completed fit retains unknown parent-process cost.',
                           'Component wall times are bounded process measurements, not isolated throughput benchmarks.']}


def audit(path):
    summary=json.loads(Path(path).read_text());run=Path(summary['run_dir']);manifest=json.loads((run/'manifest.json').read_text());validate_config(manifest['config'])
    require(summary==json.loads((run/'summary.json').read_text()) and digest((run/'manifest.json').read_bytes())==summary['manifest_sha256'],'Study summary binding differs')
    require(manifest['plan']==[{'seed':seed,'head':head} for seed in manifest['config']['seeds'] for head in HEADS],'Study fit inventory differs')
    for name,expected in manifest['snapshot_sha256'].items():require(digest((run/name).read_bytes())==expected,'Study frozen input changed')
    require(summary['test_evaluated'] is False and summary['development_only'] is True,'Study evaluation scope changed')
    states=[];components=[]
    for item in manifest['plan']:
        directory=run/'components'/f'{item["seed"]}_{item["head"]}';state=json.loads((directory/'attempt.json').read_text())
        require(state['binding_sha256']==digest(canonical(manifest)) and state['run_dir']==str(directory) and state['state'] in ('complete','interrupted','recovered_complete_unknown_cost'),'Study attempt binding/state differs');states.append(state)
    for item in summary['components']:
        path=Path(item['summary']);require(digest(path.read_bytes())==item['sha256'],'Study component changed');components.append(audit_component(path))
    for name,expected in summary['attempt_sha256'].items():require(digest((run/name).read_bytes())==expected,'Study attempt changed')
    require(aggregate(run,manifest,states,components)==summary,'Study aggregate/paired denominators differ')
    print(f"Pair-head study audit passed: {summary['completed_fits']}/{summary['planned_fits']} fits, full development replay and matched initializations.")
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--verify',action='store_true');parser.add_argument('--resume',type=Path);parser.add_argument('--component-run',type=Path);args=parser.parse_args()
    if args.component_run:return train_component(args.component_run)
    if args.verify:return audit(ROOT/'results'/f'{NAME}_summary.json')
    if args.resume:run=args.resume.resolve();manifest=json.loads((run/'manifest.json').read_text())
    else:
        config=validate_config(json.loads((ROOT/'configs/pair_head_development_study.json').read_text()));source_bytes,source,snapshots,splits=frozen_inputs(ROOT/'results/exact_comparative_development_summary.json')
        run=ROOT/'results'/f'{NAME}_runs'/timestamp();run.mkdir(parents=True);(run/'source_summary.json').write_bytes(source_bytes)
        for name,data in snapshots.items():(run/(name+'.json')).write_bytes(data)
        paths=[Path(__file__),ROOT/'scripts/train_sampled_comparative_development.py',*[ROOT/'src/rnastable'/name for name in ('pair_head_study.py','context_training.py','helix_pairs.py','stack_pairs.py','global_sparse_pairs.py','context_pairs.py','full_pair_supervision.py','exact_sparse_pairs.py','structure_model.py','reference.py','reference_audit.py','exposures.py','scoring.py','artifacts.py')]]
        manifest={'run_dir':str(run),'config':config,'base_config':source['config'],'plan':[{'seed':seed,'head':head} for seed in config['seeds'] for head in HEADS],
                  'snapshot_sha256':{name:digest((run/name).read_bytes()) for name in ('source_summary.json','train.json','validation.json')},'code_sha256':{str(path.resolve()):digest(path.read_bytes()) for path in paths},
                  'policy':'Same exposed development snapshots and matched base initializations; compare zero-initialized sequence-only feature heads. No fresh test.'}
        atomic_json(run/'manifest.json',manifest)
    with exclusive_driver(run/'.driver.lock'):
        if (run/'summary.json').exists():return audit(run/'summary.json')
        states=[];components=[]
        for item in manifest['plan']:
            directory=run/'components'/f'{item["seed"]}_{item["head"]}';directory.mkdir(parents=True,exist_ok=True);attempt_path=directory/'attempt.json'
            if attempt_path.exists():
                state=json.loads(attempt_path.read_text());require(state['binding_sha256']==digest(canonical(manifest)),'Study attempt binding changed')
                if state['state']=='started':state['state']='recovered_complete_unknown_cost' if (directory/'summary.json').exists() else 'interrupted';atomic_json(attempt_path,state)
            else:
                config=manifest['config'];deadline=datetime.fromisoformat(config['deadline_utc'])
                if datetime.now(timezone.utc)+timedelta(seconds=config['component_timeout_seconds']+15)>deadline:
                    atomic_json(run/'progress.json',{'state':'deadline_deferred','recorded_components':len(states)});return None
                for name,expected in manifest['code_sha256'].items():require(digest(Path(name).read_bytes())==expected,'Study execution source changed')
                atomic_json(directory/'manifest.json',{'study_manifest_sha256':digest((run/'manifest.json').read_bytes()),'seed':item['seed'],'head':item['head'],'config':head_config(manifest['base_config'],item['head'],item['seed'])})
                state={'binding_sha256':digest(canonical(manifest)),'run_dir':str(directory),'state':'started'};atomic_json(attempt_path,state)
                print(f"Pair-head fit: seed {item['seed']}, {item['head']}",flush=True)
                result=run_bounded([sys.executable,str(Path(__file__).resolve()),'--component-run',str(directory)],'',config['component_timeout_seconds'],config['memory_limit_gib'],ROOT)
                output=result.pop('stdout','');(directory/'process.log').write_text(output+'\nSTDERR:\n'+result.get('error',''))
                state.update(state='complete',result=result);atomic_json(attempt_path,state)
            states.append(state)
            if (directory/'summary.json').exists():components.append(audit_component(directory/'summary.json'))
        summary=aggregate(run,manifest,states,components);atomic_json(run/'summary.json',summary)
        report=['# Matched-seed pair-head development study','',manifest['policy'],'',*summary['limitations'],'',
                '| Seed | Head | Status | Selected epoch | Development pair F1 | Parameters |','|---:|---|---|---:|---:|---:|']
        for row in summary['rows']:report.append(f"| {row['seed']} | {row['head']} | {row['status']} | {row['selected_epoch']} | {row['validation_pair_f1']} | {row['parameters']} |")
        report+=['','Paired differences from the matched-seed baseline:',*['- '+str(row) for row in summary['paired_deltas']]]
        publish(ROOT,NAME,summary,summary['rows'],list(summary['rows'][0]),'\n'.join(report)+'\n');print(json.dumps(summary,indent=2));return summary

if __name__=='__main__':main()
