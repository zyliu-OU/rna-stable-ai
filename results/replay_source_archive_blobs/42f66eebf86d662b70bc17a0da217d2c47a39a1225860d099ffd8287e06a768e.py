#!/usr/bin/env python3
"""Replay source-bound comparative expansion, full labels and development checkpoint inference."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.crw_development_data import load_crw_development,select_crw,overlaps
from rnastable.exposures import exposure_records,read_exposure
from rnastable.full_pair_supervision import full_supervision
from rnastable.global_sparse_pairs import make_global_model
from rnastable.reference import digest
from rnastable.reference_audit import require,audit_reference
from rnastable.scoring import structure_agreement
from rnastable.structure_model import tokens
from train_long_comparative_development import predictions


def audit_expanded(path):
    import torch
    summary=json.loads(Path(path).read_text());run=Path(summary['run_dir']);config=summary['config']
    require(summary['complete'] is True and summary['test_evaluated'] is False and summary['mode']=='long_comparative_development_only','not development-only')
    require(summary==json.loads((run/'summary.json').read_text()),'retained summary differs')
    require(digest((run/'manifest.json').read_bytes())==summary['manifest_sha256'],'manifest changed')
    manifest=json.loads((run/'manifest.json').read_text());require(manifest['config']==config and manifest['run_dir']==str(run),'manifest identity differs')
    for name,sha in manifest['snapshot_sha256'].items():require(digest((run/name).read_bytes())==sha,'snapshot changed: '+name)
    sources=list(manifest['original_development_sources']);require(len(sources)==3,'original source inventory differs')
    for p,sha in manifest['original_development_sources'].items():require(digest(Path(p).read_bytes())==sha,'original development source changed')
    family=json.loads(Path(sources[2]).read_text());old={'train':json.loads(Path(sources[0]).read_text())['records']+family['splits']['train'],'validation':json.loads(Path(sources[1]).read_text())['records']+family['splits']['validation']}
    exposed=json.loads((run/'exposure.json').read_text());candidates,imported=load_crw_development(ROOT/'external/EternaFold',manifest['data_config']);new,exclusions=select_crw(candidates,manifest['data_config'],exposed,old);imported['selection_exclusions']=exclusions
    require(imported==json.loads((run/'import.json').read_text()) and new==json.loads((run/'new_crw.json').read_text()),'CRW source import/filter replay differs')
    splits={name:json.loads((run/(name+'.json')).read_text())['records'] for name in ('train','validation')}
    require(all(splits[name]==old[name]+new[name] for name in splits),'expanded source selection differs')
    require(summary['counts']=={s:len(rs) for s,rs in splits.items()} and summary['new_crw_counts']=={s:len(rs) for s,rs in new.items()},'expanded counts differ')
    require(summary['length_ranges']=={s:[min(len(r['sequence']) for r in rs),max(len(r['sequence']) for r in rs)] for s,rs in new.items()},'length ranges differ')
    for first in splits['train']:
        for second in splits['validation']:require(not overlaps(first['sequence'],second['sequence']),'cross-split sequence overlap')
    events=summary['exposure_events'];require([e['stage'] for e in events]==['training_started','validation_started'],'unexpected exposure stage')
    require(set(Path(e['path']).resolve() for e in events)==set(p.resolve() for p in (run/'exposures').glob('*.json')),'exposure inventory differs')
    for event,name in zip(events,('train','validation')):
        p=Path(event['path']);require(p.resolve().parent==(run/'exposures').resolve() and digest(p.read_bytes())==event['sha256'],'exposure event changed')
        data=read_exposure(p);require(data['stage']==event['stage'] and data['records']==exposure_records(splits[name],str(run)+' '+event['stage']),'exposure records differ')
    labels=[full_supervision(r,config['training_max_length']) for r in splits['train']];positive=sum(int(y.sum()) for _,y,_ in labels);negative=sum(len(y)-int(y.sum()) for _,y,_ in labels)
    require(positive==summary['train_positive_pairs'] and negative==summary['train_negative_pairs'] and (negative/positive)**config['positive_weight_exponent']==summary['train_only_positive_weight'],'full pair counts/weight differ')
    require(sum(x[2] for x in labels)==summary['excluded_train_contacts'] and sum(full_supervision(r,config['training_max_length'])[2] for r in splits['validation'])==summary['excluded_validation_contacts'],'excluded contacts differ')
    history=summary['history'];require([json.loads(line) for line in (run/'epochs.jsonl').read_text().splitlines()]==history,'epoch ledger differs')
    require([r['epoch'] for r in history]==list(range(1,config['epochs']+1)),'epoch inventory differs')
    best=max(history,key=lambda r:(r['validation_mean_pair_f1'],-r['mean_validation_loss']));require(best['epoch']==summary['selected_epoch'],'checkpoint selection differs')
    torch.set_num_threads(config['cpu_threads']);pred=[]
    for filename,method in [('initial_context_model.pt','untrained_expanded_sparse'),('best_context_model.pt','trained_expanded_sparse')]:
        p=run/filename;require(digest(p.read_bytes())==summary['checkpoint_sha256'][filename],'checkpoint changed')
        torch.manual_seed(config['seed']);model=make_global_model(config);state=torch.load(p,map_location='cpu',weights_only=True)
        if method=='untrained_expanded_sparse':require(all(torch.equal(v,state[k]) for k,v in model.state_dict().items()),'random initialization differs')
        model.load_state_dict(state);rows=predictions(model,splits['validation'],method,config);pred+=rows
        require(sum(p.numel() for p in model.parameters())==summary['parameters'],'model size differs')
        if method=='trained_expanded_sparse':
            score=sum(structure_agreement(p['structure'],r['structure'])['pair_f1'] for p,r in zip(rows,splits['validation']))/len(rows);require(score==summary['selected_validation_pair_f1']==best['validation_mean_pair_f1'],'selected validation score differs')
            losses=[];loss_fn=torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(summary['train_only_positive_weight']))
            with torch.inference_mode():
                for r in splits['validation']:
                    edges,y,_=full_supervision(r,config['training_max_length'])
                    if len(y):losses.append(loss_fn(model(tokens(r['sequence']),edges),y).item())
            require(sum(losses)/len(losses)==best['mean_validation_loss'],'selected validation loss differs')
    require(digest((run/'predictions.json').read_bytes())==summary['predictions_sha256'] and json.loads((run/'predictions.json').read_text())['records']==pred,'checkpoint predictions differ')
    p=run/'results/reference_evaluation_summary.json';audit_reference(p);evaluation=json.loads(p.read_text())
    for key,name in [('references','validation.json'),('predictions','predictions.json')]:require(Path(evaluation['sources'][key]['path']).read_bytes()==(run/name).read_bytes(),'evaluation split differs')
    require(evaluation['aggregates']==summary['aggregates'],'metrics differ')
    print(f'Expanded comparative audit passed: {summary["counts"]}; {summary["new_crw_counts"]} new source-bound development records; selected epoch {summary["selected_epoch"]}; no test inference.')
    return summary

if __name__=='__main__':audit_expanded(ROOT/'results/long_comparative_development_summary.json')
