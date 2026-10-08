#!/usr/bin/env python3
"""Audit frozen RF00017 trial provenance, random initialization, checkpoint and native inference."""
import json
import math
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.context_pairs import band_supervision,make_context_model
from rnastable.context_training import predictions
from rnastable.exposures import exposure_records,read_exposure
from rnastable.family_plan import audit_family_plan
from rnastable.folding import parse_output,tool_commands
from rnastable.reference import digest
from rnastable.reference_audit import require,audit_reference
from rnastable.rfam_data import load_rfam_candidates,select_cohort,cohort_inputs
from rnastable.scoring import structure_agreement
from rnastable.structure_model import tokens


def audit_context_trial(path):
    import torch
    summary=json.loads(Path(path).read_text());run=Path(summary['run_dir'])
    require(summary['complete'] is True and summary['mode']=='family_disjoint_comparative_context_trial','trial identity differs')
    require(json.loads((run/'summary.json').read_text())==summary,'retained summary differs')
    require(digest((run/'manifest.json').read_bytes())==summary['manifest_sha256'],'manifest changed')
    manifest=json.loads((run/'manifest.json').read_text());config=manifest['config']
    require(manifest['run_dir']==str(run),'run identity differs')
    for name,sha in summary['artifact_sha256'].items():require(digest((run/name).read_bytes())==sha,'artifact changed: '+name)
    require(digest((run/'family_plan/summary.json').read_bytes())==manifest['family_plan_sha256'],'family plan changed')
    plan=audit_family_plan(run/'family_plan');require(plan['counts']==summary['counts'] and plan['families']==summary['families'],'family summary differs')
    require(digest((run/'import.json').read_bytes())==manifest['import_sha256'],'import changed')
    imported=json.loads((run/'import.json').read_text())
    for p,sha in imported['source_sha256'].items():require(digest(Path(p).read_bytes())==sha,'upstream source changed')
    old_path=run/'source_development_families.json';require(digest(old_path.read_bytes())==manifest['prior_development_source_sha256'],'source development families changed')
    old=json.loads(old_path.read_text());exposed=json.loads((run/'family_plan/effective_exposure.json').read_text())
    candidates,replay=load_rfam_candidates(ROOT/'external/EternaFold',manifest['import_config']);test,excluded=select_cohort(candidates,manifest['import_config'],exposed);replay['selection_exclusions']=excluded
    require(replay==imported,'import and sequence selection differ')
    data=cohort_inputs(old['splits']['train']+old['splits']['validation']+test,{'families':plan['families']})
    for name,expected in zip(('references.json','assignments.json','plan.json'),data):require(json.loads((run/'family_plan'/name).read_text())==expected,'trial cohort differs')
    selection_path=run/'development_selection.json';require(digest(selection_path.read_bytes())==manifest['selection_sha256'],'development selection changed')
    selection=json.loads(selection_path.read_text());selected=max(selection['rows'],key=lambda r:r['validation_mean_pair_f1'])
    require(selected['run_dir']==selection['selected_run_dir'],'development selection differs')
    selected_path=Path(manifest['selected_development_summary']);require(selected_path==Path(selected['run_dir'])/'summary.json' and digest(selected_path.read_bytes())==manifest['selected_development_summary_sha256']==selected['summary_sha256'],'selected source checkpoint/config binding differs')
    selected_training=json.loads(selected_path.read_text());require({**config,'mode':'development_validation_only'}==selected_training['config'],'configuration differs from development selection')
    events=summary['exposure_events'];require([e['stage'] for e in events]==['training_started','validation_started','test_started'],'exposure stage order differs')
    require([e['path'] for e in events]==sorted(e['path'] for e in events),'event timestamp order differs')
    require(set(Path(e['path']).resolve() for e in events)==set(p.resolve() for p in (run/'exposures').glob('*.json')),'event inventory differs')
    for event,split in zip(events,('train','validation','test')):
        p=Path(event['path']);require(p.resolve().parent==(run/'exposures').resolve() and digest(p.read_bytes())==event['sha256'],'exposure event changed')
        data=read_exposure(p);require(data['stage']==event['stage'] and data['records']==exposure_records(plan['splits'][split],str(run)+' '+event['stage']),'exposure records differ')
    training=summary['training'];require(training==json.loads((run/'model/training.json').read_text()),'training summary differs')
    labels=[band_supervision(r,config['max_pair_span']) for r in plan['splits']['train']];positive=sum(int(y.sum()) for _,y,_ in labels);negative=sum(len(y)-int(y.sum()) for _,y,_ in labels)
    require(positive==training['train_positive_pairs'] and negative==training['train_negative_pairs'] and (negative/positive)**config.get('positive_weight_exponent',.5)==training['train_only_positive_weight'],'training weights/counts differ')
    for split in ('train','validation'):
        require(sum(band_supervision(r,config['max_pair_span'])[2] for r in plan['splits'][split])==training['excluded_'+split+'_contacts'],'excluded development contacts differ')
    require(sum(band_supervision(r,config['max_pair_span'])[2] for r in test)==summary['test_excluded_reference_contacts'],'excluded test contacts differ')
    history=training['history'];require([json.loads(line) for line in (run/'model/epochs.jsonl').read_text().splitlines()]==history,'epoch ledger differs')
    require([r['epoch'] for r in history]==list(range(1,config['epochs']+1)),'epoch inventory differs')
    best=max(history,key=lambda r:(r['validation_mean_pair_f1'],-r['mean_validation_loss']));require(best['epoch']==training['selected_epoch'],'validation selection differs')
    torch.set_num_threads(config['cpu_threads']);pred=[]
    for filename,method in [('best_context_model.pt','trained_context'),('initial_context_model.pt','untrained_context')]:
        p=run/'model'/filename;require(digest(p.read_bytes())==training['checkpoint_sha256'][filename],'checkpoint changed')
        torch.manual_seed(config['seed']);model=make_context_model(config);state=torch.load(p,map_location='cpu',weights_only=True)
        if method=='untrained_context':require(all(torch.equal(value,state[key]) for key,value in model.state_dict().items()),'initial model was not fixed-seed random initialization')
        model.load_state_dict(state);pred+=predictions(model,test,method,config['max_pair_span'])
        require(sum(p.numel() for p in model.parameters())==training['parameters'] and 1+6*sum(config['dilations'])==training['encoder_receptive_field_nt'],'architecture differs')
        if method=='trained_context':
            val=predictions(model,plan['splits']['validation'],'validation',config['max_pair_span']);f1=sum(structure_agreement(p['structure'],r['structure'])['pair_f1'] for p,r in zip(val,plan['splits']['validation']))/len(val)
            require(f1==training['selected_validation_pair_f1']==best['validation_mean_pair_f1'],'selected validation score differs')
            loss_fn=torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(training['train_only_positive_weight']));losses=[]
            with torch.inference_mode():
                for r in plan['splits']['validation']:
                    edges,y,_=band_supervision(r,config['max_pair_span'])
                    if len(y):losses.append(loss_fn(model(tokens(r['sequence']),edges),y).item())
            require(sum(losses)/len(losses)==best['mean_validation_loss'],'validation loss differs')
    pred+=[{'id':r['id'],'sequence':r['sequence'],'method':'all_unpaired','status':'ok','structure':'.'*len(r['sequence'])} for r in test]
    folds=json.loads((run/'folds.json').read_text());commands=tool_commands(ROOT,manifest['folding'])
    require([(f['reference_id'],f['tool']) for f in folds]==[(r['id'],t) for r in test for t in ('ViennaRNA','LinearFold')],'native fold inventory differs')
    for record,pair in zip(test,[folds[i:i+2] for i in range(0,len(folds),2)]):
        for fold in pair:
            if fold['status']!='unavailable':require(fold['device']=='CPU' and fold['command']==commands[fold['tool']][0],'native command differs')
            if 'raw_output' in fold:
                raw=Path(fold['raw_output']);require(raw.resolve().parent==(run/'raw').resolve() and digest(raw.read_bytes())==fold['raw_sha256'],'raw fold changed')
            if fold['status']=='ok':
                require(raw.read_text().splitlines()[0].strip()==record['sequence'],'native sequence differs');parsed=parse_output(fold['tool'],raw.read_text(),len(record['sequence']));require(all(fold[k]==v for k,v in parsed.items()),'native structure/energy differs')
            row={'id':record['id'],'sequence':record['sequence'],'method':fold['tool'],'status':fold['status'] if fold['status'] in ('ok','timeout','unavailable') else 'error'}
            if row['status']=='ok':row['structure']=fold['structure']
            else:row['error']=fold.get('error') or fold['status']
            pred.append(row)
    require(json.loads((run/'test_predictions.json').read_text())=={'schema_version':1,'methods':manifest['methods'],'records':pred},'checkpoint/native predictions differ')
    require(json.loads((run/'test_references.json').read_text())['records']==test,'evaluation test split differs')
    evaluation_path=run/'results/reference_evaluation_summary.json';audit_reference(evaluation_path);evaluation=json.loads(evaluation_path.read_text())
    for key,name in [('references','test_references.json'),('predictions','test_predictions.json')]:require(Path(evaluation['sources'][key]['path']).read_bytes()==(run/name).read_bytes(),'evaluation sources differ')
    require(evaluation['aggregates']==summary['aggregates'],'test aggregates differ')
    print(f'Context family audit passed: {summary["counts"]}; fresh random initialization, exact checkpoints, source/family/exposure replay and {len(folds)} native folds verified.')
    return summary

if __name__=='__main__':audit_context_trial(ROOT/'results/context_family_trial_summary.json')
