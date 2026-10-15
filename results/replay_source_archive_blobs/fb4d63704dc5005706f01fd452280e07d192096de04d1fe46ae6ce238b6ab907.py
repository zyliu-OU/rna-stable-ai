#!/usr/bin/env python3
"""Three proposal-ranking arms, fixed synthetic input/budgets, native-only acceptance."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import timestamp,publish,sha256
from rnastable.checkpoint_prior import TargetScorer
from rnastable.context_inference import load_checkpoint
from rnastable.exposures import record_exposure
from rnastable.folding import fold_sequence
from rnastable.optimization import check_constraints,hamming,validate_optimization_config
from rnastable.pooled_proposals import pooled_search
from rnastable.reference import digest
from rnastable.selection import select_finalist
from rnastable.sequences import write_fasta

POLICIES=('random_pool','compatibility_only','checkpoint_prior')


def result_row(policy,search,selection,original,selected,config):
    return {'policy':policy,'planned_proposal_folds':config['steps'],'attempted_proposal_folds':sum('fold' in r for r in search['history']),'successful_proposal_folds':sum(r.get('fold',{}).get('status')=='ok' for r in search['history']),'pool_candidates':sum(len(r['pool']) for r in search['history']),'proxy_evaluations':search['proxy_evaluations'],'accepted_steps':search['accepted_steps'],'search_status':search['status'],'linearfold_delta_kcal_mol':search['best'].get('mfe_kcal_mol')-search['baseline'].get('mfe_kcal_mol') if search['baseline']['status']=='ok' else None,'selection_source':selection['source'],'selection_reason':selection['reason'],'candidate_vienna_delta_kcal_mol':selection['candidate_vienna_delta_kcal_mol'],'selected_vienna_delta_kcal_mol':selection['selected_vienna_delta_kcal_mol'],'selected_mutations':hamming(original,selected),'proxy_wall_seconds':sum(r.get('proxy_wall_seconds',0) for r in search['history'])}


def main():
    config=validate_optimization_config(json.loads((ROOT/'configs/checkpoint_prior_pilot.json').read_text()));source=ROOT/'results/stack_comparative_development_summary.json';source_bytes,model_config,checkpoint,_=load_checkpoint(source)
    resources=ROOT/'results/stack_scalability_summary.json';resource_bytes=resources.read_bytes();resource=json.loads(resource_bytes);input_path=Path(resource['run_dir'])/'inputs.json';input_bytes=input_path.read_bytes();input_records=json.loads(input_bytes);record=input_records[0];original=record['sequence']
    if record['id']!='synthetic_1000' or len(original)!=1000 or config['steps']!=8 or config['pool_size']!=16:raise ValueError('Invalid fixed synthetic pilot plan')
    check_constraints(original,original,config);run=ROOT/'results/checkpoint_prior_pilot_runs'/timestamp();run.mkdir(parents=True,exist_ok=False)
    for name,data in [('source_summary.json',source_bytes),('resource_summary.json',resource_bytes),('resource_inputs.json',input_bytes)]:(run/name).write_bytes(data)
    write_fasta(run/'input.fasta',record['id'],original)
    paths=[Path(__file__),*[ROOT/'src/rnastable'/n for n in ('checkpoint_prior.py','pooled_proposals.py','optimization.py','selection.py','folding.py','context_inference.py','stack_pairs.py','global_sparse_pairs.py','context_pairs.py','exposures.py','scoring.py','reference.py')]]
    manifest={'run_dir':str(run),'config':config,'policies':list(POLICIES),'model_config':model_config,'checkpoint':str(checkpoint),'checkpoint_sha256':digest(checkpoint.read_bytes()),'snapshot_sha256':{n:digest((run/n).read_bytes()) for n in ('source_summary.json','resource_summary.json','resource_inputs.json','input.fasta')},'code_sha256':{str(p):digest(p.read_bytes()) for p in paths},'policy':'Previously exposed synthetic1000 nt input, no accuracy labels or model fitting. Native strict energy acceptance and ViennaRNA final selection. Random-pool/compatibility-only controls; equal planned native fold budgets, added neural proxy costs reported separately.'}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');events=[{'policy':'all','step':0,'event':record_exposure(run,'validation_started',[record])}];folds=[];arms=[]
    for policy in POLICIES:
        arm=run/policy;arm.mkdir()
        def native(sequence,phase,step):
            tool='LinearFold' if phase in ('baseline','proposal') else 'ViennaRNA';folding=config if tool=='LinearFold' else {**config,'timeout_seconds':config['finalist_timeout_seconds']}
            fold=fold_sequence(ROOT,sequence,folding,tool,arm/f'{phase}_{step:04d}_{tool}.txt')
            if 'raw_output' in fold:fold['raw_sha256']=digest(Path(fold['raw_output']).read_bytes())
            folds.append({'policy':policy,'phase':phase,'step':step,'sequence_sha256':sha256(sequence),**fold});return fold
        def evaluator(sequence,step):print(f'Pool search {policy}: native step{step}/{config["steps"]}',flush=True);return native(sequence,'baseline' if step==0 else 'proposal',step)
        def on_pool(step,pool):events.append({'policy':policy,'step':step,'event':record_exposure(run,'test_started',[{'id':f'{policy}_{step}_{i}','sequence':seq} for i,seq in enumerate(pool)])})
        search=pooled_search(original,config,policy,evaluator,lambda seq,structure:TargetScorer(run/'source_summary.json',seq,structure),on_pool);finalist=search['sequence'];check_constraints(finalist,original,config)
        before=native(original,'validation_input',0);after=native(finalist,'validation_finalist',0);selection=select_finalist(original,finalist,search['status'],before,after);selected=finalist if selection['source']=='finalist' else original;check_constraints(selected,original,config)
        write_fasta(arm/'finalist.fasta',policy+'_finalist',finalist);write_fasta(arm/'selected.fasta',policy+'_selected',selected)
        result={'policy':policy,'search':search,'validation':{'input':before,'finalist':after},'selection':selection,'selected_sha256':sha256(selected),'row':result_row(policy,search,selection,original,selected,config)};(arm/'result.json').write_text(json.dumps(result,indent=2)+'\n');arms.append(result)
    (run/'folds.json').write_text(json.dumps(folds,indent=2)+'\n');rows=[a['row'] for a in arms]
    requests={p:{phase:sum(f['policy']==p and f['phase']==phase for f in folds) for phase in ('baseline','proposal','validation_input','validation_finalist')} for p in POLICIES}
    summary={'complete':True,'run_dir':str(run),'test_accuracy_evaluated':False,'model_fitted':False,'manifest_sha256':digest((run/'manifest.json').read_bytes()),'artifact_sha256':{n:digest((run/n).read_bytes()) for n in ['folds.json',*[p+'/result.json' for p in POLICIES],*[p+'/'+name for p in POLICIES for name in ('finalist.fasta','selected.fasta')]]},'exposure_events':events,'rows':rows,'native_request_counts':requests,'equal_native_proposal_budget_measured':all(r['attempted_proposal_folds']==config['steps'] for r in rows),'limitations':['One exposed synthetic input/one search seed; no fresh test, generalization or biological stability claim.','Pair logits are proposal-ranking proxies, not folding energy; native tools decide acceptance/selection.','Neural arm adds128 potential proxy calls beyond matched native requests; wall/costs are not assumed equal.','Original-template compatibility is a control/prior, not proof of retained biological function.']};(run/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    report=['# Checkpoint proposal-prior pilot','',manifest['policy'],'',f'Run: `{run}`','','| Policy | Native proposals | Proxy calls | Accepted | Selected Vienna delta | Selected mutations |','|---|---:|---:|---:|---:|---:|']
    for r in rows:report.append(f'| {r["policy"]} | {r["attempted_proposal_folds"]} | {r["proxy_evaluations"]} | {r["accepted_steps"]} | {r["selected_vienna_delta_kcal_mol"]} | {r["selected_mutations"]} |')
    report+=['',*summary['limitations']];publish(ROOT,'checkpoint_prior_pilot',summary,rows,list(rows[0]),'\n'.join(report)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
