"""Separate longer-budget native validation of previously frozen synthetic finalists."""
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
from .artifacts import timestamp,publish
from .exposures import record_exposure,read_exposure,exposure_records
from .folding import fold_sequence,parse_output,tool_commands
from .native_journal import NativeJournal,atomic_json,canonical,exclusive_driver
from .optimization import check_constraints,hamming
from .pooled_native import native_runtime
from .reference import digest
from .reference_audit import require
from .selection import select_finalist
from .sequences import read_fasta,write_fasta

POLICIES=('random_pool','compatibility_only','checkpoint_prior')
NAME='checkpoint_prior_reference_extension'


def validate_config(config):
    if config['input_indices']!=[2] or config['seeds']!=[20261006,20261007] or type(config['planned_requests']) is not int or config['planned_requests']!=12:raise ValueError('Invalid fixed reference extension plan')
    if config['temperature_c']!=37 or type(config['beam_size']) is not int or config['beam_size']<1:raise ValueError('Invalid native reference settings')
    for key in ('timeout_seconds','memory_limit_gib'):
        if type(config[key]) not in (int,float) or not 0<config[key]<= (600 if key=='timeout_seconds' else 8):raise ValueError('Invalid bounded reference budget')
    deadline=datetime.fromisoformat(config['deadline_utc'])
    if deadline.tzinfo is None:raise ValueError('Reference deadline must include timezone')
    return json.loads(canonical(config))


def can_admit(config,now=None):
    now=now or datetime.now(timezone.utc)
    return now+timedelta(seconds=config['timeout_seconds']+15)<=datetime.fromisoformat(config['deadline_utc'])


def prepare(root,source_path,config,code_paths):
    root=Path(root);source_path=Path(source_path).resolve();config=validate_config(config)
    source=json.loads(source_path.read_text())
    require(source['complete'] is True and source['test_accuracy_evaluated'] is False and source['model_fitted'] is False,'Invalid frozen source replication')
    run=root/'results'/f'{NAME}_runs'/timestamp();run.mkdir(parents=True,exist_ok=False)
    (run/'source_summary.json').write_bytes(source_path.read_bytes());arms=[];records=[]
    for item in source['components']:
        path=Path(item['summary']);require(digest(path.read_bytes())==item['sha256'],'Source component changed')
        summary=json.loads(path.read_text());source_run=Path(summary['run_dir']);manifest=json.loads((source_run/'manifest.json').read_text())
        if manifest.get('input_index') not in config['input_indices']:continue
        require(summary['seed'] in config['seeds'],'Unexpected extension seed')
        source_original=read_fasta(source_run/'input.fasta')[0][1]
        for policy in POLICIES:
            key=f'{summary["seed"]}_{policy}';arm_dir=run/'arms'/key;arm_dir.mkdir(parents=True)
            finalist=read_fasta(source_run/policy/'finalist.fasta')[0][1];original=source_original
            result=json.loads((source_run/policy/'result.json').read_text());check_constraints(finalist,original,manifest['config'])
            require(result['search']['sequence']==finalist and len(original)==10000,'Frozen finalist identity differs')
            write_fasta(arm_dir/'input.fasta',key+'_input',original);write_fasta(arm_dir/'finalist.fasta',key+'_finalist',finalist)
            arm={'key':key,'seed':summary['seed'],'policy':policy,'source_summary':str(path),'source_summary_sha256':item['sha256'],'source_config':manifest['config'],
                 'source_search_status':result['search']['status'],'source_row':result['row'],'input_sha256':digest(original.encode()),'finalist_sha256':digest(finalist.encode())}
            arms.append(arm);records.extend([{'id':key+'_input','sequence':original},{'id':key+'_finalist','sequence':finalist}])
    require([(a['seed'],a['policy']) for a in arms]==[(seed,policy) for seed in config['seeds'] for policy in POLICIES],'Reference arm inventory differs')
    event=record_exposure(run,'validation_started',records)
    manifest={'schema_version':1,'run_dir':str(run),'config':config,'source_summary_sha256':digest(source_path.read_bytes()),'arms':arms,'native_runtime':native_runtime(root,config),
              'snapshot_sha256':{str(path.relative_to(run)):digest(path.read_bytes()) for path in sorted((run/'arms').glob('*/*.fasta'))},
              'code_sha256':{str(Path(path).resolve()):digest(Path(path).read_bytes()) for path in code_paths},'exposure_event':event,
              'policy':'Frozen exposed synthetic finalists, separate longer native validation budget. No new search, model fitting, accuracy labels, test-set or biological stability claim.'}
    atomic_json(run/'manifest.json',manifest);return run


def check_binding(root,run,manifest,for_execution=True):
    require(manifest['schema_version']==1 and manifest['run_dir']==str(run),'Reference extension identity differs')
    validate_config(manifest['config'])
    require(digest((run/'source_summary.json').read_bytes())==manifest['source_summary_sha256'],'Reference source snapshot changed')
    for name,expected in manifest['snapshot_sha256'].items():require(digest((run/name).read_bytes())==expected,'Reference FASTA snapshot changed')
    require([(a['seed'],a['policy']) for a in manifest['arms']]==[(seed,policy) for seed in manifest['config']['seeds'] for policy in POLICIES],'Reference fixed arm inventory differs')
    source=json.loads((run/'source_summary.json').read_text());source_components={item['summary']:item['sha256'] for item in source['components']}
    for arm in manifest['arms']:
        source_path=Path(arm['source_summary']);require(source_components.get(str(source_path))==arm['source_summary_sha256'] and digest(source_path.read_bytes())==arm['source_summary_sha256'],'Reference source component changed')
        component=json.loads(source_path.read_text());source_run=Path(component['run_dir']);source_manifest=json.loads((source_run/'manifest.json').read_text());source_result=json.loads((source_run/arm['policy']/'result.json').read_text())
        require(component['seed']==arm['seed'] and source_manifest['input_index']==2 and source_manifest['config']==arm['source_config'],'Reference source arm/config binding differs')
        require(source_result['row']==arm['source_row'] and source_result['search']['status']==arm['source_search_status'],'Reference source search/row differs')
        original=read_fasta(source_run/'input.fasta')[0][1];finalist=read_fasta(source_run/arm['policy']/'finalist.fasta')[0][1]
        require(digest(original.encode())==arm['input_sha256'] and digest(finalist.encode())==arm['finalist_sha256'] and source_result['search']['sequence']==finalist,'Reference frozen source sequence differs')
    if for_execution:
        for name,expected in manifest['code_sha256'].items():require(digest(Path(name).read_bytes())==expected,'Reference execution source changed')
        require(native_runtime(root,manifest['config'])==manifest['native_runtime'],'Reference native runtime changed')


def parameters(root,run,manifest,arm,phase):
    config=manifest['config'];command,cwd=tool_commands(Path(root),config).get('ViennaRNA',(None,None))
    return {'tool':'ViennaRNA','device':'CPU','command':command,'cwd':str(cwd) if cwd else None,'config':config,
            'raw_output':str(run/'arms'/arm['key']/f'{phase}_ViennaRNA.txt')}


def collect(run,manifest,journal):
    rows=[];folds=[]
    for arm in manifest['arms']:
        key=arm['key'];arm_dir=run/'arms'/key;original=read_fasta(arm_dir/'input.fasta')[0][1];finalist=read_fasta(arm_dir/'finalist.fasta')[0][1]
        requests=[]
        for phase in ('input','finalist'):
            payload=journal.read(key+'_'+phase);fold=payload['result'];requests.append(fold);folds.append({'key':key+'_'+phase,'seed':arm['seed'],'policy':arm['policy'],'phase':phase,'sequence_sha256':payload['sequence_sha256'],**fold})
        decision=select_finalist(original,finalist,arm['source_search_status'],*requests);selected=finalist if decision['source']=='finalist' else original;check_constraints(selected,original,arm['source_config'])
        rows.append({'input_id':'synthetic_10000','seed':arm['seed'],'policy':arm['policy'],'planned_reference_requests':2,'input_status':requests[0]['status'],'finalist_status':requests[1]['status'],
                     'candidate_vienna_delta_kcal_mol':decision['candidate_vienna_delta_kcal_mol'],'selected_vienna_delta_kcal_mol':decision['selected_vienna_delta_kcal_mol'],
                     'selection_source':decision['source'],'selection_reason':decision['reason'],'selected_mutations':hamming(original,selected),'selected_sha256':digest(selected.encode()),
                     'prior_selected_vienna_delta_kcal_mol':arm['source_row']['selected_vienna_delta_kcal_mol']})
    return rows,folds


def execute(root,run,callback=None):
    root=Path(root);run=Path(run).resolve();manifest=json.loads((run/'manifest.json').read_text())
    with exclusive_driver(run/'.driver.lock'):
        if (run/'summary.json').exists():return audit(root,run/'summary.json')
        check_binding(root,run,manifest);journal=NativeJournal(run/'native_journal',digest(canonical(manifest)));callback=callback or fold_sequence
        for arm in manifest['arms']:
            for phase in ('input','finalist'):
                key=arm['key']+'_'+phase;path=run/'arms'/arm['key']/(phase+'.fasta');sequence=read_fasta(path)[0][1];params=parameters(root,run,manifest,arm,phase)
                if not journal.path(key).exists() and not can_admit(manifest['config']):
                    atomic_json(run/'progress.json',{'state':'deadline_deferred','planned_requests':manifest['config']['planned_requests'],'recorded_requests':len(list(journal.directory.glob('*.json')))});return None
                def native():
                    fold=callback(root,sequence,manifest['config'],'ViennaRNA',Path(params['raw_output']))
                    if 'raw_output' in fold:fold['raw_sha256']=digest(Path(fold['raw_output']).read_bytes())
                    return fold
                print(f"Extended reference: {key}, timeout {manifest['config']['timeout_seconds']}s",flush=True)
                journal.run(key,sequence,params,native)
                atomic_json(run/'progress.json',{'state':'running','last_request':key,'recorded_requests':len(list(journal.directory.glob('*.json')))})
        rows,folds=collect(run,manifest,journal)
        for arm,row in zip(manifest['arms'],rows):
            directory=run/'arms'/arm['key'];seq=read_fasta(directory/('finalist.fasta' if row['selection_source']=='finalist' else 'input.fasta'))[0][1];write_fasta(directory/'selected.fasta',arm['key']+'_selected',seq)
        atomic_json(run/'folds.json',folds);payloads=[journal.read(f['key']) for f in folds]
        summary={'complete':True,'run_dir':str(run),'manifest_sha256':digest((run/'manifest.json').read_bytes()),'test_accuracy_evaluated':False,'model_fitted':False,'new_search_performed':False,
                 'planned_native_requests':manifest['config']['planned_requests'],'unique_native_requests':len(folds),'completed_native_requests':sum(p['state']=='complete' for p in payloads),
                 'unknown_native_requests':sum(p['state']!='complete' for p in payloads),'known_native_wall_seconds':sum(f.get('wall_seconds',0) for f in folds),
                 'current_invocation_callbacks':journal.callbacks_invoked,'current_invocation_cache_hits':journal.cache_hits,'rows':rows,
                 'artifact_sha256':{str(path.relative_to(run)):digest(path.read_bytes()) for path in [run/'folds.json',run/'native_journal'/'.binding',*sorted((run/'native_journal').glob('*.json')),*sorted((run/'arms').glob('*/selected.fasta'))]},
                 'limitations':['Separate increased validation budget on frozen previously exposed synthetic finalists; original 30-second results remain unchanged.',
                                'Descriptive native-energy validation only, no new search, fitting, accuracy test or biological stability claim.',
                                'Six arms share one synthetic sequence and two search seeds; no independent biological replication.',
                                'Unknown interruption costs stay unknown; timeouts are completed failed outcomes with measured cost. Wall times are not isolated throughput comparisons.']}
        atomic_json(run/'summary.json',summary);atomic_json(run/'progress.json',{'state':'complete','recorded_requests':len(folds)})
        report=['# Extended native validation of checkpoint-prior finalists','',manifest['policy'],'',f'Run: `{run}`',f"Separate planned budget: {summary['planned_native_requests']} requests at {manifest['config']['timeout_seconds']} seconds each.",'',
                '| Seed | Policy | Input status | Finalist status | Selected Vienna delta | Selection reason |','|---:|---|---|---|---:|---|']
        for row in rows:report.append(f"| {row['seed']} | {row['policy']} | {row['input_status']} | {row['finalist_status']} | {row['selected_vienna_delta_kcal_mol']} | {row['selection_reason']} |")
        report+=['',*summary['limitations']];publish(root,NAME,summary,rows,list(rows[0]),'\n'.join(report)+'\n');return summary


def audit(root,path):
    root=Path(root);summary=json.loads(Path(path).read_text());run=Path(summary['run_dir']);manifest=json.loads((run/'manifest.json').read_text());check_binding(root,run,manifest,False)
    require(summary['complete'] is True and summary==json.loads((run/'summary.json').read_text()) and digest((run/'manifest.json').read_bytes())==summary['manifest_sha256'],'Reference summary binding differs')
    require(summary['test_accuracy_evaluated'] is False and summary['model_fitted'] is False and summary['new_search_performed'] is False,'Reference scope differs')
    for name,expected in summary['artifact_sha256'].items():require(digest((run/name).read_bytes())==expected,'Reference artifact changed')
    event=manifest['exposure_event'];require(digest(Path(event['path']).read_bytes())==event['sha256'],'Reference exposure changed')
    records=[];journal=NativeJournal(run/'native_journal',digest(canonical(manifest)))
    expected_keys=[]
    for arm in manifest['arms']:
        directory=run/'arms'/arm['key'];original=read_fasta(directory/'input.fasta')[0][1];finalist=read_fasta(directory/'finalist.fasta')[0][1]
        require(digest(original.encode())==arm['input_sha256'] and digest(finalist.encode())==arm['finalist_sha256'],'Reference sequence differs');check_constraints(finalist,original,arm['source_config'])
        records.extend([{'sequence':original},{'sequence':finalist}])
        for phase,sequence in (('input',original),('finalist',finalist)):
            key=arm['key']+'_'+phase;expected_keys.append(key);payload=journal.read(key);params=parameters(root,run,manifest,arm,phase)
            require(payload['sequence_sha256']==digest(sequence.encode()) and payload['parameters']==params,'Extended native request binding differs')
            fold=payload['result'];require(fold['tool']=='ViennaRNA','Extended native tool differs')
            if fold['status']!='unavailable':require(fold['command']==params['command'] and fold['device']=='CPU','Extended native command differs')
            if 'raw_output' in fold:
                raw=Path(fold['raw_output']);require(str(raw)==params['raw_output'] and digest(raw.read_bytes())==fold['raw_sha256'],'Extended raw output changed')
            if fold['status']=='ok':
                require(fold['returncode']==0 and raw.read_text().splitlines()[0].strip()==sequence,'Extended native success binding differs')
                parsed=parse_output('ViennaRNA',raw.read_text(),len(sequence));require(all(fold[k]==v for k,v in parsed.items()),'Extended native parse differs')
    require(set(expected_keys)=={p.stem for p in journal.directory.glob('*.json')} and len(expected_keys)==manifest['config']['planned_requests'],'Extended native inventory differs')
    exposure=read_exposure(event['path']);require(exposure['stage']=='validation_started' and exposure['records']==exposure_records(records,str(run)+' validation_started'),'Extended validation exposure differs')
    rows,folds=collect(run,manifest,journal);require(rows==summary['rows'] and folds==json.loads((run/'folds.json').read_text()),'Extended selection/row replay differs')
    for arm,row in zip(manifest['arms'],rows):
        selected=read_fasta(run/'arms'/arm['key']/'selected.fasta')[0][1];require(digest(selected.encode())==row['selected_sha256'],'Extended selected sequence differs')
    payloads=[journal.read(key) for key in expected_keys]
    require(summary['planned_native_requests']==summary['unique_native_requests']==len(folds) and summary['completed_native_requests']==sum(p['state']=='complete' for p in payloads) and summary['unknown_native_requests']==sum(p['state']!='complete' for p in payloads),'Extended cost denominators differ')
    require(summary['known_native_wall_seconds']==sum(f.get('wall_seconds',0) for f in folds) and summary['current_invocation_callbacks']+summary['current_invocation_cache_hits']==len(folds),'Extended wall/callback accounting differs')
    print(f'Extended reference audit passed: {len(rows)} frozen finalist selections, {len(folds)} journal-bound native requests. No new search, fitting or accuracy evaluation.')
    return summary
