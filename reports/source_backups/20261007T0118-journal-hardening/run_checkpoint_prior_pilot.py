#!/usr/bin/env python3
"""Three proposal-ranking arms, fixed synthetic input/budgets, native-only acceptance."""
import argparse
import json
import time
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import timestamp,publish,sha256
from rnastable.checkpoint_prior import TargetScorer
from rnastable.context_inference import load_checkpoint
from rnastable.exposures import record_exposure,read_exposure,exposure_records
from rnastable.folding import tool_commands
from rnastable.native_journal import atomic_json,canonical,exclusive_driver
from rnastable.pooled_native import PooledNativeRunner,native_runtime
from rnastable.optimization import check_constraints,hamming,validate_optimization_config
from rnastable.pooled_proposals import pooled_search
from rnastable.reference import digest
from rnastable.selection import select_finalist
from rnastable.sequences import write_fasta

POLICIES=('random_pool','compatibility_only','checkpoint_prior')


def result_row(policy,search,selection,original,selected,config):
    return {'policy':policy,'planned_proposal_folds':config['steps'],'attempted_proposal_folds':sum('fold' in r for r in search['history']),'successful_proposal_folds':sum(r.get('fold',{}).get('status')=='ok' for r in search['history']),'pool_candidates':sum(len(r['pool']) for r in search['history']),'proxy_evaluations':search['proxy_evaluations'],'accepted_steps':search['accepted_steps'],'search_status':search['status'],'linearfold_delta_kcal_mol':search['best'].get('mfe_kcal_mol')-search['baseline'].get('mfe_kcal_mol') if search['baseline']['status']=='ok' else None,'selection_source':selection['source'],'selection_reason':selection['reason'],'candidate_vienna_delta_kcal_mol':selection['candidate_vienna_delta_kcal_mol'],'selected_vienna_delta_kcal_mol':selection['selected_vienna_delta_kcal_mol'],'selected_mutations':hamming(original,selected),'proxy_wall_seconds':sum(r.get('proxy_wall_seconds',0) for r in search['history'])}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resume',type=Path)
    parser.add_argument('--replication-component')
    parser.add_argument('--input-index',type=int,choices=(0,1,2),default=None)
    parser.add_argument('--seed',type=int)
    parser.add_argument('--publish-name',default='checkpoint_prior_pilot')
    args=parser.parse_args()
    config=validate_optimization_config(json.loads((ROOT/'configs/checkpoint_prior_pilot.json').read_text()))
    if args.resume:
        run=args.resume.resolve();manifest=json.loads((run/'manifest.json').read_text());config=manifest['config']
        if args.replication_component is not None and args.replication_component!=manifest.get('replication_component'):raise ValueError('Resume replication binding differs')
        if args.seed is not None and args.seed!=config['seed']:raise ValueError('Resume seed differs')
        if args.input_index is not None and args.input_index!=manifest['input_index']:raise ValueError('Resume input differs')
        source=run/'source_summary.json';resources=run/'resource_summary.json';input_path=run/'resource_inputs.json';input_index=manifest['input_index']
    else:
        input_index=args.input_index or 0
        if args.seed is not None:config['seed']=args.seed
        source=ROOT/'results/stack_comparative_development_summary.json';resources=ROOT/'results/stack_scalability_summary.json'
        input_path=Path(json.loads(resources.read_text())['run_dir'])/'inputs.json'
        run=ROOT/'results/checkpoint_prior_pilot_runs'/timestamp();run.mkdir(parents=True,exist_ok=False)
    source_bytes,model_config,checkpoint,_=load_checkpoint(source)
    resource_bytes=resources.read_bytes();input_bytes=input_path.read_bytes();record=json.loads(input_bytes)[input_index];original=record['sequence']
    if record['id']!='synthetic_'+str((1000,5000,10000)[input_index]) or len(original)!=(1000,5000,10000)[input_index] or config['steps']!=8 or config['pool_size']!=16:raise ValueError('Invalid fixed synthetic pilot plan')
    check_constraints(original,original,config)
    if not args.resume:
        for name,data in [('source_summary.json',source_bytes),('resource_summary.json',resource_bytes),('resource_inputs.json',input_bytes)]:(run/name).write_bytes(data)
        write_fasta(run/'input.fasta',record['id'],original)
    paths=[Path(__file__),*sorted((ROOT/'src/rnastable').glob('*.py'))]
    fresh_manifest={'replication_component':args.replication_component,'native_runtime':native_runtime(ROOT,config),'input_index':input_index,'run_dir':str(run),'config':config,'policies':list(POLICIES),'model_config':model_config,'checkpoint':str(checkpoint),'checkpoint_sha256':digest(checkpoint.read_bytes()),'snapshot_sha256':{n:digest((run/n).read_bytes()) for n in ('source_summary.json','resource_summary.json','resource_inputs.json','input.fasta')},'code_sha256':{str(p):digest(p.read_bytes()) for p in paths},'policy':'Previously exposed synthetic resource input, no accuracy labels or model fitting. Native strict energy acceptance and ViennaRNA final selection. Random-pool/compatibility-only controls; equal planned native fold budgets, added neural proxy costs reported separately.'}
    if not args.resume:
        manifest=fresh_manifest;atomic_json(run/'manifest.json',manifest)
    with exclusive_driver(run/'.driver.lock'):
        runner=PooledNativeRunner(ROOT,run,config,manifest)
        if (run/'summary.json').exists():
            from verify_checkpoint_prior_pilot import audit_prior
            summary=audit_prior(run/'summary.json');print(json.dumps({'resumed_complete_run':str(run),'native_callbacks':0}));return summary
        return execute(run,config,manifest,record,original,runner,args.publish_name)


def execute(run,config,manifest,record,original,runner,publish_name):
    def exposed(stage,records):
        expected=exposure_records(records,str(run)+' '+stage)
        for path in sorted((run/'exposures').glob('*.json')):
            data=read_exposure(path)
            if data['stage']==stage and data['records']==expected:
                return {'path':str(path),'sha256':digest(path.read_bytes()),'stage':stage}
        return record_exposure(run,stage,records)
    attempt_path=run/'attempts'/(timestamp()+'.json');attempt={'state':'started','completed_proxy_calls':0,'known_proxy_wall_seconds':0.0}
    atomic_json(attempt_path,attempt)
    class CountedScorer:
        def __init__(self,seq,structure):
            self.scorer=TargetScorer(run/'source_summary.json',seq,structure);self.binding=self.scorer.binding
        def score(self,seq):
            begin=time.monotonic();result=self.scorer.score(seq)
            attempt['completed_proxy_calls']+=1;attempt['known_proxy_wall_seconds']+=time.monotonic()-begin;atomic_json(attempt_path,attempt)
            return result
    events=[{'policy':'all','step':0,'event':exposed('validation_started',[record])}];folds=[];arms=[]
    for policy in POLICIES:
        arm=run/policy;arm.mkdir(exist_ok=True)
        def native(sequence,phase,step):
            fold=runner.run_request(policy,sequence,phase,step)
            folds.append({'policy':policy,'phase':phase,'step':step,'sequence_sha256':sha256(sequence),**fold});return fold
        def evaluator(sequence,step):print(f'Pool search {policy}: native step{step}/{config["steps"]}',flush=True);return native(sequence,'baseline' if step==0 else 'proposal',step)
        def on_pool(step,pool):events.append({'policy':policy,'step':step,'event':exposed('test_started',[{'id':f'{policy}_{step}_{i}','sequence':seq} for i,seq in enumerate(pool)])})
        search=pooled_search(original,config,policy,evaluator,CountedScorer,on_pool);finalist=search['sequence'];check_constraints(finalist,original,config)
        before=native(original,'validation_input',0);after=native(finalist,'validation_finalist',0);selection=select_finalist(original,finalist,search['status'],before,after);selected=finalist if selection['source']=='finalist' else original;check_constraints(selected,original,config)
        write_fasta(arm/'finalist.fasta',policy+'_finalist',finalist);write_fasta(arm/'selected.fasta',policy+'_selected',selected)
        result={'policy':policy,'search':search,'validation':{'input':before,'finalist':after},'selection':selection,'selected_sha256':sha256(selected),'row':result_row(policy,search,selection,original,selected,config)};(arm/'result.json').write_text(json.dumps(result,indent=2)+'\n');arms.append(result)
    (run/'folds.json').write_text(json.dumps(folds,indent=2)+'\n');rows=[a['row'] for a in arms]
    requests={p:{phase:sum(f['policy']==p and f['phase']==phase for f in folds) for phase in ('baseline','proposal','validation_input','validation_finalist')} for p in POLICIES}
    attempt['state']='complete';atomic_json(attempt_path,attempt)
    attempts=[json.loads(p.read_text()) for p in sorted((run/'attempts').glob('*.json'))]
    cost={'native':runner.accounting(),'completed_proxy_calls_across_attempts':sum(a['completed_proxy_calls'] for a in attempts),'known_proxy_wall_seconds_across_attempts':sum(a['known_proxy_wall_seconds'] for a in attempts),'incomplete_attempts':sum(a['state']!='complete' for a in attempts),'proxy_cost_policy':'Completed scorer calls across all attempts; incomplete attempts may have additional unknown work. Pool ranking wall includes scoring and journal writes; audit replay costs excluded.'}
    summary={'cost_accounting':cost,'input_id':record['id'],'seed':config['seed'],'complete':True,'run_dir':str(run),'test_accuracy_evaluated':False,'model_fitted':False,'manifest_sha256':digest((run/'manifest.json').read_bytes()),'artifact_sha256':{n:digest((run/n).read_bytes()) for n in ['folds.json',*[str(p.relative_to(run)) for p in sorted((run/'native_journal').glob('*.json'))],*[str(p.relative_to(run)) for p in sorted((run/'attempts').glob('*.json'))],*[p+'/result.json' for p in POLICIES],*[p+'/'+name for p in POLICIES for name in ('finalist.fasta','selected.fasta')]]},'exposure_events':events,'rows':rows,'native_request_counts':requests,'equal_native_proposal_budget_measured':all(r['attempted_proposal_folds']==config['steps'] for r in rows),'limitations':['One exposed synthetic input/one search seed per component; no fresh test, generalization or biological stability claim.','Pair logits are proposal-ranking proxies, not folding energy; native tools decide acceptance/selection.','Neural arm adds128 potential proxy calls beyond matched native requests; wall/costs are not assumed equal.','Original-template compatibility is a control/prior, not proof of retained biological function.']};atomic_json(run/'summary.json',summary)
    report=['# Checkpoint proposal-prior pilot','',manifest['policy'],'',f'Run: `{run}`','','| Policy | Native proposals | Proxy calls | Accepted | Selected Vienna delta | Selected mutations |','|---|---:|---:|---:|---:|---:|']
    for r in rows:report.append(f'| {r["policy"]} | {r["attempted_proposal_folds"]} | {r["proxy_evaluations"]} | {r["accepted_steps"]} | {r["selected_vienna_delta_kcal_mol"]} | {r["selected_mutations"]} |')
    report+=['',f'Cost accounting: `{json.dumps(cost,sort_keys=True)}`','',*summary['limitations']];publish(ROOT,publish_name,summary,rows,list(rows[0]),'\n'.join(report)+'\n');print(json.dumps(summary,indent=2));return summary

if __name__=='__main__':main()
