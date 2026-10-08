#!/usr/bin/env python3
"""Replay constrained pools/proxy scores/native decisions, raw folds and equal request budgets."""
import json
import math
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.checkpoint_prior import TargetScorer
from rnastable.context_inference import load_checkpoint
from rnastable.exposures import read_exposure,exposure_records
from rnastable.folding import parse_output,tool_commands
from rnastable.optimization import check_constraints
from rnastable.pooled_proposals import pooled_search
from rnastable.reference import digest
from rnastable.native_journal import NativeJournal,canonical
from rnastable.pooled_native import PooledNativeRunner
from rnastable.reference_audit import require
from rnastable.sequences import read_fasta
from rnastable.selection import select_finalist
from run_checkpoint_prior_pilot import POLICIES,result_row


def without_proxy_timing(search):
    return {**search,'history':[{k:v for k,v in r.items() if k!='proxy_wall_seconds'} for r in search['history']]}


def audit_prior(path):
    summary=json.loads(Path(path).read_text());run=Path(summary['run_dir']);require(summary['complete'] is True and summary['test_accuracy_evaluated'] is False and summary['model_fitted'] is False and summary==json.loads((run/'summary.json').read_text()),'Pilot identity differs')
    require(digest((run/'manifest.json').read_bytes())==summary['manifest_sha256'],'Pilot manifest changed');manifest=json.loads((run/'manifest.json').read_text());config=manifest['config'];require(manifest['run_dir']==str(run) and manifest['policies']==list(POLICIES) and config['steps']==8 and config['pool_size']==16,'Pilot plan differs')
    for name,sha in manifest['snapshot_sha256'].items():require(digest((run/name).read_bytes())==sha,'Pilot snapshot changed')
    for name,sha in summary['artifact_sha256'].items():require(digest((run/name).read_bytes())==sha,'Pilot artifact changed')
    source_bytes,model_config,checkpoint,_=load_checkpoint(run/'source_summary.json');require(model_config==manifest['model_config'] and str(checkpoint)==manifest['checkpoint'] and digest(checkpoint.read_bytes())==manifest['checkpoint_sha256'],'Pilot source model differs')
    resource=json.loads((run/'resource_summary.json').read_text());require(resource['complete'] is True and resource['accuracy_evaluated'] is False and resource==json.loads((Path(resource['run_dir'])/'summary.json').read_text()),'Synthetic resource source differs')
    require((run/'resource_inputs.json').read_bytes()==(Path(resource['run_dir'])/'inputs.json').read_bytes(),'Synthetic input source differs');input_index=manifest.get('input_index',0);record=json.loads((run/'resource_inputs.json').read_text())[input_index];original=record['sequence'];require(record['id']=='synthetic_'+str((1000,5000,10000)[input_index]) and len(original)==(1000,5000,10000)[input_index] and read_fasta(run/'input.fasta')==[(record['id'],original)],'Pilot input binding differs')
    folds=json.loads((run/'folds.json').read_text());lookup={(f['policy'],f['phase'],f['step']):f for f in folds};require(len(lookup)==len(folds),'Duplicate native request');inventory=[];expected_events=[('all',0,'validation_started',[record])];rows=[];results={}
    commands=tool_commands(ROOT,config)
    for policy in POLICIES:
        result=json.loads((run/policy/'result.json').read_text());require(result['policy']==policy,'Arm identity differs');results[policy]=result
        def evaluator(sequence,step):
            key=(policy,'baseline' if step==0 else 'proposal',step);require(key in lookup,'Missing native search request');fold=lookup[key];require(fold['sequence_sha256']==digest(sequence.encode()),'Selected native proposal differs');return {k:v for k,v in fold.items() if k not in ('policy','phase','step','sequence_sha256')}
        replay=pooled_search(original,config,policy,evaluator,lambda seq,structure:TargetScorer(run/'source_summary.json',seq,structure))
        require(without_proxy_timing(replay)==without_proxy_timing(result['search']),'Constrained pool/proxy/native-decision replay differs')
        for row in result['search']['history']:
            if 'proxy_wall_seconds' in row:
                require(type(row['proxy_wall_seconds']) in (int,float) and math.isfinite(row['proxy_wall_seconds']) and row['proxy_wall_seconds']>=0,'Invalid proxy timing')
            for seq in row['pool']:check_constraints(seq,original,config)
            if row['pool']:expected_events.append((policy,row['step'],'test_started',[{'id':f'{policy}_{row["step"]}_{i}','sequence':seq} for i,seq in enumerate(row['pool'])]))
        finalist=replay['sequence'];inventory.append((policy,'baseline',0,original))
        inventory += [(policy,'proposal',r['step'],r['pool'][r['selected_index']]) for r in replay['history'] if 'fold' in r]
        inventory += [(policy,'validation_input',0,original),(policy,'validation_finalist',0,finalist)]
        before={k:v for k,v in lookup[(policy,'validation_input',0)].items() if k not in ('policy','phase','step','sequence_sha256')};after={k:v for k,v in lookup[(policy,'validation_finalist',0)].items() if k not in ('policy','phase','step','sequence_sha256')}
        require(result['validation']=={'input':before,'finalist':after},'Validation fold binding differs');selection=select_finalist(original,finalist,replay['status'],before,after);require(selection==result['selection'],'Native final selection differs');selected=finalist if selection['source']=='finalist' else original;check_constraints(selected,original,config)
        require(read_fasta(run/policy/'finalist.fasta')==[(policy+'_finalist',finalist)] and read_fasta(run/policy/'selected.fasta')==[(policy+'_selected',selected)] and digest(selected.encode())==result['selected_sha256'],'Selected/finalist FASTA differs')
        expected_row=result_row(policy,result['search'],selection,original,selected,config);require(expected_row==result['row'],'Arm denominators/metrics differ');rows.append(expected_row)
    require([(f['policy'],f['phase'],f['step'],f['sequence_sha256']) for f in folds]==[(p,phase,step,digest(seq.encode())) for p,phase,step,seq in inventory],'Native request inventory/order differs')
    for (policy,phase,step,sequence),fold in zip(inventory,folds):
        tool='LinearFold' if phase in ('baseline','proposal') else 'ViennaRNA';require(fold['tool']==tool,'Native tool differs')
        if fold['status']!='unavailable':require(fold['device']=='CPU' and fold['command']==commands[tool][0],'Native CPU command differs')
        if 'raw_output' in fold:
            p=Path(fold['raw_output']);require(p.resolve().parent==(run/policy).resolve() and digest(p.read_bytes())==fold['raw_sha256'],'Native raw output changed')
        if fold['status']=='ok':
            require('raw_output' in fold and fold['returncode']==0 and p.read_text().splitlines()[0].strip()==sequence,'Native success/sequence binding differs');parsed=parse_output(tool,p.read_text(),len(sequence));require(all(fold[k]==v for k,v in parsed.items()),'Native structure/energy parsing differs')
    if 'cost_accounting' in summary:
        journal=NativeJournal(run/'native_journal',digest(canonical(manifest)))
        adapter=PooledNativeRunner.__new__(PooledNativeRunner);adapter.root=ROOT;adapter.run=run;adapter.config=config;adapter.journal=journal
        require(set(p.stem for p in journal.directory.glob('*.json'))=={f'{policy}_{phase}_{step:04d}' for policy,phase,step,_ in inventory},'Journal request inventory differs')
        for (policy,phase,step,sequence),fold in zip(inventory,folds):
            payload=journal.read(f'{policy}_{phase}_{step:04d}')
            require(payload['sequence_sha256']==digest(sequence.encode()) and payload['parameters']==adapter.parameters(policy,phase,step),'Journal request binding differs')
            require(payload['state'] in ('complete','interrupted') and payload['result']=={k:v for k,v in fold.items() if k not in ('policy','phase','step','sequence_sha256')},'Journal result differs')
            if payload['state']=='interrupted':require(payload['result'].get('interrupted') is True and 'wall_seconds' not in payload['result'] and 'mfe_kcal_mol' not in payload['result'],'Interrupted native result/cost differs')
        expected=adapter.accounting();cost=summary['cost_accounting'];measured=cost['native']
        for key in ('unique_requests','completed_requests','unknown_requests','known_native_wall_seconds','total_cost_known'):require(expected[key]==measured[key],'Journal cost denominator differs')
        require(measured['current_invocation_callbacks']+measured['current_invocation_cache_hits']==len(folds),'Native invocation accounting differs')
        attempts=[json.loads(p.read_text()) for p in sorted((run/'attempts').glob('*.json'))]
        require(bool(attempts) and all(a['state'] in ('started','complete') and type(a['completed_proxy_calls']) is int and 0<=a['completed_proxy_calls']<=config['steps']*config['pool_size'] and type(a['known_proxy_wall_seconds']) in (int,float) and math.isfinite(a['known_proxy_wall_seconds']) and a['known_proxy_wall_seconds']>=0 for a in attempts),'Invalid proxy execution accounting')
        require(cost['completed_proxy_calls_across_attempts']==sum(a['completed_proxy_calls'] for a in attempts) and cost['known_proxy_wall_seconds_across_attempts']==sum(a['known_proxy_wall_seconds'] for a in attempts) and cost['incomplete_attempts']==sum(a['state']!='complete' for a in attempts),'Proxy attempt accounting differs')
        require(cost['completed_proxy_calls_across_attempts']>=sum(r['proxy_evaluations'] for r in rows),'Proxy replay costs omitted')
    events=summary['exposure_events'];require(len(events)==len(expected_events),'Exposure step inventory differs');require(set(Path(e['event']['path']).resolve() for e in events)==set(p.resolve() for p in (run/'exposures').glob('*.json')),'Exposure file inventory differs')
    for item,(policy,step,stage,records) in zip(events,expected_events):
        event=item['event'];p=Path(event['path']);require(item['policy']==policy and item['step']==step and p.resolve().parent==(run/'exposures').resolve() and digest(p.read_bytes())==event['sha256'],'Exposure event changed');data=read_exposure(p);require(data['stage']==event['stage']==stage and data['records']==exposure_records(records,str(run)+' '+stage),'Exposure pool binding differs')
    requests={p:{phase:sum(f['policy']==p and f['phase']==phase for f in folds) for phase in ('baseline','proposal','validation_input','validation_finalist')} for p in POLICIES};require(requests==summary['native_request_counts'] and rows==summary['rows'],'Pilot aggregate requests/rows differ');require(summary['equal_native_proposal_budget_measured']==all(r['attempted_proposal_folds']==config['steps'] for r in rows),'Budget fulfillment differs')
    print(f'Checkpoint-prior audit passed:3 exact constrained trajectories, {len(folds)} native requests, pool/checkpoint logits, selections, exposures and budget denominators verified. No accuracy test or fitting.')
    return summary

if __name__=='__main__':audit_prior(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'results/checkpoint_prior_pilot_summary.json')
